"""The library's non-API HTML pages: sign-in, sign-up, the index, the New
video page and the account page. Each took a `Library` method before; here
they take whatever plain data they need, so they have no dependency on
`Library` itself."""
import html
import time
from urllib.parse import quote

from .starters import STARTERS


_AUTH_STYLE = ('<style>body{font:16px system-ui;background:#181b20;color:#eee;max-width:420px;margin:4rem auto;'
              'padding:0 1rem}input,button{display:block;width:100%;margin:.4rem 0;padding:.7rem;font-size:16px;'
              'box-sizing:border-box;border-radius:6px;border:1px solid #333;background:#20242b;color:#eee;'
              'min-height:44px}button{background:#2d6cdf;border:none;color:#fff;font-weight:600;cursor:pointer}'
              'a{color:#88cafa}#error{color:#f88;min-height:1.2em}'
              '@media (max-width:700px){body{margin:2rem auto}}</style>')


def signin_page(error=None):
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Sign in · Video library</title>'
           '<meta name="viewport" content="width=device-width, initial-scale=1">' + _AUTH_STYLE +
           '</head><body><h1>Video library</h1><form id="f">'
           '<label>Username<input name="username" autocomplete="username" required></label>'
           '<label>Password<input name="password" type="password" autocomplete="current-password" required>'
           '</label><button>Sign in</button></form><p id="error"></p><p><a href="/signup">Sign up</a></p>'
           '<script>document.querySelector("#f").onsubmit=async e=>{e.preventDefault();'
           'const form=new FormData(e.target);const r=await fetch("/api/login",{method:"POST",'
           'headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(form))});'
           'if(r.ok)location.href="/";else document.querySelector("#error").textContent=(await r.json()).error};'
           '</script></body></html>').encode()


def signup_page():
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Sign up · Video library</title>'
           '<meta name="viewport" content="width=device-width, initial-scale=1">' + _AUTH_STYLE +
           '</head><body><h1>Video library</h1><form id="f">'
           '<label>Username<input name="username" autocomplete="username" required></label>'
           '<label>Password<input name="password" type="password" autocomplete="new-password" required></label>'
           '<label>Confirm password<input name="confirm" type="password" autocomplete="new-password" required>'
           '</label><button>Sign up</button></form><p id="error"></p><p><a href="/login">Sign in</a></p>'
           '<script>document.querySelector("#f").onsubmit=async e=>{e.preventDefault();'
           'const form=new FormData(e.target);const r=await fetch("/api/signup",{method:"POST",'
           'headers:{"Content-Type":"application/json"},body:JSON.stringify(Object.fromEntries(form))});'
           'if(r.ok)location.href="/";else document.querySelector("#error").textContent=(await r.json()).error};'
           '</script></body></html>').encode()


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
    '.lib-grid{display:flex;flex-direction:column;gap:.75rem}'
    '.lib-card{border:1px solid #26262c;border-radius:10px;padding:.75rem .9rem;background:#141417;min-width:0}'
    '.lib-card-top{display:flex;align-items:center;justify-content:space-between;gap:.6rem;min-width:0}'
    '.lib-name{overflow-wrap:anywhere;min-width:0}'
    '.lib-empty{color:#a9a9b2}'
    '.lib-git{display:flex;align-items:center;gap:.5rem;margin-top:.5rem;min-width:0}'
    '.lib-url{flex:1 1 auto;min-width:0;overflow-wrap:anywhere;word-break:break-all;font-size:.8rem;color:#bdcaaf;'
    'user-select:all}'
    '.lib-copy{flex:0 0 auto;min-height:36px;padding:.3rem .6rem;border-radius:6px;border:1px solid #26262c;'
    'background:#0d0d10;color:#fff;font-size:.8rem}'
    '@media (max-width:480px){.lib-page{padding:.75rem .75rem 2.5rem}.lib-card-top{flex-wrap:wrap}}'
)

STARTER_STYLE = (
    '.starters{margin-bottom:1.5rem}'
    '.starters h2{font-size:1rem;color:#a9a9b2;margin:0 0 .6rem;text-transform:none;letter-spacing:0}'
    '.starter-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:.75rem;'
    'margin:0;padding:0;list-style:none}'
    '.starters.hero{padding:.5rem 0 1.75rem;border-bottom:1px solid #26262c;margin-bottom:1.25rem}'
    '.starters.hero .starter-grid{grid-template-columns:repeat(auto-fill,minmax(170px,1fr))}'
    '.starter-card{display:flex;flex-direction:column;gap:.4rem;border:1px solid #26262c;border-radius:10px;'
    'padding:.6rem;background:#141417;color:#fff;text-align:left;cursor:pointer;min-height:44px;'
    'font:inherit;text-decoration:none;box-sizing:border-box;width:100%}'
    '.starter-poster{display:block;aspect-ratio:16/9;border-radius:6px;overflow:hidden;background:#0d0d10}'
    '.starter-poster img{display:block;width:100%;height:100%;object-fit:cover}'
    '.starter-title{font-weight:600;font-size:.9rem}'
    '.starter-prompt{font-size:.8rem;color:#a9a9b2;display:-webkit-box;-webkit-line-clamp:3;'
    '-webkit-box-orient:vertical;overflow:hidden}'
    '#files-field.starter-highlight,#links-field.starter-highlight{outline:2px solid #e5483b;'
    'border-radius:8px}'
)

