"""The library's non-API HTML pages: sign-in, sign-up, the index, the New
video page and the account page. Each took a `Library` method before; here
they take whatever plain data they need, so they have no dependency on
`Library` itself."""
import html
import json
import time
from urllib.parse import quote

from .starters import STARTERS


_AUTH_STYLE = (
    '<style>'
    ':root{color-scheme:dark}'
    'body{margin:0;min-height:100vh;font:16px/1.5 system-ui,sans-serif;color:#f4f4f2;'
    'background:radial-gradient(1200px 600px at 15% -10%,rgba(229,72,59,.18),transparent 60%),#0d0d10}'
    '.auth{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(320px,400px);gap:4rem;align-items:center;'
    'max-width:1180px;margin:0 auto;padding:3.5rem 2rem;box-sizing:border-box;min-height:100vh}'
    '.brand{display:flex;align-items:center;gap:.65rem;font-weight:800;font-size:1.25rem;letter-spacing:-.01em}'
    '.brand svg{flex:none}'
    '.pitch h1{font-size:clamp(2rem,4.2vw,3.25rem);line-height:1.08;letter-spacing:-.025em;margin:2.25rem 0 1rem;'
    'font-weight:800}'
    '.pitch h1 em{font-style:normal;color:#ef5b4c}'
    '.pitch p{color:#a9a9b2;font-size:1.1rem;max-width:34rem;margin:0 0 2rem}'
    '.reel{display:block;width:100%;aspect-ratio:16/9;border-radius:14px;background:#141417;object-fit:cover;'
    'box-shadow:0 30px 80px rgba(0,0,0,.55),0 0 0 1px #26262c}'
    '.steps{list-style:none;padding:0;margin:0;display:grid;gap:.9rem;color:#c9c9cf}'
    '.steps b{color:#f4f4f2}'
    '.card{background:#141417;border:1px solid #26262c;border-radius:16px;padding:2rem;'
    'box-shadow:0 20px 60px rgba(0,0,0,.4)}'
    '.card h2{margin:0 0 1.25rem;font-size:1.35rem;letter-spacing:-.01em}'
    'label{display:block;font-size:.85rem;color:#a9a9b2;margin:.9rem 0 .35rem}'
    'input{display:block;width:100%;box-sizing:border-box;min-height:46px;padding:.7rem .85rem;font:inherit;'
    'color:#f4f4f2;background:#0d0d10;border:1px solid #2c2c33;border-radius:10px;outline:none}'
    'input:focus{border-color:#ef5b4c;box-shadow:0 0 0 3px rgba(239,91,76,.25)}'
    'button{display:block;width:100%;min-height:48px;margin-top:1.5rem;font:inherit;font-weight:700;color:#fff;'
    'background:#e5483b;border:none;border-radius:10px;cursor:pointer}'
    'button:hover{background:#ef5b4c}'
    '#error{color:#ff8a80;min-height:1.4em;margin:.75rem 0 0;font-size:.9rem}'
    '.switch{margin:1rem 0 0;color:#a9a9b2;font-size:.92rem;text-align:center}'
    '.switch a{color:#f4f4f2;font-weight:600}'
    '@media (max-width:900px){.auth{grid-template-columns:1fr;gap:2rem;padding:1.5rem 1rem 2.5rem;'
    'min-height:0}.pitch h1{margin-top:1.5rem}.pitch p{margin-bottom:1.25rem}.reel{aspect-ratio:16/9}'
    '.card{padding:1.5rem}}'
    '</style>')

_LOGO = ('<svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">'
         '<rect width="34" height="34" rx="9" fill="#e5483b"/>'
         '<path d="M13 10.5v13a1 1 0 0 0 1.5.86l10.8-6.5a1 1 0 0 0 0-1.72l-10.8-6.5A1 1 0 0 0 13 10.5z" '
         'fill="#fff"/></svg>')


def _auth_page(title, heading, fields, button, api, switch, showcase):
    """The sign-in and sign-up pages: the pitch beside the form, the showcase
    reel when it is built, three plain steps when it isn't."""
    if showcase:
        # Same portrait/landscape pick as the library's reel, for the same reason.
        show = ('<video class="reel" id="reel" muted autoplay loop playsinline preload="metadata" '
                'poster="/capabilities/showcase-16x9.jpg" aria-label="What videobuilder can make"></video>'
                '<script>(()=>{const v=document.getElementById("reel");v.src="/capabilities/showcase-16x9.mp4"})()'
                '</script>')
    else:
        show = ('<ol class="steps"><li><b>Describe it.</b> The topic, the length, the look.</li>'
                '<li><b>Watch the first version.</b> The builder makes it in a few minutes.</li>'
                '<li><b>Give notes.</b> Each one makes a new version, until it\'s right.</li></ol>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<title>{title} · videobuilder</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">' + _AUTH_STYLE +
            '</head><body><main class="auth"><section class="pitch">'
            '<div class="brand">' + _LOGO + 'videobuilder</div>'
            '<h1>Direct videos <em>in plain words.</em></h1>'
            '<p>Describe what you want, watch the version the builder makes, then give notes until '
            'it\'s right.</p>' + show + '</section>'
            f'<section class="card"><h2>{heading}</h2><form id="f">{fields}<button>{button}</button></form>'
            f'<p id="error" role="alert"></p><p class="switch">{switch}</p></section></main>'
            '<script>document.querySelector("#f").onsubmit=async e=>{e.preventDefault();'
            f'const form=new FormData(e.target);const r=await fetch("{api}",{{method:"POST",'
            'headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(form))});'
            'if(r.ok)location.href="/";else document.querySelector("#error").textContent=(await r.json()).error};'
            '</script></body></html>').encode()


def signin_page(error=None, showcase=False):
    return _auth_page(
        'Sign in', 'Sign in',
        '<label for="u">Username</label><input id="u" name="username" autocomplete="username" required>'
        '<label for="p">Password</label><input id="p" name="password" type="password" '
        'autocomplete="current-password" required>',
        'Sign in', '/api/login', 'New here? <a href="/signup">Sign up</a>', showcase)


def signup_page(showcase=False):
    return _auth_page(
        'Sign up', 'Create your account',
        '<label for="u">Username</label><input id="u" name="username" autocomplete="username" required>'
        '<label for="p">Password</label><input id="p" name="password" type="password" '
        'autocomplete="new-password" required>'
        '<label for="c">Confirm password</label><input id="c" name="confirm" type="password" '
        'autocomplete="new-password" required>',
        'Sign up', '/api/signup', 'Have an account? <a href="/login">Sign in</a>', showcase)


