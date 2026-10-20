/* The New video page (pages.new_video_page): a name, an optional project, and
   Create. Create makes a blank video (POST /api/videos/new) and lands in the
   editor, where the first note starts the build and everything else is set.
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
const project=$('#project'),newProject=$('#new-project'),go=$('#go'),err=$('#name-error');
const starter=D.starters[new URLSearchParams(location.search).get('starter')];

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
  return p?p+'/'+name:name;
}

async function post(url,body){
  const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await r.json().catch(()=>({}));
  if(!r.ok)throw Error(data.error||'something went wrong');
  return data;
}

$('#nv-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const name=fullName();
  if(!name)return;
  go.disabled=true;go.textContent='Creating…';
  const href='/v/'+name.split('/').map(encodeURIComponent).join('/')+'/';
  try{
    await post('/api/videos/new',{name,start:'blank'});
    if(starter)try{sessionStorage.setItem(DRAFT+href,starter)}catch(_){}
    location.href=href;
  }catch(x){
    err.textContent=x.message;
    go.disabled=false;go.textContent='Create';
  }
});

$('#name').focus();
})();
