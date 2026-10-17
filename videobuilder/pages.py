"""The library's non-API HTML pages: sign-in, sign-up, the index, the New
video page and the account page. Each took a `Library` method before; here
they take whatever plain data they need, so they have no dependency on
`Library` itself."""
import html
import json
import time
from importlib import resources
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
    '#error{color:#ff8a80;margin:.75rem 0 0;font-size:.9rem}#error:empty{display:none}'
    '.switch{margin:1.25rem 0 0;color:#a9a9b2;font-size:.92rem;text-align:center}'
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
                '<li><b>Watch the first version.</b> The builder makes it for you.</li>'
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


# The header every signed-in page shares (library, /new, /account, /capabilities):
# self-contained, so a page with its own stylesheet (the capabilities catalog) can
# take it as is. Classes are all `app-*` so they can't collide with a page's own.
APP_HEADER_STYLE = (
    '.app-bar{position:sticky;top:0;z-index:20;background:rgba(13,13,16,.88);'
    '-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);border-bottom:1px solid #1f1f25;'
    'font:16px/1.5 system-ui,sans-serif}'
    '.app-bar a:hover{text-decoration:none}'
    '.app-bar-inner{max-width:1180px;margin:0 auto;padding:.7rem 2rem;display:flex;align-items:center;'
    'gap:1.75rem;box-sizing:border-box}'
    '.app-brand{display:flex;align-items:center;gap:.6rem;flex:none;font-weight:800;font-size:1.15rem;'
    'letter-spacing:-.01em;color:#f4f4f2;text-decoration:none}'
    '.app-brand svg{width:30px;height:30px;flex:none}'
    '.app-nav{display:flex;gap:.25rem;min-width:0}'
    '.app-nav a{display:inline-flex;align-items:center;min-height:40px;padding:0 .8rem;border-radius:8px;'
    'color:#a9a9b2;font-weight:600;text-decoration:none;white-space:nowrap}'
    '.app-nav a:hover{color:#f4f4f2;background:#17171b}'
    '.app-nav a[aria-current=page]{color:#f4f4f2;background:#1c1c21}'
    '.app-actions{margin-left:auto;display:flex;align-items:center;gap:.75rem;flex:none}'
    '.app-new{display:inline-flex;align-items:center;gap:.35rem;min-height:40px;padding:0 1rem;border-radius:10px;'
    'background:#e5483b;color:#fff;font-weight:700;text-decoration:none;white-space:nowrap}'
    '.app-new:hover{background:#ef5b4c}'
    '.app-new span{font-size:1.2em;line-height:1}'
    '.app-account{position:relative}'
    '.app-account summary{display:flex;align-items:center;gap:.5rem;min-height:40px;padding:0 .5rem 0 .25rem;'
    'border-radius:999px;border:1px solid #26262c;background:#141417;color:#f4f4f2;cursor:pointer;'
    'list-style:none;font-weight:600;font-size:.92rem}'
    '.app-account summary::-webkit-details-marker{display:none}'
    '.app-account summary:hover,.app-account[open] summary{border-color:#3a3a42}'
    '.app-avatar{display:inline-flex;align-items:center;justify-content:center;width:30px;height:30px;'
    'border-radius:50%;background:#2a1715;color:#ef5b4c;font-weight:800;text-transform:uppercase;flex:none}'
    '.app-user{max-width:10rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}'
    '.app-menu{position:absolute;right:0;top:calc(100% + .5rem);min-width:220px;padding:.5rem;'
    'background:#141417;border:1px solid #26262c;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.5)}'
    '.app-menu p{margin:.35rem .6rem .5rem;color:#a9a9b2;font-size:.85rem;overflow-wrap:anywhere}'
    '.app-menu p strong{color:#f4f4f2}'
    '.app-menu a,.app-menu button{display:flex;align-items:center;width:100%;min-height:42px;padding:0 .6rem;'
    'border:0;border-radius:8px;background:none;color:#f4f4f2;font:inherit;font-size:.95rem;text-align:left;'
    'text-decoration:none;cursor:pointer;box-sizing:border-box}'
    '.app-menu a:hover,.app-menu button:hover{background:#1c1c21}'
    '@media (max-width:720px){'
    '.app-bar-inner{flex-wrap:wrap;gap:.25rem .75rem;padding:.55rem 16px .35rem}'
    '.app-nav{order:3;flex:1 0 100%}'
    '.app-nav a{min-height:38px}'
    '.app-user{display:none}'
    '.app-account summary{padding:0 .25rem}}'
    # Phone widths: brand, + New video and the avatar must share the first row,
    # with room to spare for a wider system font (iOS) than the one tested here.
    '@media (max-width:440px){.app-bar-inner{column-gap:.5rem}.app-brand{gap:.4rem;font-size:1.02rem}'
    '.app-brand svg{width:26px;height:26px}.app-actions{gap:.4rem}.app-new{padding:0 .75rem}}'
    '@media (max-width:374px){.app-brand b{display:none}}'
)

# The base for the pages that are wholly ours (library, /new, /account): the
# sign-in pages' palette, type and soft-bordered surfaces.
APP_STYLE = (
    ':root{color-scheme:dark}'
    'body{margin:0;min-height:100vh;font:16px/1.5 system-ui,sans-serif;color:#f4f4f2;'
    'background:radial-gradient(1200px 520px at 15% -12%,rgba(229,72,59,.11),transparent 60%),#0d0d10;'
    'overflow-x:hidden}'
    'a{color:#ef5b4c;text-decoration:none}a:hover{text-decoration:underline}'
    '.app-main{max-width:1180px;margin:0 auto;padding:2.25rem 2rem 4rem;box-sizing:border-box}'
    '.page-head{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:.5rem 1rem;'
    'margin:0 0 1.75rem}'
    '.page-head h1{margin:0;font-size:clamp(1.6rem,3vw,2.1rem);line-height:1.15;letter-spacing:-.02em;'
    'font-weight:800}'
    '.page-head p{margin:.35rem 0 0;color:#a9a9b2}'
    '.btn{display:inline-flex;align-items:center;justify-content:center;gap:.4rem;min-height:44px;'
    'padding:.5rem 1.1rem;border-radius:10px;border:1px solid #2c2c33;background:#141417;color:#f4f4f2;'
    'font:inherit;font-weight:600;cursor:pointer;text-decoration:none;box-sizing:border-box}'
    '.btn:hover{border-color:#3a3a42;text-decoration:none}'
    '.btn-primary{background:#e5483b;border-color:#e5483b;color:#fff;font-weight:700}'
    '.btn-primary:hover{background:#ef5b4c;border-color:#ef5b4c}'
    '@media (max-width:720px){.app-main{padding:1.5rem 16px 3rem}}'
) + APP_HEADER_STYLE

