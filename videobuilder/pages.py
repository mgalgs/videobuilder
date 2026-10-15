"""The library's non-API HTML pages: sign-in, sign-up, the index and the New
video page. Each took a `Library` method before; here they take whatever
plain data they need, so they have no dependency on `Library` itself."""
import html
from urllib.parse import quote


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
    'const ids=[];'
    'for(const file of files){'
    'const r=await fetch(`/v/${encodeURIComponent(name)}/api/attachments?`+new URLSearchParams('
    '{video,name:file.name}),{method:"POST",headers:{"Content-Type":file.type||"application/octet-stream"},'
    'body:file});'
    'const data=await r.json();'
    'if(!r.ok)throw Error(data.error||"could not upload "+file.name);'
    'ids.push(data.id)}'
    'return ids}'
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
    'if(start==="blank"){'
    'const description=data.get("description")||"";'
    'const links=splitLines(data.get("links"));'
    'const files=data.getAll("files").filter(f=>f&&f.size);'
    'if(description.trim()||links.length||files.length){'
    'button.textContent="Uploading…";'
    'const attachments=await uploadAll(name,result.video,files);'
    'button.textContent="Starting…";'
    'const path=name.split("/").map(encodeURIComponent).join("/");'
    'const r2=await fetch(`/v/${path}/api/videos/first-note`,{method:"POST",'
    'headers:{"Content-Type":"application/json"},body:JSON.stringify({description,attachments,links})});'
    'const note=await r2.json();'
    'if(!r2.ok)throw Error(note.error||"could not start the video")'
    '}}'
    'location.href="/v/"+name.split("/").map(encodeURIComponent).join("/")+"/"'
    '}catch(err){error.textContent=err.message;button.disabled=false;button.textContent="Create"}'
    '}'
    '</script>'
)


def index(names, accounts_enabled, user, host, scheme='http'):
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
    if accounts_enabled:
        account_bar = ('<div class="account-bar"><span>Signed in as <strong>' + html.escape(user) +
                       '</strong> · <a href="/account">API keys</a></span>'
                       '<button id="sign-out">Sign out</button></div>')
        if not names:
            body = (f'<p>No videos shared with you yet — ask the owner to invite '
                    f'<strong>{html.escape(user)}</strong>.</p>')
    new_video = '<a class="btn btn-primary new-video" href="/new">+ New video</a>' if can_create else ''
    script = ('<script>'
              'for(const b of document.querySelectorAll(".lib-copy"))b.onclick=async()=>{'
              'try{await navigator.clipboard.writeText(b.dataset.url);const t=b.textContent;'
              'b.textContent="Copied";setTimeout(()=>b.textContent=t,1200)}catch(_){}};'
              'const o=document.querySelector("#sign-out");if(o)o.onclick=async()=>{'
              'await fetch("/api/logout",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});'
              'location.href="/login"};</script>')
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Video library</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<style>' + LIBRARY_STYLE + '</style>'
            '</head><body><div class="lib-page">' + account_bar +
            '<header class="lib-header"><h1>Video library</h1>' + new_video +
            '<a class="caps-link" href="/capabilities">Capabilities</a></header>' +
            body + script +
            '</div></body></html>').encode()


def new_video_page(names):
    options = ''.join(f'<option value="{html.escape(n)}"></option>' for n in names)
    return ('<!doctype html><html><head><meta charset="utf-8"><title>New video · Video library</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<style>' + LIBRARY_STYLE + NEW_VIDEO_STYLE + '</style></head><body><div class="lib-page">'
            '<header class="lib-header"><a class="btn" href="/">&larr; Library</a>'
            '<h1>New video</h1></header>'
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
            '<label>Files<input name="files" type="file" multiple '
            'accept="image/*,video/*,audio/*,.pdf,.txt,.md"></label>'
            '<label>Links (one per line)<textarea name="links" rows="3" '
            'placeholder="https://example.com/the-feature"></textarea></label>'
            '</div>'
            '<button id="create" type="submit">Create</button>'
            '<p id="error" role="alert"></p>'
            '</form></div>' + NEW_VIDEO_SCRIPT + '</body></html>').encode()
