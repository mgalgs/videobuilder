/* The New video page (pages.new_video_page): a name, an optional project,
   files you can drop or pick, an idea box, a Plan-it-first/Just-build-it
   switch and an optional format. Create makes a blank video
   (POST /api/videos/new) and lands in the editor, where the first note
   starts the build (or pre-production) and everything else is set.

   A bare name with nothing else filled in posts exactly {name, start:
   "blank"}, as it always has -- every other field is added to the body
   only once it actually has something to say (see submit, below).

   A starter prompt (?starter=<id>, from the library's starter cards) rides
   along in sessionStorage under DRAFT + the editor's path, for director.js to
   put in the note box. */
(()=>{
const D=JSON.parse(document.getElementById('nv-data').textContent);
const $=s=>document.querySelector(s);
// Must match director.js's own DRAFT key.
const DRAFT='vb-draft:';
const PART=/^[a-z0-9][a-z0-9._-]{0,62}$/;
const slug=s=>s.trim().toLowerCase().replace(/\s+/g,'-').replace(/[^a-z0-9._-]/g,'').replace(/^[^a-z0-9]+/,'')
  .slice(0,63);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

const project=$('#project'),newProject=$('#new-project'),go=$('#go'),err=$('#name-error');
const nameInput=$('#name'),goNote=$('#go-note');
const drop=$('#drop'),filesBox=$('#files'),fileInput=$('#file-input'),fileCount=$('#file-count');
const idea=$('#idea'),ideaAttach=$('#idea-attach');
const format=$('#format');
const why=$('#why'),modePlan=$('#mode-plan'),modeBuild=$('#mode-build'),suggPlan=$('#sugg-plan'),
      suggBuild=$('#sugg-build');
const suggestName=$('#suggest-name');
const pageDrop=$('#page-drop');
const starter=D.starters[new URLSearchParams(location.search).get('starter')];

project.addEventListener('change',()=>{newProject.hidden=project.value!=='+new';if(!newProject.hidden)newProject.focus()});

function fullName(){
  err.textContent='';
  const name=slug(nameInput.value);
  if(!name||!PART.test(name)||name.endsWith('.git')){
    err.textContent='Give the video a name: letters, numbers and dashes.';nameInput.focus();return null}
  let p=project.value;
  if(p==='+new'){
    p=slug(newProject.value);
    if(!p||!PART.test(p)||p.endsWith('.git')){
      err.textContent='Give the new project a name: letters, numbers and dashes.';newProject.focus();return null}
  }
  return p?p+'/'+name:name;
}

async function post(url,body){
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(data.error||'something went wrong');
  return data;
}

/* ---------- icons: the same path data pages._NV_ICON draws server-side,
   for the file tiles this script builds at runtime (remove, play/pause, doc). ---------- */
const ICONS={
  close:['M6 6l12 12M18 6L6 18',2.2],
  play:['<path d="M7 4.5v15l13-7.5z" fill="currentColor" stroke="none"/>',2],
  pause:['<path d="M6 4h4v16H6zM14 4h4v16h-4z" fill="currentColor" stroke="none"/>',2],
  video:['<rect x="3" y="5" width="14" height="14" rx="2"/><path d="M17 10l4-2.5v9L17 14"/>',2],
  doc:['<path d="M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 15.5h6"/>',2],
  plus:['M12 5v14M5 12h14',2.4],
};
function icon(name,size=16){
  const v=ICONS[name];if(!v)return'';
  const [path,w]=v;
  const body=path.startsWith('<')?path:`<path d="${path}"/>`;
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" `+
    `stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}
function sizeLabel(bytes){
  if(bytes>=1048576)return (bytes/1048576).toFixed(1)+' MB';
  if(bytes>=1024)return Math.round(bytes/1024)+' KB';
  return bytes+' B';
}
function timeLabel(s){
  if(!isFinite(s)||s<0)return'';
  s=Math.round(s);
  return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');
}
function ring(p){
  const c=(Math.max(0,Math.min(100,p))/100*94.2).toFixed(1);
  return `<svg class="ring-prog" viewBox="0 0 36 36"><circle cx="18" cy="18" r="15" fill="none" `+
    `stroke="#ffffff33" stroke-width="3"/><circle cx="18" cy="18" r="15" fill="none" stroke="#fff" `+
    `stroke-width="3" stroke-dasharray="${c} 94.2" transform="rotate(-90 18 18)" stroke-linecap="round"/></svg>`;
}
function waveSvg(peaks){
  if(!peaks||!peaks.length)return'<svg viewBox="0 0 100 22" aria-hidden="true"></svg>';
  const n=peaks.length;
  let bars='';
  for(let i=0;i<n;i++){
    const h=Math.max(2,peaks[i]*18+2),x=i*(100/n);
    bars+=`<rect x="${x.toFixed(2)}" y="${((22-h)/2).toFixed(2)}" width="${(100/n*.55).toFixed(2)}" `+
      `height="${h.toFixed(2)}" rx=".8" fill="#6b6b75"/>`;
  }
  return `<svg viewBox="0 0 100 22" preserveAspectRatio="none" aria-hidden="true">${bars}</svg>`;
}

/* ---------- staged files ---------- */
let files=[];   // {localId, file, name, type, size, id(staged id once uploaded), progress(0-100|null),
                 //  error, xhr, url, frame, duration, peaks}
let nextLocalId=1;
let playingId=null;
const player=typeof Audio!=='undefined'?new Audio():null;
if(player)player.onended=()=>{playingId=null;renderFiles()};

function hasContent(){return files.length>0||idea.value.trim().length>0}

function tileHtml(f){
  const x=`<button type="button" class="x" data-rm="${f.localId}" aria-label="Remove ${esc(f.name)}">`+
    `${icon('close',14)}</button>`;
  const bar=f.progress!=null?`<div class="bar"><i style="width:${f.progress}%"></i></div>`:'';
  const bad=f.error?`<div class="bad">${esc(f.error)}</div>`:'';
  if(f.type.startsWith('audio/')){
    const playing=playingId===f.localId;
    return `<div class="aud">${x}<button type="button" class="play" data-play="${f.localId}" `+
      `aria-label="${playing?'Pause':'Play'} ${esc(f.name)}">${icon(playing?'pause':'play',16)}</button>`+
      `<div class="meta"><span class="name">${esc(f.name)}</span><div class="wave">${waveSvg(f.peaks)}</div>`+
      (f.progress!=null?`<span class="sub">Uploading… ${f.progress}%</span>`:'')+'</div>'+
      `<span class="dur">${f.duration?timeLabel(f.duration):''}</span>${bar}${bad}</div>`;
  }
  if(f.type==='application/pdf'||f.type==='text/plain'){
    const kind=f.type==='application/pdf'?'PDF':(/\.md$/i.test(f.name)?'MD':'TXT');
    return `<div class="doc-tile">${x}<span class="doc-ic${kind==='PDF'?'':' txt'}">${kind}</span>`+
      `<span><div class="doc-name">${esc(f.name)}</div><div class="doc-sub">${kind} · `+
      `${sizeLabel(f.size)}</div></span>${bar}${bad}</div>`;
  }
  const isVideo=f.type.startsWith('video/');
  const art=isVideo&&f.frame?`<img class="art" src="${f.frame}" alt="">`
    :!isVideo&&f.url?`<img class="art" src="${f.url}" alt="">`
    :`<div class="art icon-art">${icon(isVideo?'video':'doc',24)}</div>`;
  const overlay=isVideo?`<span class="vid-ic">${icon('video',14)}</span>`+
    `<span class="dur">${f.duration?timeLabel(f.duration):''}</span>`:`<span class="tname-ov">${esc(f.name)}</span>`;
  const up=f.progress!=null?`<div class="up">${ring(f.progress)}<span>${f.progress}%</span></div>`:'';
  return `<div class="tile">${x}${art}${overlay}${up}${bad}</div>`;
}

function renderFiles(){
  drop.hidden=files.length>0;
  filesBox.hidden=files.length===0;
  // Audio rows span two columns; keep them last so the grid packs tightly, same as the design.
  const ordered=[...files].sort((a,b)=>(a.type.startsWith('audio/'))-(b.type.startsWith('audio/')));
  filesBox.innerHTML=ordered.map(tileHtml).join('')+
    `<button type="button" class="add-more" id="add-more">${icon('plus',22)}Add more</button>`;
  const uploading=files.filter(f=>f.progress!=null).length;
  fileCount.textContent=files.length?`${files.length} file${files.length>1?'s':''}`+
    (uploading?` · ${uploading} uploading`:''):'';
}

function computePeaks(data,n){
  const peaks=[],block=Math.max(1,Math.floor(data.length/n));
  for(let i=0;i<n;i++){
    let max=0;
    for(let j=i*block;j<Math.min(data.length,(i+1)*block);j++){const v=Math.abs(data[j]);if(v>max)max=v}
    peaks.push(max);
  }
  return peaks;
}

// Best-effort client-side preview: a real thumbnail/frame/waveform from the
// file itself, never from the network -- any missing browser API (no
// AudioContext, a flaky video decode) just leaves the tile at its plain
// icon, nothing here may ever break the upload itself.
function enrich(f){
  try{
    if(f.type.startsWith('image/')){
      f.url=URL.createObjectURL(f.file);
      renderFiles();
    }else if(f.type.startsWith('video/')){
      f.url=URL.createObjectURL(f.file);
      const v=document.createElement('video');
      v.preload='metadata';v.muted=true;v.src=f.url;
      v.onloadeddata=()=>{
        f.duration=v.duration;
        try{
          const c=document.createElement('canvas');
          c.width=160;c.height=160;
          c.getContext('2d').drawImage(v,0,0,c.width,c.height);
          f.frame=c.toDataURL('image/jpeg',.7);
        }catch(_){}
        renderFiles();
      };
    }else if(f.type.startsWith('audio/')){
      const a=new Audio();
      a.preload='metadata';a.src=URL.createObjectURL(f.file);
      f.audioUrl=a.src;
      a.onloadedmetadata=()=>{f.duration=a.duration;renderFiles()};
      const Ctx=window.AudioContext||window.webkitAudioContext;
      if(Ctx&&f.file.arrayBuffer){
        f.file.arrayBuffer().then(buf=>{
          const ctx=new Ctx();
          return ctx.decodeAudioData(buf).finally(()=>{try{ctx.close()}catch(_){}});
        }).then(audioBuf=>{
          f.peaks=computePeaks(audioBuf.getChannelData(0),56);
          renderFiles();
        }).catch(()=>{});
      }
    }
  }catch(_){}
}

function upload(f){
  const xhr=new XMLHttpRequest();
  f.xhr=xhr;
  xhr.open('POST','/api/videos/staging?name='+encodeURIComponent(f.name));
  xhr.setRequestHeader('Content-Type',f.type||'application/octet-stream');
  xhr.upload.onprogress=e=>{if(e.lengthComputable){f.progress=Math.round(e.loaded/e.total*100);renderFiles()}};
  xhr.onload=()=>{
    f.xhr=null;
    if(xhr.status>=200&&xhr.status<300){
      let data={};try{data=JSON.parse(xhr.responseText)}catch(_){}
      f.id=data.id;f.progress=null;
    }else{
      let msg='upload failed';try{msg=JSON.parse(xhr.responseText).error||msg}catch(_){}
      f.error=msg;f.progress=null;
    }
    renderFiles();renderGo();renderSuggestButton();
  };
  xhr.onerror=()=>{f.xhr=null;f.error='upload failed';f.progress=null;renderFiles();renderGo()};
  xhr.send(f.file);
}

function addFiles(fileList){
  for(const file of fileList||[]){
    const f={localId:nextLocalId++,file,name:file.name,type:file.type||'',size:file.size,id:null,
             progress:0,error:null};
    files.push(f);
    upload(f);
    enrich(f);
  }
  renderFiles();renderGo();renderSuggestButton();scheduleMode();
}

function removeFile(localId){
  const i=files.findIndex(f=>f.localId===localId);
  if(i<0)return;
  const [f]=files.splice(i,1);
  if(f.xhr)try{f.xhr.abort()}catch(_){}
  if(f.url)try{URL.revokeObjectURL(f.url)}catch(_){}
  if(f.id)post('/api/videos/staging/'+f.id+'/delete',{}).catch(()=>{});
  if(playingId===localId){playingId=null;try{player.pause()}catch(_){}}
  renderFiles();renderGo();renderSuggestButton();scheduleMode();
}

function togglePlay(localId){
  const f=files.find(x=>x.localId===localId);
  if(!f||!f.audioUrl||!player)return;
  if(playingId===localId){player.pause();playingId=null}
  else{player.src=f.audioUrl;player.play().catch(()=>{});playingId=localId}
  renderFiles();
}

filesBox.addEventListener('click',e=>{
  if(e.target.closest('#add-more')){fileInput.click();return}
  const rm=e.target.closest('[data-rm]');if(rm){removeFile(+rm.dataset.rm);return}
  const pl=e.target.closest('[data-play]');if(pl){togglePlay(+pl.dataset.play);return}
});
$('#add-files').addEventListener('click',()=>fileInput.click());
ideaAttach.addEventListener('click',()=>fileInput.click());
fileInput.addEventListener('change',e=>{addFiles(e.target.files);e.target.value=''});

idea.addEventListener('paste',e=>{
  const list=[...(e.clipboardData&&e.clipboardData.files||[])];
  if(!list.length)return;
  if(!e.clipboardData.getData('text/plain'))e.preventDefault();
  addFiles(list);
});

if(document.body){
  document.body.ondragenter=e=>{
    if(e.dataTransfer&&e.dataTransfer.types&&[...e.dataTransfer.types].includes('Files')){
      e.preventDefault();pageDrop.hidden=false;
    }
  };
  document.body.ondragover=e=>{
    if(e.dataTransfer&&e.dataTransfer.types&&[...e.dataTransfer.types].includes('Files'))e.preventDefault();
  };
  document.body.ondragleave=e=>{if(!e.relatedTarget)pageDrop.hidden=true};
  document.body.ondrop=e=>{
    e.preventDefault();pageDrop.hidden=true;
    if(e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files.length)addFiles(e.dataTransfer.files);
  };
}
pageDrop.addEventListener('click',()=>{pageDrop.hidden=true});

/* ---------- plan / build ---------- */
let suggestion=null,userPicked=null,modeTimer=null;

function renderMode(){
  const sVal=suggestion?(suggestion.plan?'plan':'build'):null;
  const m=userPicked||sVal||'build';
  modePlan.setAttribute('aria-checked',String(m==='plan'));
  modeBuild.setAttribute('aria-checked',String(m==='build'));
  suggPlan.hidden=sVal!=='plan';
  suggBuild.hidden=sVal!=='build';
  if(!suggestion){
    why.hidden=true;
  }else{
    why.hidden=false;
    if(userPicked&&userPicked!==sVal){
      why.innerHTML=`<span>You picked <b>${m==='plan'?'Plan it first':'Just build it'}</b>. The builder `+
        `suggested ${sVal==='plan'?'planning it first':'building it straight away'}: ${esc(suggestion.reason)} `+
        '<button type="button" id="mode-back">Switch back</button></span>';
    }else{
      why.innerHTML=`<span>${esc(suggestion.reason)}</span>`;
    }
  }
  return m;
}

function renderGo(){
  const m=renderMode();
  const uploading=files.some(f=>f.progress!=null);
  go.disabled=uploading;
  if(uploading){
    go.textContent='Uploading…';goNote.textContent='Waiting for the files to finish uploading.';
  }else{
    go.textContent=m==='plan'?'Start planning':(hasContent()?'Create and build':'Create');
    goNote.textContent=m==='plan'?'Opens the editor on the pre-production board. Nothing renders yet.'
      :hasContent()?'Opens the editor; the first version starts rendering.':'Only the name is needed.';
  }
}

modePlan.addEventListener('click',()=>{userPicked='plan';renderGo()});
modeBuild.addEventListener('click',()=>{userPicked='build';renderGo()});
why.addEventListener('click',e=>{if(e.target&&e.target.id==='mode-back'){userPicked=null;renderGo()}});

async function fetchMode(){
  const types=files.map(f=>f.type).filter(Boolean);
  try{
    const r=await fetch('/api/videos/mode',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt:idea.value,types})});
    if(r.ok)suggestion=await r.json();
  }catch(_){ /* keep whatever suggestion we already had; this must never show an error */ }
  renderGo();
}
function scheduleMode(){clearTimeout(modeTimer);modeTimer=setTimeout(fetchMode,400)}
idea.addEventListener('input',()=>{scheduleMode();renderGo();renderSuggestButton()});

/* ---------- Suggest a name ---------- */
function renderSuggestButton(){
  if(!suggestName.hidden)suggestName.disabled=!hasContent()||suggestName.dataset.busy==='1';
}
async function refreshSuggestConfig(){
  try{
    const r=await fetch('/api/suggest/config');
    const cfg=r.ok?await r.json():{model:false};
    suggestName.hidden=!cfg.model;
  }catch(_){suggestName.hidden=true}
  renderSuggestButton();
}
suggestName.addEventListener('click',async()=>{
  suggestName.dataset.busy='1';suggestName.disabled=true;suggestName.textContent='Suggesting…';
  try{
    const attachments=files.filter(f=>f.id).map(f=>f.id);
    const data=await post('/api/videos/suggest-name',{idea:idea.value,attachments});
    const named=data.name?slug(data.name):'';
    if(named&&PART.test(named)){nameInput.value=named;err.textContent=''}
    else{err.textContent="Couldn't suggest a name from this yet."}
  }catch(x){err.textContent=x.message}
  finally{suggestName.dataset.busy='';suggestName.textContent='Suggest';renderSuggestButton()}
});

/* ---------- create ---------- */
$('#nv-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const name=fullName();
  if(!name)return;
  if(files.some(f=>f.progress!=null)){err.textContent='Wait for the files to finish uploading.';return}
  if(files.some(f=>f.error)){err.textContent='Remove the files that failed to upload first.';return}
  const body={name,start:'blank'};
  const ideaText=idea.value.trim();
  if(ideaText)body.prompt=ideaText;
  const attachments=files.filter(f=>f.id).map(f=>f.id);
  if(attachments.length)body.attachments=attachments;
  if(format.value)body.format=format.value;
  if(userPicked)body.plan=userPicked==='plan';
  go.disabled=true;go.textContent='Creating…';
  const href='/v/'+name.split('/').map(encodeURIComponent).join('/')+'/';
  try{
    await post('/api/videos/new',body);
    if(starter)try{sessionStorage.setItem(DRAFT+href,starter)}catch(_){}
    location.href=href;
  }catch(x){
    err.textContent=x.message;
    renderGo();
  }
});

renderFiles();
renderGo();
refreshSuggestConfig();
fetchMode();
nameInput.focus();
})();