APP_HEADER_SCRIPT = (
    '<script>(()=>{'
    'const o=document.getElementById("sign-out");if(o)o.onclick=async()=>{'
    'await fetch("/api/logout",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});'
    'location.href="/login"};'
    'const m=document.querySelector(".app-account");'
    'if(m)document.addEventListener("click",e=>{if(m.open&&!m.contains(e.target))m.open=false});'
    '})()</script>')

_NAV = (('library', '/', 'Library'), ('capabilities', '/capabilities', 'Capabilities'))


def app_header(active, user=None, can_create=True):
    """The shared signed-in header: the brand (back to the library), Library
    and Capabilities, + New video, and, when there are accounts (`user`
    set), a compact account menu. `active` is the nav item to mark current
    ('library', 'capabilities' or None)."""
    nav = ''.join(f'<a href="{href}"' + (' aria-current="page"' if key == active else '') + f'>{label}</a>'
                  for key, href, label in _NAV)
    new = ('<a class="app-new" href="/new"' + (' aria-current="page"' if active == 'new' else '') +
           '><span aria-hidden="true">+</span> New video</a>') if can_create else ''
    account = ''
    if user:
        name = html.escape(user)
        account = ('<details class="app-account"><summary aria-label="Account">'
                   f'<span class="app-avatar" aria-hidden="true">{html.escape(user[:1])}</span>'
                   f'<span class="app-user">{name}</span></summary>'
                   f'<div class="app-menu"><p>Signed in as <strong>{name}</strong></p>'
                   '<a href="/account">Account &amp; API keys</a>'
                   '<button id="sign-out" type="button">Sign out</button></div></details>')
    return ('<header class="app-bar"><div class="app-bar-inner">'
            '<a class="app-brand" href="/">' + _LOGO + '<b>videobuilder</b></a>'
            f'<nav class="app-nav" aria-label="Main">{nav}</nav>'
            f'<div class="app-actions">{new}{account}</div></div></header>' + APP_HEADER_SCRIPT)


def editor_page(user=None, can_create=True):
    """editor.html for a library video, with the shared header on top. The
    `has-app-bar` body class tells director.css to drop the topbar links and
    the account bar the header now covers; phones keep the compact topbar."""
    page = resources.files(__package__).joinpath('editor.html').read_text()
    header = '<div class="desktop-only app-bar-wrap">' + app_header(None, user, can_create) + '</div>'
    return (page.replace('</head>', f'<style>{APP_HEADER_STYLE}</style></head>', 1)
            .replace('<body>', '<body class="has-app-bar">', 1)
            .replace('<div id="app">', '<div id="app">' + header, 1)).encode()


def _head(title, style):
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<title>{title} · videobuilder</title>'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<style>{style}</style></head>')


LIBRARY_STYLE = (
    '.lib-group{font-size:.78rem;color:#8b8b94;margin:0 0 .8rem;text-transform:uppercase;letter-spacing:.08em;'
    'font-weight:700}'
    '.lib-section{margin:0 0 2.25rem}'
    '.lib-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:.75rem;list-style:none;'
    'margin:0;padding:0}'
    '.lib-card{display:flex;flex-direction:column;gap:.15rem;width:100%;border:1px solid #26262c;'
    'border-radius:12px;padding:0 0 .6rem;background:#141417;color:#f4f4f2;text-align:left;cursor:pointer;'
    'min-height:44px;font:inherit;box-sizing:border-box;overflow:hidden;transition:border-color .15s,transform .15s}'
    '.lib-card:hover,.lib-card:focus-visible{border-color:#e5483b;outline:none;transform:translateY(-2px)}'
    '.lib-poster{position:relative;display:block;aspect-ratio:16/9;overflow:hidden;background:#1a1a1f;'
    'margin-bottom:.45rem}'
    '.lib-poster-fallback{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;'
    'padding:.5rem;text-align:center;font-size:.85rem;color:#5d5d66;overflow-wrap:anywhere}'
    '.lib-poster img{position:relative;display:block;width:100%;height:100%;object-fit:cover}'
    '.lib-pill{position:absolute;top:.5rem;left:.5rem;max-width:calc(100% - 1rem);box-sizing:border-box;'
    'padding:.15rem .5rem;border-radius:999px;background:rgba(10,10,12,.78);border:1px solid rgba(255,255,255,.12);'
    'color:#e4e4e8;font-size:.68rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;'
    'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;-webkit-backdrop-filter:blur(4px);'
    'backdrop-filter:blur(4px)}'
    '.lib-sort{display:inline-flex;padding:3px;border:1px solid #26262c;border-radius:10px;background:#0d0d10}'
    '.lib-sort button{min-height:36px;padding:.3rem .8rem;border:0;border-radius:7px;background:none;'
    'color:#a9a9b2;font:inherit;font-size:.85rem;cursor:pointer}'
    '.lib-sort button[aria-pressed="true"]{background:#26262c;color:#f4f4f2}'
    '.lib-title{font-weight:700;font-size:.88rem;padding:0 .7rem;overflow-wrap:anywhere}'
    '.lib-meta{font-size:.75rem;color:#8b8b94;padding:0 .7rem}'
    '.lib-empty{color:#a9a9b2}'
    '.lib-start{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:1rem 2rem;'
    'background:#141417;border:1px solid #26262c;border-radius:16px;padding:1.75rem 2rem;margin:0 0 2.25rem}'
    '.lib-start h2{margin:0 0 .3rem;font-size:1.3rem;letter-spacing:-.01em}'
    '.lib-start p{margin:0;color:#a9a9b2;max-width:36rem}'
    '.howto{border:1px solid #26262c;border-radius:16px;background:#141417;padding:1.25rem 1.5rem;'
    'margin:0 0 1.5rem;line-height:1.55}'
    '.howto h2{margin:0 0 .4rem;font-size:1.1rem}'
    '.howto p{color:#a9a9b2;margin:.5rem 0 0}.howto .howto-lead{color:#e4e4e8;font-size:1.02rem}'
    '.lib-copy{flex:0 0 auto;min-height:36px;padding:.3rem .7rem;border-radius:8px;border:1px solid #2c2c33;'
    'background:#0d0d10;color:#f4f4f2;font:inherit;font-size:.8rem;cursor:pointer}'
    '@media (max-width:720px){.lib-grid{grid-template-columns:repeat(auto-fill,minmax(105px,1fr));gap:.5rem}'
    '.lib-title,.lib-meta{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.lib-upd{display:none}'
    '.lib-title{font-size:.8rem;padding:0 .5rem}.lib-meta{font-size:.7rem;padding:0 .5rem}'
    '.lib-pill{top:.3rem;left:.3rem;font-size:.58rem;padding:.1rem .4rem}'
    '.lib-start{padding:1.25rem}.lib-start .btn{width:100%}}'
)