LIBRARY_STYLE = (
    'body{font:16px/1.4 system-ui,sans-serif;background:#0d0d10;color:#fff;margin:0}'
    'a{color:#88cafa;text-decoration:none}'
    '.lib-page{max-width:900px;margin:0 auto;padding:1rem 1rem 3rem}'
    '.lib-header{display:flex;flex-wrap:wrap;align-items:center;gap:.75rem;margin-bottom:1rem}'
    '.lib-header h1{font-size:1.3rem;margin:0;flex:1 1 auto;min-width:0}'
    '.caps-link{font-size:.85rem;color:#a9a9b2}'
    '.account-bar{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;justify-content:space-between;'
    'border-bottom:1px solid #26262c;padding:.75rem 0;margin-bottom:.5rem}'
    '.btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:.5rem 1rem;'
    'border-radius:8px;border:1px solid #26262c;background:#141417;color:#fff;font-weight:600;cursor:pointer}'
    '.btn-primary{background:#e5483b;border-color:#e5483b;color:#fff}'
    'button.btn,button#sign-out{font:inherit}'
    '#sign-out{min-height:44px;padding:.5rem 1rem;border-radius:8px;border:1px solid #26262c;background:#141417;'
    'color:#fff}'
    'h2{font-size:1rem;color:#a9a9b2;margin:1.5rem 0 .5rem;text-transform:uppercase;letter-spacing:.04em}'
    '.lib-grid{display:flex;flex-wrap:wrap;gap:.75rem;list-style:none;margin:0;padding:0}'
    '.lib-grid li{flex:0 0 min(200px,45vw);min-width:140px}'
    '.lib-card{display:flex;flex-direction:column;gap:.4rem;width:100%;border:1px solid #26262c;'
    'border-radius:10px;padding:.6rem;background:#141417;color:#fff;text-align:left;cursor:pointer;'
    'min-height:44px;font:inherit;box-sizing:border-box}'
    '.lib-poster{position:relative;display:block;aspect-ratio:16/9;border-radius:6px;overflow:hidden;'
    'background:#20242b}'
    '.lib-poster-fallback{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;'
    'padding:.5rem;text-align:center;font-size:.8rem;color:#a9a9b2;overflow-wrap:anywhere}'
    '.lib-poster img{position:relative;display:block;width:100%;height:100%;object-fit:cover}'
    '.lib-title{font-weight:600;font-size:.9rem;overflow-wrap:anywhere}'
    '.lib-empty{color:#a9a9b2}'
    '.howto{border:1px solid #26262c;border-radius:10px;background:#141417;padding:.25rem 1.25rem 1rem;'
    'margin:1rem 0;max-width:42rem;line-height:1.5}'
    '.howto p{color:#a9a9b2;margin:.5rem 0}.howto .howto-lead{color:#f4f4f2;font-size:1.05rem}'
    '.lib-copy{flex:0 0 auto;min-height:36px;padding:.3rem .6rem;border-radius:6px;border:1px solid #26262c;'
    'background:#0d0d10;color:#fff;font-size:.8rem}'
    '@media (max-width:480px){.lib-page{padding:.75rem .75rem 2.5rem}}'
)

LIB_DETAIL_STYLE = (
    '.lib-detail{position:relative;border:1px solid #26262c;border-radius:12px;background:#141417;color:#fff;'
    'padding:1.25rem 1rem 1rem;max-width:420px;width:92vw;box-sizing:border-box}'
    '.lib-detail::backdrop{background:rgba(0,0,0,.6)}'
    '.lib-detail h2{margin:0 1.5rem .2rem 0;font-size:1.1rem;overflow-wrap:anywhere}'
    '.lib-detail-close{position:absolute;top:.6rem;right:.6rem;min-height:36px;min-width:36px;'
    'border-radius:8px;border:1px solid #26262c;background:#0d0d10;color:#fff;font-size:1.1rem;'
    'line-height:1;cursor:pointer}'
    '.lib-detail-project{color:#a9a9b2;margin:0 0 .9rem}'
    '#lib-detail-open{margin:0 0 .9rem}'
    '.lib-detail-git{display:flex;align-items:center;gap:.5rem;margin:0 0 .9rem;min-width:0}'
    '#lib-detail-url{flex:1 1 auto;min-width:0;overflow-wrap:anywhere;word-break:break-all;font-size:.8rem;'
    'color:#bdcaaf;user-select:all}'
    '#lib-detail-meta p{margin:.4rem 0;font-size:.85rem;color:#c9c9cf}'
)

STARTER_STYLE = (
    '.starters{margin-bottom:1.5rem}'
    '.starters h2{font-size:1rem;color:#a9a9b2;margin:0 0 .6rem;text-transform:none;letter-spacing:0}'
    '.starter-grid{display:flex;gap:.75rem;overflow-x:auto;scroll-snap-type:x proximity;'
    '-webkit-overflow-scrolling:touch;margin:0;padding:0 0 .5rem;list-style:none}'
    '.starters.hero{padding:.5rem 0 1.75rem;border-bottom:1px solid #26262c;margin-bottom:1.25rem}'
    '.starter-card{display:flex;flex-direction:column;gap:.4rem;border:1px solid #26262c;border-radius:10px;'
    'padding:.6rem;background:#141417;color:#fff;text-align:left;cursor:pointer;min-height:44px;'
    'font:inherit;text-decoration:none;box-sizing:border-box;flex:0 0 min(200px,70vw);scroll-snap-align:start}'
    '.starters.hero .starter-card{flex-basis:min(220px,75vw)}'
    '.starter-poster{display:block;aspect-ratio:16/9;border-radius:6px;overflow:hidden;background:#0d0d10}'
    '.starter-poster img{display:block;width:100%;height:100%;object-fit:cover}'
    '.starter-title{font-weight:600;font-size:.9rem}'
    '.starter-prompt{font-size:.8rem;color:#a9a9b2;display:-webkit-box;-webkit-line-clamp:3;'
    '-webkit-box-orient:vertical;overflow:hidden}'
)

