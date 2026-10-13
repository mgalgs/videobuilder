'use strict';
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
  resumeOnVisible: false
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
async function json(path, params, body) {
  const r=await fetch(api(path,params),body===undefined? {
  }
  : {
    method:'POST',headers: {
      'Content-Type':'application/json'
    },body:JSON.stringify(body)
  });
  const data=await parseJSON(r);
  if(!r.ok)throw Error(data.error||r.statusText);
  return data
}
// A proxy answers with HTML while the editor restarts; say so instead of a parse error.
async function parseJSON(r) {
  const text=await r.text();
  try {
    return JSON.parse(text)
  } catch (_) {
    throw Error(`The editor didn't answer (HTTP ${r.status}); it may be restarting. Try again in a moment.`)
  }
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
  const label=`v${v.n} · ${relative(v.time)}`;
  $('version-label').textContent=label;
  $('rail-version').textContent=`v${v.n}`;
  $('caption-by').textContent=`Builder · v${v.n}`;
  $('caption-text').textContent=v.summary||'';
  $('sheet-subtitle').textContent=`Playing v${v.n} · ${timeLabel(player.currentTime)}`;
  const url=videoUrl();
  for(const id of ['rail-save','desktop-save']) {
    if(state.videoReady)$(id).href=url;
    $(id).download=`${state.video.replaceAll('/','-')}-v${v.n}-${state.format}.mp4`
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
function resizePlayer() {
  const f=formatInfo();
  if (!f) return;
  const availableHeight=Math.max(200, window.innerHeight - 280);
  const width=Math.min(420, availableHeight * f.width / f.height);
  $('player-box').style.setProperty('--player-width', `${width}px`);
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
    const r=await fetch(url, {headers: {Range: 'bytes=0-0', Accept: 'application/json'}});
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
      throw Error(body.log||body.error||r.statusText)
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
    $('render-text').textContent=e.message;
    $('retry-render').hidden=false;
    $('poster').hidden=false;
    setPlayState('play')
  }
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
  $('desktop-play').disabled=$('fullscreen').disabled=!state.videoReady;
  $('desktop-play').setAttribute('aria-label',label);
  $('tap-player').setAttribute('aria-label',label)
}
function setView(view) {
  state.view=view;
  for(const name of ['chat','versions','tune'])$(name+'-view').hidden=name!==view;
  $('sheet-title').textContent= {
    chat:'Builder chat',versions:'Versions',tune:'Fine tuning'
  }
  [view];
  $('tab-chat').classList.toggle('active',view==='chat');
  $('tab-versions').classList.toggle('active',view==='versions');
  $('panel').dataset.view=view;
  if(view==='tune')openTuning('phone-tune-body');
  if(view==='versions')loadVersions()
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
function attachmentUrl(id) {
  return api('attachments/'+encodeURIComponent(id))
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
    if(note.reply) {
      const reply=node('div','bubble-row builder');
      const box=node('div','bubble');
      box.append(node('span','who','Builder'),node('span','msg-text',replyText(note.reply)));
      reply.append(box);
      list.append(reply)
    }
    if(['queued','working'].includes(note.state)) {
      const working=node('div','bubble-row builder'),box=node('div','bubble');
      box.append(node('span','who','Builder'));
      const dots=node('span','dots');
      for(let i=0;i<3;i++)dots.append(node('i','dot'));
      const message=note.state==='queued' ?
        'Queued. The builder takes notes one at a time and starts this one when the note before it lands.' :
        'Working on it. A new version usually takes 2–3 minutes. You can keep watching or add more notes.';
      if(note.state==='working')box.append(dots);
      box.append(node('span','state-message',message));
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
  if(atBottom)list.scrollTop=list.scrollHeight
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
      if(state.notes.some(n=>n.version))loadVersions()
    }
    // Clear only the poll's own error, never one from a send the director made.
    if(state.pollError&&$('composer-error').textContent===state.pollError)showError('');
    state.pollError=null
  }
  catch(e) {
    state.pollError=e.message;
    showError(e.message)
  }
}
function versionMeta(v) {
  const who=v.directed_by||v.author||'Someone';
  switch(v.kind) {
    case 'builder':return `Builder, from ${who} · ${relative(v.time)}`;
    case 'edit':return `${who}, fine tuning · ${relative(v.time)}`;
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
    showError(e.message)
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
// Notes the director has written but not sent: kept in this browser, per video,
// so they survive a reload. Not the "queued" note state, which is sent and waiting.
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
    const r=await fetch(api('attachments', {
      video:state.video,name:files[i].name
    }), {
      method:'POST',headers: {
        'Content-Type':files[i].type||'application/octet-stream'
      },body:files[i]
    });
    const data=await parseJSON(r);
    if(!r.ok)throw Error(data.error||r.statusText);
    out.push({id:data.id,name:files[i].name})
  }
  return out
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
  clearTimeout(state.renderTimer);
  $('video-title').textContent=libName||video;
  $('video-picker').value=video;
  renderUpgrade();
  loadPending();
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
    await loadNotes()
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
    state.name=name.name;
    updateName();
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
$('upgrade').onclick=upgradeVideo;
$('tap-player').onclick=togglePlay;
$('desktop-play').onclick=togglePlay;
// The video element itself goes full screen, with the browser's own controls while it is.
$('fullscreen').onclick=()=> {
  if(!state.videoReady)return;
  player.controls=true;
  player.requestFullscreen().catch(()=> {
    player.controls=false
  })
};
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
  if(!r.ok)throw Error(data.error);
  return data
}
function updateName() {
  $('director-name').replaceChildren();
  if (state.name) $('director-name').append('Directing as ', node('strong', null, state.name));
  else $('director-name').textContent='Set your name';
  $('director-name').setAttribute('aria-label', state.name ? 'Change your name' : 'Set your name');
}
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
stampLabel();
init();
let lastNotesPoll=0;
setInterval(()=> {
  const fast=!document.hidden && (
    state.notes.some(n=>['queued','working'].includes(n.state)) ||
    window.innerWidth>700 || $('panel').classList.contains('open'));
  if(state.video&&Date.now()-lastNotesPoll>=(fast?3000:15000)) {
    lastNotesPoll=Date.now();
    loadNotes();
  }
},1000);
setInterval(()=> {
  if(state.video)loadVersions()
},15000);
// /api/project syncs with the forge, so poll the cheap /healthz and refetch the
// project only when the editor's version changes (a deploy), for the upgrade chip.
async function checkEditorVersion() {
  if(document.hidden||!state.project)return;
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