LIB_DETAIL_STYLE = (
    # fixed, never relative: a modal <dialog> left non-fixed opens at the top of the page,
    # not of the screen, so a tap far down the library pops it up out of sight.
    '.lib-detail{position:fixed;border:1px solid #26262c;border-radius:16px;background:#141417;color:#f4f4f2;'
    'padding:1.5rem 1.25rem 1.25rem;max-width:440px;width:calc(100vw - 32px);box-sizing:border-box;'
    'box-shadow:0 30px 80px rgba(0,0,0,.6)}'
    '.lib-detail::backdrop{background:rgba(0,0,0,.65)}'
    '.lib-detail h2{margin:0 2.5rem .2rem 0;font-size:1.25rem;letter-spacing:-.01em;overflow-wrap:anywhere}'
    '.lib-detail-close{position:absolute;top:.75rem;right:.75rem;min-height:36px;min-width:36px;'
    'border-radius:8px;border:1px solid #26262c;background:#0d0d10;color:#f4f4f2;font-size:1.1rem;'
    'line-height:1;cursor:pointer}'
    '.lib-detail-project{color:#a9a9b2;margin:0 0 1rem}'
    '#lib-detail-open{margin:0 0 1rem}'
    '.lib-detail-git{display:flex;align-items:center;gap:.5rem;margin:0 0 .9rem;min-width:0;padding:.5rem .6rem;'
    'background:#0d0d10;border:1px solid #26262c;border-radius:10px}'
    '#lib-detail-url{flex:1 1 auto;min-width:0;overflow-wrap:anywhere;word-break:break-all;font-size:.8rem;'
    'color:#c9c9cf;user-select:all}'
    '#lib-detail-meta p{margin:.4rem 0;font-size:.85rem;color:#a9a9b2}'
    '#lib-detail-meta span{color:#f4f4f2}'
)

STARTER_STYLE = (
    '.starters{margin:0 0 2.25rem}'
    '.starters h2{font-size:.78rem;color:#8b8b94;margin:0 0 .8rem;text-transform:uppercase;letter-spacing:.08em;'
    'font-weight:700}'
    '.starter-grid{display:flex;gap:.9rem;overflow-x:auto;scroll-snap-type:x proximity;'
    '-webkit-overflow-scrolling:touch;margin:0;padding:0 0 .6rem;list-style:none;scrollbar-width:thin}'
    '.starter-card{display:flex;flex-direction:column;gap:0;border:1px solid #26262c;border-radius:14px;'
    'padding:0 0 .75rem;background:#141417;color:#f4f4f2;text-align:left;cursor:pointer;min-height:44px;'
    'font:inherit;text-decoration:none;box-sizing:border-box;flex:0 0 min(230px,72vw);scroll-snap-align:start;'
    'overflow:hidden;transition:border-color .15s}'
    'a.starter-card:hover{text-decoration:none}'
    '.starter-card:hover,.starter-card:focus-visible{border-color:#e5483b;outline:none}'
    '.starter-poster{display:block;aspect-ratio:16/9;overflow:hidden;background:#1a1a1f;margin-bottom:.65rem}'
    '.starter-poster img{display:block;width:100%;height:100%;object-fit:cover}'
    '.starter-title{font-weight:600;font-size:.78rem;color:#8b8b94;padding:0 .85rem}'
    # min-height keeps the posters level across a row of cards whose prompts differ in length.
    # Margin, not padding: a line-clamped box shows the clipped line through its padding.
    '.starter-prompt{font-size:.95rem;line-height:1.4;color:#d9d9d4;font-style:italic;margin:.85rem .85rem .75rem;'
    'border-left:3px solid #e5483b;padding-left:.65rem;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;min-height:5.6em}'
    '.starters.hero .starter-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));'
    'overflow:visible}'
    '@media (max-width:720px){.starters.hero .starter-grid{grid-template-columns:repeat(auto-fill,minmax(150px,1fr));'
    'gap:.75rem}.starters.hero .starter-prompt{-webkit-line-clamp:5;min-height:7em;font-size:.88rem}}'
)