NEW_VIDEO_STYLE = (
    '#new-video [hidden]{display:none !important}'
    '#new-video{display:flex;flex-direction:column;gap:1rem;max-width:560px}'
    '#new-video label{display:flex;flex-direction:column;gap:.35rem;font-size:.9rem;color:#a9a9b2}'
    '#new-video input,#new-video textarea{font:inherit;min-height:44px;padding:.5rem .6rem;border-radius:8px;'
    'border:1px solid #26262c;background:#141417;color:#fff}'
    '#new-video textarea{min-height:88px;resize:vertical}'
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
    'const copy=form.start.value==="copy";sourceField.hidden=!copy;scratchFields.hidden=copy};'
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
    '}catch(err){error.textContent=err.message;button.disabled=false;button.textContent="Create"}'
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
    'const prompt=card.dataset.prompt,needs=card.dataset.needs;'
    'const blank=form.querySelector("input[name=start][value=blank]");'
    'blank.checked=true;blank.dispatchEvent(new Event("change"));'
    'form.description.value=prompt;'
    'for(const l of form.querySelectorAll(".starter-highlight"))l.classList.remove("starter-highlight");'
    'const target=needs==="files"?document.querySelector("#files-field"):'
    'needs==="links"?document.querySelector("#links-field"):null;'
    'if(target)target.classList.add("starter-highlight");'
    'form.description.focus();'
    'const m=/\\[[^\\]]*\\]/.exec(prompt);'
    'if(m)form.description.setSelectionRange(m.index,m.index+m[0].length)}'
    'for(const c of document.querySelectorAll(".starter-card"))c.onclick=()=>applyStarter(c.dataset.id);'
    'const initial=new URLSearchParams(location.search).get("starter");'
    'if(initial)applyStarter(initial)'
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


def _starter_section_html(hero, as_link):
    cls = 'starters hero' if hero else 'starters'
    cards = ''.join(_starter_card_html(s, as_link) for s in STARTERS)
    return (f'<section class="{cls}"><h2>Start with one of these</h2>'
           f'<div class="starter-grid">{cards}</div></section>')


def index(names, accounts_enabled, user, host, scheme='http', is_admin=False):
    """`names`: [(name, has_main), ...], already access-filtered and in order."""
    groups = {}
    for name, _ in names:
        namespace = name.split('/')[0] if '/' in name else 'Videos'
        groups.setdefault(namespace, []).append(name)
    has_main = dict(names)
    rows = []
    for group, group_names in groups.items():
        rows.append(f'<h2>{html.escape(group)}</h2><div class="lib-grid">')
        for name in group_names:
            encoded = '/'.join(quote(p) for p in name.split('/'))
            url = f'{scheme}://{host}/git/{encoded}.git'
            open_or_empty = (f'<a class="btn" href="/v/{encoded}/">Open</a>' if has_main[name]
                             else '<span class="lib-empty">Empty</span>')
            rows.append('<div class="lib-card"><div class="lib-card-top">'
                       f'<strong class="lib-name">{html.escape(name)}</strong>{open_or_empty}</div>'
                       f'<div class="lib-git"><code class="lib-url">{html.escape(url)}</code>'
                       f'<button class="lib-copy" type="button" data-url="{html.escape(url)}" '
                       'aria-label="Copy git URL">Copy</button></div></div>')
        rows.append('</div>')
    account_bar = ''
    body = ''.join(rows)
    can_create = bool(user) if accounts_enabled else True
    hero = not names
    if accounts_enabled:
        account_bar = ('<div class="account-bar"><span>Signed in as <strong>' + html.escape(user) +
                       '</strong> · <a href="/account">API keys</a></span>'
                       '<button id="sign-out">Sign out</button></div>')
        if not names:
            body = (f'<p>No videos shared with you yet — ask the owner to invite '
                    f'<strong>{html.escape(user)}</strong>.</p>')
    starters = _starter_section_html(hero, as_link=True)
    new_video = '<a class="btn btn-primary new-video" href="/new">+ New video</a>' if can_create else ''
    compendium_link = '<a class="caps-link" href="/compendium">Compendium</a>' if is_admin else ''
    script = ('<script>'
              'for(const b of document.querySelectorAll(".lib-copy"))b.onclick=async()=>{'
              'try{await navigator.clipboard.writeText(b.dataset.url);const t=b.textContent;'
              'b.textContent="Copied";setTimeout(()=>b.textContent=t,1200)}catch(_){}};'
              'const o=document.querySelector("#sign-out");if(o)o.onclick=async()=>{'
              'await fetch("/api/logout",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});'
              'location.href="/login"};</script>')
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Video library</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<style>' + LIBRARY_STYLE + STARTER_STYLE + '</style>'
            '</head><body><div class="lib-page">' + account_bar +
            '<header class="lib-header"><h1>Video library</h1>' + new_video +
            '<a class="caps-link" href="/capabilities">Capabilities</a>' + compendium_link + '</header>' +
            starters + body + script +
            '</div></body></html>').encode()