NEW_VIDEO_STYLE = (
    '#new-video [hidden]{display:none !important}'
    '#new-video{display:flex;flex-direction:column;gap:1rem;max-width:560px}'
    '#new-video label{display:flex;flex-direction:column;gap:.35rem;font-size:.9rem;color:#a9a9b2}'
    '#new-video input,#new-video textarea{font:inherit;min-height:44px;padding:.5rem .6rem;border-radius:8px;'
    'border:1px solid #26262c;background:#141417;color:#fff}'
    '#new-video textarea{min-height:88px;resize:vertical}'
    '#new-video .prompt{font-size:1.05rem;color:#f4f4f2;font-weight:600}'
    '#new-video .prompt textarea{min-height:150px;font-size:1.05rem;font-weight:400;border-color:#3a3a42}'
    '#new-video .prompt textarea:focus{outline:none;border-color:#e5483b;box-shadow:0 0 0 3px rgba(229,72,59,.25)}'
    '#prompt-fields{display:flex;flex-direction:column;gap:1rem}'
    '#scratch-fields{display:flex;flex-direction:column;gap:1rem}'
    '.start-from{border:1px solid #26262c;border-radius:10px;padding:.6rem .9rem;display:flex;flex-direction:column;'
    'gap:.5rem}'
    '.start-from legend{color:#a9a9b2;font-size:.85rem;padding:0 .3rem}'
    '.radio{flex-direction:row !important;align-items:center;gap:.5rem !important;min-height:44px}'
    '#create{min-height:48px;border-radius:8px;border:1px solid #e5483b;background:#e5483b;color:#fff;'
    'font-weight:600;font-size:1rem}'
    '#error{color:#f88;min-height:1.2em;margin:0}'
    '#skipped{color:#f3c969;font-size:.85rem;margin:0;max-width:560px}'
    '#skipped-continue[hidden]{display:none}'
    '#skipped-continue{margin-top:.5rem}'
)

ORDER_STYLE = (
    '#order-step{display:flex;flex-direction:column;gap:1rem;max-width:720px}'
    '#order-step[hidden]{display:none}'
    '#order-step h2{font-size:1rem;color:#a9a9b2;margin:0}'
    '.order-list{display:flex;flex-wrap:wrap;gap:.6rem;list-style:none;margin:0;padding:0}'
    '.order-item{width:120px;display:flex;flex-direction:column;gap:.3rem;border:1px solid #26262c;'
    'border-radius:8px;padding:.4rem;background:#141417;touch-action:none}'
    '.order-item img{width:100%;height:90px;object-fit:cover;border-radius:6px;display:block;background:#0d0d10}'
    '.order-name{font-size:.75rem;color:#a9a9b2;overflow-wrap:anywhere;word-break:break-all}'
    '.order-controls{display:flex;gap:.3rem}'
    '.order-controls button{flex:1;min-height:44px;min-width:44px;border-radius:6px;border:1px solid #26262c;'
    'background:#0d0d10;color:#fff;font-size:1rem}'
    '.order-controls button:disabled{opacity:.3}'
    '#order-others ul{margin:.3rem 0;padding-left:1.1rem;color:#a9a9b2;font-size:.85rem}'
    '#order-start{min-height:48px;border-radius:8px;border:1px solid #e5483b;background:#e5483b;color:#fff;'
    'font-weight:600;font-size:1rem}'
    '#order-error{color:#f88;min-height:1.2em;margin:0}'
)