# The New video page: one centred column, prompt first. Inputs follow the sign-in
# pages' style; focus is a neutral lift, not red, so it never reads as an error.
NEW_VIDEO_STYLE = (
    '.new-wrap{max-width:780px;margin:0 auto}'
    '.new-wrap .page-head{margin-bottom:1.25rem}'
    '#new-video [hidden]{display:none !important}'
    '#new-video{display:flex;flex-direction:column;gap:1.5rem}'
    '#new-video label{display:flex;flex-direction:column;gap:.4rem;font-size:.88rem;color:#a9a9b2}'
    # 16px, not the label's .88rem: iOS zooms the page into any smaller field it focuses.
    '#new-video input:not([type=radio]):not([type=file]),#new-video textarea{font:inherit;font-size:16px;'
    'color:#f4f4f2;'
    'min-height:46px;padding:.7rem .85rem;border-radius:10px;border:1px solid #2c2c33;background:#0d0d10;'
    'outline:none;box-sizing:border-box;width:100%;transition:border-color .15s,box-shadow .15s}'
    '#new-video input:not([type=radio]):not([type=file]):focus,#new-video textarea:focus{border-color:#6b6b75;'
    'box-shadow:0 0 0 3px rgba(244,244,242,.08)}'
    '#new-video ::placeholder{color:#62626b}'
    '#new-video textarea{min-height:88px;resize:vertical}'
    '#prompt-fields{display:flex;flex-direction:column;gap:1.5rem}'
    '#new-video .prompt{font-size:1.35rem;color:#f4f4f2;font-weight:800;letter-spacing:-.015em;gap:.75rem}'
    '#new-video .prompt textarea{min-height:170px;padding:1rem 1.1rem;font-size:1.08rem;font-weight:400;'
    'line-height:1.55;letter-spacing:0;background:#141417;border-color:#2c2c33;border-radius:14px;'
    'box-shadow:0 20px 60px rgba(0,0,0,.35)}'
    '#new-video .prompt textarea:focus{border-color:#6b6b75;'
    'box-shadow:0 0 0 3px rgba(244,244,242,.08),0 20px 60px rgba(0,0,0,.35)}'
    '.details{display:flex;flex-direction:column;gap:1.1rem;background:#141417;border:1px solid #26262c;'
    'border-radius:16px;padding:1.5rem}'
    '.details>h2{margin:0;font-size:.78rem;color:#8b8b94;text-transform:uppercase;letter-spacing:.08em;'
    'font-weight:700}'
    '#scratch-fields{display:flex;flex-direction:column;gap:1.1rem}'
    '.start-from{border:0;margin:0;padding:0;min-width:0}'
    '.start-from legend{color:#a9a9b2;font-size:.88rem;padding:0;margin:0 0 .4rem}'
    '.choices{display:grid;grid-template-columns:1fr 1fr;gap:.6rem}'
    '#new-video .choice{position:relative;flex-direction:row;align-items:center;gap:.65rem;min-height:48px;'
    'padding:.6rem .85rem;border:1px solid #2c2c33;border-radius:10px;background:#0d0d10;color:#f4f4f2;'
    'font-size:.95rem;cursor:pointer;transition:border-color .15s,background .15s}'
    '#new-video .choice:hover{border-color:#3a3a42}'
    '.choice input{position:absolute;opacity:0;width:1px;height:1px;margin:0}'
    '.choice-dot{flex:none;width:18px;height:18px;border-radius:50%;border:2px solid #4a4a52;box-sizing:border-box}'
    '#new-video .choice:has(input:checked){border-color:#ef5b4c;background:#1d1312}'
    '.choice:has(input:checked) .choice-dot{border:5px solid #ef5b4c}'
    '.choice:has(input:focus-visible){box-shadow:0 0 0 3px rgba(244,244,242,.12)}'
    '.files-label{color:#a9a9b2;font-size:.88rem;margin:0 0 -.7rem}'
    '#new-video .drop{position:relative;align-items:center;justify-content:center;gap:.25rem;min-height:120px;'
    'padding:1.25rem 1rem;border:1.5px dashed #3a3a42;border-radius:12px;background:#0d0d10;text-align:center;'
    'cursor:pointer;transition:border-color .15s,background .15s}'
    '#new-video .drop:hover,#new-video .drop.over{border-color:#ef5b4c;background:#1a1211}'
    '.drop:has(input:focus-visible){box-shadow:0 0 0 3px rgba(244,244,242,.12)}'
    '.drop input{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer}'
    '.drop-title{color:#f4f4f2;font-weight:600;font-size:.98rem}'
    '.drop-title u{color:#ef5b4c;text-decoration:none}'
    '.drop-hint{color:#8b8b94;font-size:.82rem}'
    '.drop-files{color:#c9c9cf;font-size:.85rem;overflow-wrap:anywhere}'
    '.drop-files:empty{display:none}'
    '#create{min-height:52px;border-radius:12px;border:0;background:#e5483b;color:#fff;font:inherit;'
    'font-weight:700;font-size:1.05rem;cursor:pointer}'
    '#create:hover{background:#ef5b4c}#create:disabled{opacity:.6;cursor:default}'
    '#error{color:#ff8a80;margin:-.75rem 0 0;font-size:.9rem}#error:empty{display:none}'
    '#skipped{color:#f3c969;font-size:.85rem;margin:1rem 0 0}#skipped:empty{display:none}'
    '#skipped-continue[hidden]{display:none}'
    '#skipped-continue{margin-top:.5rem}'
    '@media (max-width:720px){.details{padding:1.1rem}.choices{grid-template-columns:1fr}'
    '#new-video .prompt{font-size:1.2rem}#new-video .prompt textarea{min-height:150px}}'
)