def new_video_page(names):
    options = ''.join(f'<option value="{html.escape(n)}"></option>' for n in names)
    starters = _starter_section_html(hero=False, as_link=False)
    return ('<!doctype html><html><head><meta charset="utf-8"><title>New video · Video library</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<style>' + LIBRARY_STYLE + STARTER_STYLE + NEW_VIDEO_STYLE + ORDER_STYLE + '</style></head>'
            '<body><div class="lib-page">'
            '<header class="lib-header"><a class="btn" href="/">&larr; Library</a>'
            '<h1>New video</h1></header>' + starters +
            '<form id="new-video">'
            '<label>Name<input name="name" placeholder="namespace/name" required autocapitalize="off" '
            'autocorrect="off" spellcheck="false"></label>'
            '<fieldset class="start-from"><legend>Start from</legend>'
            '<label class="radio"><input type="radio" name="start" value="blank" checked> Blank</label>'
            '<label class="radio"><input type="radio" name="start" value="copy"> A copy of an existing video</label>'
            '</fieldset>'
            f'<label id="source-field" hidden>Source video<input name="from" list="existing-videos" '
            f'placeholder="namespace/name"><datalist id="existing-videos">{options}</datalist></label>'
            '<div id="scratch-fields">'
            '<label>Description<textarea name="description" rows="5" '
            'placeholder="What is this video for? Who is it for?"></textarea></label>'
            '<label id="files-field">Files<input name="files" type="file" multiple '
            'accept="image/*,video/*,audio/*,.pdf,.txt,.md,.zip"></label>'
            '<label id="links-field">Links (one per line)<textarea name="links" rows="3" '
            'placeholder="https://example.com/the-feature"></textarea></label>'
            '</div>'
            '<button id="create" type="submit">Create</button>'
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
    '.panel code,.panel pre{display:block;background:#15171b;border-radius:6px;padding:.6rem;'
    'overflow-x:auto;word-break:break-all;white-space:pre-wrap;font-size:.85em}'
    '.panel button{min-height:44px;padding:.5rem 1rem;border-radius:6px;border:1px solid #333;'
    'background:#2d6cdf;color:#fff;margin-top:.4rem}'
    '@media (max-width:480px){.key{flex-direction:column;align-items:flex-start}}'
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
    "document.querySelector('#copy-btn').onclick=()=>{"
    "navigator.clipboard.writeText(document.querySelector('#secret-value').textContent);};"
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


def account_page(username, keys):
    keys_block = ('<ul id="keys">' + ''.join(_key_row(k) for k in keys) + '</ul>' if keys
                 else '<p id="keys" class="empty">No keys yet.</p>')
    user = html.escape(username)
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Account &middot; Video library</title>'
           '<meta name="viewport" content="width=device-width, initial-scale=1">' + _ACCOUNT_STYLE +
           '</head><body>'
           '<div class="bar"><span>Signed in as <strong>' + user + '</strong></span>'
           '<button id="sign-out" type="button">Sign out</button></div>'
           '<h1>Account <a href="/">Library</a></h1>'
           '<h2>API keys</h2>'
           '<p>A key lets an agent work with your videos over git and the API, with everything it does shown '
           'as <strong>' + user + ' (label)</strong>.</p>' + keys_block +
           '<h2>New key</h2>'
           '<form id="create"><label>Label<input name="label" maxlength="40" required></label>'
           '<label>Scope (optional namespace, e.g. gardening)<input name="scope"></label>'
           '<label>Mode<select name="mode"><option value="write">Write</option>'
           '<option value="read">Read</option></select></label>'
           '<button>Create key</button></form><p id="error"></p>'
           '<div id="secret-panel" class="panel" hidden>'
           '<p><strong>New key secret &mdash; copy it now; it will not be shown again.</strong></p>'
           '<code id="secret-value"></code><button id="copy-btn" type="button">Copy</button>'
           '<p>Git clone (replace <code>&lt;name&gt;</code> with the repository):</p><pre id="git-clone"></pre>'
           '<p>Git credential helper (e.g. <code>git credential approve</code>):</p><pre id="git-cred"></pre>'
           '<p>API header:</p><pre id="api-header"></pre>'
           '</div>' + _ACCOUNT_SCRIPT + '</body></html>').encode()
