/* The New video page (pages.new_video_page). One page: the way you start only
   decides which parts open. Start building creates the video (POST
   /api/videos/new), uploads dropped clips and sounds as its sources (or, for a
   short video, sounds as attachments), pictures and documents as attachments,
   then sends the first note with what the page knows (see new_video.py). */
(()=>{
const D=JSON.parse(document.getElementById('nv-data').textContent);
const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const fmt=t=>{t=Math.round(t||0);return Math.floor(t/60)+':'+String(t%60).padStart(2,'0')};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const svgI=(p,w=18)=>`<svg width="${w}" height="${w}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${p}</svg>`;
const ICON={
 ready:'<path d="M5 12.5l4.5 4.5L19 7.5"/>',
 clip:'<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3"/>',
 note:'<path d="M5 4h14v12l-4 4H5z"/><path d="M15 20v-4h4M8 9h8M8 13h5"/>',
 book:'<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/>',
 strip:'<rect x="3" y="7" width="5" height="10" rx="1"/><rect x="10" y="7" width="5" height="10" rx="1"/><rect x="17" y="7" width="4" height="10" rx="1"/>',
 palette:'<path d="M12 3a9 9 0 0 0 0 18c1.5 0 2-1 2-2s-1-1.5-1-2.5 1-1.5 2-1.5h2a4 4 0 0 0 4-4c0-4.4-4-8-9-8z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="10" cy="7" r="1.2"/><circle cx="15" cy="7" r="1.2"/>',
 person:'<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4.5 4.5-6.5 8-6.5s7 2 8 6.5"/>',
 audio:'<path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 7v10M21 12h0"/>',
 music:'<path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/>',
 picture:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>',
 attach:'<path d="M20 11.5l-8.2 8.2a5 5 0 0 1-7.1-7.1L13 4.3a3.3 3.3 0 0 1 4.7 4.7l-8.3 8.3a1.7 1.7 0 0 1-2.4-2.4L14.6 7.3"/>',
 grip:'<circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/>',
 down:'<path d="M6 9l6 6 6-6"/>',plus:'<path d="M12 5v14M5 12h14"/>',x:'<path d="M6 6l12 12M18 6L6 18"/>',
 flag:'<path d="M5 21V4h11l-2 4 2 4H5"/>',dots:'<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
 clock:'<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>'
};
const TYPES={mp4:'video/mp4',mov:'video/quicktime',webm:'video/webm',mp3:'audio/mpeg',wav:'audio/wav',m4a:'audio/mp4',
 aac:'audio/aac',ogg:'audio/ogg',png:'image/png',jpg:'image/jpeg',jpeg:'image/jpeg',webp:'image/webp',gif:'image/gif',
 pdf:'application/pdf',txt:'text/plain',md:'text/plain',zip:'application/zip'};
const ext=f=>(/\.([^.]+)$/.exec(f.name)||['',''])[1].toLowerCase();
const typeOf=f=>TYPES[ext(f)]||f.type||'application/octet-stream';
const FOOTAGE=['mp4','mov','webm'],SOUND=['mp3','m4a','wav','aac','ogg'],PICTURE=['png','jpg','jpeg','webp','gif'];
const WAYS={reel:['about','clips','audio'],short:['about','look','files'],epic:['about','look','bible','clips','audio','files']};
const PARTS=[
 {id:'about',icon:'note',t:'In a few words',hint:'What it is, or how to cut it'},
 {id:'look',icon:'palette',t:'Look',hint:'One look for the whole video'},
 {id:'bible',icon:'person',t:'Characters and world',hint:'Who is in it and where it happens'},
 {id:'clips',icon:'strip',t:'Clips',hint:'Your footage, or a line for each clip you want made'},
 {id:'audio',icon:'audio',t:'Audio',hint:'Songs, voice-over, sound. Each lane can hold anything'},
 {id:'files',icon:'picture',t:'Pictures and other files',hint:'Logos, references, screenshots, PDFs'}
];
const LENS=[['0:30','30 s'],['1:00','1 min'],['2:30','2:30'],['5:00','5 min'],['15:00','15 min']];
let SEQ=0;
const ST={path:null,open:{},look:null,about:'',len:null,chars:[],world:'',acts:[],clips:[],lanes:[{sound:null,over:null}],files:[],links:''};

function toast(t){$('.toast')?.remove();const d=document.createElement('div');d.className='toast';d.setAttribute('role','status');d.textContent=t;document.body.appendChild(d);clearTimeout(toast.h);toast.h=setTimeout(()=>d.remove(),3500)}
function openSheet(html){const d=document.createElement('div');d.className='sheet-shade';d.innerHTML=`<div class="nv-sheet" role="dialog" aria-modal="true">${html}</div>`;
 d.addEventListener('click',e=>{if(e.target===d||e.target.closest('[data-close]'))d.remove()});
 d.addEventListener('keydown',e=>{if(e.key==='Escape')d.remove()});
 document.body.appendChild(d);d.querySelector('input,textarea,button')?.focus();return d}
const wave=(n=60,seed=3)=>{let s='';for(let i=0;i<n;i++){const h=4+Math.abs(Math.sin(i*1.7+seed)*Math.cos(i*.43))*20+(i%8===0?4:0);s+=`<rect x="${i*4}" y="${14-h/2}" width="2.4" height="${h}" rx="1" fill="#d6d6dc"/>`}return `<svg class="wave" viewBox="0 0 ${n*4} 28" preserveAspectRatio="none" aria-hidden="true">${s}</svg>`};

/* ---- what was dropped ---- */
/* A length arrives after the card is drawn: fill it in where it shows, without
   redrawing the parts (that would take the focus from a field being typed in). */
function probe(item,kind){const el=document.createElement(kind);el.preload='metadata';el.muted=true;
 el.onloadedmetadata=()=>{item.len=isFinite(el.duration)?el.duration:null;
  for(const n of $$(`[data-len="${item.id}"]`))n.textContent=fmt(item.len)+(n.dataset.suffix||'');drawSummaries()};el.src=item.url}
function start(path){if(!ST.path)ST.path=path}
function addFiles(files,lane){
 const skipped=[];let footage=0;
 for(const f of files){const e=ext(f);
  if(FOOTAGE.includes(e)){const c={id:++SEQ,file:f,url:URL.createObjectURL(f),len:null,act:ST.acts.length?ST.acts.length-1:null};ST.clips.push(c);probe(c,'video');footage++;ST.open.clips=1}
  else if(SOUND.includes(e)){let l=lane!=null?ST.lanes[lane]:ST.lanes.find(x=>!x.sound);if(!l){l={sound:null,over:null};ST.lanes.push(l)}lane=null;
   if(l.sound)URL.revokeObjectURL(l.sound.url);l.sound={id:++SEQ,file:f,url:URL.createObjectURL(f),len:null};probe(l.sound,'audio');ST.open.audio=1}
  else if(PICTURE.includes(e)||['pdf','txt','md','zip'].includes(e)){ST.files.push({id:++SEQ,file:f,url:PICTURE.includes(e)?URL.createObjectURL(f):null});ST.open.files=1}
  else skipped.push(f.name)}
 if(footage){start('reel');if(!ST.look&&ST.path==='reel')ST.look='as-shot'}else start('custom');
 if(skipped.length)toast('Not a file the builder can use: '+skipped.join(', '));
 draw()}

/* ---- the parts ---- */
const isOpen=id=>!!ST.open[id];
const lookById=id=>D.looks.find(l=>l.id===id);
function summary(id){
 const n=ST.clips.length;
 switch(id){
  case 'about':return ST.about.trim()?`<span>${esc(ST.about.trim().slice(0,38))}${ST.about.trim().length>38?'…':''}</span>`:'';
  case 'look':{const l=lookById(ST.look);return l?`<span class="row" style="gap:6px"><span class="look-sw" style="width:40px;height:16px;display:inline-flex;border-radius:4px;overflow:hidden">${l.sw.map(c=>`<i style="background:${c};flex:1"></i>`).join('')}</span>${esc(l.name)}</span>`:'<span class="opt-tag">Builder picks</span>'}
  case 'bible':{const c=ST.chars.length;return c||ST.world.trim()?`<span>${c?`${c} character${c===1?'':'s'}`:''}${c&&ST.world.trim()?' · ':''}${ST.world.trim()?'world':''}</span>`:''}
  case 'clips':return n?`<span>${n} clip${n===1?'':'s'}${ST.acts.length?` in ${ST.acts.length} act${ST.acts.length===1?'':'s'}`:''}</span>`:'';
  case 'audio':{const k=ST.lanes.filter(l=>l.sound).length;return k?`<span>${k} on ${ST.lanes.length===1?'Audio 1':ST.lanes.length+' lanes'}</span>`:''}
  case 'files':{const k=ST.files.length;return k?`<span>${k} file${k===1?'':'s'}</span>`:''}
 }}
function part(p,body){const o=isOpen(p.id);return `<section class="part ${o?'open':'closed'}" id="part-${p.id}"><header data-act="toggle" data-id="${p.id}" role="button" tabindex="0" aria-expanded="${o}"><span class="pi">${svgI(o?ICON[p.icon]:ICON.plus,18)}</span><span class="pt"><b>${p.t}</b><small>${p.hint}</small></span><span class="sum">${summary(p.id)}</span><span class="chev">${svgI(ICON.down)}</span></header><div class="body">${o?body():''}</div></section>`}
function aboutBody(){
 const lbl={reel:'Note for the builder: how should it be cut?',epic:'Logline'}[ST.path]||'What do you want to make?';
 const ph={reel:'Cut to the beat, hard-hitting transitions…',short:'A 30-second launch video for our app: open on the problem, show three features, end on the download button.',epic:'One or two sentences: who wants what, and what is in the way.'}[ST.path]||'A 30-second launch video for our app: open on the problem, show three features, end on the download button.';
 const big=ST.path!=='reel'&&ST.path!=='epic';
 return `<label class="field-label" for="about">${lbl}</label><textarea id="about" class="tx ${big?'big-prompt':''}" rows="${big?5:3}" placeholder="${esc(ph)}" data-bind="about">${esc(ST.about)}</textarea>
 <div class="lenrow" role="group" aria-label="About how long"><span>About how long?</span>${LENS.map(([v,t])=>`<button type="button" class="pill" data-act="len" data-v="${v}" aria-pressed="${ST.len===v}">${t}</button>`).join('')}<button type="button" class="pill" data-act="len" data-v="" aria-pressed="${!ST.len}">Builder decides</button></div>`}
function lookCard(l,on){return `<button type="button" class="look ${on?'on':''}" data-act="look" data-id="${l.id}" aria-pressed="${!!on}"><span class="look-sw">${l.sw.map(c=>`<i style="background:${c}"></i>`).join('')}</span><span class="look-t"><b>${esc(l.name)}</b><small>${esc(l.d)}</small></span>${on?`<span class="look-tick">${svgI(ICON.ready,14)}Picked</span>`:''}</button>`}
function lookBody(){const footage=ST.clips.some(c=>c.file);return `<div class="looks" role="group" aria-label="Looks">${D.looks.map(l=>lookCard(l,ST.look===l.id)).join('')}</div><p class="small dim" style="margin:8px 0 0">${footage||ST.path==='reel'?'Your clips are real footage, so “As shot” keeps them as they are. Pick a look to restyle all of them.':'Every clip is made in this look. You can change it later with a note.'}</p>`}
function portrait(c){const pic=c.pics.find(p=>p.url);return `<span class="portrait">${pic?`<img src="${pic.url}" alt="">`:esc((c.name||'?').slice(0,1).toUpperCase())}</span>`}
function bibleBody(){return `<div class="field-label">Characters</div><div class="chars">${ST.chars.map((c,i)=>`<button type="button" class="char" data-act="editchar" data-i="${i}">${portrait(c)}<span style="min-width:0;display:block"><b>${esc(c.name)}</b><p>${esc(c.d)}</p><span class="more">${svgI(ICON.picture,13)}${c.pics.length} picture${c.pics.length===1?'':'s'}</span></span></button>`).join('')}<button type="button" class="add-tile" data-act="addchar">${svgI(ICON.plus)}Character</button></div>
 <div class="two"><div><label class="field-label" for="world">World</label><textarea id="world" class="tx" rows="3" placeholder="Where and when it happens. Anything that stays true in every clip." data-bind="world">${esc(ST.world)}</textarea></div>
 <div><span class="field-label">The bible</span><p class="small muted" style="margin:0">The look, characters and world are the film’s bible. Every clip’s builder gets it, so Mara wears the same raincoat in clip 5 and clip 10.</p></div></div>`}
function clipCard(c,i){
 if(c.file)return `<div class="cc" data-id="${c.id}"><span class="num">${i+1}</span><span class="poster"><video src="${c.url}#t=0.1" muted playsinline preload="metadata" aria-hidden="true"></video><span class="len" data-len="${c.id}">${c.len!=null?fmt(c.len):'…'}</span></span><span class="fnrow"><span class="fn">${esc(c.file.name)}</span><button type="button" class="rm" data-act="rmclip" data-id="${c.id}" aria-label="Remove ${esc(c.file.name)}">${svgI(ICON.x,16)}</button><button type="button" class="grip" aria-label="Drag ${esc(c.file.name)} to move it. Arrow keys move it too." data-act="grip">${svgI(ICON.grip,18)}</button></span></div>`;
 return `<div class="cc sk" data-id="${c.id}" data-act="editclip" role="button" tabindex="0" aria-label="Edit “${esc(c.title)}”"><span class="num">${i+1}</span><button type="button" class="grip" aria-label="Drag “${esc(c.title)}” to move it. Arrow keys move it too." data-act="grip">${svgI(ICON.grip,18)}</button><span class="sketchpost"></span><b>${esc(c.title)}</b><p>${esc(c.line)}</p></div>`}
function clipsBody(){
 const dropped=ST.clips.some(c=>c.file);
 const pick=`<button type="button" class="btn btn-dashed btn-sm" data-act="pickclips">${svgI(ICON.plus,16)}${dropped?'Drop more clips':'Clips from your device'}</button>`;
 const add=`<button type="button" class="btn btn-dashed btn-sm" data-act="addclip">${svgI(ICON.plus,16)}Clip</button>`;
 const actBtn=`<div class="add-act"><button type="button" class="btn btn-dashed btn-sm" data-act="addact">${svgI(ICON.flag,16)}+ Act</button><span class="hint">${ST.acts.length?'Acts group clips into parts of the story.':'Only if your video has parts, like a story in three acts.'}</span></div>`;
 if(!ST.clips.length&&!ST.acts.length)return `<button type="button" class="drop" data-act="pickclips">${svgI(ICON.clip,22)}<b>Drop clips here or <u>browse</u></b><span class="small">Your footage, in the order you want it. Or add a card for each clip you want made: a title and a line, no footage needed.</span></button><div class="row" style="margin-top:10px">${add}</div>`+actBtn;
 const tools=`<div class="clips-tools">${dropped?`<span class="hint">${svgI(ICON.grip,14)} In the order you dropped them. Drag to reorder; the builder can reorder too.</span>`:`<span class="hint">One card per clip: a title and a line. No footage needed.</span>`}</div>`;
 const row=n=>`<div class="row" style="margin-top:8px">${dropped?pick:''}${add.replace('data-act="addclip"',`data-act="addclip" data-act-n="${n}"`)}</div>`;
 if(!ST.acts.length)return tools+`<div class="pile ${dropped?'':'sketch'}" data-act-n="">${ST.clips.map(clipCard).join('')}</div>`+row('')+actBtn;
 let i=0;const loose=ST.clips.filter(c=>c.act==null);
 const pile=(cs,n)=>`<div class="pile ${cs.some(c=>c.file)?'':'sketch'}" data-act-n="${n}">${cs.map(c=>clipCard(c,i++)).join('')}</div>`;
 return tools+(loose.length?pile(loose,'')+'<div style="height:12px"></div>':'')+ST.acts.map((a,n)=>{const cs=ST.clips.filter(c=>c.act===n);const tot=cs.reduce((t,c)=>t+(c.len||0),0);
  return `<div class="act"><div class="act-head"><span class="an">${svgI(ICON.flag,12)}Act ${n+1}</span><b>${esc(a.title)}</b><span class="dim">${cs.length} clip${cs.length===1?'':'s'}${tot?` · ~${fmt(tot)}`:''}</span><span class="spacer"></span><button type="button" class="btn btn-ghost btn-sm" data-act="editact" data-n="${n}" aria-label="Act ${n+1} options">${svgI(ICON.dots)}</button></div>${pile(cs,n)}${row(n)}</div>`}).join('')+actBtn}
const overLabel=o=>o==null?'the whole video':`Act ${o+1}`;
function audioBody(){
 return ST.lanes.map((l,i)=>{const it=l.sound;
  const segs=ST.acts.length?ST.acts.map((a,n)=>`<span class="seg ${it&&(l.over==null||l.over===n)?'on':''}" style="--w:${Math.max(1,ST.clips.filter(c=>c.act===n).length)}">Act ${n+1}</span>`).join(''):`<span class="seg on" style="--w:1">Whole video</span>`;
  return `<div class="lane"><span class="ln">${svgI(ICON.audio,16)}Audio ${i+1}</span>${it?`<div class="song">${svgI(ICON.music,18)}<div style="display:flex;flex-direction:column"><b>${esc(it.file.name)}</b><small><span data-len="${it.id}" data-suffix=" · ">${it.len!=null?fmt(it.len)+' · ':''}</span>the builder finds the beats</small></div>${wave(60,i+3)}</div>`:`<button type="button" class="empty" data-act="pickaudio" data-n="${i}">Drop a song, a voice-over or any sound here, or say what you want in the note</button>`}
  <button type="button" class="icon-btn sm" aria-label="Remove Audio ${i+1}" data-act="rmlane" data-n="${i}">${svgI(ICON.x,16)}</button>
  ${it?`<div class="span-map" aria-label="Plays over ${overLabel(l.over)}">${segs}</div><label class="over-pick">Plays over <select data-over="${i}" aria-label="Audio ${i+1} plays over"><option value="">the whole video</option>${ST.acts.map((a,n)=>`<option value="${n}" ${l.over===n?'selected':''}>Act ${n+1}</option>`).join('')}</select>${ST.clips.some(c=>c.file)?'<span>· the builder trims the song to the video</span>':''}</label>`:''}</div>`}).join('')+
 `<div class="add-act"><button type="button" class="btn btn-dashed btn-sm" data-act="addlane">${svgI(ICON.plus,16)}Audio lane</button><span class="hint">Lanes play at the same time: a song on one, a voice-over on another. The builder lowers the others under speech.</span></div>`}
function filesBody(){return `<button type="button" class="drop" data-act="pickfiles">${svgI(ICON.attach,22)}<b>Drop files here or <u>browse</u></b><span class="small">Pictures, clips, audio, PDF, text, or a .zip of them. Clips go to Clips, audio to Audio, the rest stays here.</span></button>${ST.files.length?`<div class="thumbs">${ST.files.map(f=>`<div class="thumb"><span class="poster">${f.url?`<img src="${f.url}" alt="">`:esc(ext(f.file).toUpperCase())}</span>${esc(f.file.name)}<button type="button" class="rm" data-act="rmfile" data-id="${f.id}" aria-label="Remove ${esc(f.file.name)}">${svgI(ICON.x,14)}</button></div>`).join('')}</div>`:''}
 <div class="links"><label class="field-label" for="links">Links (one per line)</label><textarea id="links" class="tx" rows="2" placeholder="https://example.com/the-feature" data-bind="links">${esc(ST.links)}</textarea></div>`}
const BODIES={about:aboutBody,look:lookBody,bible:bibleBody,clips:clipsBody,audio:audioBody,files:filesBody};

function what(){
 if(!ST.path)return '<span class="dim">Pick a way to start, or open any part.</span>';
 const sounds=ST.lanes.map((l,i)=>l.sound?l.sound.file.name.replace(/\.[^.]+$/,'')+' on Audio '+(i+1):null).filter(Boolean);
 const n=ST.clips.length,l=lookById(ST.look);
 return [n?`<span>${svgI(ICON.strip,15)}${n} clip${n===1?'':'s'}${ST.acts.length?` · ${ST.acts.length} act${ST.acts.length===1?'':'s'}`:''}</span>`:'',
  sounds.length?`<span>${svgI(ICON.audio,15)}${esc(sounds.join(', '))}</span>`:'',
  l?`<span>${svgI(ICON.palette,15)}${esc(l.name)}</span>`:'',
  ST.chars.length?`<span>${svgI(ICON.person,15)}${ST.chars.length} character${ST.chars.length===1?'':'s'}</span>`:'',
  ST.len?`<span class="dim">${svgI(ICON.clock,15)}about ${ST.len}</span>`:''].join('')}
function drawSummaries(){for(const p of PARTS){const s=$(`#part-${p.id} .sum`);if(s)s.innerHTML=summary(p.id)}$('#what').innerHTML=what()}
function draw(){
 const ways=$('.ways');ways.classList.toggle('compact',!!ST.path);
 for(const b of $$('.way'))b.setAttribute('aria-pressed',String(ST.path===b.dataset.way));
 $('.dropall').hidden=!!ST.path;
 const y=scrollY;
 $('#parts').innerHTML=PARTS.map(p=>part(p,BODIES[p.id])).join('');
 scrollTo(0,y);
 $('#what').innerHTML=what();
 wireDrag();
}

/* ---- sheets: a character, a planned clip, an act ---- */
function charSheet(i){
 const c=i==null?{name:'',d:'',pics:[]}:ST.chars[i];let pics=[...c.pics];
 const sh=openSheet(`<h3>${i==null?'New character':esc(c.name)}</h3><label class="field-label" for="ch-name">Name</label><input id="ch-name" class="tx" value="${esc(c.name)}" placeholder="Mara">
  <label class="field-label" for="ch-d">Who they are</label><textarea id="ch-d" class="tx" rows="3" placeholder="A girl of 12 in a yellow raincoat. Brave, rude when scared.">${esc(c.d)}</textarea>
  <span class="field-label">Pictures</span><div class="thumbs" id="ch-pics"></div><button type="button" class="btn btn-dashed btn-sm" id="ch-add">${svgI(ICON.picture,16)}Add pictures</button>
  <p class="field-error" id="ch-err"></p><div class="row">${i==null?'':'<button type="button" class="btn btn-ghost" id="ch-rm">Remove</button>'}<button type="button" class="btn" data-close>Cancel</button><button type="button" class="btn btn-primary" id="ch-save">Save</button></div>`);
 const show=()=>{sh.querySelector('#ch-pics').innerHTML=pics.map((p,k)=>`<div class="thumb"><span class="poster"><img src="${p.url}" alt=""></span>${esc(p.file.name)}<button type="button" class="rm" data-k="${k}" aria-label="Remove ${esc(p.file.name)}">${svgI(ICON.x,14)}</button></div>`).join('')};
 show();
 sh.querySelector('#ch-pics').onclick=e=>{const b=e.target.closest('[data-k]');if(b){pics.splice(+b.dataset.k,1);show()}};
 sh.querySelector('#ch-add').onclick=()=>pickFiles('image/*',fs=>{for(const f of fs)if(PICTURE.includes(ext(f)))pics.push({file:f,url:URL.createObjectURL(f)});show()});
 sh.querySelector('#ch-rm')?.addEventListener('click',()=>{ST.chars.splice(i,1);sh.remove();draw()});
 sh.querySelector('#ch-save').onclick=()=>{const name=sh.querySelector('#ch-name').value.trim();
  if(!name){sh.querySelector('#ch-err').textContent='Give them a name.';return}
  if(ST.chars.some((x,k)=>k!==i&&x.name.toLowerCase()===name.toLowerCase())){sh.querySelector('#ch-err').textContent='There is already a character called that.';return}
  const next={name,d:sh.querySelector('#ch-d').value.trim(),pics};if(i==null)ST.chars.push(next);else ST.chars[i]=next;
  start('custom');ST.open.bible=1;sh.remove();draw()}}
function clipSheet(c){
 const sh=openSheet(`<h3>${esc(c.title||'New clip')}</h3><label class="field-label" for="cl-t">Title</label><input id="cl-t" class="tx" value="${esc(c.title)}">
  <label class="field-label" for="cl-l">What happens</label><textarea id="cl-l" class="tx" rows="3" placeholder="A line about what happens">${esc(c.line)}</textarea>
  ${ST.acts.length?`<label class="field-label" for="cl-a">Act</label><select id="cl-a" class="tx">${ST.acts.map((a,n)=>`<option value="${n}" ${c.act===n?'selected':''}>Act ${n+1}: ${esc(a.title)}</option>`).join('')}</select>`:''}
  <div class="row"><button type="button" class="btn btn-ghost" id="cl-rm">Remove</button><button type="button" class="btn" data-close>Cancel</button><button type="button" class="btn btn-primary" id="cl-save">Save</button></div>`);
 sh.querySelector('#cl-rm').onclick=()=>{ST.clips=ST.clips.filter(x=>x!==c);sh.remove();draw()};
 sh.querySelector('#cl-save').onclick=()=>{c.title=sh.querySelector('#cl-t').value.trim()||'Untitled clip';c.line=sh.querySelector('#cl-l').value.trim();
  const a=sh.querySelector('#cl-a');if(a){c.act=+a.value;sortByAct()}sh.remove();draw()}}
function actSheet(n){const a=ST.acts[n];
 const sh=openSheet(`<h3>Act ${n+1}</h3><label class="field-label" for="act-t">Title</label><input id="act-t" class="tx" value="${esc(a.title)}">
  <div class="row"><button type="button" class="btn btn-ghost" id="act-rm">Remove act</button><button type="button" class="btn" data-close>Cancel</button><button type="button" class="btn btn-primary" id="act-save">Save</button></div>`);
 sh.querySelector('#act-save').onclick=()=>{a.title=sh.querySelector('#act-t').value.trim()||a.title;sh.remove();draw()};
 sh.querySelector('#act-rm').onclick=()=>{ST.acts.splice(n,1);
  const to=ST.acts.length?Math.max(0,n-1):null;
  for(const c of ST.clips){if(c.act===n)c.act=to;else if(c.act>n)c.act--}
  for(const l of ST.lanes){if(l.over===n)l.over=null;else if(l.over>n)l.over--}
  sortByAct();sh.remove();draw();toast(`Act ${n+1} removed`)}}
/* clips stay grouped by act, in act order, so acts are runs of clips (timeline.json needs that) */
function sortByAct(){const key=c=>c.act==null?-1:c.act;ST.clips=ST.clips.map((c,i)=>[c,i]).sort((x,y)=>key(x[0])-key(y[0])||x[1]-y[1]).map(x=>x[0])}

/* ---- events ---- */
function pickFiles(accept,then){const inp=$('#nv-pick');inp.accept=accept;inp.value='';inp.onchange=()=>then([...inp.files]);inp.click()}
const ACT={
 way(b,e){const p=b.dataset.way;ST.path=p;for(const id of WAYS[p])ST.open[id]=1;if(p==='reel'&&!ST.look)ST.look='as-shot';if(p!=='reel'&&ST.look==='as-shot'&&!ST.clips.some(c=>c.file))ST.look=null;draw();if(e)$('.ways').scrollIntoView({block:'start',behavior:'smooth'})},
 toggle(b){const id=b.dataset.id;start('custom');ST.open[id]=!ST.open[id];draw();document.querySelector(`#part-${id}>header`)?.focus()},
 look(b){ST.look=ST.look===b.dataset.id?null:b.dataset.id;draw()},
 len(b){ST.len=b.dataset.v||null;draw()},
 addact(){const n=ST.acts.length;ST.acts.push({title:n===0?'Act one':`Act ${n+1}`});if(n===0)ST.clips.forEach(c=>c.act=0);draw();actSheet(n);
  toast(n===0?'Act 1 holds every clip so far. Add more acts and drag clips into them.':`Act ${n+1} added. Drag clips into it.`)},
 editact(b){actSheet(+b.dataset.n)},
 addclip(b){const n=b.dataset.actN;const c={id:++SEQ,title:'New clip',line:'',act:n===''||n==null?(ST.acts.length?ST.acts.length-1:null):+n};ST.clips.push(c);sortByAct();draw();clipSheet(c)},
 editclip(b){const c=ST.clips.find(x=>x.id===+b.dataset.id);if(c)clipSheet(c)},
 rmclip(b){const c=ST.clips.find(x=>x.id===+b.dataset.id);if(c?.url)URL.revokeObjectURL(c.url);ST.clips=ST.clips.filter(x=>x!==c);draw()},
 pickclips(){pickFiles('.mp4,.mov,.webm,video/mp4,video/quicktime,video/webm',fs=>addFiles(fs))},
 pickaudio(b){pickFiles('.mp3,.m4a,.wav,.aac,.ogg,audio/*',fs=>addFiles(fs,+b.dataset.n))},
 pickfiles(){pickFiles('image/*,video/*,audio/*,.pdf,.txt,.md,.zip',fs=>addFiles(fs))},
 rmfile(b){ST.files=ST.files.filter(f=>f.id!==+b.dataset.id);draw()},
 addlane(){ST.lanes.push({sound:null,over:null});ST.open.audio=1;draw()},
 rmlane(b){const n=+b.dataset.n;ST.lanes.splice(n,1);if(!ST.lanes.length)ST.lanes=[{sound:null,over:null}];draw();toast(`Audio ${n+1} removed`)},
 addchar(){charSheet(null)},
 editchar(b){charSheet(+b.dataset.i)}
};
document.addEventListener('click',e=>{if(e.target.closest('.sheet-shade'))return;const b=e.target.closest('[data-act]');if(!b||b.dataset.act==='grip')return;ACT[b.dataset.act]?.(b,e)});
document.addEventListener('keydown',e=>{
 const h=e.target.closest?.('[data-act=toggle],[data-act=editclip]');if(h&&e.target===h&&(e.key==='Enter'||e.key===' ')){e.preventDefault();ACT[h.dataset.act](h);return}
 const g=e.target.closest?.('.grip');if(g&&(e.key==='ArrowLeft'||e.key==='ArrowRight')){e.preventDefault();
  const id=+g.closest('.cc').dataset.id,i=ST.clips.findIndex(c=>c.id===id),j=i+(e.key==='ArrowLeft'?-1:1);if(j<0||j>=ST.clips.length)return;
  const [c]=ST.clips.splice(i,1);ST.clips.splice(j,0,c);if(ST.acts.length&&ST.clips[j+(j>i?-1:1)])c.act=ST.clips[j+(j>i?-1:1)].act;sortByAct();draw();document.querySelector(`.cc[data-id="${id}"] .grip`)?.focus()}});
document.addEventListener('input',e=>{const k=e.target.dataset?.bind;if(k){ST[k]=e.target.value;if(!ST.path&&e.target.value)ST.path='custom';drawSummaries()}});
document.addEventListener('change',e=>{const o=e.target.dataset?.over;if(o!=null){ST.lanes[+o].over=e.target.value===''?null:+e.target.value;draw()}});
/* drag to reorder with a pointer (mouse or touch), across acts too */
function wireDrag(){
 $$('.cc .grip').forEach(g=>g.addEventListener('pointerdown',e=>{
  e.preventDefault();const card=g.closest('.cc'),r=card.getBoundingClientRect();
  const ghost=card.cloneNode(true);ghost.classList.add('ghost');ghost.style.width=r.width+'px';ghost.style.left=r.left+'px';ghost.style.top=r.top+'px';document.body.appendChild(ghost);
  card.classList.add('dragging');const dx=e.clientX-r.left,dy=e.clientY-r.top;
  const mv=ev=>{ghost.style.left=ev.clientX-dx+'px';ghost.style.top=ev.clientY-dy+'px';
   const el=document.elementFromPoint(ev.clientX,ev.clientY);const over=el?.closest('.cc:not(.dragging)'),pile=el?.closest('.pile');
   if(over&&over.parentNode.classList.contains('pile')){const o=over.getBoundingClientRect();const after=ev.clientX>o.left+o.width/2;over.parentNode.insertBefore(card,after?over.nextSibling:over)}
   else if(pile&&!over)pile.appendChild(card);
   if(ev.clientY<80)scrollBy(0,-12);if(ev.clientY>innerHeight-110)scrollBy(0,12)};
  const up=()=>{removeEventListener('pointermove',mv);ghost.remove();card.classList.remove('dragging');
   const order=$$('.pile .cc[data-id]').map(c=>({id:+c.dataset.id,act:c.closest('.pile').dataset.actN===''?null:+c.closest('.pile').dataset.actN}));
   ST.clips=order.map(o=>{const c=ST.clips.find(x=>x.id===o.id);c.act=ST.acts.length?o.act:null;return c});draw()};
  addEventListener('pointermove',mv);addEventListener('pointerup',up,{once:true})}));
}
/* drop files anywhere: clips go to Clips, audio to Audio, the rest to Files */
let dz=null,depth=0;
addEventListener('dragenter',e=>{if(!e.dataTransfer?.types?.includes('Files'))return;depth++;if(!dz){dz=document.createElement('div');dz.className='dropshade';dz.textContent='Drop to add: clips go to Clips, audio to Audio';document.body.appendChild(dz)}});
addEventListener('dragleave',()=>{if(--depth<=0){depth=0;dz?.remove();dz=null}});
addEventListener('dragover',e=>e.preventDefault());
addEventListener('drop',e=>{e.preventDefault();depth=0;dz?.remove();dz=null;const fs=[...(e.dataTransfer?.files||[])];if(!fs.length)return;
 const lane=e.target.closest?.('[data-act=pickaudio]');addFiles(fs,lane?+lane.dataset.n:undefined)});

/* ---- the name ---- */
const PART=/^[a-z0-9][a-z0-9._-]{0,62}$/;
const slug=s=>s.trim().toLowerCase().replace(/\s+/g,'-').replace(/[^a-z0-9._-]/g,'').replace(/^[^a-z0-9]+/,'').slice(0,63);
const project=$('#project'),newProject=$('#new-project');
project.addEventListener('change',()=>{newProject.hidden=project.value!=='+new';if(!newProject.hidden)newProject.focus()});
function fullName(){
 const err=$('#name-error');err.textContent='';
 const name=slug($('#name').value);
 if(!name||!PART.test(name)||name.endsWith('.git')){err.textContent='Give the video a name: letters, numbers and dashes.';$('#name').focus();return null}
 let p=project.value;
 if(p==='+new'){p=slug(newProject.value);if(!p||!PART.test(p)||p.endsWith('.git')){err.textContent='Give the new project a name: letters, numbers and dashes.';newProject.focus();return null}}
 return p?p+'/'+name:name}

/* ---- Start building ---- */
async function post(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const data=await r.json().catch(()=>({}));if(!r.ok)throw Error(data.error||'something went wrong');return data}
async function upload(url,file){const r=await fetch(url,{method:'POST',headers:{'Content-Type':typeOf(file)},body:file});
 const data=await r.json().catch(()=>({}));if(!r.ok)throw Error((data.error||'could not upload')+': '+file.name);return data}
const go=$('#go');
function status(t){go.textContent=t}
function fail(m,created){$('#what').innerHTML=`<span class="err" role="alert">${esc(m)}</span>`+(created?` <a href="/v/${created}/">Open the video</a>`:'');go.disabled=false;status('Start building')}
let made=null;
// Once the video exists, a retry after a failed step resumes: it skips the
// create and every upload already done (keyed by the File), then carries on.
let created=null;const sent=new Map();
async function once(file,url){if(!sent.has(file))sent.set(file,await upload(url,file));return sent.get(file)}
go.addEventListener('click',async()=>{
 if(made){location.href='/v/'+made+'/';return}
 const name=created?created.name:fullName();if(!name)return;
 go.disabled=true;status('Creating…');
 let path=created&&created.path;
 try{
  if(!created){const r=await post('/api/videos/new',{name,start:'blank'});
   created={name,path:name.split('/').map(encodeURIComponent).join('/'),video:r.video};path=created.path;
   for(const el of [$('#name'),project,newProject])el.disabled=true}
  const video=created.video;
  const footage=ST.clips.filter(c=>c.file),sketches=ST.clips.filter(c=>!c.file);
  const planned=sketches.length||ST.chars.length||ST.world.trim();
  const sounds=ST.lanes.filter(l=>l.sound);
  // A film of clips or a planned film reaches its sounds as sources; a short video gets them as attachments.
  const asSources=footage.length||planned;
  const total=footage.length+(asSources?sounds.length:0);let n=0;
  for(const c of footage){status(`Uploading clip ${++n} of ${total}…`);c.source=(await once(c.file,`/v/${path}/api/sources?`+new URLSearchParams({video,filename:c.file.name}))).name}
  if(asSources)for(const l of sounds){status(`Uploading sound ${++n-footage.length} of ${sounds.length}…`);l.source=(await once(l.sound.file,`/v/${path}/api/sources?`+new URLSearchParams({video,filename:l.sound.file.name}))).name}
  const attach=[...ST.files.map(f=>f.file),...(asSources?[]:sounds.map(l=>l.sound.file))];
  const attachments=[],skipped=[];
  for(const [k,f] of attach.entries()){status(`Uploading file ${k+1} of ${attach.length}…`);
   const data=await once(f,`/v/${path}/api/attachments?`+new URLSearchParams({video,name:f.name}));
   if(/\.zip$/i.test(f.name)){attachments.push(...data.attachments.map(a=>a.id));for(const s of data.skipped||[])skipped.push(s.name+' ('+s.reason+')')}
   else attachments.push(data.id)}
  const characters=[];
  for(const c of ST.chars){const pictures=[];for(const p of c.pics){status(`Uploading ${c.name}…`);pictures.push((await once(p.file,`/v/${path}/api/attachments?`+new URLSearchParams({video,name:p.file.name}))).id)}
   characters.push({name:c.name,description:c.d,pictures})}
  const links=ST.links.split('\n').map(x=>x.trim()).filter(Boolean);
  const body={description:ST.about,attachments,links};
  if(ST.look)body.look=ST.look;
  if(ST.len)body.length=ST.len;
  if(asSources)body.film={acts:ST.acts.map(a=>a.title),
   clips:ST.clips.map(c=>c.file?{source:c.source,act:c.act}:{title:c.title,line:c.line,act:c.act}),
   lanes:sounds.map(l=>({sound:l.source,act:l.over})),world:ST.world,characters};
  if(ST.about.trim()||links.length||attachments.length||body.look||body.length||body.film){
   status('Starting…');await post(`/v/${path}/api/videos/first-note`,body)}
  if(skipped.length){fail(`Skipped ${skipped.length} file${skipped.length===1?'':'s'}: `+skipped.join(', '),path);made=path;status('Open the video');return}
  location.href='/v/'+path+'/'
 }catch(err){fail(err.message,path)}
});

/* ---- copy an existing video instead ---- */
$('#copy-go')?.addEventListener('click',async()=>{
 const name=fullName();if(!name)return;const from=$('#copy-from').value;const b=$('#copy-go');b.disabled=true;
 try{await post('/api/videos/new',{name,start:'copy',from});location.href='/v/'+name.split('/').map(encodeURIComponent).join('/')+'/'}
 catch(err){$('#name-error').textContent=err.message;b.disabled=false}});

/* ---- where we start: ?path=reel|short|epic, or a starter prompt from the library ---- */
const Q=new URLSearchParams(location.search);
const prompt=D.starters[Q.get('starter')];
const way=prompt?'short':Q.get('path');
if(WAYS[way])ACT.way({dataset:{way}});else draw();
if(prompt){ST.about=prompt;draw();const t=$('#about');t.focus();const m=/\[[^\]]*\]/.exec(prompt);if(m)t.setSelectionRange(m.index,m.index+m[0].length)}

/* suggest.js runs in its own <script>, so it can't reach ST/D/draw directly:
   it calls this to keep the Look field in step with a look picked from "In a
   few words" (suggest-notes.md q2). Only a name in D.looks (a whole-video
   look this field can hold) is accepted. draw() is never called here: the
   pick just rewrote #about and suggest.js is about to flash the change, so a
   full redraw of #parts would tear out that textarea mid-edit (fresh node,
   empty undo stack, focus lost) and leave suggest.js holding a reference to
   the now-detached one. Update only the Look part and the summaries instead. */
window.nvSetLook=id=>{if(!D.looks.some(l=>l.id===id))return;ST.look=id;const sec=$('#part-look');if(sec){const b=sec.querySelector('.body');if(b&&isOpen('look'))b.innerHTML=lookBody()}drawSummaries()};
})();