ORDER_STYLE = (
    '#order-step{display:flex;flex-direction:column;gap:1rem}'
    '#order-step[hidden]{display:none}'
    '#order-step h2{font-size:1.2rem;margin:0}'
    '#order-step p{color:#a9a9b2;margin:0}'
    '.order-list{display:flex;flex-wrap:wrap;gap:.6rem;list-style:none;margin:0;padding:0}'
    '.order-item{width:120px;display:flex;flex-direction:column;gap:.3rem;border:1px solid #26262c;'
    'border-radius:10px;padding:.4rem;background:#141417;touch-action:none}'
    '.order-item img{width:100%;height:90px;object-fit:cover;border-radius:6px;display:block;background:#0d0d10}'
    '.order-name{font-size:.75rem;color:#a9a9b2;overflow-wrap:anywhere;word-break:break-all}'
    '.order-controls{display:flex;gap:.3rem}'
    '.order-controls button{flex:1;min-height:44px;min-width:44px;border-radius:8px;border:1px solid #26262c;'
    'background:#0d0d10;color:#f4f4f2;font-size:1rem}'
    '.order-controls button:disabled{opacity:.3}'
    '#order-others ul{margin:.3rem 0;padding-left:1.1rem;color:#a9a9b2;font-size:.85rem}'
    '#order-start{min-height:52px;border-radius:12px;border:0;background:#e5483b;color:#fff;font:inherit;'
    'font-weight:700;font-size:1.05rem;cursor:pointer}'
    '#order-start:hover{background:#ef5b4c}'
    '#order-error{color:#ff8a80;margin:0;font-size:.9rem}#order-error:empty{display:none}'
)