NEW_VIDEO_SCRIPT = (
    '<script>'
    'const form=document.querySelector("#new-video");'
    'const sourceField=document.querySelector("#source-field");'
    'const scratchFields=document.querySelector("#scratch-fields");'
    'for(const r of form.querySelectorAll("input[name=start]"))r.onchange=()=>{'
    'const copy=form.start.value==="copy";sourceField.hidden=!copy;scratchFields.hidden=copy;'
    'document.querySelector("#prompt-fields").hidden=copy};'
    'function splitLines(s){return (s||"").split("\\n").map(x=>x.trim()).filter(Boolean)}'
    'async function uploadAll(name,video,files){'
    'const records=[],skipped=[];'
    'for(const file of files){'
    'const r=await fetch(`/v/${encodeURIComponent(name)}/api/attachments?`+new URLSearchParams('
    '{video,name:file.name}),{method:"POST",headers:{"Content-Type":file.type||"application/octet-stream"},'
    'body:file});'
    'const data=await r.json();'
    'if(!r.ok)throw Error(data.error||"could not upload "+file.name);'
    'if(/\\.zip$/i.test(file.name)){'
    'records.push(...data.attachments);'
    'for(const s of data.skipped||[])skipped.push(s.name+" ("+s.reason+")")'
    '}else{records.push(data)}}'
    'return {records,skipped}}'
    'function showSkipped(skipped){'
    'const el=document.querySelector("#skipped");'
    'el.textContent=skipped.length?'
    '`Skipped ${skipped.length} file${skipped.length===1?"":"s"}: `+skipped.join(", "):""}'
    'function waitIfSkipped(skipped){'
    'if(!skipped.length)return Promise.resolve();'
    'const btn=document.querySelector("#skipped-continue");'
    'btn.hidden=false;'
    'return new Promise(resolve=>{btn.onclick=()=>{btn.hidden=true;resolve()}})}'
    'function naturalSort(records){'
    'return records.slice().sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true}))}'
    'async function startVideo(path,description,links,attachments){'
    'const r=await fetch(`/v/${path}/api/videos/first-note`,{method:"POST",'
    'headers:{"Content-Type":"application/json"},body:JSON.stringify({description,attachments,links})});'
    'const note=await r.json();'
    'if(!r.ok)throw Error(note.error||"could not start the video")}'
    'let order=[];'
    'function moveItem(from,to){'
    'if(to<0||to>=order.length)return;'
    'const item=order.splice(from,1)[0];'
    'order.splice(to,0,item)}'
    'function startDrag(e,li,index,path){'
    'if(e.target.closest("button"))return;'
    'li.setPointerCapture(e.pointerId);'
    'const list=document.querySelector("#order-list");'
    'let to=index;'
    'const onMove=ev=>{'
    'const target=document.elementFromPoint(ev.clientX,ev.clientY);'
    'const item=target&&target.closest(".order-item");'
    'if(item&&item.parentElement===list){'
    'const idx=Array.prototype.indexOf.call(list.children,item);'
    'if(idx>=0)to=idx}};'
    'const onUp=()=>{'
    'li.removeEventListener("pointermove",onMove);li.removeEventListener("pointerup",onUp);'
    'if(to!==index)moveItem(index,to);'
    'renderOrder(path)};'
    'li.addEventListener("pointermove",onMove);'
    'li.addEventListener("pointerup",onUp)}'
    'function renderOrder(path){'
    'const ul=document.querySelector("#order-list");'
    'ul.innerHTML="";'
    'order.forEach((att,i)=>{'
    'const li=document.createElement("li");'
    'li.className="order-item";li.dataset.id=att.id;'
    'const img=document.createElement("img");'
    'img.src=`/v/${path}/api/attachments/${att.id}`;img.alt=att.name;img.draggable=false;'
    'const name=document.createElement("div");'
    'name.className="order-name";name.textContent=att.name;'
    'const controls=document.createElement("div");'
    'controls.className="order-controls";'
    'const up=document.createElement("button");'
    'up.type="button";up.textContent="\\u25c0";up.setAttribute("aria-label","Move "+att.name+" earlier");'
    'up.disabled=i===0;up.onclick=()=>{moveItem(i,i-1);renderOrder(path)};'
    'const down=document.createElement("button");'
    'down.type="button";down.textContent="\\u25b6";down.setAttribute("aria-label","Move "+att.name+" later");'
    'down.disabled=i===order.length-1;down.onclick=()=>{moveItem(i,i+1);renderOrder(path)};'
    'controls.append(up,down);'
    'li.append(img,name,controls);'
    'li.onpointerdown=e=>startDrag(e,li,i,path);'
    'ul.appendChild(li)})}'
    'function startOrderStep(path,description,links,records){'
    'form.hidden=true;'
    'const images=naturalSort(records.filter(r=>r.type.startsWith("image/")));'
    'const others=naturalSort(records.filter(r=>!r.type.startsWith("image/")));'
    'order=images;'
    'renderOrder(path);'
    'const othersEl=document.querySelector("#order-others");'
    'othersEl.innerHTML=others.length?'
    '"<p>Other files:</p><ul>"+others.map(o=>`<li>${o.name}</li>`).join("")+"</ul>":"";'
    'document.querySelector("#order-step").hidden=false;'
    'document.querySelector("#order-start").onclick=async()=>{'
    'const startButton=document.querySelector("#order-start");'
    'startButton.disabled=true;'
    'try{'
    'await startVideo(path,description,links,[...order,...others].map(a=>a.id));'
    'location.href="/v/"+path+"/"'
    '}catch(err){'
    'document.querySelector("#order-error").textContent=err.message;'
    'startButton.disabled=false}}}'
    'form.onsubmit=async e=>{'
    'e.preventDefault();'
    'const error=document.querySelector("#error"),button=document.querySelector("#create");'
    'error.textContent="";button.disabled=true;'
    'const data=new FormData(form);'
    'const name=data.get("name").trim(),start=data.get("start");'
    'try{'
    'const body={name,start};'
    'if(start==="copy")body.from=data.get("from").trim();'
    'const r=await fetch("/api/videos/new",{method:"POST",headers:{"Content-Type":"application/json"},'
    'body:JSON.stringify(body)});'
    'const result=await r.json();'
    'if(!r.ok)throw Error(result.error||"could not create the video");'
    'const path=name.split("/").map(encodeURIComponent).join("/");'
    'if(start==="blank"){'
    'const description=data.get("description")||"";'
    'const links=splitLines(data.get("links"));'
    'const files=data.getAll("files").filter(f=>f&&f.size);'
    'if(description.trim()||links.length||files.length){'
    'button.textContent="Uploading…";'
    'const {records,skipped}=await uploadAll(name,result.video,files);'
    'showSkipped(skipped);'
    'const images=records.filter(r=>r.type.startsWith("image/"));'
    'if(images.length>=2){'
    'startOrderStep(path,description,links,records);'
    'return}'
    'button.textContent="Starting…";'
    'await startVideo(path,description,links,records.map(a=>a.id));'
    'await waitIfSkipped(skipped)'
    '}}'
    'location.href="/v/"+path+"/"'
    '}catch(err){error.textContent=err.message;button.disabled=false;button.textContent="Start building"}'
    '}'
    '</script>'
)

STARTER_SCRIPT = (
    '<script>'
    '(function(){'
    'const form=document.querySelector("#new-video");'
    'function applyStarter(id){'
    'const card=document.querySelector(\'.starter-card[data-id="\'+id+\'"]\');'
    'if(!card)return;'
    'const prompt=card.dataset.prompt;'
    'const blank=form.querySelector("input[name=start][value=blank]");'
    'blank.checked=true;blank.dispatchEvent(new Event("change"));'
    'form.description.value=prompt;'
    'form.description.focus();'
    'const m=/\\[[^\\]]*\\]/.exec(prompt);'
    'if(m)form.description.setSelectionRange(m.index,m.index+m[0].length)}'
    'for(const c of document.querySelectorAll(".starter-card"))c.onclick=()=>applyStarter(c.dataset.id);'
    'const initial=new URLSearchParams(location.search).get("starter");'
    # Arriving from the library's row, the choice is already made: show the form, not the row again.
    'if(initial&&document.querySelector(\'.starter-card[data-id="\'+initial+\'"]\')){'
    'document.querySelector(".starters").hidden=true;applyStarter(initial)}'
    '})();'
    '</script>'
)


def _starter_poster_html(poster):
    return (f'<span class="starter-poster"><img src="/capabilities/{poster}.jpg" alt="" loading="lazy" '
           'onerror="this.remove()"></span>')


def _starter_card_html(s, as_link):
    title = html.escape(s['title'])
    prompt = html.escape(s['prompt'])
    poster = _starter_poster_html(s['poster'])
    if as_link:
        return (f'<a class="starter-card" href="/new?starter={quote(s["id"])}">' + poster +
               f'<span class="starter-title">{title}</span>'
               f'<span class="starter-prompt">{prompt}</span></a>')
    return (f'<button type="button" class="starter-card" data-id="{html.escape(s["id"])}" '
           f'data-prompt="{prompt}" data-needs="{html.escape(s["needs"])}">' + poster +
           f'<span class="starter-title">{title}</span>'
           f'<span class="starter-prompt">{prompt}</span></button>')


def _starter_section_html(hero, as_link, heading='Starter prompts'):
    cls = 'starters hero' if hero else 'starters'
    cards = ''.join(_starter_card_html(s, as_link) for s in STARTERS)
    return (f'<section class="{cls}"><h2>{heading}</h2>'
           f'<div class="starter-grid">{cards}</div></section>')


SHOWCASE_STYLE = (
    '.showcase{margin:0 0 1.5rem}'
    '.showcase h2{font-size:1rem;color:#a9a9b2;margin:0 0 .6rem;text-transform:none;letter-spacing:0}'
    '.showcase video{display:block;width:100%;max-width:720px;max-height:70vh;border-radius:10px;'
    'background:#0d0d10;cursor:pointer}'
    '.showcase p{font-size:.85rem;color:#a9a9b2;margin:.5rem 0 0}'
)


