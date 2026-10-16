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
function formatInfo() {
  return state.info?.formats.find(f=>f.name===state.format)
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
  const label=v.kind==='blank'?'Not built yet':`v${v.n} · ${relative(v.time)}`;
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
  $('phone-format').textContent=state.format.replace('x',':');
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
  const url=videoUrl();
  const poster=frameUrl();
  player.poster=poster;
  $('poster').src=poster;
  const v=currentVersion();
  $('building').hidden=true;
  $('render-status').classList.remove('calm');
  if(v?.kind==='blank') {
    showBlank();
    return
  }
  if(retry) {
    try {
      await json('video/retry',null, {
        video:state.video,commit:state.commit,format:state.format
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
  $('render-text').textContent=`Rendering v${v?.n||'…'}…`;
  $('retry-render').hidden=true;
  try {
    const r=await reach(url, {headers: {Range: 'bytes=0-0', Accept: 'application/json'}});
    if(url!==videoUrl())return;
    if(r.status===202) {
      const body=await parseJSON(r);
      const position=body.position ? ` · queue position ${body.position}` : '';
      $('render-text').textContent=`Rendering v${v?.n||'…'}…${position}`;
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
    for(const id of ['rail-save','desktop-save'])$(id).href=url;
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
  if(state.stamp)stampLabel()
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
  if(currentVersion()?.kind==='blank'&&!$('building').hidden)renderProgress(note,$('build-steps'));
  updateBuildPill()
}
// While a later version builds, the player keeps playing the current one; a pill over
// it shows the newest step. A blank video's first build has the full checklist instead.
function updateBuildPill() {
  const note=currentVersion()?.kind==='blank' ? null :
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
function renderNotes() {
  const list=$('note-list'),atBottom=list.scrollHeight-list.scrollTop-list.clientHeight<80;
  list.replaceChildren();
  for(const note of state.notes) {
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
    bubble.append(node('span','msg-text',note.text));
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
        ? `These paths were outside this video: ${(note.refused || []).join(', ')}`
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
      if(currentVersion()?.kind==='blank')showBlank();
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
function renderFiles() {
  const wrap=$('attachments');
  wrap.replaceChildren();
  state.files.forEach((f,i)=> {
    const chip=node('span','file-chip',f.name);
    const remove=node('button');
    remove.append(icon('close'));
    remove.setAttribute('aria-label',`Remove ${f.name}`);
    remove.onclick=()=> {
      state.files.splice(i,1);
      renderFiles();
    };
    chip.append(remove);
    wrap.append(chip);
  })
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
  try {
    data=await json('pictures', {
      video
    })
  }
  catch(e) {
    if(e.status===404) {
      state.pictures=null;
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
  head.append(node('p','picture-prompt',job.prompt));
  const count=job.n===1?'1 picture':`${job.n} pictures`;
  head.append(node('span','picture-meta',`${count}${job.cutout?' · cut out':''} · ${relative(job.created*1000)}`));
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
  img.alt=`${job.prompt}, picture ${picture.index+1}${showCutout?', background cut out':''}`;
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
  return tile
}
async function addPicture(job,picture,cutout,tile) {
  const key=pictureKey(job,picture,cutout);
  if(state.files.some(f=>f.pictureKey===key)) {
    showPictureAdded('Already in your note');
    return
  }
  if(tile.classList.contains('adding'))return;
  tile.classList.add('adding');
  $('pictures-error').hidden=true;
  try {
    const record=await json(`pictures/${job.id}/${picture.index}/attach`,null, {
      video:state.video,cutout
    });
    addFiles([{...record,pictureKey:key}]);
    tile.replaceWith(pictureTile(job,picture));
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
  $('pictures-make').textContent='Starting…';
  $('pictures-error').hidden=true;
  renderPictureStatus();
  try {
    const job=await json('pictures',null, {
      video:state.video,prompt,n:state.pictureCount,cutout:$('pictures-cutout').checked
    });
    state.pictures=[job,...(state.pictures||[]).filter(j=>j.id!==job.id)];
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
    $('pictures-make').textContent='Make';
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
  if(document.hidden||!state.video||!state.pictures||state.signedOut||state.restarting)return;
  const pending=picturesPending().length>0;
  const every=picturesOpen()?(pending?3000:15000):pending?15000:0;
  if(every&&Date.now()-lastPicturesPoll>=every) {
    lastPicturesPoll=Date.now();
    loadPictures()
  }
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
    out.push({id:data.id,name:files[i].name})
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
async function sendPending() {
  if(state.sending||!state.pending.length)return;
  if(!await ensureName())return;
  state.sending=true;
  $('send-all').disabled=true;
  showError('Sending…');
  try {
    await json('notes',null, {
      video:state.video,format:state.format,...batchBody(state.pending)
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
  clearTimeout(state.renderTimer);
  $('video-title').textContent=libName||video;
  $('video-picker').value=video;
  renderUpgrade();
  loadPending();
  state.pictures=null;
  $('pictures-badge').hidden=true;
  loadPictures();
  try {
    state.info=await json('info', {
      video
    });
    const formats=state.info.formats;
    let saved;
    try {
      saved=localStorage.getItem(`director-format:${video}`);
    } catch (_) {
      saved=null;
    }
    const preferred=window.innerWidth<=700 ? formats.find(f=>f.name==='9x16')?.name : null;
    state.format=formats.find(f=>f.name===saved)?.name || preferred || formats[0]?.name;
    renderFormats();
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
    if(state.user)loadAccess();
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
    if(picked)await openVideo(picked);
    else toast('No videos found in this project.')
  }
  catch(e) {
    toast(e.message)
  }
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
  $('tab-share').hidden=$('rail-share').hidden=!a.can_share;
  $('share-username').closest('.composer-row').hidden=!a.can_share
}
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
    await json('notes',null, {
      video:state.video,format:state.format,...batchBody([{text,time,attachments}])
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
