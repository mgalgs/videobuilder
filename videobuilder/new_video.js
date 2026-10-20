/* The New video page (pages.new_video_page): a name, a project, an optional
   description, and Create. Create makes a blank video (POST /api/videos/new);
   with a description it sends it as the first note (POST
   /v/<path>/api/videos/first-note), so the builder starts on it right away.
   Either way it lands in the editor, where everything else is set. */
(()=>{
const D=JSON.parse(document.getElementById('nv-data').textContent);
const $=s=>document.querySelector(s);
const LAST='vb-new-project';
const PART=/^[a-z0-9][a-z0-9._-]{0,62}$/;
const slug=s=>s.trim().toLowerCase().replace(/\s+/g,'-').replace(/[^a-z0-9._-]/g,'').replace(/^[^a-z0-9]+/,'')
  .slice(0,63);
const project=$('#project'),newProject=$('#new-project'),about=$('#about'),go=$('#go'),err=$('#name-error');

// The project used last, in this browser.
try{
  const last=localStorage.getItem(LAST);
  if(last!=null&&[...project.options].some(o=>o.value===last&&last!=='+new'))project.value=last;
}catch(_){}
project.addEventListener('change',()=>{newProject.hidden=project.value!=='+new';if(!newProject.hidden)newProject.focus()});

function fullName(){
  err.textContent='';
  const name=slug($('#name').value);
  if(!name||!PART.test(name)||name.endsWith('.git')){
    err.textContent='Give the video a name: letters, numbers and dashes.';$('#name').focus();return null}
  let p=project.value;
  if(p==='+new'){
    p=slug(newProject.value);
    if(!p||!PART.test(p)||p.endsWith('.git')){
      err.textContent='Give the new project a name: letters, numbers and dashes.';newProject.focus();return null}
  }
  return {name:p?p+'/'+name:name,project:p};
}

async function post(url,body){
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(data.error||'something went wrong');
  return data;
}

// Once the video exists, a retry after a failed first note only sends the note again.
let created=null;
$('#nv-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const want=created||fullName();
  if(!want)return;
  go.disabled=true;go.textContent='Creating…';
  const path=want.name.split('/').map(encodeURIComponent).join('/');
  try{
    if(!created){
      await post('/api/videos/new',{name:want.name,start:'blank'});
      created=want;
      try{localStorage.setItem(LAST,want.project)}catch(_){}
      for(const el of [$('#name'),project,newProject])el.disabled=true;
    }
    if(about.value.trim()){
      go.textContent='Starting…';
      await post(`/v/${path}/api/videos/first-note`,{description:about.value});
    }
    location.href='/v/'+path+'/';
  }catch(x){
    err.textContent=x.message;
    if(created)err.insertAdjacentHTML('beforeend',` <a href="/v/${path}/">Open the video</a>`);
    go.disabled=false;go.textContent=created?'Try again':'Create';
  }
});

// A starter prompt from the library: its words in the description, the first blank chosen.
const prompt=D.starters[new URLSearchParams(location.search).get('starter')];
if(prompt){
  about.value=prompt;
  about.focus();
  const m=/\[[^\]]*\]/.exec(prompt);
  if(m)about.setSelectionRange(m.index,m.index+m[0].length);
}
})();
