'use strict';
// ---- Shared state and small DOM/format helpers ----
const $ = id => document.getElementById(id);
const api = (path, params) => 'api/' + path + (params ? '?' + new URLSearchParams(params) : '');
const libMode = location.pathname.startsWith('/v/');
// The library entry (e.g. "test/smoke"), not a video id: the API under /v/<name>/ is already
// scoped to that repo, and its videos come from api/project.
const libName = libMode ? decodeURIComponent(location.pathname.split('/').slice(2, -1).join('/')) : null;
const state = {
  video: null,
  project: null,
  info: null,
  name: null,
  user: null,
  access: null,
  notes: [],
  versions: [],
  format: null,
  commit: null,
  deliberate: false,
  view: 'chat',
  stamp: true,
  files: [],
  pending: [],
  sending: false,
  versionCursor: null,
  loadingVersions: false,
  renderTimer: null,
  resumeOnVisible: false,
  signedOut: false,
  restarting: false,
  musicSources: [],
  musicSourceId: null,
  musicSource: null,
  musicTracks: [],
  musicPlayingId: null,
  pictures: null,
  pictureCount: 2,
  pictureGpu: 'unknown',
  pictureGpuAt: 0,
  pictureMaking: false,
  pictureOriginals: new Set(),
  picturesAbsent: false,
  pose: null,
  pictureActions: null,
  steps: {},
  pendingAnswers: {},
  sources: [],
  sourcePending: null,
  sourcePlayer: null
};
const player = $('player');
const timeLabel = s => {
  s = Math.max(0, Math.floor(s || 0));
  return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`
};
const relative = value => {
  const ms = Date.now() - new Date(value).getTime();
  if (!Number.isFinite(ms)) return 'now';
  const m = Math.max(0,Math.floor(ms/60000));
  if (m < 1) return 'now';
  if (m < 60) return `${m} min ago`;
  if (m < 1440) return `${Math.floor(m / 60)} h ago`;
  return `${Math.floor(m / 1440)} d ago`;
};
const node = (tag, className, text) => {
  const n=document.createElement(tag);
  if(className)n.className=className;
  if(text!=null)n.textContent=text;
  return n
};
// Replies stored before the runner stripped its "== result: ... ==" banner.
const replyText = reply => reply && reply.replace(/^== result:[^\n]*==\n+/, '');
// cost_usd/tokens are stripped entirely for a non-admin (see video_api.py), so the
// field's mere presence on a note, even when null (not yet known), means an admin is viewing.
const costLabel = cost => cost==null ? 'cost unknown' : `≈ $${cost.toFixed(2)}`;
// ---- Networking: fetch/json, errors and toasts ----
async function json(path, params, body) {
  const r=await reach(api(path,params),body===undefined? {
  }
  : {
    method:'POST',headers: {
      'Content-Type':'application/json'
    },body:JSON.stringify(body)
  });
  const data=await parseJSON(r);
  if(!r.ok)throw httpError(r,data);
  if(state.signedOut)clearSignedOut();
  return data
}
// A proxy answers with HTML while the editor restarts; say so instead of a parse error.
async function parseJSON(r) {
  const text=await r.text();
  try {
    return JSON.parse(text)
  } catch (_) {
    if(GATEWAY.includes(r.status))throw restarting();
    throw Error(`The editor didn't answer (HTTP ${r.status}); it may be restarting. Try again in a moment.`)
  }
}
// ---- Editor restarts ----
// A deploy stops the editor for a while: requests fail with no answer, the proxy's non-JSON
// 502-504, or the editor's own drain 503 (editor.py UPDATING). A banner says so, polling
// pauses, and /healthz is retried until it is back; nothing typed or picked is touched.
// Other JSON 502s are the editor's real errors (an upstream music fetch) and are shown.
const GATEWAY=[502,503,504];
const draining=(status,data)=>status===503&&String(data?.error||'').startsWith('The editor is updating');
const RESTART_MESSAGE='The editor is updating. Nothing you wrote is lost; send it again once it is back.';
async function reach(url, init) {
  try {
    return await fetch(url,init)
  } catch (_) {
    throw restarting()
  }
}
function restarting() {
  if(!state.restarting) {
    state.restarting=true;
    $('restart-banner').hidden=false;
    setTimeout(waitForEditor,2000)
  }
  return Error(RESTART_MESSAGE)
}
async function waitForEditor() {
  try {
    const r=await fetch('/healthz', {cache: 'no-store'});
    if(r.ok&&(await r.text()).startsWith('ok ')) {
      editorBack();
      return
    }
  } catch (_) {
    // Still down.
  }
  setTimeout(waitForEditor,document.hidden ? 10000 : 3000)
}
function editorBack() {
  state.restarting=false;
  $('restart-banner').hidden=true;
  for(const id of ['composer-error','source-error']) {
    if($(id).textContent===RESTART_MESSAGE)$(id).textContent='The editor is back. Send it again when you’re ready.'
  }
  lastNotesPoll=Date.now();
  loadNotes();
  loadVersions();
  checkEditorVersion();
  if(state.view==='sources')loadSources();
  // A render the old editor was making, or one whose poll failed, is asked for again.
  if(!state.videoReady)loadPlayer()
}
// A session can expire while the tab sits open: the note being typed, queued or sent
// must survive that, so a 401 shows a banner (never a redirect, which would drop it)
// and the usual polling stops until a request succeeds again.
const SIGNED_OUT_MESSAGE="You’ve been signed out. Sign in again to keep going; your note is kept.";
function handleSignedOut() {
  if(state.signedOut)return;
  state.signedOut=true;
  $('signed-out-banner').hidden=false
}
function clearSignedOut() {
  state.signedOut=false;
  $('signed-out-banner').hidden=true
}
function httpError(r, data) {
  if(r.status===401) {
    handleSignedOut();
    return Error(SIGNED_OUT_MESSAGE)
  }
  if(draining(r.status,data))return restarting();
  const error=Error(data.log||data.error||r.statusText);
  error.status=r.status;
  return error
}
// Called when the tab regains focus: the sign-in link opens in a new tab, so this
// one's draft was never touched; once a session exists again, polling resumes.
async function resumeFromSignedOut() {
  if(!state.signedOut)return;
  try {
    await json('project')
  }
  catch(_) {
    return
  }
  lastNotesPoll=Date.now();
  loadNotes();
  loadVersions();
  checkEditorVersion()
}
function showError(error) {
  $('composer-error').textContent=error;
  $('composer-error').hidden=!error
}
let toastTimer;
function toast(message, watch) {
  const t=$('toast');
  t.textContent=message;
  if(watch) {
    const b=node('button',null,'Watch');
    b.onclick=()=> {
      playVersion(watch,false);
      t.hidden=true
    };
    t.append(b)
  }
  t.hidden=false;
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>t.hidden=true,6000)
}
async function ensureName() {
  if(state.name)return true;
  const value=prompt('What should we call you?');
  if(value===null)return false;
  try {
    state.name=(await jsonName(value)).name;
    updateName();
    return true
  }
  catch(e) {
    showError(e.message);
    return false
  }
}
// ---- Version, format and URL helpers ----
function versionBy(commit) {
  return state.versions.find(v=>v.commit===commit)
}
function currentVersion() {
  return versionBy(state.commit)||state.versions[0]
}
// Not built yet: the blank start, and any Film details saved before the first build (versions.py).
const notBuilt=v=>v?.kind==='blank'||!!v?.unbuilt;
function formatInfo() {
  return state.info?.formats?.find(f=>f.name===state.format)
}
function videoUrl(commit=state.commit) {
  const params={video: state.video, format: state.format};
  if (commit) params.commit=commit;
  return api('video', params);
}
function frameUrl() {
  return api('frame', {
    video: state.video, format: state.format, frame: 0, scale: 0.5
  })
}
function updateLabels() {
  const v=currentVersion();
  if(!v)return;
  const label=notBuilt(v)?'Not built yet':`v${v.n} · ${relative(v.time)}`;
  $('version-label').textContent=label;
  $('rail-version').textContent=`v${v.n}`;
  $('caption-by').textContent=`Builder · v${v.n}`;
  $('caption-text').textContent=v.summary||'';
  $('sheet-subtitle').textContent=`Playing v${v.n} · ${timeLabel(player.currentTime)}`;
  const url=videoUrl();
  const multi=(state.project?.videos?.length||0)>1;
  const base=libName?(multi?`${libName}-${state.video}`:libName):state.video;
  for(const id of ['rail-save','desktop-save']) {
    if(state.videoReady)$(id).href=url;
    $(id).download=`${base.replaceAll('/','-')}-v${v.n}-${state.format}.mp4`
  }
  renderVersions()
}
function renderFormats() {
  const formats=state.info?.formats||[];
  const f=formatInfo();
  if(f) {
    $('player-box').style.aspectRatio=`${f.width} / ${f.height}`;
    resizePlayer();
  }
  $('phone-format').textContent=(state.format||'').replace('x',':');
  const wrap=$('desktop-formats');
  wrap.replaceChildren();
  for(const item of formats) {
    const b=node('button','format-chip'+(item.name===state.format?' active':''),item.name.replace('x',':'));
    b.onclick=()=>setFormat(item.name);
    wrap.append(b)
  }
}
// ---- Player: sizing, transport, scrubbing and sheet/view switching ----
function resizePlayer() {
  const f=formatInfo();
  if (!f) return;
  // Fill the watch column, leaving the controls and the collapsed tuning
  // bar in view (16px is .watch's gap). Phone CSS ignores --player-width.
  const watch=document.querySelector('.watch');
  const below=document.querySelector('.watch-controls').offsetHeight
    + $('desktop-tune-toggle').offsetHeight + 2 + 2 * 16;
  const availableHeight=Math.max(200, watch.clientHeight - below);
  const width=Math.min(watch.clientWidth, availableHeight * f.width / f.height);
  $('player-box').style.setProperty('--player-width', `${Math.floor(width)}px`);
}
async function setFormat(format) {
  if(format===state.format)return;
  state.format=format;
  try {
    localStorage.setItem(`director-format:${state.video}`, format);
  } catch (_) {
    // Private browsing can deny storage.
  }
  renderFormats();
  loadTimeline();
  await loadPlayer()
}
async function loadPlayer(retry=false) {
  if(!state.video||!state.format)return;
  clearTimeout(state.renderTimer);
  // visibilitychange treats a non-null timer as "render still pending".
  state.renderTimer=null;
  state.videoReady=false;
  setPlayState('busy');
  player.pause();
  player.removeAttribute('src');
  player.load();
  const url=playUrl();
  const poster=tlNoteClip()?tlPoster():frameUrl();
  player.poster=poster;
  $('poster').src=poster;
  const v=currentVersion();
  $('building').hidden=true;
  $('blank-details').hidden=true;
  $('render-status').classList.remove('calm');
  if(notBuilt(v)) {
    showBlank();
    return
  }
  if(retry) {
    try {
      await json('video/retry',null, {
        video:state.video,commit:state.commit,format:state.format,...(tlNoteClip()?{clip:tlNoteClip()}:{})
      })
    }
    catch(e) {
      $('render-text').textContent=e.message;
      setPlayState('play');
      return
    }
  }
  $('render-status').hidden=false;
  for(const id of ['rail-save','desktop-save'])$(id).removeAttribute('href');
  const what=tlNoteClip()?`clip ${state.tl.data.clips.findIndex(c=>c.id===tlNoteClip())+1}`:`v${v?.n||'…'}`;
  $('render-text').textContent=`Rendering ${what}…`;
  $('retry-render').hidden=true;
  try {
    const r=await reach(url.split('#')[0], {headers: {Range: 'bytes=0-0', Accept: 'application/json'}});
    if(url!==playUrl())return;
    if(r.status===202) {
      const body=await parseJSON(r);
      const position=body.position ? ` · queue position ${body.position}` : '';
      $('render-text').textContent=`Rendering ${what}…${position}`;
      $('poster').hidden=false;
      state.renderTimer=setTimeout(()=>loadPlayer(),document.hidden ? 15000 : 2000);
      return
    }
    if(!r.ok) {
      const body=await parseJSON(r);
      throw httpError(r,body)
    }
    if (r.status !== 206) throw Error(`Unexpected video response: ${r.status}`);
    await r.body?.cancel();
    state.videoReady=true;
    setPlayState('play');
    for(const id of ['rail-save','desktop-save'])$(id).href=videoUrl();
    $('poster').hidden=true;
    $('render-status').hidden=true;
    player.src=url;
    player.load();
    if (!document.hidden) player.play().catch(()=>{});
    updateLabels()
  }
  catch(e) {
    $('poster').hidden=false;
    // editorBack polls again; until then the render reads as still on its way.
    if(state.restarting)return;
    $('render-text').textContent=e.message;
    $('retry-render').hidden=false;
    setPlayState('play')
  }
}
// A new video's first commit is an empty frame for the builder to start
// from, not a version anyone made: never render or play it.
function showBlank() {
  const building=state.notes.some(n=>['gathering','queued','working'].includes(n.state));
  $('building').hidden=!building;
  const working=state.notes.find(n=>n.state==='working');
  $('build-steps').hidden=!working;
  if(working) {
    renderProgress(working,$('build-steps'));
    if(working.handle)loadSteps(working)
  }
  $('render-status').classList.toggle('calm',building);
  $('poster').hidden=true;
  $('retry-render').hidden=true;
  $('render-status').hidden=false;
  $('render-text').textContent=building
    ? 'The builder is making your first version. It plays here when it\'s ready.'
    : 'Nothing built yet. Say what you want below and the builder makes the first version.';
  $('blank-details').hidden=building
}
function playVersion(v,deliberate) {
  state.commit=v.commit;
  state.deliberate=deliberate;
  updateLabels();
  loadPlayer()
}
function updateTime() {
  const duration=Number.isFinite(player.duration)?player.duration:(state.info?state.info.frames/state.info.fps:0);
  $('time-display').textContent=`${timeLabel(player.currentTime)} / ${timeLabel(duration)}`;
  $('sheet-subtitle').textContent=`Playing v${currentVersion()?.n||'…'} · ${timeLabel(player.currentTime)}`;
  const percent=duration ? Math.min(100, 100*player.currentTime/duration) : 0;
  $('progress-fill').style.width=`${percent}%`;
  $('progress').setAttribute('aria-valuenow', Math.round(percent));
  if(state.stamp)stampLabel();
  tlPlayhead()
}
function stampLabel() {
  const b=$('timestamp');
  b.replaceChildren();
  if (state.stamp) b.append(icon('clock'), `at ${timeLabel(player.currentTime)}`, icon('close'));
  else b.append(`+ Attach the time (${timeLabel(player.currentTime)})`);
  b.classList.toggle('off',!state.stamp);
  b.setAttribute('aria-label', state.stamp
    ? 'Remove the timestamp from this message'
    : 'Attach the playhead time to this message');
}
function icon(name) {
  return document.querySelector(`#icon-${name}`).content.firstElementChild.cloneNode(true);
}
function togglePlay() {
  if(!state.videoReady)return;
  if(player.paused)player.play().catch(()=> {
  });
  else player.pause()
}
// 'busy' while there is no video to play yet (a render is pending), then 'play'/'pause'.
function setPlayState(mode) {
  const busy=mode==='busy',label=busy?'Rendering…':mode==='pause'?'Pause video':'Play video';
  $('play-glyph').hidden=busy||mode==='pause';
  $('desktop-play').replaceChildren(busy?node('span','spinner'):icon(mode));
  $('desktop-play').disabled=$('fullscreen').disabled=$('rail-fullscreen').disabled=!state.videoReady;
  $('desktop-play').setAttribute('aria-label',label);
  $('tap-player').setAttribute('aria-label',label)
}
function setView(view) {
  state.view=view;
  for(const name of ['chat','versions','tune','sources','share'])$(name+'-view').hidden=name!==view;
  $('sheet-title').textContent= {
    chat:'Builder chat',versions:'Versions',tune:'Fine tuning',sources:'Sources',share:'Share'
  }
  [view];
  $('tab-chat').classList.toggle('active',view==='chat');
  $('tab-versions').classList.toggle('active',view==='versions');
  $('tab-sources').classList.toggle('active',view==='sources');
  $('tab-share').classList.toggle('active',view==='share');
  $('panel').dataset.view=view;
  if(view==='tune')openTuning('phone-tune-body');
  if(view==='versions')loadVersions();
  if(view==='sources')loadSources();
  if(view==='share')loadAccess()
}
function openSheet(view) {
  setView(view);
  $('panel').classList.add('open');
  $('shade').hidden=false;
  // No auto-focus: on a phone it raises the keyboard over the chat before the
  // director has read it.
  if(view==='chat')renderNotes()
}
// Lift the sheet above the on-screen keyboard (see --kb in director.css).
function trackKeyboard() {
  const vv=window.visualViewport;
  const kb=vv ? Math.max(0, window.innerHeight-vv.height-vv.offsetTop) : 0;
  document.documentElement.style.setProperty('--kb', `${Math.round(kb)}px`);
  $('app').scrollTop=0
}
window.visualViewport?.addEventListener('resize', trackKeyboard);
window.visualViewport?.addEventListener('scroll', trackKeyboard);
function videoDuration() {
  return Number.isFinite(player.duration) ? player.duration : 0
}
function seekTo(fraction) {
  const duration=videoDuration();
  if(!duration)return;
  player.currentTime=Math.min(1, Math.max(0, fraction))*duration;
  updateTime()
}
function scrubAt(e) {
  const r=$('progress').getBoundingClientRect();
  seekTo((e.clientX-r.left)/r.width)
}
function setFullSheet(full) {
  $('panel').classList.toggle('full', full);
  $('sheet-full').replaceChildren(icon(full ? 'collapse' : 'expand'));
  $('sheet-full').setAttribute('aria-pressed', full);
  $('sheet-full').setAttribute('aria-label', full ? 'Exit full screen' : 'Full screen')
}
function closeSheet() {
  setFullSheet(false);
  $('panel').classList.remove('open');
  $('shade').hidden=true;
  document.activeElement?.blur();
  // iOS can still scroll #app when its keyboard opens.
  $('app').scrollTop=0
}
// ---- Notes: chat feed, builder step feed, and question cards ----
function attachmentUrl(id) {
  return api('attachments/'+encodeURIComponent(id))
}
// The note's "Show builder log" feed: a redacted-free, formatted read of its builder
// transcript (see transcript.py), polled every 3s while expanded and not yet
// in a final state. state.steps[note.id].el is the live body element, kept so
// a poll can refresh just that feed without the full note-list re-render.
function renderStepsFeed(note) {
  const data=state.steps[note.id];
  if(!data||!data.el)return;
  const body=data.el,atBottom=body.scrollHeight-body.scrollTop-body.clientHeight<40;
  body.replaceChildren();
  if(!data.entries.length) {
    body.append(node('p','steps-empty','No steps recorded'));
    return
  }
  const open=data.openSteps||(data.openSteps=new Set());
  let current=null;
  data.entries.forEach((entry,i)=> {
    if(entry.kind==='leg') {
      body.append(node('div','steps-leg',entry.text));
      current=null;
      return
    }
    if(entry.kind==='step') {
      const row=node('div','steps-step'),head=node('button','steps-step-head',entry.text);
      const details=node('div','steps-step-details');
      details.hidden=!open.has(i);
      head.setAttribute('aria-expanded',String(!details.hidden));
      head.onclick=()=> {
        details.hidden=!details.hidden;
        head.setAttribute('aria-expanded',String(!details.hidden));
        if(details.hidden)open.delete(i);else open.add(i)
      };
      row.append(head,details);
      body.append(row);
      current=details;
      return
    }
    (current||body).append(node('div','steps-'+entry.kind,entry.text))
  });
  if(atBottom)body.scrollTop=body.scrollHeight
}
async function loadSteps(note) {
  const data=state.steps[note.id];
  if(!data||data.loading)return;
  data.loading=true;
  try {
    const result=await json(`notes/${encodeURIComponent(note.id)}/log`,
      data.source?{after:data.next,source:data.source}:{after:data.next});
    if(result.reset) {
      data.entries=[];
      data.openSteps=null
    }
    data.entries.push(...result.entries);
    data.next=result.next;
    data.source=result.source;
    data.done=result.done
  }
  catch(e) {
    // keep what we have; the next poll tries again
  }
  finally {
    data.loading=false;
    if(data.open)renderStepsFeed(note);
    refreshProgress(note)
  }
}
function stepsData(note) {
  return state.steps[note.id]||(state.steps[note.id]= {
    open:false,entries:[],next:0,done:false,loading:false
  });
}
// A working note's progress as a checklist that grows as the builder's
// "Step:" lines land: earlier steps ticked, the newest one in progress.
const SHOWN_STEPS=5;
function renderProgress(note,el) {
  const steps=stepsData(note).entries.filter(e=>e.kind==='step');
  el.replaceChildren();
  const items=steps.length?steps.map(s=>s.text):['Getting started'];
  const hidden=Math.max(0,items.length-SHOWN_STEPS);
  if(hidden)el.append(node('li','build-step earlier',`${hidden} earlier step${hidden===1?'':'s'} done`));
  items.slice(hidden).forEach((text,i,shown)=> {
    const current=i===shown.length-1;
    const li=node('li','build-step '+(current?'current':'done'));
    li.append(node('span','build-step-mark'),node('span','build-step-text',text));
    if(current)li.setAttribute('aria-current','step');
    el.append(li)
  })
}
function refreshProgress(note) {
  const data=stepsData(note);
  if(data.progressEl?.isConnected)renderProgress(note,data.progressEl);
  if(notBuilt(currentVersion())&&!$('building').hidden)renderProgress(note,$('build-steps'));
  updateBuildPill()
}
// While a later version builds, the player keeps playing the current one; a pill over
// it shows the newest step. A blank video's first build has the full checklist instead.
function updateBuildPill() {
  const note=notBuilt(currentVersion()) ? null :
    state.notes.find(n=>['gathering','queued','working'].includes(n.state));
  $('build-pill').hidden=!note;
  if(!note)return;
  const steps=stepsData(note).entries.filter(e=>e.kind==='step');
  $('build-pill-text').textContent=note.state==='gathering' ? 'Gathering pages…' :
    note.state==='queued' ? 'Waiting for the note before this one' :
    steps.length ? steps[steps.length-1].text : 'Getting started';
  const label=`The builder is working: ${$('build-pill-text').textContent}. Open the chat`;
  $('build-pill').setAttribute('aria-label',label)
}
$('build-pill').onclick=()=> {
  if(window.innerWidth<=700)openSheet('chat');
  else setView('chat')
};
function renderStepsToggle(note) {
  const data=stepsData(note);
  const wrap=node('div','steps-wrap');
  const toggle=node('button','steps-toggle',data.open?'Hide builder log':'Show builder log');
  toggle.setAttribute('aria-expanded',String(data.open));
  const body=node('div','steps-body');
  body.hidden=!data.open;
  data.el=body;
  toggle.onclick=()=> {
    data.open=!data.open;
    toggle.textContent=data.open?'Hide builder log':'Show builder log';
    toggle.setAttribute('aria-expanded',String(data.open));
    body.hidden=!data.open;
    if(data.open) {
      renderStepsFeed(note);
      if(!data.done)loadSteps(note)
    }
  };
  if(data.open)renderStepsFeed(note);
  wrap.append(toggle,body);
  return wrap
}
function questionAnswered(note) {
  if(!note.answered)return null;
  if(note.answered_build)return [];
  return note.questions.map((q,i)=>[q.text,(note.answered_answers||[])[i]])
}
function renderQuestionsCard(note) {
  const wrap=node('div','questions-wrap'),card=node('div','questions-card'),answered=questionAnswered(note);
  if(answered) {
    card.append(node('strong','questions-done',answered.length?'Answered':'Asked to use best judgement'));
    for(const [q,a] of answered) {
      const row=node('div','questions-summary-row');
      row.append(node('span','questions-summary-q',q),node('span','questions-summary-a',a));
      card.append(row)
    }
    wrap.append(card);
    return wrap
  }
  if(note.state!=='questions') {
    card.append(node('strong','questions-done','Asked, but built it anyway'));
    for(const q of note.questions) {
      const row=node('div','questions-summary-row');
      row.append(node('span','questions-summary-q',q.text));
      card.append(row)
    }
    wrap.append(card);
    return wrap
  }
  const answers=state.pendingAnswers[note.id]||(state.pendingAnswers[note.id]=note.questions.map(()=>''));
  let send;
  const refresh=()=>send.disabled=answers.some(a=>!a.trim());
  note.questions.forEach((q,i)=> {
    const block=node('div','question');
    block.append(node('div','question-text',q.text));
    if(q.choices&&q.choices.length) {
      const row=node('div','choice-row'),other=node('input','question-input other-input');
      other.type='text';
      other.placeholder='Type your answer';
      const matched=q.choices.includes(answers[i]);
      const isOther=!!answers[i]&&!matched;
      other.hidden=!isOther;
      if(isOther)other.value=answers[i];
      for(const choice of q.choices) {
        const chip=node('button','choice-chip'+(choice===answers[i]?' active':''),choice);
        chip.type='button';
        chip.onclick=()=> {
          answers[i]=choice;
          row.querySelectorAll('.choice-chip').forEach(c=>c.classList.remove('active'));
          chip.classList.add('active');
          other.hidden=true;
          refresh()
        };
        row.append(chip)
      }
      const otherChip=node('button','choice-chip other'+(isOther?' active':''),'Other…');
      otherChip.type='button';
      otherChip.onclick=()=> {
        row.querySelectorAll('.choice-chip').forEach(c=>c.classList.remove('active'));
        otherChip.classList.add('active');
        other.hidden=false;
        other.focus();
        answers[i]=other.value.trim();
        refresh()
      };
      other.oninput=()=> {
        answers[i]=other.value.trim();
        refresh()
      };
      row.append(otherChip);
      block.append(row,other)
    }
    else {
      const input=node('input','question-input');
      input.type='text';
      input.placeholder='Your answer';
      input.value=answers[i]||'';
      input.oninput=()=> {
        answers[i]=input.value.trim();
        refresh()
      };
      block.append(input)
    }
    card.append(block)
  });
  const actions=node('div','questions-actions');
  send=node('button','questions-send','Send answers');
  send.disabled=answers.some(a=>!a.trim());
  send.onclick=()=>sendAnswers(note,send,answers);
  const buildBtn=node('button','questions-build','Just build it');
  buildBtn.onclick=()=>sendAnswers(note,buildBtn,null);
  actions.append(send,buildBtn);
  card.append(actions);
  wrap.append(card);
  return wrap
}
async function sendAnswers(note, button, answers) {
  button.disabled=true;
  try {
    await json(`notes/${encodeURIComponent(note.id)}/answer`,null,answers?{answers}:{build:true});
    delete state.pendingAnswers[note.id];
    await loadNotes()
  }
  catch(e) {
    button.disabled=false;
    showError(e.message)
  }
}
// A replied note's message ("it's fixing it") only holds while its automatic fix note is on the way.
function fixingMessage(note, notes) {
  const fixing=notes.some(n=>n.retry_for===note.id&&['gathering','queued','working'].includes(n.state));
  return note.state==='replied'&&note.message&&fixing ? note.message : null
}
function renderNotes() {
  const list=$('note-list'),atBottom=list.scrollHeight-list.scrollTop-list.clientHeight<80;
  fdShowLink();
  list.replaceChildren();
  for(const note of notesInView()) {
    const mine=note.author===state.name;
    const row=node('div','bubble-row'+(mine?' mine':''));
    const bubble=node('div','bubble');
    bubble.append(node('span','who',mine?'You':note.author||'Director'));
    if(note.time!=null) {
        const stamp=node('button','stamp');
        stamp.append(icon('clock'), timeLabel(note.time));
        stamp.setAttribute('aria-label', `Jump to ${timeLabel(note.time)}`);
      stamp.onclick=()=> {
        player.currentTime=note.time;
        closeSheet()
      };
      bubble.append(stamp)
    }
    bubble.append(node('span','msg-text',note.said||note.text));
    for(const attachment of note.attachments||[]) {
      if(attachment.type?.startsWith('image/')) {
        const img=node('img');
        img.src=attachmentUrl(attachment.id);
        img.alt=attachment.name;
        bubble.append(img)
      }
      else {
        const a=node('a','file-chip',attachment.name);
        a.href=attachmentUrl(attachment.id);
        a.target='_blank';
        a.rel='noopener';
        bubble.append(a)
      }
    }
    row.append(bubble);
    list.append(row);
    if(note.handle)list.append(renderStepsToggle(note));
    if(note.reply||note.shortfalls?.length) {
      const reply=node('div','bubble-row builder');
      const box=node('div','bubble');
      box.append(node('span','who','Builder'));
      if(note.reply)box.append(node('span','msg-text',replyText(note.reply)));
      for(const s of note.shortfalls||[]) {
        const label=s.kind==='cannot'?'Couldn\'t do: ':'Rough edges: ';
        box.append(node('span','shortfall-line',label+s.what))
      }
      if('cost_usd' in note)box.append(node('span','note-cost',costLabel(note.cost_usd)));
      reply.append(box);
      list.append(reply)
    }
    if(note.questions)list.append(renderQuestionsCard(note));
    const fixing=fixingMessage(note,state.notes);
    if(fixing) {
      const row=node('div','bubble-row builder'),box=node('div','bubble');
      box.append(node('span','who','Builder'),node('span','state-message',fixing));
      row.append(box);
      list.append(row)
    }
    if(['gathering','queued','working'].includes(note.state)) {
      const working=node('div','bubble-row builder'),box=node('div','bubble');
      box.append(node('span','who','Builder'));
      const dots=node('span','dots');
      for(let i=0;i<3;i++)dots.append(node('i','dot'));
      const message=note.state==='gathering' ? 'Gathering pages…' : note.state==='queued' ?
        'Queued. The builder takes notes one at a time and starts this one when the note before it lands.' :
        'Working on it. You can keep watching or add more notes.';
      if(note.state==='gathering')box.append(dots);
      box.append(node('span','state-message',message));
      if(note.state==='working') {
        const progress=node('ol','build-steps');
        stepsData(note).progressEl=progress;
        renderProgress(note,progress);
        box.append(progress);
        if(note.handle)loadSteps(note)
      }
      working.append(box);
      list.append(working)
    }
    if(note.state==='refused'||note.state==='conflict'||note.state==='failed') {
      const problem=node('div','bubble-row builder'),box=node('div','bubble');
      const title = note.state === 'refused' ? 'Change not kept' :
        note.state === 'conflict' ? 'Conflict' : 'Builder error';
      const detail = note.state === 'refused'
        ? "The builder changed files it isn't allowed to change, so none of its change was kept: " +
          (note.refused || []).join(', ')
        : note.message || replyText(note.reply) || 'Please try again.';
      box.append(node('span','who',title),node('span','problem',detail));
      if((note.state==='conflict'||note.state==='failed')&&!note.automatic) {
        if(note.retried)box.append(node('span','state-message','Retried on the latest version below.'));
        else {
          const retry=node('button','retry','Retry on latest');
          retry.onclick=()=>retryNote(note,retry);
          box.append(retry)
        }
      }
      problem.append(box);
      list.append(problem)
    }
    if(note.version) {
      const v=versionBy(note.version.commit),ready=node('div','ready-row');
      ready.append(node('strong',null,`v${note.version.n} is ready${v?.summary?' · '+v.summary:''}`));
      const watch=node('button',null,state.commit===note.version.commit?'Playing':'Watch');
      watch.disabled=state.commit===note.version.commit;
      watch.onclick=()=>playVersion( {
        commit:note.version.commit
      },true);
      ready.append(watch);
      list.append(ready)
    }
  }
  $('chat-count').textContent=state.notes.length;
  renderVideoCost();
  if(atBottom)list.scrollTop=list.scrollHeight
}
// An admin-only running total for the open video: visible only when at least one
// note carries cost_usd at all, since that field is stripped entirely otherwise.
function renderVideoCost() {
  const costed=state.notes.filter(n=>'cost_usd' in n);
  const el=$('video-cost');
  if(!costed.length) {
    el.hidden=true;
    return
  }
  const known=costed.filter(n=>n.cost_usd!=null);
  const total=known.reduce((sum,n)=>sum+n.cost_usd,0);
  const unknown=costed.length-known.length;
  el.textContent=`≈ $${total.toFixed(2)}`+(unknown?` (+${unknown} unknown)`:'');
  el.hidden=false
}
async function retryNote(note, button) {
  button.disabled=true;
  try {
    await json(`notes/${encodeURIComponent(note.id)}/retry`,null, {});
    await loadNotes()
  }
  catch(e) {
    button.disabled=false;
    showError(e.message)
  }
}
async function loadNotes() {
  if(!state.video)return;
  try {
    const data=await json('notes', {
      video:state.video
    });
    const prev=JSON.stringify(state.notes.map(n=>[n.id,n.state,n.version?.commit]));
    state.notes=data.notes;
    const next=JSON.stringify(state.notes.map(n=>[n.id,n.state,n.version?.commit]));
    if(prev!==next) {
      renderNotes();
      if(notBuilt(currentVersion()))showBlank();
      if(state.notes.some(n=>n.version))loadVersions()
    }
    updateBuildPill();
    // Clear only the poll's own error, never one from a send the director made.
    if(state.pollError&&$('composer-error').textContent===state.pollError)showError('');
    state.pollError=null
  }
  catch(e) {
    if(state.restarting)return;
    state.pollError=e.message;
    showError(e.message)
  }
}
// ---- Versions list and the upgrade chip ----
function versionMeta(v) {
  const who=v.directed_by||v.author||'Someone';
  switch(v.kind) {
    case 'builder':return `Builder, from ${who} · ${relative(v.time)}`;
    case 'edit':return `${who}, fine tuning · ${relative(v.time)}`;
    case 'blank':return `Empty start, nothing built · ${relative(v.time)}`;
    case 'upgrade':return `${who}, upgraded videobuilder · ${relative(v.time)}`;
    case 'restore': {
      const n = state.versions.find(x => x.commit === v.restores)?.n || '?';
      return `${who}, restored v${n} · ${relative(v.time)}`;
    }
    default:return `${v.author||who} · ${relative(v.time)}`
  }
}
function renderVersions() {
  const list=$('version-list');
  fdShowLink();
  list.replaceChildren();
  for(const v of state.versions) {
    const row=node('div','version-row'),main=node('div','version-main');
    main.append(node('strong',null,`v${v.n} · ${v.summary||'Version'}`),node('span',null,versionMeta(v)));
    main.onclick=()=>playVersion(v,true);
    main.style.cursor='pointer';
    row.append(main);
    if(v.commit===state.commit)row.append(node('span','playing-badge','Playing'));
    else {
      const watch=node('button',null,'Watch');
      watch.onclick=()=>playVersion(v,true);
      row.append(watch);
      const restore=node('button','restore','Restore');
      restore.onclick=()=>restoreVersion(v);
      row.append(restore)
    }
    list.append(row)
  }
}
async function loadVersions(more=false) {
  if(!state.video||state.loadingVersions)return;
  state.loadingVersions=true;
  try {
    const before=more?state.versionCursor:null;
    if(more&&!before)return;
    const data=await json('versions', {
      video:state.video,limit:50,...(before? {
        before
      }
      : {
      })
    });
    const old=state.versions[0];
    if(more)state.versions.push(...data.versions);
    else state.versions=data.versions;
    state.versionCursor=data.versions.length===50?data.versions.at(-1).commit:null;
    const latest=state.versions[0];
    if(latest&&old&&latest.commit!==old.commit) {
      if(state.deliberate) {
        toast(`v${latest.n} is ready`,latest)
      }
      else {
        state.commit=latest.commit;
        toast(`v${latest.n} is ready · now playing`);
        loadPlayer()
      }
    }
    if(!state.commit&&latest) {
      state.commit=latest.commit;
      loadPlayer()
    }
    updateLabels()
  }
  catch(e) {
    if(!state.restarting)showError(e.message)
  }
  finally {
    state.loadingVersions=false
  }
}
async function restoreVersion(v) {
  if(!await ensureName())return;
  try {
    const result=await json('versions/restore',null, {
      video:state.video,commit:v.commit
    });
    await loadVersions();
    if(result.changed) {
      state.deliberate=false;
      state.commit=result.commit;
      loadPlayer();
      toast(`v${result.n} restores v${v.n}`)
    }
  }
  catch(e) {
    toast(e.message)
  }
}
function renderUpgrade() {
  const button=$('upgrade');
  const upgrade=state.project?.videos?.find(v=>v.id===state.video)?.upgrade;
  button.hidden=!upgrade;
  if(!upgrade)return;
  button.replaceChildren(node('span',null,`This video uses videobuilder ${upgrade.from} · `),
                         node('strong',null,`Upgrade to ${upgrade.to}`))
}
async function upgradeVideo() {
  if(!await ensureName())return;
  const button=$('upgrade');
  button.disabled=true;
  try {
    const result=await json('upgrade',null, {
      video:state.video
    });
    state.project=await json('project');
    renderUpgrade();
    await loadVersions();
    state.deliberate=false;
    if(state.commit!==result.commit) {
      state.commit=result.commit;
      loadPlayer()
    }
    toast(`v${result.n} upgrades videobuilder to ${result.to}`)
  }
  catch(e) {
    toast(e.message);
    // A refusal can mean the pin changed under us; show what the project says now.
    json('project').then(project=> {
      state.project=project;
      renderUpgrade()
    }).catch(()=> {})
  }
  finally {
    button.disabled=false
  }
}
// ---- File attachments and the music picker ----
// A chip's thumbnail: a picked or dropped image's own object URL (made once, revoked once the
// file leaves the note), a picture's stored thumbnail, or an uploaded image's attachment.
const chipUrls=new Map();
const isImage=f=>/^image\/(png|jpeg|webp|gif)$/.test(f.type||'')||/\.(png|jpe?g|webp|gif)$/i.test(f.name||'');
function chipThumb(f) {
  if(!isImage(f))return null;
  if(f instanceof Blob) {
    if(!chipUrls.has(f))chipUrls.set(f,URL.createObjectURL(f));
    return chipUrls.get(f)
  }
  return f.thumb||(f.id?attachmentUrl(f.id):null)
}
function renderFiles() {
  const wrap=$('attachments');
  wrap.replaceChildren();
  state.files.forEach((f,i)=> {
    const thumb=chipThumb(f);
    const chip=node('span','file-chip');
    if(thumb) {
      chip.classList.add('with-thumb');
      const img=node('img','file-thumb');
      img.alt='';
      img.decoding='async';
      // An attachment past its expiry has nothing to show: back to the plain chip.
      img.onerror=()=> {
        img.remove();
        chip.classList.remove('with-thumb')
      };
      img.src=thumb;
      chip.append(img)
    }
    chip.append(node('span','file-name',f.name));
    chip.title=f.name;
    if(f instanceof Blob&&isFootage(f)&&canAddClip()) {
      // Footage of the film itself, not a reference for the builder: a clip on the timeline.
      const clip=node('button','file-clip','Add as a clip');
      clip.onclick=()=> {
        state.files.splice(state.files.indexOf(f),1);
        renderFiles();
        addAsClip(f,showError).then(()=>showError('')).catch(e=>showError(e.message))
      };
      chip.append(clip)
    }
    const remove=node('button');
    remove.append(icon('close'));
    remove.setAttribute('aria-label',`Remove ${f.name}`);
    remove.onclick=()=> {
      state.files.splice(i,1);
      renderFiles();
    };
    chip.append(remove);
    wrap.append(chip);
  });
  for(const [f,url] of chipUrls)if(!state.files.includes(f)) {
    URL.revokeObjectURL(url);
    chipUrls.delete(f)
  }
}
function addFiles(files) {
  for(const f of files)state.files.push(f);
  renderFiles()
}
async function loadMusicSources() {
  try {
    state.musicSources=await json('music/sources')
  }
  catch(e) {
    state.musicSources=[]
  }
  $('music-button').hidden=!state.musicSources.length
}
function openMusicPicker() {
  $('music-error').hidden=true;
  $('music-dialog').hidden=false;
  $('music-shade').hidden=false;
  if(!state.musicSourceId)state.musicSourceId=state.musicSources[0]?.id;
  renderMusicSourceSelect();
  loadMusicTracks(state.musicSourceId)
}
function closeMusicPicker() {
  $('music-dialog').hidden=true;
  $('music-shade').hidden=true;
  $('music-preview').pause()
}
function renderMusicSourceSelect() {
  const select=$('music-source');
  select.hidden=state.musicSources.length<2;
  select.replaceChildren();
  for(const s of state.musicSources) {
    const opt=node('option',null,s.name);
    opt.value=s.id;
    select.append(opt)
  }
  select.value=state.musicSourceId
}
async function loadMusicTracks(sourceId) {
  $('music-list').replaceChildren();
  $('music-license').textContent='Loading…';
  $('music-error').hidden=true;
  try {
    const data=await json('music/tracks', {
      source:sourceId
    });
    state.musicSourceId=sourceId;
    state.musicSource=data.source;
    state.musicTracks=data.tracks;
    $('music-license').textContent=data.source.name+' · '+data.source.license;
    renderMusicList()
  }
  catch(e) {
    $('music-license').textContent='';
    $('music-error').textContent=e.message;
    $('music-error').hidden=false
  }
}
function musicMatches(track,query) {
  const words=query.toLowerCase().split(/\s+/).filter(Boolean);
  const haystack=[track.title,...track.tags].join(' ').toLowerCase();
  return words.every(w=>haystack.includes(w))
}
function renderMusicList() {
  const query=$('music-search').value.trim();
  const list=$('music-list');
  list.replaceChildren();
  const tracks=state.musicTracks.filter(t=>!query||musicMatches(t,query));
  const audio=$('music-preview');
  for(const track of tracks) {
    const row=node('div','music-row'),play=node('button','music-play');
    const playing=state.musicPlayingId===track.id&&!audio.paused;
    play.append(icon(playing?'pause':'play'));
    play.setAttribute('aria-label',`${playing?'Pause':'Preview'} ${track.title}`);
    play.onclick=()=>toggleMusicPreview(track);
    const info=node('div','music-info');
    const head=node('div','music-title-line');
    head.append(node('span','music-title',track.title));
    if(track.duration!=null)head.append(node('span','music-duration',timeLabel(track.duration)));
    info.append(head);
    if(track.tags.length) {
      const tags=node('div','music-tags');
      // Every tag here is a music tag; the "music/" prefix is noise in this list.
      for(const tag of track.tags)tags.append(node('span','music-tag',tag.replace(/^music\//,'')));
      info.append(tags)
    }
    // The licence is shown once, in the dialog's header, not on every row.
    const useWrap=node('div','music-use'),use=node('button',null,'Use');
    use.onclick=()=>useMusicTrack(track,use);
    useWrap.append(use);
    row.append(play,info,useWrap);
    list.append(row)
  }
  if(!tracks.length)list.append(node('p','music-empty',state.musicTracks.length?'No tracks match.':'No tracks.'))
}
function toggleMusicPreview(track) {
  const audio=$('music-preview');
  if(state.musicPlayingId===track.id&&!audio.paused) {
    audio.pause();
    return
  }
  state.musicPlayingId=track.id;
  audio.src=track.audio_url;
  audio.play().catch(()=> {
  })
}
async function useMusicTrack(track,button) {
  button.disabled=true;
  $('music-error').hidden=true;
  try {
    const record=await json('music/attach',null, {
      video:state.video,source:state.musicSourceId,track:track.id
    });
    addFiles([record]);
    closeMusicPicker()
  }
  catch(e) {
    $('music-error').textContent=e.message;
    $('music-error').hidden=false;
    button.disabled=false
  }
}
$('music-button').onclick=openMusicPicker;
$('music-close').onclick=closeMusicPicker;
$('music-shade').onclick=closeMusicPicker;
$('music-search').oninput=renderMusicList;
$('music-source').onchange=e=>loadMusicTracks(e.target.value);
$('music-preview').onplay=$('music-preview').onpause=$('music-preview').onended=()=> {
  if($('music-preview').paused)state.musicPlayingId=null;
  if(!$('music-dialog').hidden)renderMusicList()
};
// ---- Pictures: make pictures from a description and add them to the note ----
// Shown only when the editor has a picture service (api/pictures answers 404 otherwise). Sets are made
// in the background and can wait a long time for the shared GPU, so the list is polled: often while
// the sheet is open, slowly while one is on the way and it is closed, then not at all.
function picturesOpen() {
  return !$('pictures-dialog').hidden
}
async function loadPictures() {
  const video=state.video;
  let data;
  lastPicturesPoll=Date.now();
  try {
    data=await json('pictures', {
      video
    })
  }
  catch(e) {
    if(e.status===404&&video===state.video) {
      state.pictures=null;
      state.picturesAbsent=true;
      $('pictures-button').hidden=true
    }
    return
  }
  if(video!==state.video)return;
  const before=state.pictures;
  state.pictures=data.jobs;
  $('pictures-button').hidden=false;
  // A set that finished while the sheet was closed earns the button a dot.
  if(before&&!picturesOpen()) {
    const done=new Set(before.filter(j=>j.status==='done').map(j=>j.id));
    if(data.jobs.some(j=>j.status==='done'&&!done.has(j.id)))$('pictures-badge').hidden=false
  }
  if(picturesOpen())renderPictures()
}
async function loadPictureGpu() {
  try {
    state.pictureGpu=(await json('pictures/gpu')).gpu
  }
  catch(e) {
    state.pictureGpu='unknown'
  }
  if(picturesOpen())renderPictureStatus()
}
function openPictures() {
  $('pictures-badge').hidden=true;
  $('pictures-error').hidden=true;
  $('pictures-added').hidden=true;
  $('pictures-dialog').hidden=false;
  $('pictures-shade').hidden=false;
  renderPictureCount();
  renderPictures();
  loadPictures();
  loadPictureGpu()
}
function closePictures() {
  closePictureActions();
  endPose();
  $('pictures-dialog').hidden=true;
  $('pictures-shade').hidden=true;
  $('pictures-prompt').blur()
}
function renderPictureCount() {
  for(const b of $('pictures-count').children) {
    const on=Number(b.dataset.n)===state.pictureCount;
    b.classList.toggle('active',on);
    b.setAttribute('aria-checked',String(on))
  }
}
const picturesPending=()=>(state.pictures||[]).filter(j=>j.status==='waiting'||j.status==='making');
function renderPictureStatus() {
  const status=$('pictures-status'),full=picturesPending().length>=2;
  $('pictures-make').disabled=full||state.pictureMaking;
  $('pictures-make').textContent=state.pictureMaking?'Starting…':state.pose?'Make 2 poses':'Make';
  status.textContent=full?'Two sets are on the way. You can make more when one is done.'
    : state.pictureGpu==='free'?'GPU free: about a minute'
    : state.pictureGpu==='busy'?'The GPU is busy. Your pictures will wait in line and show up here.'
    : 'Pictures usually take about a minute.';
  status.classList.toggle('busy',!full&&state.pictureGpu==='busy')
}
function pictureUrl(job,picture,cutout,full) {
  return api(`pictures/${job.id}/${picture.index}`, {
    video:state.video,...(cutout?{cutout:1}:{}),...(full?{full:1}:{})
  })
}
const pictureKey=(job,picture,cutout)=>`${job.id}/${picture.index}${cutout?'/cutout':''}`;
function renderPictures() {
  renderPictureStatus();
  const list=$('pictures-list');
  list.replaceChildren();
  const jobs=state.pictures||[];
  if(!jobs.length) {
    list.append(node('p','pictures-empty','Describe a picture and the builder can use it in your video.'));
    return
  }
  for(const job of jobs)list.append(pictureCard(job))
}
function pictureCard(job) {
  const card=node('section','picture-card');
  const head=node('div','picture-card-head');
  // A set made from another picture is headed by it: a pose and an edit say what is new, more like it doesn't.
  if(job.poseOf)head.append(sourceRow(job.poseOf,'Pose of'));
  if(job.likeOf)head.append(sourceRow(job.likeOf,'More like'));
  if(job.editOf)head.append(sourceRow(job.editOf,'Edit of'));
  if(!job.likeOf)head.append(node('p','picture-prompt',job.editOf?job.editOf.label:job.prompt));
  const count=job.n===1?'1 picture':`${job.n} pictures`;
  const unedited=(job.poseOf||job.likeOf||{}).edited?' · from the picture before it was edited':'';
  const when=relative(job.created*1000);
  head.append(node('span','picture-meta',`${count}${job.cutout?' · cut out':''}${unedited} · ${when}`));
  card.append(head);
  if(job.status==='failed') {
    const row=node('div','picture-failed');
    row.append(node('span',null,job.message||'These pictures couldn’t be made.'));
    if(job.retryable!==false) {
      const retry=node('button',null,'Retry');
      retry.onclick=()=>retryPictures(job,retry);
      row.append(retry)
    }
    card.append(row);
    return card
  }
  const grid=node('div','picture-grid');
  if(job.status!=='done') {
    for(let i=0;i<job.n;i++)grid.append(node('div','picture-tile picture-wait'));
    card.append(grid);
    const making=job.status==='making';
    card.append(node('p','picture-wait-text',making?`Making ${count}…`:'Waiting for the GPU…'));
    return card
  }
  for(const picture of job.pictures)grid.append(pictureTile(job,picture));
  card.append(grid);
  return card
}
function pictureTile(job,picture) {
  const tile=node('div','picture-tile');
  const showCutout=picture.cutout&&!state.pictureOriginals.has(pictureKey(job,picture));
  tile.classList.toggle('checker',showCutout);
  const add=node('button','picture-add');
  const img=node('img');
  img.src=pictureUrl(job,picture,showCutout);
  const which=job.editOf?job.editOf.label.toLowerCase():`picture ${picture.index+1}`;
  img.alt=`${job.prompt}, ${which}${showCutout?', background cut out':''}`;
  img.loading='lazy';
  img.decoding='async';
  add.append(img);
  const key=pictureKey(job,picture,showCutout);
  const added=state.files.some(f=>f.pictureKey===key);
  add.setAttribute('aria-label',added?'Added to your note':`Add picture ${picture.index+1} to your note`);
  if(added) {
    const mark=node('span','picture-added-mark');
    mark.append(icon('check'));
    add.append(mark)
  }
  add.onclick=()=>addPicture(job,picture,showCutout,tile);
  tile.append(add);
  if(picture.cutout) {
    const flip=node('button','picture-flip',showCutout?'See original':'See cut-out');
    flip.setAttribute('aria-label',showCutout?'Show the original picture':'Show it with the background cut out');
    flip.onclick=()=> {
      const k=pictureKey(job,picture);
      if(state.pictureOriginals.has(k))state.pictureOriginals.delete(k);
      else state.pictureOriginals.add(k);
      tile.replaceWith(pictureTile(job,picture))
    };
    tile.append(flip)
  }
  const more=node('button','picture-more');
  more.type='button';
  more.append(icon('more'));
  more.title='More you can do with this picture';
  more.setAttribute('aria-label',`More for picture ${picture.index+1}`);
  more.setAttribute('aria-haspopup','dialog');
  more.onclick=()=>openPictureActions(job,picture,showCutout,more);
  tile.append(more);
  return tile
}
// Which picture a set was made from: its thumbnail, while the set is still kept, and its words.
function sourceRow(source,label) {
  const row=node('div','picture-pose-of');
  const img=node('img');
  img.alt='';
  img.loading='lazy';
  img.decoding='async';
  img.onerror=()=>img.remove();
  img.src=pictureUrl({id:source.id}, {index:source.index},source.cutout);
  if(source.cutout)img.className='checker';
  row.append(img,node('span',null,`${label}: ${source.prompt}`));
  return row
}
// ---- A picture's actions: one "⋯" per tile opens a small sheet over the Pictures sheet ----
const PICTURE_CROPS=[
  ['square','Square',null],
  ['16:9','Wide','16:9, like a landscape video'],
  ['9:16','Tall','9:16, like a phone video'],
  ['trim','Trim the empty edges','Down to just what was cut out']
];
const PICTURE_CROP_SHAPES={'square':[1,1],'16:9':[16,9],'9:16':[9,16]};
function openPictureActions(job,picture,cutout,opener) {
  state.pictureActions={job,picture,cutout,opener,busy:false};
  const thumb=$('picture-actions-thumb');
  thumb.classList.toggle('checker',cutout);
  thumb.src=pictureUrl(job,picture,cutout);
  $('picture-actions-title').textContent=job.editOf?job.editOf.label:`Picture ${picture.index+1}`;
  $('picture-actions-prompt').textContent=job.prompt;
  $('picture-actions-error').hidden=true;
  $('picture-actions').hidden=false;
  $('picture-actions-shade').hidden=false;
  renderPictureActions('main');
  $('picture-actions-list').querySelector('button')?.focus({preventScroll: true})
}
function closePictureActions() {
  const open=state.pictureActions;
  if(!open)return;
  state.pictureActions=null;
  $('picture-actions').hidden=true;
  $('picture-actions-shade').hidden=true;
  $('picture-actions-thumb').removeAttribute('src');
  if(open.opener.isConnected)open.opener.focus({preventScroll: true})
}
function pictureAction(iconName,label,detail,onclick,disabled) {
  const b=node('button','picture-action');
  b.type='button';
  b.append(icon(iconName));
  const text=node('span','picture-action-text');
  text.append(node('span',null,label));
  if(detail)text.append(node('small',null,detail));
  b.append(text);
  b.disabled=!!disabled;
  b.onclick=onclick;
  return b
}
function renderPictureActions(view) {
  const open=state.pictureActions,list=$('picture-actions-list');
  const {job,picture,cutout}=open;
  open.view=view;
  list.replaceChildren();
  if(view==='crop') {
    list.append(pictureAction('back','Back',null,()=>renderPictureActions('main')));
    // The server refuses a crop to the shape the picture already has, so say so here instead.
    const thumb=$('picture-actions-thumb');
    if(!thumb.naturalWidth)thumb.addEventListener('load',()=> {
      if(state.pictureActions===open&&open.view==='crop')renderPictureActions('crop')
    },{once: true});
    for(const [edit,label,detail] of PICTURE_CROPS) {
      if(edit==='trim'&&!picture.cutout)continue;
      const shape=PICTURE_CROP_SHAPES[edit];
      const already=shape&&thumb.naturalWidth&&
        Math.abs(thumb.naturalWidth/thumb.naturalHeight/(shape[0]/shape[1])-1)<0.01;
      list.append(pictureAction('crop',label,already?'It is already this shape':detail,()=>editPicture(edit),already))
    }
  }
  else {
    const key=pictureKey(job,picture,cutout),added=state.files.some(f=>f.pictureKey===key);
    list.append(pictureAction(added?'check':'add',added?'In your note':'Add to note',null,()=> {
      // The list may have been redrawn by a poll while the sheet was open: then its tile is a new one.
      const tile=open.opener.isConnected?open.opener.closest('.picture-tile'):null;
      closePictureActions();
      addPicture(job,picture,cutout,tile)
    },added));
    if(picture.posable) {
      // An edit has no drawing of its own to start from, so these start from the picture before it.
      const before=job.editOf?'From the picture before it was edited':null;
      const full=picturesPending().length>=2;
      list.append(pictureAction('pose','Another pose',before,()=> {
        closePictureActions();
        startPose(job,picture)
      }));
      const likeDetail=full?'Two sets are on the way. Wait for one.':before||'2 more in the same style';
      list.append(pictureAction('like','More like this',likeDetail,()=>varyPicture(),full));
    }
    list.append(pictureAction('flip','Flip left to right',null,()=>editPicture('flip')));
    list.append(pictureAction('rotate-left','Rotate left',null,()=>editPicture('rotate-left')));
    list.append(pictureAction('rotate-right','Rotate right',null,()=>editPicture('rotate-right')));
    list.append(pictureAction('crop','Crop…',picture.cutout?'Square, wide, tall or trimmed':'Square, wide or tall',
      ()=>renderPictureActions('crop')))
  }
  for(const b of list.children)if(open.busy)b.disabled=true
}
// Runs one action of the open sheet; the new set goes to the top of the list, the sheet closes.
async function runPictureAction(path,body) {
  const open=state.pictureActions;
  if(!open||open.busy)return;
  open.busy=true;
  for(const b of $('picture-actions-list').children)b.disabled=true;
  $('picture-actions-error').hidden=true;
  try {
    const job=await json(`pictures/${open.job.id}/${open.picture.index}/${path}`,null, {
      video:state.video,...body
    });
    state.pictures=[job,...(state.pictures||[]).filter(j=>j.id!==job.id)];
    if(state.pictureActions===open)closePictureActions();
    renderPictures();
    const card=$('pictures-list').firstElementChild;
    card?.classList.add('fresh');
    card?.scrollIntoView({block:'nearest'})
  }
  catch(e) {
    if(state.pictureActions!==open)return;
    open.busy=false;
    $('picture-actions-error').textContent=e.message;
    $('picture-actions-error').hidden=false;
    renderPictureActions(open.view)
  }
}
const varyPicture=()=>runPictureAction('vary', {});
const editPicture=edit=>runPictureAction('edit', {edit});
// "Make another pose of this" turns the form at the top into a pose form for that picture: the
// description becomes the pose, and the set's size and cut-out follow the picture. What was being
// described waits, and comes back after.
function startPose(job,picture) {
  if(!state.pose)state.picturePrompt=$('pictures-prompt').value;
  state.pose={job,picture};
  const prompt=$('pictures-prompt');
  prompt.value='';
  prompt.maxLength=300;
  prompt.placeholder='The new pose, like “waving, arm raised towards the right edge of the image”';
  $('pictures-form').classList.add('posing');
  $('pictures-pose').hidden=false;
  $('pictures-hint').hidden=false;
  const thumb=$('pictures-pose-thumb');
  const cutout=picture.cutout;
  thumb.classList.toggle('checker',cutout);
  thumb.src=pictureUrl(job,picture,cutout);
  $('pictures-pose-source').textContent=job.prompt;
  $('pictures-error').hidden=true;
  renderPictureStatus();
  document.querySelector('.pictures-scroll').scrollTop=0;
  prompt.focus({preventScroll: true})
}
function endPose() {
  if(!state.pose)return;
  state.pose=null;
  const prompt=$('pictures-prompt');
  prompt.value=state.picturePrompt||'';
  prompt.maxLength=1000;
  prompt.placeholder='Describe a picture…';
  $('pictures-form').classList.remove('posing');
  $('pictures-pose').hidden=true;
  $('pictures-hint').hidden=true;
  $('pictures-pose-thumb').removeAttribute('src');
  renderPictureStatus()
}
async function addPicture(job,picture,cutout,tile) {
  const key=pictureKey(job,picture,cutout);
  if(state.files.some(f=>f.pictureKey===key)) {
    showPictureAdded('Already in your note');
    return
  }
  tile=tile||node('div');
  if(tile.classList.contains('adding'))return;
  tile.classList.add('adding');
  $('pictures-error').hidden=true;
  try {
    const record=await json(`pictures/${job.id}/${picture.index}/attach`,null, {
      video:state.video,cutout
    });
    addFiles([{...record,pictureKey:key,thumb:pictureUrl(job,picture,cutout)}]);
    if(tile.isConnected)tile.replaceWith(pictureTile(job,picture));
    else renderPictures();
    showPictureAdded('Added to your note')
  }
  catch(e) {
    tile.classList.remove('adding');
    $('pictures-error').textContent=e.message;
    $('pictures-error').hidden=false
  }
}
let pictureAddedTimer=null;
function showPictureAdded(text) {
  $('pictures-added-text').textContent=text;
  const pill=$('pictures-added');
  pill.hidden=false;
  pill.classList.remove('pop');
  void pill.offsetWidth;
  pill.classList.add('pop');
  clearTimeout(pictureAddedTimer);
  pictureAddedTimer=setTimeout(()=>pill.hidden=true,4000)
}
async function makePictures(e) {
  e.preventDefault();
  const prompt=$('pictures-prompt').value.trim();
  if(!prompt) {
    $('pictures-prompt').focus();
    return
  }
  if(state.pictureMaking)return;
  state.pictureMaking=true;
  $('pictures-error').hidden=true;
  renderPictureStatus();
  const pose=state.pose;
  try {
    const job=pose
      ? await json(`pictures/${pose.job.id}/${pose.picture.index}/pose`,null, {
        video:state.video,pose:prompt
      })
      : await json('pictures',null, {
        video:state.video,prompt,n:state.pictureCount,cutout:$('pictures-cutout').checked
      });
    state.pictures=[job,...(state.pictures||[]).filter(j=>j.id!==job.id)];
    if(pose&&state.pose===pose)endPose();
    // Down goes the keyboard, so the new set is in view; the words stay, to tweak and make again.
    $('pictures-prompt').blur();
    document.querySelector('.pictures-scroll').scrollTop=0
  }
  catch(e) {
    $('pictures-error').textContent=e.message;
    $('pictures-error').hidden=false
  }
  finally {
    state.pictureMaking=false;
    renderPictures()
  }
}
async function retryPictures(job,button) {
  button.disabled=true;
  $('pictures-error').hidden=true;
  try {
    const again=await json(`pictures/${job.id}/retry`,null, {
      video:state.video
    });
    state.pictures=(state.pictures||[]).map(j=>j.id===again.id?again:j);
    renderPictures()
  }
  catch(e) {
    button.disabled=false;
    $('pictures-error').textContent=e.message;
    $('pictures-error').hidden=false
  }
}
$('pictures-button').onclick=openPictures;
$('pictures-close').onclick=closePictures;
$('pictures-shade').onclick=closePictures;
$('pictures-back').onclick=closePictures;
$('pictures-form').onsubmit=makePictures;
$('picture-actions-close').onclick=closePictureActions;
$('picture-actions-shade').onclick=closePictureActions;
$('picture-actions').onkeydown=e=> {
  if(e.key==='Escape') {
    e.stopPropagation();
    closePictureActions()
  }
};
$('pictures-pose-cancel').onclick=()=> {
  endPose();
  $('pictures-prompt').focus({preventScroll: true})
};
$('pictures-prompt').onkeydown=e=> {
  if(e.key==='Enter'&&!e.shiftKey) {
    e.preventDefault();
    $('pictures-form').requestSubmit()
  }
};
for(const b of $('pictures-count').children) {
  b.onclick=()=> {
    state.pictureCount=Number(b.dataset.n);
    renderPictureCount()
  }
}
let lastPicturesPoll=0;
setInterval(()=> {
  if(document.hidden||!state.video||state.signedOut||state.restarting)return;
  // A first load that failed (the editor busy or restarting) is tried again, so the button
  // still turns up without a reload; only a 404, no picture service at all, stops it.
  if(!state.pictures) {
    if(!state.picturesAbsent&&Date.now()-lastPicturesPoll>=20000)loadPictures();
    return
  }
  const pending=picturesPending().length>0;
  const every=picturesOpen()?(pending?3000:15000):pending?15000:0;
  if(every&&Date.now()-lastPicturesPoll>=every)loadPictures();
  if(picturesOpen()&&Date.now()-(state.pictureGpuAt||0)>=30000) {
    state.pictureGpuAt=Date.now();
    loadPictureGpu()
  }
},1000);
// ---- Source videos: upload, list, pick a span, delete ----
// m:ss, or h:mm:ss past an hour -- distinct from timeLabel, which never shows hours.
function sourceClock(seconds) {
  seconds=Math.max(0,Math.floor(seconds||0));
  const h=Math.floor(seconds/3600),m=Math.floor((seconds%3600)/60),s=seconds%60;
  return (h?`${h}:${String(m).padStart(2,'0')}`:`${m}`)+':'+String(s).padStart(2,'0')
}
function sourceUrl(name) {
  return api('sources/'+encodeURIComponent(name), {
    video:state.video
  })
}
async function loadSources() {
  try {
    const data=await json('sources', {
      video:state.video
    });
    state.sources=data.sources;
    $('source-error').hidden=true;
    renderSources()
  }
  catch(e) {
    $('source-error').textContent=e.message;
    $('source-error').hidden=false
  }
}
function renderSources() {
  const list=$('source-list');
  list.replaceChildren();
  for(const s of state.sources) {
    const row=node('div','source-row');
    const poster=document.createElement('video');
    poster.className='source-poster';
    poster.muted=true;
    poster.playsInline=true;
    poster.preload='metadata';
    poster.src=sourceUrl(s.name)+'#t=0.1';
    row.append(poster);
    const info=node('div','source-info');
    info.append(node('span','source-name',s.name));
    const meta=[sourceClock(s.duration)];
    if(s.width&&s.height)meta.push(`${s.width}×${s.height}`);
    meta.push(s.has_audio?'audio':'no audio');
    if(s.caption)meta.push('caption');
    if(!s.preview_ready)meta.push('Preparing…');
    info.append(node('span','source-meta',meta.join(' · ')));
    row.append(info);
    const del=node('button','source-delete','Delete');
    del.setAttribute('aria-label','Delete '+s.name);
    del.onclick=e=> {
      e.stopPropagation();
      confirmDeleteSource(del,s.name)
    };
    row.append(del);
    row.onclick=()=>openSourcePlayer(s);
    list.append(row)
  }
  if(!state.sources.length)list.append(node('p','source-empty','No source videos yet.'))
}
let deleteConfirmTimer=null;
function confirmDeleteSource(button,name) {
  if(button.dataset.confirm) {
    deleteSource(name);
    return
  }
  button.dataset.confirm='1';
  button.textContent='Really delete?';
  clearTimeout(deleteConfirmTimer);
  deleteConfirmTimer=setTimeout(()=> {
    button.dataset.confirm='';
    button.textContent='Delete'
  },3000)
}
async function deleteSource(name) {
  try {
    await json('sources/'+encodeURIComponent(name)+'/delete',null, {
      video:state.video
    });
    await loadSources()
  }
  catch(e) {
    $('source-error').textContent=e.message;
    $('source-error').hidden=false
  }
}
function xhrUpload(path,params,file,onProgress) {
  return new Promise((resolve,reject)=> {
    const xhr=new XMLHttpRequest();
    xhr.open('POST',api(path,params));
    xhr.setRequestHeader('Content-Type',file.type||'application/octet-stream');
    xhr.upload.onprogress=e=> {
      if(e.lengthComputable)onProgress(e.loaded/e.total)
    };
    xhr.onload=()=> {
      let data=null;
      try {
        data=JSON.parse(xhr.responseText)
      } catch (_) {
      }
      if(xhr.status>=200&&xhr.status<300&&data)resolve(data);
      else if(data ? draining(xhr.status,data) : GATEWAY.includes(xhr.status))reject(restarting());
      else reject(Error((data&&(data.error||data.log))||`upload failed (HTTP ${xhr.status})`))
    };
    xhr.onerror=()=>reject(restarting());
    xhr.send(file)
  })
}
$('source-add-button').onclick=()=>$('source-file-picker').click();
$('source-file-picker').onchange=e=> {
  const file=e.target.files[0];
  e.target.value='';
  if(!file)return;
  state.sourcePending= {
    file,captionFile:null
  };
  $('source-name').value=file.name.replace(/\.[^.]+$/,'');
  $('source-caption-name').textContent='';
  $('source-upload-progress').hidden=true;
  $('source-upload-fill').style.width='0%';
  $('source-pending').hidden=false;
  $('source-error').hidden=true
};
$('source-caption-button').onclick=()=>$('source-caption-picker').click();
$('source-caption-picker').onchange=e=> {
  const file=e.target.files[0];
  e.target.value='';
  if(!file||!state.sourcePending)return;
  state.sourcePending.captionFile=file;
  $('source-caption-name').textContent=file.name
};
$('source-cancel').onclick=()=> {
  state.sourcePending=null;
  $('source-pending').hidden=true
};
async function uploadCaption(name,file) {
  const r=await reach(api('sources/'+encodeURIComponent(name)+'/caption', {
    video:state.video,filename:file.name
  }), {
    method:'POST',headers: {
      'Content-Type':file.type||'text/vtt'
    },body:file
  });
  const data=await parseJSON(r);
  if(!r.ok)throw httpError(r,data)
}
$('source-upload-button').onclick=async()=> {
  const pending=state.sourcePending;
  if(!pending)return;
  const name=$('source-name').value.trim();
  $('source-error').hidden=true;
  $('source-upload-progress').hidden=false;
  $('source-upload-button').disabled=true;
  try {
    const params= {
      video:state.video,filename:pending.file.name,...(name? {
        name
      }:{
      })
    };
    const record=await xhrUpload('sources',params,pending.file,frac=> {
      $('source-upload-fill').style.width=`${Math.round(frac*100)}%`;
      $('source-upload-label').textContent=`Uploading… ${Math.round(frac*100)}%`
    });
    if(pending.captionFile)await uploadCaption(record.name,pending.captionFile);
    state.sourcePending=null;
    $('source-pending').hidden=true;
    await loadSources()
  }
  catch(e) {
    $('source-error').textContent=e.message;
    $('source-error').hidden=false
  }
  finally {
    $('source-upload-button').disabled=false
  }
};
function updateAddToNoteEnabled() {
  const sp=state.sourcePlayer;
  $('source-add-to-note').disabled=!(sp&&sp.start!=null&&sp.end!=null)
}
function openSourcePlayer(source) {
  state.sourcePlayer= {
    name:source.name,start:null,end:null
  };
  $('source-player-name').textContent=source.name;
  $('source-player').src=sourceUrl(source.name);
  $('source-start-label').textContent='–';
  $('source-end-label').textContent='–';
  $('source-player-error').hidden=true;
  updateAddToNoteEnabled();
  $('source-player-dialog').hidden=false;
  $('source-player-shade').hidden=false
}
function closeSourcePlayer() {
  $('source-player-dialog').hidden=true;
  $('source-player-shade').hidden=true;
  $('source-player').pause();
  $('source-player').removeAttribute('src');
  $('source-player').load();
  state.sourcePlayer=null
}
$('source-mark-start').onclick=()=> {
  const sp=state.sourcePlayer;
  if(!sp)return;
  sp.start=$('source-player').currentTime;
  $('source-start-label').textContent=sourceClock(sp.start);
  updateAddToNoteEnabled()
};
$('source-mark-end').onclick=()=> {
  const sp=state.sourcePlayer;
  if(!sp)return;
  sp.end=$('source-player').currentTime;
  $('source-end-label').textContent=sourceClock(sp.end);
  updateAddToNoteEnabled()
};
function insertAtCursor(el,text) {
  const start=el.selectionStart??el.value.length,end=el.selectionEnd??el.value.length;
  el.value=el.value.slice(0,start)+text+el.value.slice(end);
  const pos=start+text.length;
  el.selectionStart=el.selectionEnd=pos;
  el.focus()
}
$('source-add-to-note').onclick=()=> {
  const sp=state.sourcePlayer;
  if(!sp||sp.start==null||sp.end==null)return;
  const [a,b]=sp.start<=sp.end?[sp.start,sp.end]:[sp.end,sp.start];
  insertAtCursor($('message'),`use ${sourceClock(a)}–${sourceClock(b)} from ${sp.name} `);
  fitMessage();
  closeSourcePlayer()
};
$('source-player-close').onclick=closeSourcePlayer;
$('source-player-shade').onclick=closeSourcePlayer;
// Notes the director has written but not sent: kept in this browser, per video,
// so they survive a reload. Not the "queued" note state, which is sent and waiting.
// ---- Pending notes: drafted locally, batched before sending ----
const pendingKey=()=>`director-pending:${location.pathname}:${state.video}`;
function savePending() {
  try {
    localStorage.setItem(pendingKey(), JSON.stringify(state.pending))
  } catch (_) {
  }
}
function loadPending() {
  try {
    state.pending=JSON.parse(localStorage.getItem(pendingKey()))||[]
  } catch (_) {
    state.pending=[]
  }
  renderPending()
}
function renderPending() {
  const list=$('pending-list'),n=state.pending.length;
  $('pending').hidden=!n;
  list.replaceChildren();
  state.pending.forEach((item,i)=> {
    const row=node('li','pending-item'),edit=node('button','pending-text');
    if(item.time!=null)edit.append(node('span','pending-time',timeLabel(item.time)));
    edit.append(node('span',null,item.text));
    const files=item.attachments.length;
    if(files)edit.append(node('span','pending-files',files===1?'+1 file':`+${files} files`));
    edit.setAttribute('aria-label',`Edit: ${item.text}`);
    edit.onclick=()=>editPending(i);
    const remove=node('button','pending-remove');
    remove.append(icon('close'));
    remove.setAttribute('aria-label',`Remove: ${item.text}`);
    remove.onclick=()=> {
      state.pending.splice(i,1);
      savePending();
      renderPending()
    };
    row.append(edit,remove);
    list.append(row)
  });
  $('send-all').textContent=n>1?`Send ${n} notes to the builder`:'Send to the builder'
}
function editPending(i) {
  if($('message').value.trim()||state.files.length) {
    showError('Add or clear the note you are writing first.');
    return
  }
  const [item]=state.pending.splice(i,1);
  savePending();
  renderPending();
  $('message').value=item.text;
  fitMessage();
  state.files=item.attachments;
  renderFiles();
  state.stamp=item.time!=null;
  if(state.stamp&&state.videoReady)player.currentTime=item.time;
  stampLabel();
  $('message').focus({preventScroll: true})
}
// Uploads File objects; entries already uploaded ({id, name}) pass through.
async function uploadFiles(files) {
  const out=[];
  for(let i=0;i<files.length;i++) {
    if(files[i].id) {
      out.push(files[i]);
      continue
    }
    showError(`Uploading ${i+1} of ${files.length}…`);
    const r=await reach(api('attachments', {
      video:state.video,name:files[i].name
    }), {
      method:'POST',headers: {
        'Content-Type':files[i].type||'application/octet-stream'
      },body:files[i]
    });
    const data=await parseJSON(r);
    if(!r.ok)throw httpError(r,data);
    out.push({id:data.id,name:files[i].name,type:files[i].type})
  }
  return out
}
// Call after every programmatic change to the box's value: only typing fires `input`.
function fitMessage() {
  const el=$('message');
  el.style.height='auto';
  el.style.height=el.scrollHeight+2+'px';
  el.style.overflowY=el.scrollHeight+2>parseFloat(getComputedStyle(el).maxHeight)?'auto':'hidden'
}
// After a note joins the list, the empty input says how to send it.
let hintTimer=null;
function hintSendAgain() {
  const input=$('message');
  input.dataset.placeholder ??= input.placeholder;
  input.placeholder='Hit Enter again to send to the builder';
  clearTimeout(hintTimer);
  hintTimer=setTimeout(()=>input.placeholder=input.dataset.placeholder, 5000)
}
async function addPending() {
  if(state.sending)return;
  const text=$('message').value.trim();
  if(!text) {
    $('message').focus({preventScroll: true});
    return
  }
  state.sending=true;
  $('add-note').disabled=true;
  showError('');
  const time=state.stamp?player.currentTime||0:null;
  try {
    const attachments=await uploadFiles([...state.files]);
    state.pending.push({text,time,attachments});
    savePending();
    renderPending();
    $('message').value='';
    fitMessage();
    // A suggestion layer (suggest.js) listens for 'input' to know the note was cleared.
    $('message').dispatchEvent(new Event('input',{bubbles:true}));
    hintSendAgain();
    state.files=[];
    renderFiles();
    showError('')
  }
  catch(e) {
    showError(e.message)
  }
  finally {
    state.sending=false;
    $('add-note').disabled=false
  }
}
// One item goes out as an ordinary note, keeping its pinned frame. Several go
// out as one numbered note: the builder handles them in one turn, one version.
function batchBody(items) {
  const ids=items.flatMap(item=>item.attachments.map(a=>a.id));
  if(items.length===1) {
    const [item]=items;
    return {text:item.text,attachments:ids,...(item.time!=null?{time:item.time}:{})}
  }
  const lines=items.map((item,i)=> {
    const at=item.time!=null?`At ${timeLabel(item.time)}: `:'';
    const names=item.attachments.map(a=>a.name).join(', ');
    return `${i+1}. ${at}${item.text}${names?` (attached: ${names})`:''}`
  });
  return {text:lines.join('\n'),attachments:ids}
}
// A video's first note, while it is not built yet, starts it the way New video does
// (videos/first-note): the builder is also told what Film details set.
function postNote(body) {
  if(notBuilt(currentVersion())&&!state.notes.length&&!body.clip)
    return json('videos/first-note',null,{description:body.text,attachments:body.attachments});
  return json('notes',null,body)
}
async function sendPending() {
  if(state.sending||!state.pending.length)return;
  if(!await ensureName())return;
  state.sending=true;
  $('send-all').disabled=true;
  showError('Sending…');
  try {
    await postNote({
      video:state.video,format:state.format,...noteScope(),...batchBody(state.pending)
    });
    state.pending=[];
    savePending();
    renderPending();
    showError('');
    await loadNotes()
  }
  catch(e) {
    showError(e.message)
  }
  finally {
    state.sending=false;
    $('send-all').disabled=false
  }
}
// ---- Fine-tuning iframe, opening a video, and startup ----
function openTuning(target) {
  let frame=$(target).querySelector('iframe');
  if(!frame) {
    frame=node('iframe','tune-frame');
    frame.title='Fine tuning timeline and copy editor';
    $(target).append(frame)
  }
  const src='tuning.html#video='+encodeURIComponent(state.video);
  if(frame.getAttribute('src')!==src)frame.src=src
}
async function openVideo(video) {
  state.video=video;
  state.commit=null;
  state.deliberate=false;
  state.videoReady=false;
  state.versions=[];
  state.notes=[];
  state.versionCursor=null;
  state.steps={};
  state.tl=null;
  renderTimeline();
  renderScope();
  clearTimeout(state.renderTimer);
  $('video-title').textContent=libName||video;
  $('video-picker').value=video;
  renderUpgrade();
  loadPending();
  state.pictures=null;
  state.picturesAbsent=false;
  $('pictures-badge').hidden=true;
  loadPictures();
  try {
    state.info=await json('info', {
      video
    });
    // A film that doesn't load has no formats; versions and notes still load, so it can be fixed or left.
    const formats=state.info.formats||[];
    if(state.info.error&&!formats.length)
      toast(`This version doesn't load: ${state.info.error.trim().split('\n').pop()}`);
    let saved;
    try {
      saved=localStorage.getItem(`director-format:${video}`);
    } catch (_) {
      saved=null;
    }
    const preferred=window.innerWidth<=700 ? formats.find(f=>f.name==='9x16')?.name : null;
    state.format=formats.find(f=>f.name===saved)?.name || preferred || formats[0]?.name;
    renderFormats();
    await loadTimeline();
    await loadVersions();
    await loadNotes();
  }
  catch(e) {
    toast(e.message)
  }
}
async function init() {
  if(libMode)$('library-link').href='/';
  else {
    $('library-link').hidden=true;
    document.querySelector('.topbar .slash').hidden=true;
  }
  try {
    const [project,name]=await Promise.all([json('project'),fetch(libMode?'/api/name':'api/name').then(parseJSON)]);
    state.project=project;
    state.user=project.user||null;
    state.name=name.name;
    updateName();
    updateAccountBar();
    if(state.user||libMode)loadAccess();
    loadMusicSources();
    const videos=project.videos||[];
    const picker=$('video-picker');
    for(const v of videos) {
      const opt=node('option',null,v.id);
      opt.value=v.id;
      picker.append(opt)
    }
    const picked=videos[0]?.id;
    if(videos.length>1) {
      picker.hidden=false;
      $('video-title').hidden=true
    }
    if(picked) {
      await openVideo(picked);
      takeDraft()
    }
    else toast('No videos found in this project.')
  }
  catch(e) {
    toast(e.message)
  }
}
// A starter prompt New video left for the video it just made (new_video.js writes the same key).
const DRAFT='vb-draft:';
function takeDraft() {
  let text=null;
  try {
    text=sessionStorage.getItem(DRAFT+location.pathname);
    sessionStorage.removeItem(DRAFT+location.pathname)
  }
  catch(_) {}
  const el=$('message');
  if(!text||el.value.trim())return;
  el.value=text;
  fitMessage();
  el.focus({preventScroll: true});
  const blank=/\[[^\]]*\]/.exec(text);
  if(blank)el.setSelectionRange(blank.index,blank.index+blank[0].length);
  el.dispatchEvent(new Event('input',{bubbles: true}))
}
// ---- Player and transport controls wiring ----
$('upgrade').onclick=upgradeVideo;
$('tap-player').onclick=togglePlay;
$('desktop-play').onclick=togglePlay;
// The video element itself goes full screen, with the browser's own controls while it is.
// iPhone Safari has no element requestFullscreen, only the video's own webkitEnterFullscreen.
function enterFullscreen() {
  if(!state.videoReady)return;
  if(!player.requestFullscreen) {
    player.webkitEnterFullscreen?.();
    return
  }
  player.controls=true;
  player.requestFullscreen().catch(()=> {
    player.controls=false
  })
}
$('fullscreen').onclick=enterFullscreen;
$('rail-fullscreen').onclick=enterFullscreen;
document.addEventListener('fullscreenchange',()=> {
  if(!document.fullscreenElement)player.controls=false
});
window.addEventListener('resize', resizePlayer);
// loadPlayer pauses and reloads the element while a render is pending; those events must not
// replace the spinner.
player.onpause=()=> {
  if(state.videoReady)setPlayState('play')
};
player.onplay=()=> {
  if(state.videoReady)setPlayState('pause')
};
player.onvolumechange=()=> {
  $('mute').replaceChildren(icon(player.muted ? 'muted' : 'volume'));
  $('mute').setAttribute('aria-label', player.muted ? 'Unmute' : 'Mute');
  $('mute').setAttribute('aria-pressed', String(player.muted))
};
$('mute').onclick=()=> {
  player.muted=!player.muted
};
player.ontimeupdate=updateTime;
$('progress').onpointerdown=e=> {
  $('progress').setPointerCapture(e.pointerId);
  $('progress').classList.add('scrubbing');
  scrubAt(e)
};
$('progress').onpointermove=e=> {
  if($('progress').classList.contains('scrubbing'))scrubAt(e)
};
$('progress').onpointerup=$('progress').onpointercancel=()=>$('progress').classList.remove('scrubbing');
$('progress').onkeydown=e=> {
  const step={ArrowLeft:-5,ArrowRight:5}[e.key];
  if(!step||!videoDuration())return;
  e.preventDefault();
  seekTo((player.currentTime+step)/videoDuration())
};
$('retry-render').onclick=()=>loadPlayer(true);
$('phone-format').onclick=()=> {
  const formats=state.info?.formats||[];
  const i=formats.findIndex(f=>f.name===state.format);
  if(formats.length)setFormat(formats[(i+1)%formats.length].name)
};
$('rail-chat').onclick=()=>openSheet('chat');
$('sheet-full').onclick=()=>setFullSheet(!$('panel').classList.contains('full'));
$('rail-versions').onclick=()=>openSheet('versions');
$('rail-tune').onclick=async()=> {
  if(await ensureName())openSheet('tune')
};
$('sheet-close').onclick=closeSheet;
$('shade-close').onclick=closeSheet;
$('tab-chat').onclick=()=>setView('chat');
$('tab-versions').onclick=()=>setView('versions');
$('desktop-tune-toggle').onclick=async()=> {
  if(!await ensureName())return;
  const body=$('desktop-tune-body');
  body.hidden=!body.hidden;
  $('desktop-tune-toggle').setAttribute('aria-expanded',!body.hidden);
  if(!body.hidden)openTuning('desktop-tune-body')
};
// ---- Account: name, sign-out and access sharing ----
$('director-name').onclick=async()=> {
  const value=prompt('What should we call you?',state.name||'');
  if(value===null)return;
  state.name=null;
  try {
    const r=await jsonName(value);
    state.name=r.name;
    updateName();
  }
  catch(e) {
    showError(e.message)
  }
};
async function jsonName(value) {
  const r=await fetch(libMode?'/api/name':'api/name', {
    method:'POST',headers: {
      'Content-Type':'application/json'
    },body:JSON.stringify( {
      name:value
    })
  });
  const data=await parseJSON(r);
  if(!r.ok)throw httpError(r,data);
  return data
}
function updateName() {
  if (state.user) {
    $('director-name').hidden=true;
    return
  }
  $('director-name').replaceChildren();
  if (state.name) $('director-name').append('Directing as ', node('strong', null, state.name));
  else $('director-name').textContent='Set your name';
  $('director-name').setAttribute('aria-label', state.name ? 'Change your name' : 'Set your name');
}
function updateAccountBar() {
  if (!state.user) {
    $('account-bar').hidden=true;
    return
  }
  $('account-name').textContent=state.user;
  $('account-bar').hidden=false
}
$('account-signout').onclick=async()=> {
  await fetch(libMode?'/api/logout':'api/logout', {
    method:'POST',headers: {
      'Content-Type':'application/json'
    },body:'{}'
  });
  location.href='/login'
};
async function loadAccess() {
  try {
    state.access=await json('access');
    renderAccess()
  }
  catch(e) {
    $('share-error').textContent=e.message;
    $('share-error').hidden=false
  }
}
function renderAccess() {
  const a=state.access;
  if(!a)return;
  $('share-owner').textContent='Owner: '+(a.owner||'(admin)');
  $('share-list').replaceChildren();
  for (const name of a.collaborators) {
    const li=node('li','pending-item');
    li.append(node('span','pending-text',name));
    const remove=node('button','pending-remove','✕');
    remove.setAttribute('aria-label','Remove '+name);
    remove.onclick=()=>changeAccess('remove',name);
    li.append(remove);
    $('share-list').append(li)
  }
  $('tab-share').hidden=$('rail-share').hidden=!(a.can_share||a.can_delete);
  $('share-username').closest('.composer-row').hidden=!a.can_share;
  // Without accounts there is no one to share with: the tab holds only Delete.
  $('share-people').hidden=!a.can_share;
  $('delete-video').hidden=!a.can_delete
}
// The video's library name, as /v/<name>/ shows it.
function videoName() {
  return decodeURIComponent(location.pathname.replace(/^\/v\//,'').replace(/\/+$/,''))
}
function showDeleteConfirm(open) {
  $('delete-confirm').hidden=!open;
  $('delete-open').hidden=open;
  $('delete-error').hidden=true;
  $('delete-name').value='';
  $('delete-go').disabled=true;
  if (open) {
    $('delete-expected').textContent=videoName();
    $('delete-name').focus()
  }
}
$('delete-open').onclick=()=>showDeleteConfirm(true);
$('delete-cancel').onclick=()=>showDeleteConfirm(false);
$('delete-name').oninput=()=> {
  $('delete-go').disabled=$('delete-name').value.trim()!==videoName()
};
$('delete-go').onclick=async()=> {
  $('delete-error').hidden=true;
  $('delete-go').disabled=true;
  try {
    const r=await fetch('/api/videos/delete', {
      method:'POST',headers: {
        'Content-Type':'application/json'
      },body:JSON.stringify( {
        name:videoName()
      })
    });
    const data=await parseJSON(r);
    if(!r.ok)throw httpError(r,data);
    location.href='/'
  }
  catch(e) {
    $('delete-error').textContent=e.message;
    $('delete-error').hidden=false;
    $('delete-go').disabled=false
  }
};
async function changeAccess(action,username) {
  $('share-error').hidden=true;
  try {
    state.access=await json('access',null, {
      action,username
    });
    renderAccess();
    if(action==='invite')$('share-username').value=''
  }
  catch(e) {
    $('share-error').textContent=e.message;
    $('share-error').hidden=false
  }
}
$('share-invite').onclick=()=> {
  const username=$('share-username').value.trim();
  if(username)changeAccess('invite',username)
};
$('tab-share').onclick=()=>setView('share');
$('rail-share').onclick=()=>openSheet('share');
$('tab-sources').onclick=()=>setView('sources');
$('rail-sources').onclick=()=>openSheet('sources');
// ---- Composer wiring: drag/drop, paste, keyboard shortcuts ----
window.addEventListener('message',async e=> {
  if (e.origin!==location.origin || e.data?.type!=='videobuilder:edit' ||
      e.data.video!==state.video) return;
  state.info=await json('info', {
    video:state.video
  });
  renderFormats();
  loadVersions();
});
$('timestamp').onclick=()=> {
  state.stamp=!state.stamp;
  stampLabel()
};
$('attach-button').onclick=()=>$('file-picker').click();
$('file-picker').onchange=e=> {
  addFiles(e.target.files);
  e.target.value=''
};
$('add-note').onclick=addPending;
$('send-all').onclick=sendPending;
// Ctrl/Cmd+Enter sends the typed note on its own; pending notes stay put.
async function sendNow() {
  const text=$('message').value.trim();
  if(state.sending||!text)return;
  if(!await ensureName())return;
  state.sending=true;
  showError('Sending…');
  const time=state.stamp?player.currentTime||0:null;
  try {
    const attachments=await uploadFiles([...state.files]);
    await postNote({
      video:state.video,format:state.format,...noteScope(),...batchBody([{text,time,attachments}])
    });
    $('message').value='';
    fitMessage();
    state.files=[];
    renderFiles();
    showError('');
    await loadNotes()
  }
  catch(e) {
    showError(e.message)
  }
  finally {
    state.sending=false
  }
}
$('message').onkeydown=e=> {
  if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)) {
    e.preventDefault();
    sendNow()
  }
  else if(e.key==='Enter'&&!e.shiftKey) {
    e.preventDefault();
    if(!$('message').value.trim()&&state.pending.length&&!state.files.length)sendPending();
    else addPending()
  }
};
$('message').oninput=fitMessage;
$('message').onpaste=e=> {
  const files=[...e.clipboardData?.files||[]];
  if(!files.length)return;
  // Office apps put an image beside the text; keep the text pasting as usual.
  if(!e.clipboardData.getData('text/plain'))e.preventDefault();
  addFiles(files)
};
$('video-picker').onchange=e=>openVideo(e.target.value);
$('version-list').onscroll=e=> {
  const el=e.target;
  if(el.scrollTop+el.clientHeight>=el.scrollHeight-100)loadVersions(true)
};
$('panel').ondragover=e=> {
  if(e.dataTransfer?.types.includes('Files')) {
    e.preventDefault();
    e.dataTransfer.dropEffect='copy'
  }
};
$('panel').ondrop=e=> {
  e.preventDefault();
  setView('chat');
  addFiles(e.dataTransfer.files)
};
// ---- Timeline: a film made of clips (timeline.json) ----
// The strip under the player and the chat, for a video with a timeline file. Its direct edits
// (order, trims, transitions, J/L cuts, Audio lanes) each commit the timeline file alone
// (POST api/timeline, against the commit they were made on); everything else is a note.
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const svg=(p,w=18)=>`<svg width="${w}" height="${w}" viewBox="0 0 24 24" fill="none" stroke="currentColor" `+
  `stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
const TL_ICON={
  film:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M3 15h18M8 4v5M16 4v5M8 15v5M16 15v5"/>',
  down:'<path d="M6 9l6 6 6-6"/>',plus:'<path d="M12 5v14M5 12h14"/>',minus:'<path d="M5 12h14"/>',
  flag:'<path d="M5 21V4h11l-2 4 2 4H5"/>',audio:'<path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 7v10"/>',
  dots:'<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
  zin:'<circle cx="11" cy="11" r="7"/><path d="M21 21l-5-5M8 11h6M11 8v6"/>',
  zout:'<circle cx="11" cy="11" r="7"/><path d="M21 21l-5-5M8 11h6"/>',
  fit:'<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',ready:'<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  building:'<path class="tl-spin" d="M12 3a9 9 0 1 0 9 9"/>',
  waiting:'<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>',
  failed:'<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17v.5"/>',music:'<path d="M9 18V5l11-2v13"/>'+
    '<circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
  sound:'<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16 9a4 4 0 0 1 0 6"/>',
  speech:'<path d="M4 5.5h16v10H9l-4.5 3.5v-3.5H4z"/>',trash:'<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>',
  muted:'<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M17 9l5 6M22 9l-5 6"/>',duck:'<path d="M3 8h5l3 8h2l3-8h5"/>',
  clip:'<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3"/>',
  cut:'<path d="M12 3v18"/>',dissolve:'<circle cx="9" cy="12" r="6"/><circle cx="15" cy="12" r="6"/>',
  wipe:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M12 5v14M15 9l3 3-3 3"/>',
  whip:'<path d="M3 8h13M3 12h18M3 16h13"/>',flash:'<path d="M13 2L5 14h6l-1 8 8-12h-6z"/>',
  match:'<path d="M4 12h6M14 12h6"/><circle cx="12" cy="12" r="2.5"/>'
};
const TL_TRANSITIONS=[['cut','Cut','Straight cut'],['dissolve','Dissolve','One clip fades into the next'],
  ['wipe','Wipe','The next clip slides across'],['whip','Whip pan','A fast slide with motion blur'],
  ['flash','Flash','A quick cut through white']];
const TL_LATER=[['match','Match cut']];
// A new transition's length, as a share of a second: whips and flashes are quick.
const TL_LEN={whip:1/4,flash:1/5};
const TL_WORD={ready:'Ready',building:'Rendering',waiting:'Not rendered yet',failed:'Render failed',
  missing:'Missing'};
const tlClone=o=>JSON.parse(JSON.stringify(o));
const tlPhone=()=>window.innerWidth<=700;
const tlClock=frames=> {
  const s=frames/state.tl.fps,m=Math.floor(s/60),r=s-m*60;
  return `${m}:${String(Math.floor(r)).padStart(2,'0')}${r%1>.01&&s<60?'.'+Math.round((r%1)*10)%10:''}`
};
const tlSecs=frames=>`${(frames/state.tl.fps).toFixed(frames%state.tl.fps?2:0)} s`;
const tlTitle=c=>c.id.replace(/-/g,' ');
const tlInfo=id=>state.tl.clips.find(c=>c.id===id)||{state:'waiting',frames:null,speech:[]};
const tlFootage=c=>'footage' in c;
function tlState(info) {
  if(info.state==='ready'||info.state==='missing'||info.state==='failed'||info.state==='building')return info.state;
  return info.state==='queued'||info.state==='rendering'?'building':'waiting'
}
// Where every clip lands, as timeline_file.place does it. A clip not rendered yet has no known
// length: it is drawn 3 s long (dashed) until its render says.
function tlPlace(data=state.tl.data) {
  const fps=state.tl.fps,out=[];
  let at=0;
  data.clips.forEach((c,i)=> {
    const info=tlInfo(c.id),foot=tlFootage(c);
    const span=foot?c.out-(c.in||0):(info.frames??3*fps);
    const frames=Math.max(1,span-(c.head||0)-(c.tail||0));
    const start=at-(i?c.cut?.frames||0:0);
    const source=(foot?c.in||0:0)+(c.head||0);
    const media=info.frames;
    // What a J/L cut can reveal: the trimmed media before and after what the clip shows.
    const before=source,after=media==null?(foot?0:c.tail||0):Math.max(0,media-source-frames);
    out.push({c,i,info,start,frames,end:start+frames,source,media,before,after,guess:!foot&&info.frames==null});
    at=start+frames
  });
  return {places:out,total:Math.max(1,at)}
}
// Where the cut into a placed clip is (timeline_file.cut_frame): a transition's middle.
const tlCutAt=p=>p.start+((p.c.cut?.frames||0)>>1);
// A reel's beat grid (timeline_file.beat_grid, beats.BeatGrid): beat k of the song on Audio `lane`,
// item `item`, is `zero` plus k beats rounded half up, from where the item starts playing to where
// it stops. Null for a timeline with no grid.
function tlGrid(data=state.tl.data) {
  const b=data.beats,it=b&&data.lanes?.[b.lane-1]?.items?.[b.item-1];
  if(!it)return null;
  const fpb=state.tl.fps*60/b.bpm,zero=it.at-(it.offset||0)+(b.first||0),lo=it.at,hi=it.at+it.frames;
  const bar=b.bar||4,frame=k=>zero+Math.floor(k*fpb+.5);
  let first=Math.max(0,Math.ceil((lo-zero)/fpb)-1),last=Math.max(-1,Math.floor((hi-zero)/fpb)+1);
  while(frame(first)<lo)first++;
  while(last>=0&&frame(last)>hi)last--;
  if(last<first)return null;
  const index=f=> {
    const k=Math.min(last,Math.max(first,Math.floor((f-zero)/fpb)));
    let best=null;
    for(const j of [k-1,k,k+1]) {
      if(j>=first&&j<=last&&(best==null||Math.abs(frame(j)-f)<=Math.abs(frame(best)-f)))best=j
    }
    return best
  };
  // n beats on from frame f (back, for n<0); from between beats, the next (or previous) is the first.
  const step=(f,n)=> {
    const k=index(f),at=frame(k);
    if(n>0&&at>f||n<0&&at<f)n-=Math.sign(n);
    return frame(Math.max(first,Math.min(last,k+n)))
  };
  const name=f=> {
    const k=index(f);
    return k%bar?`beat ${k+1}`:`bar ${k/bar+1}`
  };
  return {fpb,bar,bpm:b.bpm,first,last,lo,hi,frame,index,step,name,snap:f=>frame(index(f)),
    off:f=>f<lo||f>hi?0:f-frame(index(f))}
}
function tlLabelWidth() {
  return tlPhone()?46:104
}
function tlFit(total) {
  const w=($('timeline').clientWidth||window.innerWidth)-tlLabelWidth()-16;
  return Math.max(0.05,w/total)
}
function tlZoom(total) {
  return state.tl.z??tlFit(total)
}
// Speech on the timeline, [from, to) frames: where a ducked lane dips.
function tlSpeech(places) {
  const out=[];
  for(const p of places) {
    if(!p.info.audio)continue;
    const early=Math.min(p.c.sound?.early||0,p.before),late=Math.min(p.c.sound?.late||0,p.after);
    const lo=p.source-early,hi=p.source+p.frames+late;
    for(const [at,n] of p.info.speech||[]) {
      const a=Math.max(at,lo),b=Math.min(at+n,hi);
      if(b>a)out.push([p.start+a-p.source,p.start+b-p.source])
    }
  }
  return out
}
function tlThumbUrl(c,info) {
  if(info.state!=='ready')return '';
  const k=info.key||`${c.footage}:${c.in||0}:${c.head||0}`;
  return api('timeline/thumb',{video:state.video,clip:c.id,format:state.tl.format,k})
}
function tlThumb(c,info) {
  const src=tlThumbUrl(c,info);
  return src?`<img src="${esc(src)}" alt="" loading="lazy" draggable="false">`:''
}
function tlBlock(p,z) {
  const t=state.tl,c=p.c,info=p.info,n=p.i+1,st=tlState(info);
  // Neighbours overlapping in a transition meet at its middle, where its + is.
  const din=p.i?c.cut?.frames||0:0,dout=t.data.clips[p.i+1]?.cut?.frames||0;
  const left=(p.start+din/2)*z,w=Math.max(8,(p.frames-din/2-dout/2)*z);
  const sel=!t.whole&&t.sel===c.id;
  const unknown=!tlFootage(c)&&info.frames==null;
  const talk=info.speech?.length>0;
  const band=unknown?'':talk?'speech':info.audio?'clip sound':'no sound';
  const bandIcon=talk?TL_ICON.speech:info.audio?TL_ICON.sound:'';
  const len=unknown?'length known once it renders':tlClock(p.frames);
  const label=`Clip ${n}: ${tlTitle(c)}, ${len}, ${TL_WORD[st]}${tlFootage(c)?', footage':''}`;
  return `<button class="tl-blk st-${st}${sel?' sel':''}${p.guess?' guess':''}" data-tl="pick" data-id="${esc(c.id)}"`+
    ` style="left:${left}px;width:${w}px" aria-label="${esc(label)}" title="${esc(label)}"`+
    ` aria-pressed="${sel}">${tlThumb(c,info)}<span class="tl-bn">${n}</span>`+
    `${st!=='ready'||w>44?`<span class="tl-bst">${svg(TL_ICON[st==='missing'?'failed':st],12)}</span>`:''}`+
    `${w>60?`<span class="tl-bt">${esc(tlTitle(c))}</span>`:''}`+
    `<span class="tl-snd${talk?' talk':''}${band==='no sound'?' none':''}">`+
    `${w>40&&bandIcon?svg(bandIcon,10):''}${w>64?band:''}</span></button>`
}
// The clip's own sound reaching across a cut: J before its picture, L after it.
function tlOverhangs(places,z) {
  let h='';
  for(const p of places) {
    const early=Math.min(p.c.sound?.early||0,p.before),late=Math.min(p.c.sound?.late||0,p.after);
    if(early)h+=`<span class="tl-jl j" style="left:${(p.start-early)*z}px;width:${Math.max(6,early*z)}px"`+
      ` title="J-cut: ${esc(tlTitle(p.c))}’s sound starts ${tlSecs(early)} early"><b>J</b></span>`;
    if(late)h+=`<span class="tl-jl l" style="left:${p.end*z}px;width:${Math.max(6,late*z)}px"`+
      ` title="L-cut: ${esc(tlTitle(p.c))}’s sound runs ${tlSecs(late)} on"><b>L</b></span>`
  }
  return h
}
function tlPluses(places,z) {
  const grid=tlGrid();
  return places.slice(1).map(p=> {
    const c=p.c,d=c.cut?.frames||0,prev=places[p.i-1];
    const kind=c.cut?.transition||'cut';
    const jl=(c.sound?.early&&p.before)?'J':(prev.c.sound?.late&&prev.after)?'L':'';
    // Off the beat: a cut a reel's grid doesn't have on a beat (it can't tell while a length is a guess).
    const off=grid&&!places.slice(0,p.i).some(q=>q.guess)?grid.off(tlCutAt(p)):0;
    const what=`${TL_TRANSITIONS.find(x=>x[0]===kind)?.[1]||kind}${jl?`, ${jl}-cut`:''}`+
      `${off?`, ${Math.abs(off)} frame${Math.abs(off)===1?'':'s'} off the beat`:''}`;
    return `<button class="tl-plus${off?' off':''}" data-tl="cut" data-i="${p.i}" style="left:${(p.start+d/2)*z}px"`+
      ` aria-label="Between ${p.i} and ${p.i+1}: ${what}. Insert a clip, trim, transition, sound"`+
      ` title="${esc(what)}">${svg(TL_ICON.plus,13)}`+
      `${kind!=='cut'?`<span class="tl-pg">${svg(TL_ICON[kind],12)}</span>`:''}`+
      `${jl?`<span class="tl-pj">${jl}</span>`:''}</button>`
  }).join('')+(places.length?`<button class="tl-plus tl-end" data-tl="append" `+
    `style="left:${places.at(-1).end*z}px" aria-label="After the last clip: add a clip" title="Add a clip">`+
    `${svg(TL_ICON.plus,13)}</button>`:'')
}
// A reel's beats on the ruler: every beat while they are 5 px apart, else every bar's first.
function tlBeatTicks(z) {
  const g=tlGrid();
  if(!g)return '';
  const every=g.fpb*z>=5?1:g.fpb*g.bar*z>=5?g.bar:0;
  let h='';
  for(let k=g.first;every&&k<=g.last;k++) {
    if(k%every===0)h+=`<i class="tl-beat${k%g.bar?'':' bar'}" style="left:${g.frame(k)*z}px"></i>`
  }
  return h
}
function tlTicks(total,z) {
  const fps=state.tl.fps;
  const step=[.5,1,2,5,10,15,30,60,120,300,600].find(s=>s*fps*z>=56)||600;
  let h='';
  for(let s=0;s*fps<=total;s+=step)h+=`<span class="tl-tick" style="left:${s*fps*z}px">${tlClock(s*fps)}</span>`;
  return h
}
// A lane item's name: its file's, or a bank sound effect's id (`sfx`, its peak or onset on `at`, drawn
// from there for its `frames`, else half a second: the take's own length is in the pack, not the file).
function tlItemName(it) {
  return it.sfx?it.sfx+(it.variant?` ${it.variant}`:it.note?` ${it.note}`:''):it.sound.split('/').pop()
}
function tlLaneRow(lane,k,speech,z,total) {
  const items=lane.items||[];
  if(!items.length)return `<div class="tl-r tl-r-lane${lane.mute?' muted':''}"><div class="tl-lanedrop" `+
    `style="width:${Math.max(160,Math.min(total*z,600))}px">${svg(TL_ICON.audio,15)}Empty: add a sound from its menu, `+
    `or describe one in a note</div></div>`;
  return `<div class="tl-r tl-r-lane${lane.mute?' muted':''}">${items.map(it=> {
    const a=it.at,b=it.at+(it.frames||(it.sfx?Math.round(state.tl.fps/2):0)),w=Math.max(4,(b-a)*z),h=34;
    const dips=lane.duck?speech.filter(([x,y])=>y>a&&x<b).map(([x,y])=>[Math.max(x,a),Math.min(y,b)]):[];
    const r=Math.max(3,.1*state.tl.fps*z),hi=h*.3,lo=h*.72;
    const pts=[[0,hi]];
    for(const [x,y] of dips)pts.push([(x-a)*z-r,hi],[(x-a)*z,lo],[(y-a)*z,lo],[(y-a)*z+r,hi]);
    pts.push([w,hi]);
    const poly=pts.map(q=>q.map(v=>Math.round(Math.max(0,Math.min(w,v))*10)/10).join(',')).join(' ');
    const name=tlItemName(it);
    return `<div class="tl-lanebar" style="left:${a*z}px;width:${w}px" title="${esc(name)}${dips.length?
      ': dips under speech':''}"><svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true">`+
      `<polygon points="0,${h} ${poly} ${w},${h}" fill="#ffffff1c"/><polyline points="${poly}" fill="none" `+
      `stroke="#fff" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg><span class="tl-ln">`+
      `${svg(TL_ICON.music,11)}${esc(name)}${lane.mute?' · muted':''}</span></div>`
  }).join('')}</div>`
}
function renderTimeline() {
  const t=state.tl,box=$('timeline');
  document.body.classList.toggle('has-timeline',!!t);
  $('play-scope').hidden=!t;
  if(!t) {
    box.hidden=true;
    box.replaceChildren();
    return
  }
  const keep=$('tl-scroll')?.scrollLeft;
  const {places,total}=tlPlace(),d=t.data,acts=d.acts||[],lanes=d.lanes||[];
  box.hidden=false;
  box.className='tl-card '+(t.open?'open':'collapsed');
  const count=`${places.length} clip${places.length===1?'':'s'} · ${tlClock(total)}`;
  const head=`<button class="tl-head" data-tl="toggle" aria-expanded="${t.open}">${svg(TL_ICON.film,16)}`+
    `<b>Timeline</b><span class="tl-tot">${count}</span><span id="tl-status" class="tl-status">`+
    `${esc(t.status||'')}</span><span class="tl-chev">${svg(TL_ICON.down)}</span></button>`;
  if(!t.open) {
    box.innerHTML=head;
    return
  }
  const z=tlZoom(total),W=Math.ceil(total*z)+(tlPhone()?60:16);
  const L=(cls,icon,text,sub='')=>`<div class="tl-l ${cls}">${icon?svg(TL_ICON[icon],15):''}<span class="tl-lt">`+
    `${text}${sub?`<small>${sub}</small>`:''}</span></div>`;
  const byId=Object.fromEntries(places.map(p=>[p.c.id,p]));
  const actRow=acts.map((a,k)=> {
    const s=byId[a.clips[0]]?.start??0,e=byId[a.clips.at(-1)]?.end??s,w=(e-s)*z-4;
    return `<button class="tl-act" data-tl="act" data-k="${k}" style="left:${s*z+2}px;width:${Math.max(4,w)}px" `+
      `title="Act ${k+1}: ${esc(a.title)}" aria-label="Act ${k+1}: ${esc(a.title)}. Rename or remove">`+
      `${svg(TL_ICON.flag,12)}Act ${k+1}${w>110?` <span>${esc(a.title)}</span>`:''}</button>`
  }).join('');
  const actLines=acts.slice(1).map(a=>`<i class="tl-actline" style="left:${(byId[a.clips[0]]?.start??0)*z}px"></i>`)
    .join('');
  const labels=L('tl-l-ruler','','')+(acts.length?L('tl-l-acts','flag','Acts'):'')+L('tl-l-cuts','plus','Between')+
    L('tl-l-clips','film','Clips','with own sound')+lanes.map((lane,k)=>`<div class="tl-l tl-l-lane`+
    `${t.newLane===k?' new':''}${lane.mute?' muted':''}"><span class="tl-lane-name">`+
    `${svg(TL_ICON[lane.mute?'muted':'audio'],15)}<span>Audio ${k+1}</span></span><button class="tl-lmenu" `+
    `data-tl="lane" data-k="${k}" aria-label="Audio ${k+1} options">${svg(TL_ICON.dots,16)}</button></div>`).join('');
  const speech=tlSpeech(places);
  box.innerHTML=head+`<div class="tl-tools"><button class="tl-icon" data-tl="zoom" data-d="0.6" aria-label="Zoom out">`+
    `${svg(TL_ICON.zout)}</button><button class="tl-icon" data-tl="zoom" data-d="1.6" aria-label="Zoom in">`+
    `${svg(TL_ICON.zin)}</button><button class="tl-icon" data-tl="fit" aria-label="Fit the whole video">`+
    `${svg(TL_ICON.fit)}</button><span class="tl-hint">${tlGrid()?`A reel at ${tlGrid().bpm} bpm: cuts go on `+
    'the beat. ':''}Drag a clip to move it; tap + between clips to cut.</span>`+
    `<button class="tl-link" data-tl="details">Film details</button>`+
    `<button class="tl-btn" data-tl="newact" aria-label="Start an act at ${t.sel?'the selected clip':'clip 1'}">`+
    `${svg(TL_ICON.plus,16)}Act</button>`+
    `<button class="tl-btn" data-tl="addlane" aria-label="Add Audio">${svg(TL_ICON.plus,16)}Audio</button>`+
    `</div>`+
    `<div class="tl-grid"><div class="tl-labels">${labels}</div><div class="tl-scroll" id="tl-scroll">`+
    `<div class="tl-track" id="tl-track" style="width:${W}px"><div class="tl-r tl-r-ruler" data-tl="seek">`+
    `${tlTicks(total,z)}${tlBeatTicks(z)}</div>${acts.length?`<div class="tl-r tl-r-acts">${actRow}</div>`:''}`+
    `<div class="tl-r tl-r-cuts">${tlPluses(places,z)}</div><div class="tl-r tl-r-clips" id="tl-clips">`+
    `${places.map(p=>tlBlock(p,z)).join('')}${tlOverhangs(places,z)}</div>`+
    `${lanes.map((lane,k)=>tlLaneRow(lane,k,speech,z,total)).join('')}${actLines}`+
    `<span class="tl-playhead" id="tl-playhead" hidden></span></div></div></div>`;
  const sc=$('tl-scroll');
  if(keep!=null&&!t.recenter)sc.scrollLeft=keep;
  else if(t.sel&&byId[t.sel]) {
    const p=byId[t.sel];
    sc.scrollLeft=Math.max(0,(p.start+p.frames/2)*z-sc.clientWidth/2)
  }
  t.recenter=false;
  tlWire(sc);
  tlPlayhead()
}
function tlPlayhead() {
  const t=state.tl,ph=$('tl-playhead');
  if(!t||!ph||!state.videoReady)return;
  const {places,total}=tlPlace(),z=tlZoom(total),f=player.currentTime*t.fps;
  let at=f;
  if(!t.whole&&t.sel) {
    const p=places.find(x=>x.c.id===t.sel);
    if(!p)return;
    at=p.start+Math.max(0,Math.min(p.frames,f-(tlFootage(p.c)?p.source:p.c.head||0)))
  }
  ph.hidden=false;
  ph.style.left=`${Math.min(total,at)*z}px`
}
function tlSetStatus(text) {
  state.tl.status=text;
  if($('tl-status'))$('tl-status').textContent=text
}
// `force` takes main's file even when it looks unchanged: after a refused save the strip holds
// the edit main never got, at the same commit.
async function loadTimeline(force) {
  if(!state.video)return;
  const video=state.video;
  try {
    const r=await json('timeline',{video,format:state.format||''});
    if(video!==state.video)return;
    const t=state.tl;
    if(t&&(t.saving||t.dirty))return;
    if(!r.timeline) {
      if(t||r.error) {
        state.tl=null;
        renderTimeline();
        renderScope()
      }
      if(r.error)toast(`The timeline file doesn't load: ${r.error}`);
      return
    }
    if(!force&&t&&t.commit===r.commit&&JSON.stringify(t.clips)===JSON.stringify(r.clips))return;
    tlTake(r);
    renderTimeline();
    renderScope()
  }
  catch(e) {
    // A poll that fails says nothing; the next one catches up.
  }
}
function tlTake(r) {
  const prev=state.tl||{open:false,z:null,sel:null,whole:true,status:''};
  state.tl={...prev,data:r.timeline,commit:r.commit,fps:r.fps,format:r.format,formats:r.formats,clips:r.clips,
    dirs:r.dirs,dirty:false};
  if(state.tl.sel&&!r.timeline.clips.some(c=>c.id===state.tl.sel)) {
    state.tl.sel=null;
    state.tl.whole=true
  }
}
// One direct edit: `change` edits a copy of the timeline (or returns a whole new one); it is drawn
// at once and saved shortly after, so steppers clicked in a row commit once.
function tlChange(change,summary,after) {
  const t=state.tl,before=JSON.stringify(t.data);
  const data=tlClone(t.data);
  const next=change(data)||data;
  const first=next.clips[0];
  if(first?.cut)delete first.cut;
  for(const c of next.clips)if(c.sound&&!Object.keys(c.sound).length)delete c.sound;
  if(next.acts&&!next.acts.length)delete next.acts;
  if(JSON.stringify(next)===before)return false;
  t.data=next;
  t.dirty=true;
  t.summary=summary;
  t.after=after||null;
  t.undo=t.undo||JSON.parse(before);
  tlSetStatus('Saving…');
  renderTimeline();
  clearTimeout(t.saveTimer);
  t.saveTimer=setTimeout(saveTimeline,after?0:700);
  return true
}
async function saveTimeline() {
  const t=state.tl;
  if(!t||!t.dirty)return;
  if(t.saving) {
    t.again=true;
    return
  }
  if(!await ensureName()) {
    // Every version says who directed it: no name, no edit.
    t.dirty=false;
    tlUnsaved(t.undo);
    t.undo=null;
    return loadTimeline(true)
  }
  t.saving=true;
  t.dirty=false;
  const sent=tlClone(t.data),after=t.after,undo=t.undo;
  // A planned clip a later edit took out again needs no directory.
  const plans=t.plans&&Object.fromEntries(Object.entries(t.plans).filter(([id])=>sent.clips.some(c=>c.id===id)));
  t.after=null;
  t.undo=null;
  t.plans=null;
  try {
    const r=await json('timeline',null,{video:state.video,timeline:sent,base:t.commit,summary:t.summary,
      ...(plans?{plans}:{})});
    t.commit=r.commit;
    t.clips=r.clips;
    t.dirs=r.dirs;
    if(!t.dirty)t.data=r.timeline;
    tlSetStatus(r.changed?`Saved · v${r.n}`:'Saved');
    if(after)after(undo);
    loadVersions()
  }
  catch(e) {
    // Refused (the loader's message) or stale (409): show why, and the timeline as it is on main.
    t.dirty=false;
    t.again=false;
    t.undo=null;
    tlUnsaved(undo);
    toast(e.message);
    t.saving=false;
    await loadTimeline(true);
    return
  }
  finally {
    t.saving=false;
    renderTimeline()
  }
  if(t.again||t.dirty) {
    t.again=false;
    saveTimeline()
  }
}
// A save that didn't happen: put back the file the edits started from, so nothing on screen (or
// in the next edit) claims what main never got. The reload that follows confirms it from main.
function tlUnsaved(undo) {
  const t=state.tl;
  if(undo)t.data=undo;
  tlSetStatus('Not saved');
  renderTimeline()
}
function tlUndoToast(text,undo,summary) {
  const box=$('tl-toast');
  box.replaceChildren(node('span',null,text));
  const b=node('button',null,'Undo');
  b.onclick=()=> {
    box.hidden=true;
    tlChange(()=>tlClone(undo),summary,()=>toast('Undone'))
  };
  box.append(b);
  box.hidden=false;
  clearTimeout(box.timer);
  box.timer=setTimeout(()=>box.hidden=true,8000)
}
// ---- Timeline: what the player plays, and which notes the chat shows ----
function tlNoteClip() {
  const t=state.tl;
  return t&&!t.whole&&t.sel?t.sel:null
}
function noteScope() {
  const clip=tlNoteClip();
  return clip?{clip}:{}
}
// The selected clip's thumbnail stands in for the poster frame (the root film's is a title card).
function tlPoster() {
  const c=state.tl.data.clips.find(x=>x.id===tlNoteClip());
  return c?tlThumbUrl(c,tlInfo(c.id)):''
}
function playUrl() {
  const t=state.tl,clip=tlNoteClip();
  if(!clip)return videoUrl();
  const c=t.data.clips.find(x=>x.id===clip);
  if(c&&tlFootage(c)) {
    const from=((c.in||0)+(c.head||0))/t.fps,to=(c.out-(c.tail||0))/t.fps;
    return api('timeline/footage',{video:state.video,clip})+`#t=${from},${to}`
  }
  const fmt=t.formats.includes(state.format)?state.format:t.format;
  return api('clip',{video:state.video,clip,format:fmt,...(state.commit?{commit:state.commit}:{})})
}
function notesInView() {
  const all=state.notes,clip=tlNoteClip();
  // A server that doesn't know which clip a note is about sends no `clip`: show every note.
  if(!state.tl||!all.some(n=>'clip' in n))return all;
  return all.filter(n=>(n.clip??null)===clip)
}
function renderScope() {
  const t=state.tl,clip=tlNoteClip(),card=$('chat-scope');
  fdShowLink();
  $('scope-clip').setAttribute('aria-pressed',String(!!clip));
  $('scope-whole').setAttribute('aria-pressed',String(!clip));
  if(!t) {
    card.hidden=true;
    $('message').placeholder='Note for the builder…';
    return
  }
  const i=clip?t.data.clips.findIndex(c=>c.id===clip):-1;
  card.hidden=false;
  card.replaceChildren();
  if(clip) {
    card.append(node('strong',null,`Notes on clip ${i+1}: ${tlTitle(t.data.clips[i])}`),
      node('span',null,'What it shows, its motion, its own sound. The builder changes this clip only.'));
    $('message').placeholder=`Note on clip ${i+1}…`
  }
  else {
    card.append(node('strong',null,'Notes on the whole video'),
      node('span',null,'For the story, the order, new clips and the sound. A note here can change many clips.'));
    $('message').placeholder='Note on the whole video…'
  }
}
function tlPick(id,whole=false) {
  const t=state.tl;
  t.sel=id;
  t.whole=whole;
  renderTimeline();
  renderScope();
  renderNotes();
  loadPlayer()
}
// ---- Timeline: the + sheet, the lane menu and inserting a clip ----
function tlOpenSheet(html,label) {
  const shade=$('tl-shade');
  shade.innerHTML=`<div class="tl-sheet" role="dialog" aria-modal="true" aria-label="${esc(label)}">${html}</div>`;
  shade.hidden=false;
  shade.querySelector('button')?.focus({preventScroll:true});
  return shade.firstElementChild
}
function tlCloseSheet() {
  const shade=$('tl-shade');
  shade.hidden=true;
  shade.replaceChildren();
  state.tl&&(state.tl.sheet=null);
  if(state.tl)renderTimeline()
}
function tlStepper(label,key,value,hint,unit='frame') {
  return `<div class="tl-stepper"><span>${label}${hint?`<small>${hint}</small>`:''}</span>`+
    `<button class="tl-icon" data-step="${key}" data-d="-1" aria-label="${esc(label)}: one ${unit} less">`+
    `${svg(TL_ICON.minus,16)}</button><output>${value}</output><button class="tl-icon" data-step="${key}" `+
    `data-d="1" aria-label="${esc(label)}: one ${unit} more">${svg(TL_ICON.plus,16)}</button></div>`
}
// Whether the + sheet's trims step a beat at a time: on a reel, unless Frames is chosen, and once
// every clip up to the cut has a known length (before that, where the beats fall is a guess).
function tlBeatSteps(places,i) {
  return !!tlGrid()&&!state.tl.frameSteps&&!places.slice(0,i+2).some(p=>p.guess)
}
function tlOpt(attrs,on,icon,title,detail,disabled) {
  return `<button class="tl-opt" ${attrs} aria-pressed="${on}"${disabled?' disabled':''}>`+
    `<span class="tl-ico">${icon}</span><span><b>${title}</b><small>${detail}</small></span>`+
    `<span class="tl-tick-on">${svg(TL_ICON.ready,16)}</span></button>`
}
function tlCutSheet(i) {
  const t=state.tl;
  t.sheet={kind:'cut',i};
  const {places}=tlPlace(),pa=places[i-1],pb=places[i],a=pa.c,b=pb.c,fps=t.fps;
  const kind=b.cut?.transition||'cut',len=b.cut?.frames||0;
  const trim=(f)=>f?`−${tlSecs(f)}`:'0 s';
  const jAvail=pb.before,lAvail=pa.after;
  const mode=b.sound?.early?'J':a.sound?.late?'L':'none';
  const jl=mode==='J'?b.sound.early:mode==='L'?a.sound.late:0;
  const na=`${i}. ${esc(tlTitle(a))}`,nb=`${i+1}. ${esc(tlTitle(b))}`;
  const grid=tlGrid(),beat=tlBeatSteps(places,i),unit=beat?'beat':'frame';
  const at=tlCutAt(pb),off=grid?grid.off(at):0;
  const plural=n=>`${Math.abs(n)} frame${Math.abs(n)===1?'':'s'}`;
  const onBeat=!grid?'':off?`${plural(off)} ${off>0?'after':'before'} ${grid.name(at)}. Reels cut on the beat: `+
    'put it on the beat, or ask the builder for an off-beat cut in a note.':at<grid.lo||at>grid.hi?
    'Outside the song: no beat to cut on.':`On ${grid.name(at)}.`;
  const where=!grid?'':`<p class="tl-sub tl-onbeat${off?' off':''}">${onBeat}</p>`+
    `${off?'<button class="tl-btn" data-x="snap">Put it on the beat</button>':''}`+
    `<div class="tl-dirs tl-unit" role="group" aria-label="Trim steps"><button data-x="unit" data-k="beat" `+
    `aria-pressed="${!t.frameSteps}">Beats</button><button data-x="unit" data-k="frame" `+
    `aria-pressed="${!!t.frameSteps}">Frames</button></div>`;
  const trans=TL_TRANSITIONS.map(([k,name,d])=>tlOpt(`data-x="t" data-k="${k}"`,kind===k,svg(TL_ICON[k],16),name,d))
    .join('')+TL_LATER.map(([k,name])=>tlOpt('',false,svg(TL_ICON[k],16),name,'Coming soon',true)).join('');
  const dirs=kind==='wipe'||kind==='whip'?`<div class="tl-dirs" role="group" aria-label="${kind==='wipe'?'Wipe':
    'Whip'} direction">${['left','right','up','down']
    .map(dd=>`<button data-x="dir" data-k="${dd}" aria-pressed="${(b.cut.direction||'left')===dd}">${dd}</button>`)
    .join('')}</div>`:'';
  const sounds=[
    tlOpt('data-x="jl" data-k="none"',mode==='none',svg(TL_ICON.minus,16),'None','The sound changes at the cut'),
    tlOpt('data-x="jl" data-k="J"',mode==='J','J',`J-cut: ${nb}’s sound starts early`,jAvail?
      `Heard over the end of ${na}`:`Trim the start of ${nb} first: a J-cut reveals its trimmed sound`,!jAvail),
    tlOpt('data-x="jl" data-k="L"',mode==='L','L',`L-cut: ${na}’s sound runs on`,lAvail?
      `Heard over the start of ${nb}`:`Trim the end of ${na} first: an L-cut reveals its trimmed sound`,!lAvail)
  ].join('');
  const html=`<div class="tl-cutsheet"><h3>Between ${na} and ${nb}</h3><p class="tl-sub">How clip ${i} hands over `+
    `to clip ${i+1}. Each change saves a version; no clip renders again.</p><button class="tl-insert" data-x="insert">`+
    `${svg(TL_ICON.plus)}Insert a clip here</button>`+tlOpt('data-x="act"',false,svg(TL_ICON.flag,16),
      `Start an act at ${nb}`,'Acts are titles over runs of clips')+
    `<div class="tl-sec">Trim at this cut</div>${where}`+
    tlStepper(`End of ${na}`,'tail',trim(a.tail||0),beat?'Moves this cut a beat':'',unit)+
    tlStepper(`Start of ${nb}`,'head',trim(b.head||0),beat?`Moves the end of ${nb} a beat`:'',unit)+
    `<p class="tl-sub">${beat?'Tap for a beat; Alt-click, or Frames, for a frame.':
    'Tap for a frame; hold, or Shift-click, for a second.'}</p><div class="tl-sec">Transition</div>`+
    `<div class="tl-two">${trans}</div>${kind!=='cut'?tlStepper('Length','len',tlSecs(len),`${len} frames`):''}`+
    `${dirs}<div class="tl-sec">Sound across this cut</div>${sounds}`+
    `${mode!=='none'?tlStepper(mode==='J'?'Starts early by':'Runs on for','jl',tlSecs(jl),`${jl} frames`):''}`+
    `<div class="tl-sheet-foot"><button class="tl-btn" data-x="close">Done</button></div></div>`;
  const was=document.activeElement?.closest?.('.tl-sheet [data-step],.tl-sheet [data-x]');
  const again=was&&(was.dataset.step?`[data-step="${was.dataset.step}"][data-d="${was.dataset.d}"]`:
    `[data-x="${was.dataset.x}"]${was.dataset.k?`[data-k="${was.dataset.k}"]`:''}`);
  const sheet=tlOpenSheet(html,`Between clip ${i} and clip ${i+1}`);
  if(again)sheet.querySelector(again)?.focus({preventScroll:true});
  tlWireSheet(sheet,i,fps)
}
function tlStep(i,key,d,unit='frame') {
  const {places}=tlPlace(),pa=places[i-1],pb=places[i];
  // Frames a clip can still lose and keep at least one beyond its transitions.
  const room=p=>p.media==null&&!tlFootage(p.c)?Infinity:p.frames-1-(p.c.cut?.frames||0)-
    (places[p.i+1]?.c.cut?.frames||0);
  if(unit==='beat'&&(key==='tail'||key==='head')) {
    // A beat at a time: the cut the trim moves (the one into b for a's end; b's own end for its start)
    // goes to the beat d beats away, trimming more (d>0) moving it earlier.
    // Outside the song, where there are no beats, a beat's worth of frames.
    const g=tlGrid(),nx=places[i+1],from=key==='tail'?tlCutAt(pb):nx?tlCutAt(nx):pb.end;
    d=from<g.lo||from>g.hi?d*Math.round(g.fpb):from-g.step(from,-d)
  }
  const was=tlOnBeat(places);
  return tlChange(data=> {
    const a=data.clips[i-1],b=data.clips[i];
    if(key==='tail'||key==='head') {
      const c=key==='tail'?a:b,add=d>0?Math.min(d,room(key==='tail'?pa:pb)):d;
      if(add<=0&&d>0)return;
      const v=Math.max(0,(c[key]||0)+add);
      if(v)c[key]=v;
      else delete c[key]
    }
    else if(key==='len') {
      const cur=b.cut.frames,max=Math.max(1,Math.min(room(pa),room(pb))+1+cur);
      b.cut.frames=Math.max(1,Math.min(max,cur+d))
    }
    else if(key==='jl') {
      if(b.sound?.early)b.sound.early=Math.max(1,Math.min(pb.before,b.sound.early+d));
      else if(a.sound?.late)a.sound.late=Math.max(1,Math.min(pa.after,a.sound.late+d))
    }
    if(unit==='beat')tlKeepOnBeat(data,key==='tail'?i+1:i+2,was);
    // A transition's length moves its middle, the cut, and every cut after it.
    if(key==='len')tlKeepOnBeat(data,i,was)
  },{tail:`trim the end of ${pa.c.id}`,head:`trim the start of ${pb.c.id}`,len:`transition into ${pb.c.id}`,
    jl:`sound across the cut into ${pb.c.id}`}[key])
}
// A stepper held down steps a second at a time. The sheet is drawn again after every step, so
// the hold lives here, not on the sheet, and any pointerup ends it.
const tlHold={timer:null,repeat:null,held:false};
function tlHoldStop() {
  clearTimeout(tlHold.timer);
  clearInterval(tlHold.repeat);
  tlHold.timer=tlHold.repeat=null
}
window.addEventListener('pointerup',tlHoldStop);
window.addEventListener('pointercancel',tlHoldStop);
function tlWireSheet(sheet,i,fps) {
  sheet.onpointerdown=e=> {
    const b=e.target.closest('[data-step]');
    if(!b)return;
    tlHoldStop();
    tlHold.held=false;
    const key=b.dataset.step,d=+b.dataset.d;
    const beat=(key==='tail'||key==='head')&&tlBeatSteps(tlPlace().places,i);
    tlHold.timer=setTimeout(()=> {
      tlHold.held=true;
      const go=()=> {
        if(beat)tlStep(i,key,d,'beat');
        else tlStep(i,key,d*fps);
        tlCutSheet(i)
      };
      go();
      tlHold.repeat=setInterval(go,450)
    },450)
  };
  sheet.onclick=e=> {
    const b=e.target.closest('[data-step],[data-x]');
    if(!b||b.disabled)return;
    const t=state.tl;
    if(b.dataset.step) {
      tlHoldStop();
      const key=b.dataset.step,d=+b.dataset.d;
      const beat=!e.altKey&&(key==='tail'||key==='head')&&tlBeatSteps(tlPlace().places,i);
      if(!tlHold.held)tlStep(i,key,beat?d:d*(e.shiftKey?fps:1),beat?'beat':'frame');
      tlHold.held=false;
      return tlCutSheet(i)
    }
    const x=b.dataset.x,k=b.dataset.k,id=t.data.clips[i].id;
    if(x==='close')return tlCloseSheet();
    if(x==='insert')return tlInsertSheet(i);
    if(x==='act')return tlActSheet(null,i);
    if(x==='unit')t.frameSteps=k==='frame';
    if(x==='snap')tlSnapCut(i);
    if(x==='t')tlTransition(i,k);
    if(x==='dir')tlChange(data=> {
      data.clips[i].cut.direction=k
    },`${t.data.clips[i].cut.transition} ${k} into ${id}`);
    if(x==='jl') {
      const {places}=tlPlace();
      tlChange(data=> {
        const a=data.clips[i-1],b=data.clips[i];
        if(b.sound)delete b.sound.early;
        if(a.sound)delete a.sound.late;
        if(k==='J')(b.sound??={}).early=Math.min(fps,places[i].before);
        if(k==='L')(a.sound??={}).late=Math.min(fps,places[i-1].after)
      },k==='none'?`no J/L cut into ${id}`:`${k}-cut into ${id}`)
    }
    tlCutSheet(i)
  }
}
// The cut into clip i becomes transition k ('cut' for a hard cut). A transition starts the clip earlier
// and puts the cut at its middle, so on a reel the cuts that were on the beat go back on it. The cut's
// sound effect stays, but "auto" knows only a whip and a flash (timeline_file.AUTO_SOUNDS).
function tlTransition(i,k) {
  const fps=state.tl.fps,was=tlOnBeat(tlPlace().places),snd=state.tl.data.clips[i].cut?.sound;
  const lost=snd!=null&&(snd.sfx??snd)==='auto'&&k!=='whip'&&k!=='flash';
  tlChange(data=> {
    const c=data.clips[i],sound=lost||snd==null?{}:{sound:c.cut.sound};
    if(k==='cut') {
      if(sound.sound)c.cut={transition:'cut',...sound};
      else delete c.cut
    }
    else if(c.cut?.transition!==k) {
      const frames=c.cut?.frames||Math.max(2,Math.round(fps*(TL_LEN[k]||.5)));
      c.cut={transition:k,frames,...(k==='wipe'||k==='whip'?{direction:c.cut?.direction||'left'}:{}),...sound}
    }
    tlKeepOnBeat(data,i,was)
  },`${k} into ${state.tl.data.clips[i].id}${lost?' (its "auto" sound dropped: name one for a '+k+')':''}`)
}
// Puts the cut into clip i on the beat (timeline_file.snap_cuts, for one cut): the nearest, else the one
// on its other side, by trimming the end of the clip before it.
// The indexes of the clips whose cut into them is on the beat.
function tlOnBeat(places) {
  const g=tlGrid();
  return new Set(g?places.slice(1).filter(p=>!p.guess&&!g.off(tlCutAt(p))).map(p=>p.i):[])
}
// After a beat step, a transition or a new clip: the cuts from clip `from` on that were on the beat
// (`was`) go back on it, by the trims of the clip before each. A beat isn't always a whole number of
// frames, so moving everything after a cut by one can leave the next cut a frame off.
function tlKeepOnBeat(data,from,was) {
  const g=tlGrid(data);
  for(let j=from;g&&j<data.clips.length;j++) {
    const ps=tlPlace(data).places,p=ps[j],off=p.guess?0:g.off(tlCutAt(p)),a=data.clips[j-1];
    if(!was.has(j)||!off)continue;
    // Its tail first; what a tail can't give back, a footage clip's out (as far as its file goes),
    // then its head.
    const left=Math.max(0,-off-(a.tail||0)),out=tlFootage(a)?Math.min(left,ps[j-1].after):0;
    const tail=Math.max(0,(a.tail||0)+off),head=(a.head||0)-(left-out);
    if(head<0)continue;
    if(out)a.out+=out;
    for(const [k,v] of [['tail',tail],['head',head]]) {
      if(v)a[k]=v;
      else delete a[k]
    }
  }
}
function tlSnapCut(i) {
  const {places}=tlPlace(),g=tlGrid(),pa=places[i-1],pb=places[i],at=tlCutAt(pb);
  const room=pa.media==null&&!tlFootage(pa.c)?Infinity:pa.frames-1-(pa.c.cut?.frames||0)-(pb.c.cut?.frames||0);
  const near=g.snap(at),other=g.step(at,near>at?-1:1);
  // The cut moves by -delta of the trim: a longer tail moves it earlier.
  const fits=to=>(pa.c.tail||0)-(to-at)>=0&&at-to<=room;
  const to=fits(near)?near:fits(other)?other:null;
  if(to==null)return toast('This cut can\u2019t reach a beat from here: trim the clips either side of it.');
  const was=tlOnBeat(places);
  tlChange(data=> {
    const a=data.clips[i-1],v=(a.tail||0)-(to-at);
    if(v)a.tail=v;
    else delete a.tail;
    tlKeepOnBeat(data,i+1,was)
  },`put the cut into ${pb.c.id} on the beat`)
}
// A new clip's id: not in the timeline, nor a clip directory on main (one a removed clip left behind).
const tlNewId=(name,data)=> {
  const base=(name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'')||'clip').slice(0,60);
  const dirs=state.tl.dirs||[];
  let id=base,n=2;
  while(data.clips.some(c=>c.id===id)||dirs.includes(id))id=`${base}-${n++}`;
  return id
};
function tlAddFootage(i,source) {
  const fps=state.tl.fps,out=Math.floor((source.duration||0)*fps);
  if(out<1)return toast('That source has no length yet; try again in a moment.');
  // The cuts on the beat stay on it: the new clip's own (where the cut into clip i was) and those after.
  const was=new Set([...tlOnBeat(tlPlace().places)].flatMap(j=>j<i?[j]:j>i?[j+1]:[j,j+1]));
  tlChange(data=> {
    tlInsert(data,{id:tlNewId(source.name,data),footage:`sources/${source.name}.${source.ext}`,in:0,out},i);
    tlKeepOnBeat(data,Math.max(1,i),was)
  },`add footage ${source.name}`,()=>toast(`Footage “${source.name}” added as clip ${i+1}`));
  tlCloseSheet()
}
async function tlUploadFootage(i,file,status) {
  try {
    status.textContent=`Uploading ${file.name}…`;
    const record=await xhrUpload('sources',{video:state.video,filename:file.name},file,
      f=>status.textContent=`Uploading ${file.name}… ${Math.round(f*100)}%`);
    loadSources();
    tlAddFootage(i,record)
  }
  catch(e) {
    status.textContent=e.message
  }
}
// A whole-video note does not ask for planned clips: a clip note on one does.
const planNote=(clip,title,line)=>json('notes',null,{video:state.video,format:state.format,clip,
  text:`Make this planned clip${title?` (${title})`:''}: ${line||title}`}).then(loadNotes);