# The drop zone is a real file input stretched over it, so a click (or a tap) opens
# the picker natively; a drop sets the same input's files, and the form reads it as before.
DROP_SCRIPT = (
    '<script>(()=>{'
    'const zone=document.getElementById("files-field");if(!zone)return;'
    'const input=zone.querySelector("input[type=file]"),list=zone.querySelector(".drop-files");'
    'const show=()=>{const n=input.files.length;list.textContent=n?(n===1?input.files[0].name:'
    'n+" files: "+[...input.files].map(f=>f.name).join(", ")):""};'
    'input.addEventListener("change",show);'
    'for(const t of ["dragenter","dragover"])zone.addEventListener(t,e=>{e.preventDefault();zone.classList.add("over")});'
    'for(const t of ["dragleave","dragend"])zone.addEventListener(t,()=>zone.classList.remove("over"));'
    'zone.addEventListener("drop",e=>{e.preventDefault();zone.classList.remove("over");'
    'if(e.dataTransfer&&e.dataTransfer.files.length){input.files=e.dataTransfer.files;show()}});'
    '})()</script>'
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

# The library's starter cards link to /new?starter=<id>; this fills the prompt in.
STARTER_SCRIPT = (
    '<script>'
    '(function(){'
    'const prompts=' + json.dumps({s['id']: s['prompt'] for s in STARTERS}).replace('</', '<\\/') + ';'
    'const prompt=prompts[new URLSearchParams(location.search).get("starter")];'
    'if(!prompt)return;'
    'const form=document.querySelector("#new-video");'
    'const blank=form.querySelector("input[name=start][value=blank]");'
    'blank.checked=true;blank.dispatchEvent(new Event("change"));'
    'form.description.value=prompt;'
    'form.description.focus();'
    'const m=/\\[[^\\]]*\\]/.exec(prompt);'
    'if(m)form.description.setSelectionRange(m.index,m.index+m[0].length)'
    '})();'
    '</script>'
)


def _starter_poster_html(poster):
    return (f'<span class="starter-poster"><img src="/capabilities/{poster}.jpg" alt="" loading="lazy" '
           'onerror="this.remove()"></span>')


def _starter_card_html(s):
    return (f'<a class="starter-card" href="/new?starter={quote(s["id"])}">'
            f'<span class="starter-prompt">{html.escape(s["prompt"])}</span>' + _starter_poster_html(s['poster']) +
            f'<span class="starter-title">{html.escape(s["title"])}</span></a>')


def _starter_section_html(hero):
    cls = 'starters hero' if hero else 'starters'
    cards = ''.join(_starter_card_html(s) for s in STARTERS)
    return (f'<section class="{cls}"><h2>Starter prompts</h2>'
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


LIB_SORT_SCRIPT = (
    '<script>(()=>{'
    'const views={recent:document.getElementById("lib-recent"),projects:document.getElementById("lib-projects")};'
    'const btns=document.querySelectorAll(".lib-sort button");'
    'function show(k,save){if(!views[k])return;'
    'for(const v in views)views[v].hidden=v!==k;'
    'for(const b of btns)b.setAttribute("aria-pressed",String(b.dataset.sort===k));'
    'if(save)try{localStorage.setItem("vb-lib-sort",k)}catch(_){}}'
    'let saved=null;try{saved=localStorage.getItem("vb-lib-sort")}catch(_){}'
    'if(saved)show(saved,false);'
    'for(const b of btns)b.onclick=()=>show(b.dataset.sort,true);'
    '})()</script>'
)


def _howto_html(user):
    return ('<section class="howto"><h2>How it works</h2>'
            '<p class="howto-lead">Direct a video in plain words. Click <strong>+ New video</strong> and say '
            'what you want, and the builder makes a first version. Watch it, then write a note '
            '("make the title bigger here"): each note makes the next version, and every version is kept.</p>'
            '<p class="howto-lead">Bring your own material too. Drop photos, clips, audio or a PDF in when '
            'you start a video or with any note, and upload longer footage under <strong>Sources</strong> '
            'in the editor.</p>'
            '<p>Someone sharing a video with you? It shows up here once they invite '
            f'<strong>{html.escape(user)}</strong>.</p></section>')


TOUR_STYLE = (
    '.tour{position:fixed;inset:0;z-index:50;display:flex;align-items:flex-start;justify-content:center;'
    'padding:4vh 1rem;overflow-y:auto;background:rgba(5,5,7,.78);'
    '-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);box-sizing:border-box}'
    '.tour[hidden]{display:none}'
    'html:has(.tour:not([hidden])){overflow:hidden}'
    '.tour-box{position:relative;width:100%;max-width:760px;background:#141417;border:1px solid #26262c;'
    'border-radius:18px;padding:2rem;box-shadow:0 40px 120px rgba(0,0,0,.7);box-sizing:border-box}'
    '.tour-box>h2{margin:0 2.5rem .35rem 0;font-size:clamp(1.5rem,3vw,1.9rem);line-height:1.15;'
    'letter-spacing:-.02em;font-weight:800}'
    '.tour-box>h2 em{font-style:normal;color:#ef5b4c}'
    '.tour-intro{margin:0 0 1.5rem;color:#a9a9b2}'
    '.tour-skip{position:absolute;top:1rem;right:1rem;min-width:40px;min-height:40px;border-radius:10px;'
    'border:1px solid #26262c;background:#0d0d10;color:#f4f4f2;font:inherit;font-size:1.2rem;line-height:1;'
    'cursor:pointer}'
    '.tour-skip:hover{border-color:#3a3a42}'
    '.tour .showcase{margin:0 0 1.25rem}'
    '.tour .showcase video{max-width:none;max-height:56vh;aspect-ratio:16/9;border-radius:12px;background:#000;'
    'box-shadow:0 0 0 1px #26262c}'
    '@media (orientation:portrait){.tour .showcase video{aspect-ratio:9/16;height:56vh;width:auto;max-width:100%;'
    'margin:0 auto}}'
    '.tour-box:focus{outline:none}'
    '.tour .howto{background:#0d0d10;margin:0 0 1.5rem}'
    '.tour-actions{display:flex;flex-wrap:wrap;align-items:center;gap:.75rem 1.25rem}'
    '.tour-later{background:none;border:0;padding:.5rem 0;color:#a9a9b2;font:inherit;cursor:pointer}'
    '.tour-later:hover{color:#f4f4f2}'
    '@media (max-width:720px){.tour{padding:16px 16px}.tour-box{padding:1.4rem 1.1rem}'
    '.tour-actions .btn{width:100%}.tour-later{width:100%}}'
)

TOUR_SCRIPT = (
    '<script>(()=>{'
    'const tour=document.getElementById("tour");if(!tour)return;'
    # Recorded on the server, so it's once per account on every device. keepalive lets
    # the request finish even though "Start your first video" navigates away at once.
    'let sent=null;'
    'const seen=()=>sent||(sent=fetch("/api/account/tour/dismiss",{method:"POST",keepalive:true,'
    'headers:{"Content-Type":"application/json"},body:"{}"}).catch(()=>{}));'
    'const reel=document.getElementById("showcase");'
    'const close=()=>{seen();if(reel)reel.pause();tour.hidden=true};'
    'for(const b of tour.querySelectorAll("[data-tour-close]"))b.onclick=close;'
    'document.getElementById("tour-start").onclick=e=>{e.preventDefault();'
    'const href=e.currentTarget.href;Promise.race([seen(),new Promise(r=>setTimeout(r,1500))])'
    '.then(()=>{location.href=href})};'
    'tour.addEventListener("click",e=>{if(e.target===tour)close()});'
    'document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!tour.hidden)close()});'
    'tour.querySelector(".tour-box").focus({preventScroll:true});'
    'if(reel&&!matchMedia("(prefers-reduced-motion: reduce)").matches)reel.play().catch(()=>{});'
    '})()</script>'
)


def _tour_html(user, showcase):
    """The first-run tour, once per account: what the builder can make (the
    reel, when it's built), how it works, and one way in."""
    return ('<div class="tour" id="tour" role="dialog" aria-modal="true" aria-labelledby="tour-title">'
            '<div class="tour-box" tabindex="-1">'
            '<button type="button" class="tour-skip" data-tour-close aria-label="Close">&times;</button>'
            '<h2 id="tour-title">Welcome to videobuilder. <em>Here\'s the idea.</em></h2>'
            '<p class="tour-intro">A quick look before you start. You\'ll only see this once.</p>' +
            (_showcase_section_html() if showcase else '') + _howto_html(user) +
            '<div class="tour-actions"><a class="btn btn-primary" id="tour-start" href="/new">'
            'Start your first video</a>'
            '<button type="button" class="tour-later" data-tour-close>Skip</button></div>'
            '</div></div>' + TOUR_SCRIPT)


def _ago(seconds, now=None):
    """'3 days ago' for a unix time: the card's quiet "last changed" line."""
    delta = max(0, (now or time.time()) - seconds)
    for size, unit in ((365 * 86400, 'year'), (30 * 86400, 'month'), (7 * 86400, 'week'), (86400, 'day'),
                       (3600, 'hour'), (60, 'minute')):
        if delta >= size:
            n = int(delta // size)
            return f'{n} {unit}{"" if n == 1 else "s"} ago'
    return 'just now'


def index(entries, accounts_enabled, user, host, scheme='http', showcase=False, tour=False):
    """`entries`: [{name, has_main, updated, subject}, ...], already
    access-filtered and in order; `updated` (unix seconds) and `subject` are
    None without a main branch. `tour`: open with the first-run tour (an
    account that hasn't dismissed it yet); `showcase`: the reel is built, so
    the tour leads with it. The library itself is only the creator's videos:
    the reel and the how-to live in the tour."""
    groups = {}
    cards = []
    for e in entries:
        name = e['name']
        group, leaf = name.split('/', 1) if '/' in name else ('Videos', name)
        groups.setdefault(group, []).append(len(cards))
        encoded = '/'.join(quote(p) for p in name.split('/'))
        cards.append({'name': name, 'leaf': leaf, 'project': group, 'url': f'{scheme}://{host}/git/{encoded}.git',
                      'hasMain': e['has_main'], 'updated': e['updated'], 'subject': e['subject'],
                      'encoded': encoded, 'inProject': '/' in name})

    def card_html(idx, pill):
        c = cards[idx]
        leaf = html.escape(c['leaf'])
        meta = f'<span class="lib-upd">Updated </span>{_ago(c["updated"])}' if c['updated'] else 'Empty'
        pill_html = (f'<span class="lib-pill">{html.escape(c["project"])}</span>'
                     if pill and c['inProject'] else '')
        return (f'<li><button type="button" class="lib-card" data-idx="{idx}">'
                f'<span class="lib-poster"><span class="lib-poster-fallback">{leaf}</span>'
                f'<img src="/v/{c["encoded"]}/api/thumbnail" alt="" loading="lazy" '
                f'onerror="this.style.display=\'none\'">{pill_html}</span>'
                f'<span class="lib-title">{leaf}</span>'
                f'<span class="lib-meta">{meta}</span></button></li>')

    # Both orders are rendered, the "by project" one hidden: the switch swaps them
    # without a reload, and hidden <img loading=lazy> never fetch.
    recent = sorted(range(len(cards)), key=lambda i: -(cards[i]['updated'] or 0))
    has_projects = any(c['inProject'] for c in cards)
    rows = ['<section class="lib-section" id="lib-recent"><ul class="lib-grid">',
            *(card_html(i, True) for i in recent), '</ul></section>']
    if has_projects:
        rows.append('<div id="lib-projects" hidden>')
        for group, idxs in groups.items():
            rows.append(f'<section class="lib-section"><h2 class="lib-group">{html.escape(group)}</h2>'
                        '<ul class="lib-grid">')
            rows.extend(card_html(i, False) for i in idxs)
            rows.append('</ul></section>')
        rows.append('</div>' + LIB_SORT_SCRIPT)
    for c in cards:
        del c['encoded'], c['inProject']
    can_create = bool(user) if accounts_enabled else True
    hero = not entries
    if hero:
        # A new account: nothing of theirs yet, so say so and point at the one next step.
        body = ('<section class="lib-start"><div><h2>No videos yet</h2>'
                '<p>Say what you want to make and the builder makes the first version. '
                'Or pick a starter below and fill in the blanks.</p></div>' +
                ('<a class="btn btn-primary" href="/new">Start your first video</a>' if can_create else '') +
                '</section>')
        content = body + _starter_section_html(True)
    else:
        content = ''.join(rows) + _starter_section_html(False)
    count = len(entries)
    sub = f'<p>{count} video{"" if count == 1 else "s"}</p>' if count else ''
    sort = ''
    if not hero and has_projects:
        sort = ('<div class="lib-sort" role="group" aria-label="Sort videos">'
                '<button type="button" data-sort="recent" aria-pressed="true">Recent</button>'
                '<button type="button" data-sort="projects" aria-pressed="false">By project</button></div>')
    # A commit subject holding e.g. "<!--<script>" must not push the tokenizer into
    # the script-data double-escaped state, where a literal </script> no longer closes
    # this block: escape every '<' (and '>', '&' along with it) as a \u escape.
    cards_json = (json.dumps(cards).replace('<', '\\u003c').replace('>', '\\u003e')
                 .replace('&', '\\u0026'))
    script = (f'<script type="application/json" id="lib-data">{cards_json}</script>' + LIB_DETAIL_SCRIPT)
    style = APP_STYLE + LIBRARY_STYLE + LIB_DETAIL_STYLE + STARTER_STYLE
    tour_html = ''
    if tour:
        style += SHOWCASE_STYLE + TOUR_STYLE
        tour_html = _tour_html(user, showcase)
    return (_head('Your videos', style) +
            '<body>' + app_header('library', user if accounts_enabled else None, can_create) +
            f'<main class="app-main"><div class="page-head"><div><h1>Your videos</h1>{sub}</div>{sort}</div>' +
            content + _LIB_DETAIL_HTML + script + '</main>' + tour_html + '</body></html>').encode()


def new_video_page(names, user=None):
    """`user`: who is signed in, for the header's account menu; None without accounts."""
    options = ''.join(f'<option value="{html.escape(n)}"></option>' for n in names)
    return (_head('New video', APP_STYLE + NEW_VIDEO_STYLE + ORDER_STYLE) +
            '<body>' + app_header('new', user) + '<main class="app-main"><div class="new-wrap">'
            '<div class="page-head"><h1>New video</h1></div>'
            '<form id="new-video">'
            '<div id="prompt-fields">'
            '<label class="prompt">What do you want to make?<textarea name="description" rows="6" autofocus '
            'placeholder="A 30-second launch video for our app: open on the problem, show three features, '
            'end on the download button. Bold type, upbeat."></textarea></label>'
            '</div>'
            '<section class="details"><h2>Details</h2>'
            '<label>Name<input name="name" placeholder="name, or project/name to group it in a project" '
            'required autocapitalize="off" autocorrect="off" spellcheck="false"></label>'
            '<fieldset class="start-from"><legend>Start from</legend><div class="choices">'
            '<label class="choice"><input type="radio" name="start" value="blank" checked>'
            '<span class="choice-dot" aria-hidden="true"></span> Blank</label>'
            '<label class="choice"><input type="radio" name="start" value="copy">'
            '<span class="choice-dot" aria-hidden="true"></span> A copy of an existing video</label>'
            '</div></fieldset>'
            f'<label id="source-field" hidden>Video to copy<input name="from" list="existing-videos" '
            f'placeholder="project/name"><datalist id="existing-videos">{options}</datalist></label>'
            '<div id="scratch-fields">'
            '<p class="files-label">Files</p>'
            '<label id="files-field" class="drop"><input name="files" type="file" multiple '
            'accept="image/*,video/*,audio/*,.pdf,.txt,.md,.zip" aria-label="Files">'
            '<span class="drop-title">Drop files here or <u>browse</u></span>'
            '<span class="drop-hint">Photos, video, audio, PDF, text, or a .zip of them</span>'
            '<span class="drop-files" aria-live="polite"></span></label>'
            '<label id="links-field">Links (one per line)<textarea name="links" rows="3" '
            'placeholder="https://example.com/the-feature"></textarea></label>'
            '</div></section>'
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
            '</div></main>' + NEW_VIDEO_SCRIPT + STARTER_SCRIPT + DROP_SCRIPT + '</body></html>').encode()


_ACCOUNT_STYLE = (
    '.account{max-width:760px;margin:0 auto}'
    '.account h2{font-size:1.1rem;margin:0 0 .5rem;letter-spacing:-.01em}'
    '.account section.box{background:#141417;border:1px solid #26262c;border-radius:16px;padding:1.5rem;'
    'margin:0 0 1.25rem}'
    '.account .lead{color:#a9a9b2;margin:0 0 1rem;overflow-wrap:anywhere}'
    '.account .lead strong{color:#f4f4f2}'
    '.account code{background:#0d0d10;border:1px solid #26262c;border-radius:6px;padding:.05rem .35rem;'
    'font-size:.85em;overflow-wrap:anywhere}'
    'button{cursor:pointer}button:disabled{cursor:default}'
    'ul#keys{list-style:none;margin:0;padding:0}'
    '.key{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.4rem .8rem;'
    'padding:.85rem 0;border-top:1px solid #22222a}'
    '.key-main{flex:1 1 auto;min-width:0}.key-main strong{word-break:break-word}'
    '.badge{display:inline-block;font-size:.72em;font-weight:700;padding:.1rem .55rem;border-radius:1em;'
    'background:#2a1715;color:#ef5b4c;margin-left:.45rem;text-transform:uppercase;letter-spacing:.04em}'
    '.badge.read{background:#1f1f25;color:#a9a9b2}'
    '.key-meta{flex:1 1 100%;color:#8b8b94;font-size:.85em}'
    'button.revoke{min-height:40px;padding:0 .9rem;border-radius:8px;border:1px solid #4a2522;'
    'background:transparent;color:#ff8a80;font:inherit;font-size:.9rem}'
    'button.revoke:hover{background:#2a1715}'
    '.empty{color:#8b8b94;margin:0}'
    'form#create{display:grid;grid-template-columns:1fr 1fr;gap:.9rem 1rem;margin-top:.25rem}'
    'form#create label{display:flex;flex-direction:column;gap:.35rem;font-size:.85rem;color:#a9a9b2}'
    'form#create .wide{grid-column:1/-1}'
    'form#create input,form#create select{min-height:46px;padding:.6rem .8rem;font:inherit;border-radius:10px;'
    'border:1px solid #2c2c33;background:#0d0d10;color:#f4f4f2;box-sizing:border-box;width:100%;outline:none}'
    'form#create input:focus,form#create select:focus{border-color:#55555f;box-shadow:0 0 0 3px rgba(239,91,76,.18)}'
    'form#create button{grid-column:1/-1;justify-self:start;min-height:46px;padding:0 1.4rem;border:none;'
    'border-radius:10px;background:#e5483b;color:#fff;font:inherit;font-weight:700}'
    'form#create button:hover{background:#ef5b4c}'
    '#error{color:#ff8a80;margin:.75rem 0 0;font-size:.9rem}#error:empty{display:none}'
    '.panel{background:#141417;border:1px solid #4a2522;border-radius:16px;padding:1.5rem;margin:0 0 1.25rem}'
    '.panel pre{display:block;background:#0d0d10;border:1px solid #26262c;border-radius:8px;padding:.6rem .75rem;'
    'margin:.4rem 0 0;overflow-x:auto;word-break:break-all;white-space:pre-wrap;font-size:.85em}'
    '.panel p{margin:1.1rem 0 0;color:#c9c9cf}.panel p:first-child{margin-top:0}'
    '.panel button{min-height:40px;padding:0 1rem;border-radius:8px;border:1px solid #2c2c33;background:#1c1c21;'
    'color:#f4f4f2;font:inherit;font-size:.9rem;margin-top:.5rem}'
    '.limits-default{color:#8b8b94;margin:0 0 .8rem}'
    'ul#limits{list-style:none;margin:0;padding:0}'
    '.limit-row{padding:.85rem 0;border-top:1px solid #22222a}'
    '.limit-row-top{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:.3rem .8rem}'
    '.limit-usage{color:#8b8b94;font-size:.85em}'
    '.limit-controls{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin-top:.5rem}'
    '.limit-controls select,.limit-controls input{min-height:40px;padding:.3rem .55rem;font-size:16px;'
    'border-radius:8px;border:1px solid #2c2c33;background:#0d0d10;color:#f4f4f2;box-sizing:border-box}'
    '.limit-custom{display:flex;flex-wrap:wrap;gap:.5rem}'
    '.limit-custom label{display:flex;flex-direction:column;gap:.15rem;font-size:.8em;color:#a9a9b2}'
    '.limit-custom input{width:6.5rem}'
    '.limit-save{min-height:40px;padding:.4rem 1rem;border-radius:8px;border:none;background:#e5483b;color:#fff;'
    'font:inherit;font-weight:700}'
    '.limit-status{font-size:.85em;color:#8c8}'
    '@media (max-width:560px){.account section.box,.panel{padding:1.1rem}'
    'form#create{grid-template-columns:1fr}.key{flex-direction:column;align-items:flex-start}'
    '.limit-row-top{flex-direction:column;align-items:flex-start}}'
)

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
    limits_block = ('<section class="box">' + _limits_section_html(limits) + '</section>'
                    if limits is not None else '')
    limits_script = _LIMITS_SCRIPT if limits is not None else ''
    return (_head('Account', APP_STYLE + _ACCOUNT_STYLE) +
           '<body>' + app_header(None, username) + '<main class="app-main"><div class="account">'
           '<div class="page-head"><div><h1>Account</h1>'
           '<p>Signed in as <strong>' + user + '</strong></p></div></div>'
           '<section class="box"><h2>API keys</h2>'
           '<p class="lead">A key lets an agent work with your videos over git and the API, with everything it '
           'does shown as <strong>' + user + ' (label)</strong>. A write key can also start a brand-new video '
           'inside its own project (if it has one): <code>POST /api/videos/new {"name":"project/video",'
           '"start":"blank"}</code> with an <code>Authorization: Bearer &lt;key&gt;</code> header.</p>' +
           keys_block + '</section>'
           '<section class="box"><h2>New key</h2>'
           '<form id="create"><label class="wide">Label<input name="label" maxlength="40" required></label>'
           '<label>Project (optional: limit the key to one project, e.g. gardening)<input name="scope"></label>'
           '<label>Mode<select name="mode"><option value="write">Write</option>'
           '<option value="read">Read</option></select></label>'
           '<button>Create key</button></form><p id="error"></p></section>'
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
           '</div>' +
           limits_block + '</div></main>' + _ACCOUNT_SCRIPT + limits_script + '</body></html>').encode()