def _showcase_section_html():
    # The 9:16 cut for portrait screens is picked in JS, not with <source media>,
    # which older Safari and Firefox ignore.
    return ('<section class="showcase" aria-label="Showcase"><h2>What it can make</h2>'
            '<video id="showcase" poster="/capabilities/showcase-16x9.jpg" muted playsinline loop controls '
            'preload="none" aria-label="Showcase: every capability in one film"></video>'
            '<p>Every shot is something the builder can do for you; '
            '<a href="/capabilities">see them one by one</a>.</p></section>'
            '<script>(()=>{const v=document.getElementById("showcase");'
            'const f=matchMedia("(orientation:portrait)").matches?"showcase-9x16":"showcase-16x9";'
            'v.poster="/capabilities/"+f+".jpg";v.src="/capabilities/"+f+".mp4"})()</script>')


_LIB_DETAIL_HTML = (
    '<dialog id="lib-detail" class="lib-detail">'
    '<button type="button" class="lib-detail-close" aria-label="Close">&times;</button>'
    '<h2 id="lib-detail-name"></h2>'
    '<p class="lib-detail-project" id="lib-detail-project"></p>'
    '<p id="lib-detail-open"></p>'
    '<div class="lib-detail-git"><code id="lib-detail-url"></code>'
    '<button class="lib-copy" type="button" id="lib-detail-copy">Copy</button></div>'
    '<div id="lib-detail-meta">'
    '<p>Last updated: <span id="lib-detail-updated"></span></p>'
    '<p>Latest change: <span id="lib-detail-subject"></span></p>'
    '</div>'
    '</dialog>'
)

LIB_DETAIL_SCRIPT = (
    '<script>'
    '(function(){'
    'const data=JSON.parse(document.getElementById("lib-data").textContent);'
    'const dialog=document.getElementById("lib-detail");'
    'function relTime(sec){'
    'let v=Date.now()/1000-sec,unit="second";'
    'const units=[[60,"second"],[60,"minute"],[24,"hour"],[7,"day"],[4.345,"week"],[12,"month"],[Infinity,"year"]];'
    'for(const[n,u]of units){if(v<n){unit=u;break}v/=n}'
    'const n=Math.max(1,Math.round(v));'
    'return n+" "+unit+(n===1?"":"s")+" ago"}'
    'async function copyText(el){const s=el.textContent;'
    'try{await navigator.clipboard.writeText(s);return true}catch(_){}'
    'const r=document.createRange();r.selectNodeContents(el);const sel=getSelection();'
    'sel.removeAllRanges();sel.addRange(r);'
    'try{return document.execCommand("copy")}catch(_){return false}}'
    'function openDetail(idx){'
    'const d=data[idx];'
    'document.getElementById("lib-detail-name").textContent=d.leaf;'
    'document.getElementById("lib-detail-project").textContent="Project: "+d.project;'
    'const openEl=document.getElementById("lib-detail-open");'
    'openEl.textContent="";'
    'if(d.hasMain){'
    'const a=document.createElement("a");'
    'a.className="btn btn-primary";'
    'a.href="/v/"+d.name.split("/").map(encodeURIComponent).join("/")+"/";'
    'a.textContent="Open in editor";'
    'openEl.appendChild(a)'
    '}else{'
    'const span=document.createElement("span");'
    'span.className="lib-empty";span.textContent="Empty";'
    'openEl.appendChild(span)}'
    'document.getElementById("lib-detail-url").textContent=d.url;'
    'const copyBtn=document.getElementById("lib-detail-copy");'
    'copyBtn.textContent="Copy";'
    'const meta=document.getElementById("lib-detail-meta");'
    'if(d.updated){'
    'meta.hidden=false;'
    'const updatedEl=document.getElementById("lib-detail-updated");'
    'updatedEl.textContent=relTime(d.updated);'
    'updatedEl.title=new Date(d.updated*1000).toISOString();'
    'document.getElementById("lib-detail-subject").textContent=d.subject||""'
    '}else{meta.hidden=true}'
    'dialog.showModal()}'
    'for(const b of document.querySelectorAll(".lib-card"))'
    'b.onclick=()=>openDetail(Number(b.dataset.idx));'
    'document.querySelector(".lib-detail-close").onclick=()=>dialog.close();'
    'dialog.addEventListener("click",e=>{'
    'const r=dialog.getBoundingClientRect();'
    'if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close()});'
    'document.getElementById("lib-detail-copy").onclick=async()=>{'
    'const btn=document.getElementById("lib-detail-copy");'
    'const ok=await copyText(document.getElementById("lib-detail-url"));'
    'btn.textContent=ok?"Copied":"Selected \\u2014 press Ctrl+C";'
    'setTimeout(()=>{btn.textContent="Copy"},2000)}'
    '})();'
    '</script>'
)


def _howto_html(user):
    return ('<section class="howto"><h2>How it works</h2>'
            '<p class="howto-lead">Direct a video in plain words. Click <strong>+ New video</strong> and say '
            'what you want, and the builder makes a first version. Watch it, then write a note '
            '("make the title bigger here"): each note makes the next version, and every version is kept.</p>'
            '<p>Someone sharing a video with you? It shows up here once they invite '
            f'<strong>{html.escape(user)}</strong>.</p></section>')