// A planned clip: a clip directory with a placeholder card (film_setup.planned_clip), written with
// the timeline that names it (POST api/timeline `plans`). "Make it now" also sends a note on it.
function tlPlanClip(i,title,line,now) {
  let id=null;
  const was=new Set([...tlOnBeat(tlPlace().places)].flatMap(j=>j<i?[j]:j>i?[j+1]:[j,j+1]));
  const done=()=> {
    toast(`Clip ${i+1} planned${now?': the builder is making it':'. A note on it has the builder make it'}`);
    if(now)planNote(id,title,line).catch(e=>toast(e.message))
  };
  tlChange(data=> {
    id=tlNewId(title||line.split(/\s+/).slice(0,6).join(' '),data);
    tlInsert(data,{id,dir:`clips/${id}`},i);
    tlKeepOnBeat(data,Math.max(1,i),was)
  },`plan clip ${title||'new'}`,done);
  (state.tl.plans??={})[id]={title,line};
  tlCloseSheet()
}
async function tlInsertSheet(i) {
  const t=state.tl,a=t.data.clips[i-1],b=t.data.clips[i];
  const where=!a?'first':b?`between ${i}. ${tlTitle(a)} and ${i+1}. ${tlTitle(b)}`:`after ${i}. ${tlTitle(a)}`;
  const sheet=tlOpenSheet(`<div class="tl-cutsheet"><h3>New clip ${esc(where)}</h3><div class="tl-sec">Plan a clip`+
    `</div><p class="tl-sub">A title and a line. It shows as a card with them until the builder makes it.</p>`+
    `<label class="sr-only" for="tl-plan-title">Title of the new clip</label><input id="tl-plan-title" `+
    `class="tl-field" maxlength="200" placeholder="Title"><label class="sr-only" for="tl-new-text">What happens `+
    `in the new clip</label><textarea id="tl-new-text" rows="3" placeholder="What happens in it…"></textarea>`+
    `<div class="tl-sheet-foot"><button class="tl-btn" data-x="close">Cancel</button><button class="tl-btn" `+
    `data-x="plan">Plan it</button><button class="tl-btn accent" data-x="send">Make it now</button></div>`+
    `<div class="tl-sec">Or add footage</div><div class="tl-drop" id="tl-drop">${svg(TL_ICON.clip,18)}Drop a video `+
    `file here, or <button data-x="pick">choose one</button></div><input id="tl-file" type="file" `+
    `accept=".mp4,.mov,.webm" hidden><p class="tl-sub" id="tl-up"></p><div id="tl-sources"></div></div>`,
  'Insert a clip');
  sheet.querySelector('#tl-plan-title').focus();
  const status=sheet.querySelector('#tl-up'),drop=sheet.querySelector('#tl-drop');
  drop.ondragover=e=> {
    e.preventDefault();
    drop.classList.add('over')
  };
  drop.ondragleave=()=>drop.classList.remove('over');
  drop.ondrop=e=> {
    e.preventDefault();
    const f=e.dataTransfer.files[0];
    if(f)tlUploadFootage(i,f,status)
  };
  sheet.querySelector('#tl-file').onchange=e=>e.target.files[0]&&tlUploadFootage(i,e.target.files[0],status);
  sheet.onclick=async e=> {
    const btn=e.target.closest('[data-x]');
    if(!btn)return;
    const x=btn.dataset.x;
    if(x==='close')return tlCloseSheet();
    if(x==='pick')return sheet.querySelector('#tl-file').click();
    if(x==='source')return tlAddFootage(i,state.sources.find(s=>s.name===btn.dataset.k));
    if(x==='plan'||x==='send') {
      const title=sheet.querySelector('#tl-plan-title').value.trim(),line=sheet.querySelector('textarea').value.trim();
      if(!title&&!line)return sheet.querySelector(title?'textarea':'#tl-plan-title').focus();
      if(!await ensureName())return;
      tlPlanClip(i,title,line,x==='send')
    }
  };
  try {
    await loadSources();
  } catch (_) {
    // The list is a convenience; dropping a file still works.
  }
  const usable=(state.sources||[]).filter(s=>s.duration&&s.width);
  if(usable.length&&sheet.isConnected)sheet.querySelector('#tl-sources').innerHTML=`<p class="tl-sub">Or one `+
    `of this video’s sources:</p>`+usable.map(s=>`<button class="tl-opt" data-x="source" data-k="${esc(s.name)}">`+
    `<span class="tl-ico">${svg(TL_ICON.clip,16)}</span><span><b>${esc(s.name)}</b><small>${esc(s.ext)} · `+
    `${Math.round(s.duration)} s</small></span></button>`).join('')
}
async function tlLaneSheet(k) {
  const t=state.tl,lane=t.data.lanes[k],n=k+1;
  const items=(lane.items||[]).map(it=>esc(tlItemName(it))).join(', ')||'Empty';
  const sheet=tlOpenSheet(`<div class="tl-cutsheet"><h3>Audio ${n}</h3><p class="tl-sub">${items}</p>`+
    tlOpt('data-x="add"',false,svg(TL_ICON.plus,16),'Add a sound','From this video’s sources, where the '+
      (tlNoteClip()?'selected clip starts':'video starts'))+'<div id="tl-lane-sources"></div>'+
    tlOpt('data-x="duck"',!!lane.duck,svg(TL_ICON.duck,16),'Dip under speech','Quieter wherever a clip speaks')+
    tlOpt('data-x="mute"',!!lane.mute,svg(TL_ICON.muted,16),lane.mute?'Muted':'Mute this lane',
      'Kept on the timeline, left out of the sound')+
    tlOpt('data-x="remove"',false,svg(TL_ICON.trash,16),`Remove Audio ${n}`,lane.items?.length?
      'Its sounds are removed too':'It’s empty')+
    `<div class="tl-sheet-foot"><button class="tl-btn" data-x="close">Done</button></div></div>`,`Audio ${n}`);
  sheet.onclick=async e=> {
    const b=e.target.closest('[data-x]');
    if(!b)return;
    const x=b.dataset.x;
    if(x==='close')return tlCloseSheet();
    if(x==='duck'||x==='mute') {
      tlChange(data=> {
        const l=data.lanes[k];
        if(l[x]) {
          delete l[x];
          if(x==='duck')delete l.duck_db
        }
        else l[x]=true
      },`${x==='duck'?'dip':'mute'} Audio ${n}${lane[x]?' off':''}`);
      return tlLaneSheet(k)
    }
    if(x==='remove') {
      tlCloseSheet();
      tlChange(data=> {
        data.lanes.splice(k,1);
        // The beat grid names its song's lane by position: it goes with the song, and follows a later lane.
        if(data.beats?.lane===k+1)delete data.beats;
        else if(data.beats?.lane>k+1)data.beats.lane--
      },`remove Audio ${n}`,undo=>tlUndoToast(`Audio ${n} removed`,undo,`bring back Audio ${n}`));
      return
    }
    if(x==='add') {
      const box=sheet.querySelector('#tl-lane-sources');
      box.textContent='Loading sources…';
      try {
        await loadSources()
      } catch (_) {
        // Shown as no sources below.
      }
      const usable=(state.sources||[]).filter(s=>s.has_audio&&s.duration);
      box.innerHTML=usable.map(s=>`<button class="tl-opt" data-x="sound" data-k="${esc(s.name)}">`+
        `<span class="tl-ico">${svg(TL_ICON.music,16)}</span><span><b>${esc(s.name)}</b>`+
        `<small>${Math.round(s.duration)} s</small></span></button>`).join('')+
        tlOpt('data-x="upload"',false,svg(TL_ICON.plus,16),'Upload a song or sound','An audio file, or a video '+
          'with sound; it joins this video’s sources')+'<input id="tl-lane-file" type="file" accept=".mp3,.m4a,'+
        '.wav,.aac,.ogg,.mp4,.mov,.webm" hidden><p class="tl-sub" id="tl-lane-up"></p>';
      box.querySelector('#tl-lane-file').onchange=async e=> {
        const file=e.target.files[0],up=box.querySelector('#tl-lane-up');
        if(!file)return;
        try {
          const s=await xhrUpload('sources',{video:state.video,filename:file.name},file,
            f=>up.textContent=`Uploading ${file.name}… ${Math.round(f*100)}%`);
          loadSources();
          if(!s.has_audio)return up.textContent=`${file.name} has no sound to play.`;
          tlLaneAdd(k,s)
        }
        catch(err) {
          up.textContent=err.message
        }
      };
      return
    }
    if(x==='upload')return sheet.querySelector('#tl-lane-file').click();
    if(x==='sound')tlLaneAdd(k,state.sources.find(v=>v.name===b.dataset.k))
  }
}
// A sound from the video's sources onto Audio k+1: where the selected clip starts, else at the start.
function tlLaneAdd(k,s) {
  const t=state.tl,{places,total}=tlPlace(),n=k+1;
  const at=tlNoteClip()?places.find(p=>p.c.id===t.sel).start:0;
  const frames=Math.max(1,Math.min(Math.floor(s.duration*t.fps),total-at));
  tlChange(data=> {
    data.lanes[k].items=[...data.lanes[k].items||[],{sound:`sources/${s.name}.${s.ext}`,at,frames}]
  },`add ${s.name} to Audio ${n}`);
  tlCloseSheet()
}
// An act's sheet: rename it or take it away (its clips stay). With `from` (a clip's index) instead of
// an act, a new act starting at that clip: it runs to the end of the act the clip was in (splitting
// it), or, outside any act, up to the next act.
function tlActSheet(k,from) {
  const t=state.tl,acts=t.data.acts||[],fresh=k==null;
  if(fresh) {
    const id=t.data.clips[from].id,j=acts.findIndex(a=>a.clips[0]===id);
    if(j>=0)return tlActSheet(j)
  }
  const a=fresh?null:acts[k],head=fresh?`New act from clip ${from+1}`:`Act ${k+1}`;
  const sheet=tlOpenSheet(`<div class="tl-cutsheet"><h3>${esc(head)}</h3><label class="tl-sub" for="tl-act-title">`+
    `Title</label><input id="tl-act-title" class="tl-field" maxlength="200" value="${esc(a?.title||'')}" `+
    `placeholder="${fresh?'The river':''}">${fresh?'':tlOpt('data-x="remove"',false,svg(TL_ICON.trash,16),
      'Remove this act','Its clips stay where they are')}<div class="tl-sheet-foot"><button class="tl-btn" `+
    `data-x="close">Cancel</button><button class="tl-btn accent" data-x="save">${fresh?'Add the act':'Save'}`+
    `</button></div></div>`,head);
  const input=sheet.querySelector('input');
  input.focus();
  input.select();
  input.onkeydown=e=>e.key==='Enter'&&sheet.querySelector('[data-x="save"]').click();
  sheet.onclick=e=> {
    const x=e.target.closest('[data-x]')?.dataset.x;
    if(x==='close')return tlCloseSheet();
    if(x==='remove') {
      tlCloseSheet();
      return tlChange(data=> {
        data.acts.splice(k,1)
      },`remove act ${a.title}`,undo=>tlUndoToast(`Act ${k+1} removed`,undo,`bring back act ${a.title}`))
    }
    if(x!=='save')return;
    const title=input.value.trim();
    if(!title)return input.focus();
    tlCloseSheet();
    if(!fresh)return tlChange(data=> {
      data.acts[k].title=title
    },`rename act ${k+1} to ${title}`);
    tlChange(data=> {
      const acts=data.acts??=[],ids=data.clips.map(c=>c.id),id=ids[from];
      const j=acts.findIndex(x=>x.clips.includes(id));
      let run=[];
      if(j>=0)run=acts[j].clips.splice(acts[j].clips.indexOf(id));
      else {
        const inAct=new Set(acts.flatMap(x=>x.clips));
        for(let m=from;m<ids.length&&!inAct.has(ids[m]);m++)run.push(ids[m])
      }
      acts.push({title,clips:run});
      acts.sort((p,q)=>ids.indexOf(p.clips[0])-ids.indexOf(q.clips[0]))
    },`start act ${title}`)
  }
}
// ---- Timeline: moving clips, zoom and the strip's own events ----
// The act a clip put in at `to` (moved or new) lands in is its left neighbour's (else its right
// one's), so every act stays a run of consecutive clips.
function tlInsert(data,c,to) {
  const actOf=new Map();
  (data.acts||[]).forEach((a,k)=>a.clips.forEach(x=>actOf.set(x,k)));
  data.clips.splice(to,0,c);
  if(data.acts) {
    const left=data.clips[to-1],right=data.clips[to+1];
    const k=left&&actOf.has(left.id)?actOf.get(left.id):right&&actOf.has(right.id)?actOf.get(right.id):undefined;
    if(k===undefined)actOf.delete(c.id);
    else actOf.set(c.id,k);
    data.acts=data.acts.map((a,j)=>({...a,clips:data.clips.filter(x=>actOf.get(x.id)===j).map(x=>x.id)}))
      .filter(a=>a.clips.length)
  }
}
function tlMove(data,id,to) {
  const [c]=data.clips.splice(data.clips.findIndex(c=>c.id===id),1);
  tlInsert(data,c,to)
}
function tlMoveTo(id,to) {
  const from=state.tl.data.clips.findIndex(c=>c.id===id);
  if(to===from)return;
  // On a reel the cuts stay on the beat: one between the same two clips as before keeps its place
  // on or off it; the three the move makes (either side of the clip, and where it left) are on it
  // if a cut into or out of the clip was.
  const clips=state.tl.data.clips,prev=new Map(clips.map((c,j)=>[c.id,clips[j-1]?.id]));
  const on=new Set([...tlOnBeat(tlPlace().places)].map(j=>clips[j].id));
  const moved=on.has(id)||on.has(clips[from+1]?.id);
  tlChange(data=> {
    tlMove(data,id,to);
    const was=new Set(data.clips.flatMap((c,j)=>!j?[]:
      (c.id!==id&&prev.get(c.id)===data.clips[j-1].id?on.has(c.id):moved)?[j]:[]));
    tlKeepOnBeat(data,1,was)
  },`move ${id} to ${to+1}`)
}
let tlDrag=null;
function tlWire(sc) {
  const pts=new Map();
  let d0=0,z0=0;
  sc.addEventListener('pointerdown',e=> {
    if(e.pointerType!=='touch')return;
    pts.set(e.pointerId,e.clientX);
    if(pts.size===2) {
      const [a,b]=[...pts.values()];
      d0=Math.abs(a-b);
      z0=tlZoom(tlPlace().total)
    }
  });
  sc.addEventListener('pointermove',e=> {
    if(!pts.has(e.pointerId))return;
    pts.set(e.pointerId,e.clientX);
    if(pts.size===2&&d0>20) {
      const [a,b]=[...pts.values()],total=tlPlace().total;
      state.tl.z=Math.max(tlFit(total)*.5,Math.min(40,z0*Math.abs(a-b)/d0))
    }
  });
  const end=e=> {
    if(pts.delete(e.pointerId)&&pts.size<2&&d0) {
      d0=0;
      renderTimeline()
    }
  };
  sc.addEventListener('pointerup',end);
  sc.addEventListener('pointercancel',end);
  sc.addEventListener('wheel',e=> {
    if(!e.ctrlKey)return;
    e.preventDefault();
    tlZoomBy(e.deltaY<0?1.15:.87)
  },{passive:false});
  // Once a drag has begun (a long press on touch), the strip must not scroll under it.
  sc.addEventListener('touchmove',e=> {
    if(tlDrag?.active)e.preventDefault()
  },{passive:false});
  $('tl-clips').addEventListener('pointerdown',tlDragStart)
}
function tlZoomBy(f) {
  const t=state.tl,total=tlPlace().total;
  t.z=Math.max(tlFit(total)*.5,Math.min(40,tlZoom(total)*f));
  renderTimeline()
}
function tlDragStart(e) {
  const blk=e.target.closest('.tl-blk');
  if(!blk||e.button>0)return;
  const x0=e.clientX,touch=e.pointerType==='touch',id=blk.dataset.id;
  const drag=tlDrag={id,active:false,moved:false};
  let timer=null,marker=null;
  const begin=()=> {
    drag.active=true;
    blk.classList.add('dragging');
    marker=node('i','tl-dropmark');
    $('tl-clips').append(marker)
  };
  const target=ev=> {
    const {places,total}=tlPlace(),z=tlZoom(total);
    const x=(ev.clientX-$('tl-track').getBoundingClientRect().left)/z;
    const others=places.filter(p=>p.c.id!==id);
    const to=others.filter(p=>p.start+p.frames/2<x).length;
    return {to,at:to<others.length?others[to].start*z:places.at(-1).end*z}
  };
  const move=ev=> {
    if(!drag.active) {
      if(Math.abs(ev.clientX-x0)<6)return;
      if(touch)return cleanup();
      begin()
    }
    ev.preventDefault();
    drag.moved=true;
    blk.style.transform=`translateX(${ev.clientX-x0}px)`;
    marker.style.left=`${target(ev).at}px`
  };
  const up=ev=> {
    const done=drag.active&&drag.moved;
    cleanup();
    if(done) {
      blk.addEventListener('click',x=>x.stopPropagation(),{capture:true,once:true});
      tlMoveTo(id,target(ev).to)
    }
  };
  function cleanup() {
    clearTimeout(timer);
    window.removeEventListener('pointermove',move);
    window.removeEventListener('pointerup',up);
    window.removeEventListener('pointercancel',cleanup);
    blk.classList.remove('dragging');
    blk.style.transform='';
    marker?.remove();
    setTimeout(()=>tlDrag===drag&&(tlDrag=null),0)
  }
  if(touch)timer=setTimeout(begin,400);
  window.addEventListener('pointermove',move);
  window.addEventListener('pointerup',up);
  window.addEventListener('pointercancel',cleanup)
}
const TL_ACT={
  toggle() {
    const t=state.tl;
    t.open=!t.open;
    t.recenter=true;
    renderTimeline();
    resizePlayer();
    if(t.open&&!tlPhone())$('timeline').scrollIntoView({block:'nearest'})
  },
  pick(b) {
    if(tlDrag?.moved)return;
    tlPick(b.dataset.id)
  },
  cut(b) {
    tlCutSheet(+b.dataset.i)
  },
  lane(b) {
    tlLaneSheet(+b.dataset.k)
  },
  append() {
    tlInsertSheet(state.tl.data.clips.length)
  },
  act(b) {
    tlActSheet(+b.dataset.k)
  },
  newact() {
    const t=state.tl;
    tlActSheet(null,Math.max(0,t.data.clips.findIndex(c=>c.id===t.sel)))
  },
  details() {
    openFilmDetails()
  },
  zoom(b) {
    state.tl.recenter=true;
    tlZoomBy(+b.dataset.d)
  },
  fit() {
    state.tl.z=null;
    renderTimeline()
  },
  addlane() {
    const n=(state.tl.data.lanes||[]).length+1;
    state.tl.newLane=n-1;
    tlChange(data=> {
      (data.lanes??=[]).push({items:[]})
    },`add Audio ${n}`,()=>toast(`Audio ${n} added. Add a sound from its menu, or describe one in a note.`))
  },
  seek(b,e) {
    if(!state.videoReady)return;
    const {total}=tlPlace(),z=tlZoom(total);
    const f=(e.clientX-$('tl-track').getBoundingClientRect().left)/z;
    if(tlNoteClip())return tlPick(state.tl.sel,true);
    player.currentTime=Math.max(0,f/state.tl.fps)
  }
};
$('timeline').onclick=e=> {
  const b=e.target.closest('[data-tl]');
  if(b)TL_ACT[b.dataset.tl]?.(b,e)
};
$('timeline').onkeydown=e=> {
  // Alt+arrows move the focused clip: the keyboard's drag.
  const b=e.target.closest?.('.tl-blk');
  if(!b||!e.altKey||!['ArrowLeft','ArrowRight'].includes(e.key))return;
  e.preventDefault();
  const clips=state.tl.data.clips,from=clips.findIndex(c=>c.id===b.dataset.id);
  const to=Math.max(0,Math.min(clips.length-1,from+(e.key==='ArrowLeft'?-1:1)));
  tlMoveTo(b.dataset.id,to);
  requestAnimationFrame(()=>document.querySelector(`.tl-blk[data-id="${CSS.escape(b.dataset.id)}"]`)?.focus())
};
$('tl-shade').onclick=e=> {
  if(e.target===$('tl-shade'))tlCloseSheet()
};
document.addEventListener('keydown',e=> {
  if(e.key==='Escape'&&!$('tl-shade').hidden)tlCloseSheet()
});
$('scope-clip').onclick=()=> {
  const t=state.tl;
  if(t)tlPick(t.sel||t.data.clips[0].id)
};
$('scope-whole').onclick=()=> {
  const t=state.tl;
  if(t&&!t.whole)tlPick(t.sel,true)
};
window.addEventListener('resize',()=> {
  if(state.tl?.open)renderTimeline()
});
// ---- Adding footage: a video file dropped on the timeline, or "Add as a clip" in the composer ----
const isFootage=f=>/\.(mp4|mov|webm)$/i.test(f.name||'');
// A source becomes a clip at the end of the film; a video not built yet becomes a film of clips with
// it as its first clip (film_api.start).
async function addAsClip(file,say) {
  if(!await ensureName())return;
  const record=await xhrUpload('sources',{video:state.video,filename:file.name},file,
    f=>say(`Uploading ${file.name}… ${Math.round(f*100)}%`));
  loadSources();
  if(state.tl)return tlAddFootage(state.tl.data.clips.length,record);
  say('');
  await filmStart({footage:record.name})
}
// Whether a video file can go in as a clip rather than an attachment: on a film of clips, or a video
// not built yet (which it makes a film of clips).
const canAddClip=()=>!!state.tl||(notBuilt(currentVersion())&&!state.notes.length);
async function filmStart(body) {
  const r=await json('film/start',null,{video:state.video,...body});
  tlCloseSheet();
  toast(`A film of clips now: open the timeline to add more · v${r.n}`);
  await loadVersions();
  await loadTimeline(true);
  if(state.tl&&!state.tl.open)TL_ACT.toggle()
}
$('timeline').ondragover=e=> {
  if(state.tl&&e.dataTransfer?.types.includes('Files')) {
    e.preventDefault();
    e.dataTransfer.dropEffect='copy'
  }
};
$('timeline').ondrop=e=> {
  const file=[...e.dataTransfer?.files||[]].find(isFootage);
  if(!state.tl||!file)return;
  e.preventDefault();
  addAsClip(file,tlSetStatus).catch(err=>toast(err.message))
};
// ---- Film details: the look, length, world and characters every clip follows (film_api.py) ----
// A sheet behind quiet links (the not-built-yet message, Sources, the timeline's tools). Save writes
// the bible as one version; nothing in it renders. A video not built yet can also start as a film of
// clips here, with footage of its own or a planned clip for the builder to make.
const FD_ICON={x:'<path d="M6 6l12 12M18 6L6 18"/>',person:'<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4.5 '+
  '4.5-6.5 8-6.5s7 2 8 6.5"/>',picture:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" '+
  'r="2"/><path d="M21 16l-5-5-9 9"/>',note:'<path d="M5 4h14v12l-4 4H5z"/><path d="M15 20v-4h4M8 9h8M8 13h5"/>'};
let fdLooks=null;
// The whole-video looks the suggestions picker shows (api/suggest/catalog), one per vb.looks name.
async function fdLoadLooks() {
  if(fdLooks)return fdLooks;
  try {
    const seen=new Set();
    fdLooks=((await json('suggest/catalog'))?.looks||[])
      .filter(l=>l.look&&l.kind!=='filter'&&!seen.has(l.look)&&seen.add(l.look))
  } catch (_) {
    fdLooks=[]
  }
  return fdLooks
}
async function openFilmDetails() {
  const sheet=tlOpenSheet('<div class="tl-cutsheet fd"><h3>Film details</h3><p class="tl-sub">Loading…</p></div>',
    'Film details');
  try {
    const [r]=await Promise.all([json('film',{video:state.video}),fdLoadLooks()]);
    state.fd=null;
    fdTake(r);
    if(!sheet.isConnected)return;
    fdRender();
    // The look chosen, in view in its row.
    const on=document.querySelector('.fd-look[aria-pressed=true]');
    if(on)on.parentElement.scrollLeft=on.offsetLeft-on.parentElement.offsetLeft-8
  } catch(e) {
    if(sheet.isConnected)sheet.querySelector('.tl-sub').textContent=e.message
  }
}
// In place: the open sheet's handlers keep their hold on it.
function fdTake(r) {
  const d=r.details;
  state.fd=Object.assign(state.fd||{},{base:r.commit,unbuilt:r.unbuilt,film:r.film,look:d.look,
    length:d.length||'',world:d.world||'',
    chars:d.characters.map(c=>({slug:c.slug,name:c.name,description:c.description,keep:[...c.pictures],add:[]}))})
}
const fdUrl=file=>file.fdUrl??=URL.createObjectURL(file);
function fdRender(focus) {
  const f=state.fd,old=document.querySelector('.tl-sheet');
  const top=old?.scrollTop||0;
  const looks=[['','None','The builder picks'],['as-shot','As shot','Footage keeps its own look'],
    ...fdLooks.map(l=>[l.look,l.title,'',l.poster])];
  const look=looks.map(([id,title,d,poster])=>`<button type="button" class="fd-look" data-x="look" `+
    `data-k="${esc(id)}" aria-pressed="${(f.look||'')===id}">`+
    `${poster?`<img src="${esc(poster)}" alt="" loading="lazy">`:`<span class="fd-plain">${esc(d)}</span>`}`+
    `<b>${esc(title)}</b></button>`).join('');
  const pic=(src,i,kind,k)=>`<span class="fd-pic"><img src="${esc(src)}" alt=""><button type="button" `+
    `data-x="unpic" data-i="${i}" data-kind="${kind}" data-k="${k}" aria-label="Remove this picture">`+
    `${svg(FD_ICON.x,14)}</button></span>`;
  const chars=f.chars.map((c,i)=>`<div class="fd-char"><div class="fd-row"><span class="fd-ava">`+
    `${svg(FD_ICON.person,18)}</span><input class="tl-field" data-f="name" data-i="${i}" maxlength="80" `+
    `value="${esc(c.name)}" placeholder="Name" aria-label="Character ${i+1}: name"><button type="button" `+
    `class="tl-icon" data-x="drop" data-i="${i}" aria-label="Remove ${esc(c.name||`character ${i+1}`)}">`+
    `${svg(TL_ICON.trash,16)}</button></div><textarea data-f="description" data-i="${i}" rows="2" `+
    `placeholder="Who they are, how they look and sound…" aria-label="Character ${i+1}: description">`+
    `${esc(c.description)}</textarea><div class="fd-pics">`+
    c.keep.map(n=>pic(api('film/picture',{video:state.video,name:n}),i,'keep',n)).join('')+
    c.add.map((file,j)=>pic(fdUrl(file),i,'add',j)).join('')+`<button type="button" class="fd-addpic" `+
    `data-x="pic" data-i="${i}">${svg(FD_ICON.picture,16)}Picture</button></div></div>`).join('');
  const start=f.unbuilt&&!f.film?`<div class="tl-sec">Start with clips</div><p class="tl-sub">Makes this video a `+
    `film of clips right away, with a timeline to add more.</p>`+
    tlOpt('data-x="footage"',false,svg(TL_ICON.clip,16),'Add footage','A video file of your own, the first clip')+
    tlOpt('data-x="plan"',false,svg(FD_ICON.note,16),'Plan a clip','A title and a line; the builder makes it')+
    `<div class="fd-plan" id="fd-plan" hidden><input class="tl-field" id="fd-plan-title" maxlength="200" `+
    `placeholder="Title" aria-label="Title of the clip"><textarea id="fd-plan-line" rows="2" placeholder="What `+
    `happens in it…" aria-label="What happens in the clip"></textarea><div class="tl-sheet-foot"><button `+
    `class="tl-btn" data-x="planadd">Plan it</button><button class="tl-btn accent" data-x="planadd" `+
    `data-now="1">Make it now</button></div></div><p class="tl-sub" id="fd-clip-up"></p>`:'';
  const sheet=tlOpenSheet(`<div class="tl-cutsheet fd"><h3>Film details</h3><p class="tl-sub">What every clip `+
    `follows. Save keeps them as one version.</p><div class="tl-sec">Look</div><div class="fd-looks" role="group" `+
    `aria-label="Look">${look}</div><div class="tl-sec"><label for="fd-length">Length</label></div><input `+
    `class="tl-field fd-len" id="fd-length" data-f="length" maxlength="80" value="${esc(f.length)}" `+
    `placeholder="About how long: 0:30, 2:30…"><div class="tl-sec"><label for="fd-world">World</label></div>`+
    `<textarea id="fd-world" data-f="world" rows="3" placeholder="Where and when it happens, and how it feels…">`+
    `${esc(f.world)}</textarea><div class="tl-sec">Characters</div>${chars}<button type="button" `+
    `class="tl-btn fd-add" data-x="addchar">${svg(TL_ICON.plus,16)}Add a character</button>${start}`+
    `<input type="file" id="fd-file" accept=".png,.jpg,.jpeg,.webp,.gif" multiple hidden><input type="file" `+
    `id="fd-footage" accept=".mp4,.mov,.webm" hidden><p class="tl-sub fd-status" id="fd-status" role="status">`+
    `</p><div class="tl-sheet-foot fd-foot"><button class="tl-btn" data-x="close">Cancel</button><button `+
    `class="tl-btn accent" data-x="save">Save</button></div></div>`,'Film details');
  sheet.scrollTop=top;
  if(focus)sheet.querySelector(focus)?.focus();
  fdWire(sheet)
}
function fdWire(sheet) {
  const f=state.fd,say=(t,id='fd-status')=>sheet.querySelector('#'+id)&&(sheet.querySelector('#'+id).textContent=t);
  sheet.oninput=e=> {
    const el=e.target,k=el.dataset.f;
    if(!k)return;
    if(el.dataset.i!=null)f.chars[+el.dataset.i][k]=el.value;
    else f[k]=el.value
  };
  let picFor=0;
  sheet.querySelector('#fd-file').onchange=e=> {
    f.chars[picFor].add.push(...e.target.files);
    fdRender()
  };
  // Starting with a clip closes the sheet: what is typed above is saved first, not lost.
  const start=async go=> {
    const to=t=>say(t,'fd-clip-up');
    try {
      if(await fdCommit(to))await go(to)
    }
    catch(err) {
      to(err.message)
    }
  };
  sheet.querySelector('#fd-footage').onchange=e=> {
    const file=e.target.files[0];
    if(file)start(to=>addAsClip(file,to))
  };
  sheet.onclick=async e=> {
    const b=e.target.closest('[data-x]');
    if(!b)return;
    const x=b.dataset.x,i=+b.dataset.i;
    if(x==='close')return tlCloseSheet();
    if(x==='look') {
      f.look=b.dataset.k||null;
      for(const o of sheet.querySelectorAll('.fd-look'))o.setAttribute('aria-pressed',o===b)
    }
    if(x==='addchar') {
      f.chars.push({slug:null,name:'',description:'',keep:[],add:[]});
      fdRender(`[data-f="name"][data-i="${f.chars.length-1}"]`)
    }
    if(x==='drop') {
      f.chars.splice(i,1);
      fdRender()
    }
    if(x==='pic') {
      picFor=i;
      sheet.querySelector('#fd-file').click()
    }
    if(x==='unpic') {
      const c=f.chars[i];
      if(b.dataset.kind==='keep')c.keep=c.keep.filter(n=>n!==b.dataset.k);
      else c.add.splice(+b.dataset.k,1);
      fdRender()
    }
    if(x==='footage')sheet.querySelector('#fd-footage').click();
    if(x==='plan') {
      sheet.querySelector('#fd-plan').hidden=false;
      sheet.querySelector('#fd-plan-title').focus()
    }
    if(x==='planadd') {
      const title=sheet.querySelector('#fd-plan-title').value.trim();
      const line=sheet.querySelector('#fd-plan-line').value.trim();
      if(!title&&!line)return sheet.querySelector('#fd-plan-title').focus();
      b.disabled=true;
      // The film's one clip is the planned one; only a note on it has the builder make it.
      await start(async()=> {
        await filmStart({plan:{title,line}});
        if(b.dataset.now)await planNote(state.tl.data.clips[0].id,title,line).catch(err=>toast(err.message))
      });
      b.disabled=false
    }
    if(x==='save')fdSave(b,say)
  }
}
// Saves the sheet as one version (none when nothing changed): the POST api/film body, or null when the
// video still has no name.
async function fdCommit(say) {
  const f=state.fd;
  if(f.chars.some(c=>!c.name.trim()))throw new Error('Every character needs a name.');
  if(!await ensureName())return null;
  const characters=[];
  for(const c of f.chars) {
    const add=[];
    for(const file of c.add) {
      say(`Uploading ${file.name}…`);
      add.push((await xhrUpload('attachments',{video:state.video,name:file.name},file,()=> {
      })).id)
    }
    characters.push({...c.slug?{slug:c.slug}:{},name:c.name,description:c.description,keep:c.keep,add})
  }
  say('Saving…');
  const r=await json('film',null,{video:state.video,base:f.base,look:f.look,length:f.length,world:f.world,
    characters});
  // As saved: a retry after a failed start sends nothing twice.
  fdTake(r);
  if(r.changed)loadVersions();
  say('');
  return r
}
async function fdSave(btn,say) {
  btn.disabled=true;
  try {
    const r=await fdCommit(say);
    if(!r)return btn.disabled=false;
    tlCloseSheet();
    toast(r.changed?`Film details saved · v${r.n}`:'Nothing changed')
  }
  catch(e) {
    say(e.message);
    btn.disabled=false
  }
}
for(const id of ['blank-details','sources-details'])$(id).onclick=openFilmDetails;
// The builder reads the details only on a film of clips (each clip's brief) or in a first note still
// to come (film_setup.note_lines): on a video built as one film, Save would change nothing it sees.
function fdShowLink() {
  $('sources-details').hidden=!canAddClip()
}
// ---- Startup and periodic polling ----
stampLabel();
init();
let lastNotesPoll=0;
setInterval(()=> {
  const fast=!document.hidden && (
    state.notes.some(n=>['gathering','queued','working'].includes(n.state)) ||
    window.innerWidth>700 || $('panel').classList.contains('open'));
  if(state.video&&!state.signedOut&&!state.restarting&&Date.now()-lastNotesPoll>=(fast?3000:15000)) {
    lastNotesPoll=Date.now();
    loadNotes();
  }
},1000);
setInterval(()=> {
  if(state.video&&!state.signedOut&&!state.restarting)loadVersions()
},15000);
// A film of clips: fast while a clip renders, slow otherwise (the builder may change the file too).
let lastTimelinePoll=0;
setInterval(()=> {
  const t=state.tl,busy=t?.clips.some(c=>!['ready','missing','failed'].includes(c.state));
  if(!t||document.hidden||state.signedOut||state.restarting)return;
  if(Date.now()-lastTimelinePoll>=(busy?4000:15000)) {
    lastTimelinePoll=Date.now();
    loadTimeline()
  }
},1000);
setInterval(()=> {
  if(document.hidden||state.signedOut||state.restarting)return;
  for(const note of state.notes) {
    const data=state.steps[note.id];
    if(data&&!data.done&&(data.open||(note.state==='working'&&note.handle)))loadSteps(note)
  }
},3000);
setInterval(()=> {
  if(document.hidden||state.signedOut||state.restarting||state.view!=='sources')return;
  if((state.sources||[]).some(s=>!s.preview_ready))loadSources()
},3000);
// /api/project syncs with the forge, so poll the cheap /healthz and refetch the
// project only when the editor's version changes (a deploy), for the upgrade chip.
async function checkEditorVersion() {
  if(document.hidden||!state.project||state.signedOut||state.restarting)return;
  try {
    const text=await (await fetch('/healthz')).text();
    const version=text.startsWith('ok ')?text.slice(3).trim():null;
    if(!version||version===state.project.version)return;
    state.project=await json('project');
    renderUpgrade()
  } catch (_) {
    // A restarting editor; the next check catches up.
  }
}
setInterval(checkEditorVersion,60000);
// A sign-in window beside this one never hides it, so focus must also wake it.
window.addEventListener('focus', resumeFromSignedOut);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    state.resumeOnVisible=!player.paused;
    player.pause();
    if (state.renderTimer) {
      clearTimeout(state.renderTimer);
      state.renderTimer=setTimeout(()=>loadPlayer(),15000);
    }
    return;
  }
  if (state.signedOut) {
    resumeFromSignedOut();
    return;
  }
  // waitForEditor catches up once it is back.
  if (state.restarting) return;
  if (state.renderTimer) {
    clearTimeout(state.renderTimer);
    loadPlayer();
  }
  lastNotesPoll=Date.now();
  loadNotes();
  loadVersions();
  checkEditorVersion();
  if (state.resumeOnVisible && state.videoReady) player.play().catch(()=>{});
  state.resumeOnVisible=false;
});