def index(entries, accounts_enabled, user, host, scheme='http', showcase=False):
    """`entries`: [{name, has_main, updated, subject}, ...], already
    access-filtered and in order; `updated` (unix seconds) and `subject` are
    None without a main branch. `showcase`: the reel is built, so a library
    with no videos leads with it."""
    groups = {}
    for e in entries:
        group = e['name'].split('/')[0] if '/' in e['name'] else 'Videos'
        groups.setdefault(group, []).append(e)
    rows = []
    cards = []
    for group, group_entries in groups.items():
        rows.append(f'<h2>{html.escape(group)}</h2><ul class="lib-grid">')
        for e in group_entries:
            name = e['name']
            leaf = name.split('/', 1)[1] if '/' in name else name
            encoded = '/'.join(quote(p) for p in name.split('/'))
            url = f'{scheme}://{host}/git/{encoded}.git'
            idx = len(cards)
            cards.append({'name': name, 'leaf': leaf, 'project': group, 'url': url,
                         'hasMain': e['has_main'], 'updated': e['updated'], 'subject': e['subject']})
            rows.append(f'<li><button type="button" class="lib-card" data-idx="{idx}">'
                       f'<span class="lib-poster"><span class="lib-poster-fallback">{html.escape(leaf)}</span>'
                       f'<img src="/v/{encoded}/api/thumbnail" alt="" loading="lazy" '
                       'onerror="this.style.display=\'none\'"></span>'
                       f'<span class="lib-title">{html.escape(leaf)}</span></button></li>')
        rows.append('</ul>')
    account_bar = ''
    howto = ''
    body = ''.join(rows)
    can_create = bool(user) if accounts_enabled else True
    hero = not entries
    if accounts_enabled:
        account_bar = ('<div class="account-bar"><span>Signed in as <strong>' + html.escape(user) +
                       '</strong> · <a href="/account">API keys</a></span>'
                       '<button id="sign-out">Sign out</button></div>')
        if not entries:
            howto = _howto_html(user)
    starters = _starter_section_html(hero, as_link=True)
    if hero and showcase:
        starters = _showcase_section_html() + starters
    new_video = '<a class="btn btn-primary new-video" href="/new">+ New video</a>' if can_create else ''
    # A commit subject holding e.g. "<!--<script>" must not push the tokenizer into
    # the script-data double-escaped state, where a literal </script> no longer closes
    # this block: escape every '<' (and '>', '&' along with it) as a \u escape.
    cards_json = (json.dumps(cards).replace('<', '\\u003c').replace('>', '\\u003e')
                 .replace('&', '\\u0026'))
    script = ('<script>'
              'const o=document.querySelector("#sign-out");if(o)o.onclick=async()=>{'
              'await fetch("/api/logout",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});'
              'location.href="/login"};</script>'
              f'<script type="application/json" id="lib-data">{cards_json}</script>' + LIB_DETAIL_SCRIPT)
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Video library</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<style>' + LIBRARY_STYLE + LIB_DETAIL_STYLE + STARTER_STYLE + SHOWCASE_STYLE + '</style>'
            '</head><body><div class="lib-page">' + account_bar +
            '<header class="lib-header"><h1>Video library</h1>' + new_video +
            '<a class="caps-link" href="/capabilities">Capabilities</a></header>' +
            howto + starters + body + _LIB_DETAIL_HTML + script +
            '</div></body></html>').encode()


def new_video_page(names):
    options = ''.join(f'<option value="{html.escape(n)}"></option>' for n in names)
    starters = _starter_section_html(hero=False, as_link=False, heading='Or start from one of these')
    return ('<!doctype html><html><head><meta charset="utf-8"><title>New video · videobuilder</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<style>' + LIBRARY_STYLE + STARTER_STYLE + NEW_VIDEO_STYLE + ORDER_STYLE + '</style></head>'
            '<body><div class="lib-page">'
            '<header class="lib-header"><a class="btn" href="/">&larr; Library</a>'
            '<h1>New video</h1></header>'
            '<form id="new-video">'
            '<div id="prompt-fields">'
            '<label class="prompt">What do you want to make?<textarea name="description" rows="6" autofocus '
            'placeholder="A 30-second launch video for our app: open on the problem, show three features, '
            'end on the download button. Bold type, upbeat."></textarea></label>' + starters +
            '</div>'
            '<label>Name<input name="name" placeholder="name, or project/name to group it in a project" '
            'required autocapitalize="off" autocorrect="off" spellcheck="false"></label>'
            '<fieldset class="start-from"><legend>Start from</legend>'
            '<label class="radio"><input type="radio" name="start" value="blank" checked> Blank</label>'
            '<label class="radio"><input type="radio" name="start" value="copy"> A copy of an existing video</label>'
            '</fieldset>'
            f'<label id="source-field" hidden>Video to copy<input name="from" list="existing-videos" '
            f'placeholder="project/name"><datalist id="existing-videos">{options}</datalist></label>'
            '<div id="scratch-fields">'
            '<label id="files-field">Files<input name="files" type="file" multiple '
            'accept="image/*,video/*,audio/*,.pdf,.txt,.md,.zip"></label>'
            '<label id="links-field">Links (one per line)<textarea name="links" rows="3" '
            'placeholder="https://example.com/the-feature"></textarea></label>'
            '</div>'
            '<button id="create" type="submit">Start building</button>'
            '<p id="error" role="alert"></p>'
            '</form>'
            '<p id="skipped" role="status"></p>'
            '<button id="skipped-continue" class="btn" type="button" hidden>Continue</button>'
            '<div id="order-step" hidden>'
            '<h2>Order your images</h2>'
            '<p>Drag to reorder, or use the arrows below each photo. Then press Start.</p>'
            '<ul id="order-list" class="order-list"></ul>'
            '<div id="order-others"></div>'
            '<button id="order-start" type="button">Start</button>'
            '<p id="order-error" role="alert"></p>'
            '</div>'
            '</div>' + NEW_VIDEO_SCRIPT + STARTER_SCRIPT + '</body></html>').encode()


_ACCOUNT_STYLE = (
    '<style>'
    'body{font:16px system-ui;background:#181b20;color:#eee;max-width:720px;margin:0 auto;'
    'padding:1.2rem 1rem 4rem;box-sizing:border-box}'
    'h1{font-size:1.3em}a{color:#88cafa}'
    'button{cursor:pointer}button:disabled{cursor:default}'
    '.bar{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.6rem;'
    'border-bottom:1px solid #333;padding-bottom:1rem;margin-bottom:1.2rem}'
    '.bar button{min-height:44px;padding:.5rem 1rem;border-radius:6px;border:1px solid #333;'
    'background:#20242b;color:#eee}'
    'ul#keys{list-style:none;margin:0;padding:0}'
    '.key{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.4rem .8rem;'
    'padding:.8rem 0;border-bottom:1px solid #2a2e36}'
    '.key-main{flex:1 1 auto;min-width:0}.key-main strong{word-break:break-word}'
    '.badge{display:inline-block;font-size:.75em;padding:.1rem .5rem;border-radius:1em;'
    'background:#2d6cdf;color:#fff;margin-left:.4rem}.badge.read{background:#555}'
    '.key-meta{flex:1 1 100%;color:#9aa0ab;font-size:.85em}'
    'button.revoke{min-height:44px;min-width:44px;padding:.5rem 1rem;border-radius:6px;'
    'border:1px solid #633;background:#2b1d1d;color:#f88}'
    '.empty{color:#9aa0ab}'
    'form#create{display:flex;flex-direction:column;gap:.6rem;margin-top:1rem;max-width:420px}'
    'form#create input,form#create select,form#create button{min-height:44px;padding:.6rem;'
    'font-size:16px;border-radius:6px;border:1px solid #333;background:#20242b;color:#eee;'
    'box-sizing:border-box}'
    'form#create button{background:#2d6cdf;border:none;color:#fff;font-weight:600;cursor:pointer}'
    'label{display:flex;flex-direction:column;gap:.25rem;font-size:.9em;color:#bbb}'
    '#error{color:#f88;min-height:1.2em}'
    '.panel{background:#20242b;border:1px solid #333;border-radius:8px;padding:1rem;margin:1rem 0}'
    '.panel pre{display:block;background:#15171b;border-radius:6px;padding:.6rem;margin:.4rem 0 0;'
    'overflow-x:auto;word-break:break-all;white-space:pre-wrap;font-size:.85em}'
    '.panel p code{background:#15171b;border-radius:4px;padding:.1rem .3rem;font-size:.85em}'
    '.panel p{margin:1.1rem 0 0}'
    '.panel button{min-height:44px;padding:.5rem 1rem;border-radius:6px;border:1px solid #333;'
    'background:#2d6cdf;color:#fff;margin-top:.4rem}'
    '@media (max-width:480px){.key{flex-direction:column;align-items:flex-start}}'
    '.limits-default{color:#9aa0ab;margin:0 0 .8rem}'
    'ul#limits{list-style:none;margin:0;padding:0}'
    '.limit-row{padding:.8rem 0;border-bottom:1px solid #2a2e36}'
    '.limit-row-top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.3rem .8rem}'
    '.limit-usage{color:#9aa0ab;font-size:.85em}'
    '.limit-controls{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin-top:.5rem}'
    '.limit-controls select,.limit-controls input{min-height:40px;padding:.3rem .5rem;font-size:16px;'
    'border-radius:6px;border:1px solid #333;background:#20242b;color:#eee;box-sizing:border-box}'
    '.limit-custom{display:flex;flex-wrap:wrap;gap:.5rem}'
    '.limit-custom label{display:flex;flex-direction:column;gap:.15rem;font-size:.8em;color:#bbb}'
    '.limit-custom input{width:6.5rem}'
    '.limit-save{min-height:40px;padding:.4rem 1rem;border-radius:6px;border:none;background:#2d6cdf;color:#fff;'
    'font-weight:600;cursor:pointer}'
    '.limit-status{font-size:.85em;color:#8c8}'
    '@media (max-width:480px){.limit-row-top{flex-direction:column;align-items:flex-start}}'
    '</style>')

_ACCOUNT_SCRIPT = (
    '<script>'
    "const err=document.querySelector('#error');"
    "function fmtTime(s){return new Date(s*1000).toISOString().slice(0,16).replace('T',' ')+' UTC';}"
    'function keyRow(k){'
    "const li=document.createElement('li');li.className='key';li.dataset.id=k.id;"
    "const main=document.createElement('div');main.className='key-main';"
    "const strong=document.createElement('strong');strong.textContent=k.label;main.appendChild(strong);"
    "const badge=document.createElement('span');badge.className='badge'+(k.mode==='read'?' read':'');"
    'badge.textContent=k.mode;main.appendChild(badge);'
    "const meta=document.createElement('div');meta.className='key-meta';"
    "meta.textContent='Scope: '+(k.scope||'all projects')+' \\u00b7 Created: '+fmtTime(k.created)+"
    "' \\u00b7 Last used: never';"
    "const btn=document.createElement('button');btn.className='revoke';btn.type='button';"
    "btn.dataset.id=k.id;btn.textContent='Revoke';"
    'li.appendChild(main);li.appendChild(meta);li.appendChild(btn);return li;}'
    'function addRow(k){'
    "let ul=document.querySelector('#keys');"
    "if(!ul||ul.tagName!=='UL'){ul=document.createElement('ul');ul.id='keys';"
    "document.querySelector('#keys').replaceWith(ul);}"
    'ul.appendChild(keyRow(k));}'
    'function showSecret(data){'
    'const host=location.host;'
    "const panel=document.querySelector('#secret-panel');panel.hidden=false;"
    "document.querySelector('#secret-value').textContent=data.secret;"
    "document.querySelector('#git-clone').textContent="
    "'https://x:'+data.secret+'@'+host+'/git/<name>.git';"
    "document.querySelector('#git-cred').textContent="
    "'protocol=https\\nhost='+host+'\\nusername=x\\npassword='+data.secret;"
    "document.querySelector('#api-header').textContent='Authorization: Bearer '+data.secret;"
    "panel.scrollIntoView({behavior:'smooth',block:'nearest'});}"
    "document.querySelector('#create').onsubmit=async e=>{"
    "e.preventDefault();err.textContent='';"
    'const form=new FormData(e.target);'
    "const body={label:form.get('label'),mode:form.get('mode')};"
    "const scope=(form.get('scope')||'').trim();if(scope)body.scope=scope;"
    "const r=await fetch('/api/account/keys',{method:'POST',"
    "headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});"
    'const data=await r.json();'
    'if(!r.ok){err.textContent=data.error;return;}'
    'e.target.reset();addRow(data);showSecret(data);};'
    # The clipboard API can be refused (no secure context, no permission), so
    # fall back to selecting the text and execCommand, and say what happened.
    'async function copyText(el){const s=el.textContent;'
    'try{await navigator.clipboard.writeText(s);return true;}catch(_){}'
    'const r=document.createRange();r.selectNodeContents(el);const sel=getSelection();'
    'sel.removeAllRanges();sel.addRange(r);'
    "try{return document.execCommand('copy');}catch(_){return false;}}"
    "for(const b of document.querySelectorAll('button.copy'))b.onclick=async()=>{"
    "const ok=await copyText(document.getElementById(b.dataset.copy));"
    "b.textContent=ok?'Copied':'Selected \\u2014 press Ctrl+C';"
    "setTimeout(()=>{b.textContent='Copy';},2000);};"
    "document.body.addEventListener('click',async e=>{"
    "if(!e.target.classList.contains('revoke'))return;"
    'const id=e.target.dataset.id;'
    "const r=await fetch('/api/account/keys/'+encodeURIComponent(id)+'/revoke',"
    "{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});"
    'if(r.ok)location.reload();});'
    "const o=document.querySelector('#sign-out');"
    'if(o)o.onclick=async()=>{'
    "await fetch('/api/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});"
    "location.href='/login';};"
    '</script>')


def _key_row(k):
    scope = html.escape(k['scope']) if k['scope'] else 'all projects'
    created = time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(k['created']))
    last_used = time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(k['last_used'])) if k['last_used'] else 'never'
    badge = 'badge read' if k['mode'] == 'read' else 'badge'
    kid = html.escape(k['id'])
    return (f'<li class="key" data-id="{kid}"><div class="key-main"><strong>{html.escape(k["label"])}</strong>'
            f'<span class="{badge}">{k["mode"]}</span></div><div class="key-meta">Scope: {scope} &middot; '
            f'Created: {created} &middot; Last used: {last_used}</div>'
            f'<button class="revoke" type="button" data-id="{kid}">Revoke</button></li>')


_LIMIT_KIND_LABELS = (('default', 'Default'), ('custom', 'Custom'), ('unlimited', 'Unlimited'))


def _cap_text(value, unit):
    return 'No cap' if value is None else f'{value:g}{unit}'


def _limits_defaults_html(defaults):
    notes = _cap_text(defaults['notes'], ' notes/day')
    cost = _cap_text(defaults['cost_usd'], ' $/day')
    return f'<p class="limits-default">Library default: {notes} &middot; {cost}</p>'


def _limit_row_html(account):
    name = html.escape(account['name'])
    limit, usage = account['limit'], account['usage']
    options = ''.join(f'<option value="{k}"{" selected" if limit["kind"] == k else ""}>{label}</option>'
                      for k, label in _LIMIT_KIND_LABELS)
    notes_val = '' if limit['notes'] is None else limit['notes']
    cost_val = '' if limit['cost_usd'] is None else limit['cost_usd']
    custom_hidden = '' if limit['kind'] == 'custom' else ' hidden'
    admin_badge = ' <span class="badge">admin</span>' if account['admin'] else ''
    return ('<li class="limit-row" data-user="' + name + '">'
           '<div class="limit-row-top"><strong>' + name + '</strong>' + admin_badge +
           f'<span class="limit-usage">{usage["notes"]} notes today &middot; ${usage["cost_usd"]:.2f}</span></div>'
           '<div class="limit-controls">'
           f'<select class="limit-kind">{options}</select>'
           f'<span class="limit-custom"{custom_hidden}>'
           f'<label>Notes/day<input type="number" min="1" step="1" class="limit-notes" value="{notes_val}"></label>'
           f'<label>$/day<input type="number" min="0" step="0.01" class="limit-cost" value="{cost_val}"></label>'
           '</span>'
           '<button class="limit-save" type="button">Save</button>'
           '<span class="limit-status" role="status"></span>'
           '</div></li>')


def _limits_section_html(limits):
    rows = ''.join(_limit_row_html(a) for a in limits['accounts'])
    return ('<h2>Usage limits</h2>' + _limits_defaults_html(limits['defaults']) +
           f'<ul id="limits">{rows}</ul>')


_LIMITS_SCRIPT = (
    '<script>'
    "document.querySelectorAll('.limit-kind').forEach(sel=>{"
    "sel.onchange=()=>{sel.closest('.limit-row').querySelector('.limit-custom').hidden=sel.value!=='custom'}});"
    "document.querySelectorAll('.limit-save').forEach(btn=>{"
    "btn.onclick=async()=>{"
    "const row=btn.closest('.limit-row'),user=row.dataset.user;"
    "const kind=row.querySelector('.limit-kind').value;"
    "const status=row.querySelector('.limit-status');"
    "const body={user,kind,notes:null,cost_usd:null};"
    "if(kind==='custom'){"
    "const n=row.querySelector('.limit-notes').value.trim(),c=row.querySelector('.limit-cost').value.trim();"
    "body.notes=n?Number(n):null;body.cost_usd=c?Number(c):null}"
    "status.textContent='';"
    "let ok=false,msg=\"Couldn't save -- try again.\";"
    "try{const r=await fetch('/api/admin/limits',{method:'POST',headers:{'Content-Type':'application/json'},"
    "body:JSON.stringify(body)});"
    "const data=await r.json().catch(()=>({}));"
    "ok=r.ok;if(ok)msg='Saved';else if(data.error)msg=data.error}catch(_){}"
    "status.style.color=ok?'#8c8':'#f88';status.textContent=msg}});"
    '</script>')


def account_page(username, keys, limits=None):
    keys_block = ('<ul id="keys">' + ''.join(_key_row(k) for k in keys) + '</ul>' if keys
                 else '<p id="keys" class="empty">No keys yet.</p>')
    user = html.escape(username)
    limits_block = _limits_section_html(limits) if limits is not None else ''
    limits_script = _LIMITS_SCRIPT if limits is not None else ''
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Account &middot; Video library</title>'
           '<meta name="viewport" content="width=device-width, initial-scale=1">' + _ACCOUNT_STYLE +
           '</head><body>'
           '<div class="bar"><span>Signed in as <strong>' + user + '</strong></span>'
           '<button id="sign-out" type="button">Sign out</button></div>'
           '<h1>Account <a href="/">Library</a></h1>'
           '<h2>API keys</h2>'
           '<p>A key lets an agent work with your videos over git and the API, with everything it does shown '
           'as <strong>' + user + ' (label)</strong>. A write key can also start a brand-new video inside its '
           'own project (if it has one): <code>POST /api/videos/new {"name":"project/video","start":"blank"}'
           '</code> with an <code>Authorization: Bearer &lt;key&gt;</code> header.</p>' + keys_block +
           '<h2>New key</h2>'
           '<form id="create"><label>Label<input name="label" maxlength="40" required></label>'
           '<label>Project (optional: limit the key to one project, e.g. gardening)<input name="scope"></label>'
           '<label>Mode<select name="mode"><option value="write">Write</option>'
           '<option value="read">Read</option></select></label>'
           '<button>Create key</button></form><p id="error"></p>'
           '<div id="secret-panel" class="panel" hidden>'
           '<p><strong>New key secret &mdash; copy it now; it will not be shown again.</strong></p>'
           '<pre id="secret-value"></pre>'
           '<button class="copy" type="button" data-copy="secret-value">Copy</button>'
           '<p>Git clone (replace <code>&lt;name&gt;</code> with the repository):</p><pre id="git-clone"></pre>'
           '<button class="copy" type="button" data-copy="git-clone">Copy</button>'
           '<p>Git credential helper (e.g. <code>git credential approve</code>):</p><pre id="git-cred"></pre>'
           '<button class="copy" type="button" data-copy="git-cred">Copy</button>'
           '<p>API header:</p><pre id="api-header"></pre>'
           '<button class="copy" type="button" data-copy="api-header">Copy</button>'
           '</div>' + limits_block + _ACCOUNT_SCRIPT + limits_script + '</body></html>').encode()
