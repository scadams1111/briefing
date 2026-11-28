"""The web reading experience: 'Midnight' story cards. One story per screen,
swipe or tap Next to move through the day's briefing."""
from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path
from urllib.parse import quote, urlsplit

DOCS = Path("docs")
e = html.escape

FONTS = ("<link rel='preconnect' href='https://fonts.googleapis.com'>"
         "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
         "<link href='https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700"
         "&family=Inter:wght@400;500;600;700&display=swap' rel='stylesheet'>")

CSS = r"""
:root{
  --bg:#0B1220; --card:#131C2E; --tile:#172136; --tile-open:#1C2740; --ink:#EAF0FA; --muted:#8D9AB3;
  --detail:#BAC5D8; --accent:#F2B544; --on-accent:#1A1305; --img:#1E2A44; --line:#2A3653;
  --serif:"Fraunces","New York",Georgia,serif;
  --sans:"Inter",-apple-system,BlinkMacSystemFont,system-ui,sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased;-webkit-text-size-adjust:100%}
a{color:inherit;text-decoration:none}
button{font:inherit;color:inherit;cursor:pointer}

/* shell */
.top{max-width:560px;margin:0 auto;padding:calc(14px + env(safe-area-inset-top)) 16px 0;display:flex;align-items:center;justify-content:space-between;gap:12px}
/* story pages: a fixed app frame, so the page itself never scrolls out of reach */
body.app{position:fixed;inset:0;display:flex;flex-direction:column;overflow:hidden;overscroll-behavior:none}
body.app .top{flex:none;width:100%}
body.app .reader{flex:1;min-height:0;height:auto;width:100%}
.brand{font-family:var(--serif);font-weight:700;font-size:21px;letter-spacing:-.01em}
.brand span{color:var(--accent)}
.tabs{display:flex;gap:2px;background:var(--tile);padding:3px;border-radius:999px}
.tabs a{font-size:13px;font-weight:600;padding:7px 12px;border-radius:999px;color:var(--muted)}
.tabs a.on{background:var(--line);color:var(--ink)}
@media (max-width:430px){.tabs a{padding:7px 9px}}
.tabs a svg{display:block;margin:1px 0}

/* story deck */
.reader{max-width:560px;margin:0 auto;height:calc(100dvh - 58px);display:flex;flex-direction:column;padding:12px 0 calc(14px + env(safe-area-inset-bottom))}
.bars{display:flex;gap:4px;padding:0 16px}
.bars button{flex:1;height:14px;border:0;background:none;padding:5px 0}
.bars button i{display:block;height:3px;border-radius:2px;background:var(--line);transition:background .2s}
.bars button.seen i{background:var(--ink)}
.status{display:flex;justify-content:space-between;align-items:center;padding:8px 16px 10px;font-size:13px;color:var(--muted)}
.status b{color:var(--ink);font-weight:600}
.deck{flex:1;min-height:0;display:flex;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;scrollbar-width:none;overscroll-behavior-x:contain}
.deck::-webkit-scrollbar{display:none}
.slide{flex:0 0 100%;scroll-snap-align:start;scroll-snap-stop:always;padding:0 16px;display:flex}
.card{flex:1;min-width:0;border-radius:24px;background:var(--card);overflow:hidden;display:flex;flex-direction:column}
.scroll{overflow-y:auto;flex:1;min-height:0;overscroll-behavior:contain}
.media{position:relative;height:190px;background:var(--img);display:flex;align-items:flex-end;padding:14px}
.media img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.pill{position:relative;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;background:var(--accent);color:var(--on-accent);padding:5px 9px;border-radius:6px}
.body{padding:16px 18px 20px;display:flex;flex-direction:column;gap:12px}
.src{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--muted)}
.src img{width:16px;height:16px;border-radius:4px;background:var(--tile)}
h1.head{margin:0;font-family:var(--serif);font-weight:700;font-size:25px;line-height:1.16;letter-spacing:-.01em}
.room{margin:0;font-family:var(--serif);font-style:italic;font-size:16px;line-height:1.5;color:var(--detail)}
.points{display:flex;flex-direction:column;gap:8px}
.points details{border-radius:14px;background:var(--tile)}
.points details[open]{background:var(--tile-open)}
.points summary{list-style:none;display:flex;gap:10px;padding:12px;font-size:14.5px;line-height:1.42;font-weight:600;cursor:pointer}
.points summary::-webkit-details-marker{display:none}
.points summary .n{color:var(--accent);flex:none;width:12px}
.points summary svg{flex:none;margin-left:auto;margin-top:2px;color:var(--muted);transition:transform .2s}
.points details[open] summary svg{transform:rotate(180deg)}
.points p{margin:0;padding:0 14px 14px 34px;font-size:14px;line-height:1.6;color:var(--detail)}
.why{font-size:13px;line-height:1.5;color:var(--muted);border-top:1px solid var(--line);padding-top:12px}
.why b{color:var(--ink);font-weight:600}
.fb{display:flex;gap:8px;flex-wrap:wrap;padding-top:2px}
.fbb{display:inline-flex;align-items:center;gap:6px;height:36px;padding:0 12px;border-radius:10px;border:1px solid var(--line);
  background:transparent;color:var(--muted);font-size:13px;font-weight:600}
.fbb.on[data-act=more]{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
.fbb.on[data-act=less]{background:var(--line);border-color:var(--muted);color:var(--ink)}
.toast{position:fixed;left:50%;bottom:calc(84px + env(safe-area-inset-bottom));transform:translateX(-50%);max-width:92vw;
  background:var(--ink);color:var(--bg);font-size:14px;font-weight:600;padding:11px 16px;border-radius:12px;z-index:50;
  box-shadow:0 8px 24px rgba(0,0,0,.4);text-align:center}
.toast a{text-decoration:underline}
.listen{display:flex;align-items:center;gap:12px;margin:0 16px 10px;padding:8px 12px 8px 8px;border-radius:14px;background:var(--tile)}
.listen .pb{flex:none;width:36px;height:36px;border-radius:50%;border:0;background:var(--accent);color:var(--on-accent);
  display:flex;align-items:center;justify-content:center}
.listen .lt{flex:1;min-width:0;font-size:13px;font-weight:600}
.listen .lt small{display:block;font-weight:500;color:var(--muted);font-size:11.5px;margin-top:2px}
.listen .bar{height:3px;border-radius:2px;background:var(--line);margin-top:6px;overflow:hidden}
.listen .bar i{display:block;height:100%;width:0;background:var(--accent)}
.listen .sp{flex:none;font-size:12px;font-weight:700;color:var(--muted);border:1px solid var(--line);border-radius:8px;padding:4px 7px;background:none}
.extras{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding-top:4px}
.chip{display:inline-flex;align-items:center;gap:7px;height:36px;padding:0 13px;border-radius:10px;border:1px solid var(--line);background:var(--tile);color:var(--detail);font-size:13px;font-weight:600;transition:background .15s,border-color .15s}
.chip svg{color:var(--accent)}
.chip:hover,.chip:active{background:var(--tile-open);border-color:var(--muted)}
.hint{font-size:12px;color:var(--muted)}

.actions{display:flex;gap:10px;padding:12px 16px 0}
.btn{flex:1;height:48px;border-radius:14px;border:1px solid var(--line);background:transparent;display:flex;align-items:center;justify-content:center;gap:6px;font-size:15px;font-weight:600}
.btn.icon{flex:none;width:48px}
.btn.primary{background:var(--ink);color:var(--bg);border-color:var(--ink);font-weight:700}
.btn[disabled]{opacity:.35}

/* end slide + lists */
.end h1{margin:4px 0 2px;font-family:var(--serif);font-size:28px}
.toc{display:flex;flex-direction:column}
.toc button,.toc a{display:flex;gap:12px;align-items:baseline;text-align:left;width:100%;padding:12px 0;border:0;border-bottom:1px solid var(--line);background:none;font-size:15px;line-height:1.35}
.toc .k{color:var(--accent);font-weight:700;flex:none;width:18px}
.toc small{display:block;color:var(--muted);font-size:12px;margin-top:3px}
.page{max-width:560px;margin:0 auto;padding:10px 16px 60px}
.page .card{margin:14px 0}
.hero{padding:18px 4px 6px}
.hero .kicker{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}
.hero h1{margin:6px 0 4px;font-family:var(--serif);font-size:32px;line-height:1.1}
.hero p{margin:0;color:var(--muted);font-size:14px}
.empty{color:var(--muted);text-align:center;padding:60px 0}
.foot{color:var(--muted);font-size:12px;text-align:center;margin-top:14px}
.foot a{text-decoration:underline}
.subs{display:flex;flex-direction:column;gap:10px}
.sub{display:flex;flex-direction:column;gap:6px;padding:14px;border-radius:14px;background:var(--tile)}
.sub strong{font-family:var(--serif);font-size:18px;line-height:1.25}
.sub .tk{font-size:14px;line-height:1.5;color:var(--detail)}
.subhit{display:flex;flex-direction:column;gap:6px}
.subrow{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:4px}
.sub .open{display:flex;align-items:center;gap:4px;font-size:13px;font-weight:700;color:var(--accent)}
.chip.sm{height:32px;padding:0 10px;font-size:12px;border-radius:9px;background:var(--card)}

/* ── design system: one set of tokens and components for every page ── */
:root{--sp1:4px;--sp2:8px;--sp3:12px;--sp4:16px;--sp5:24px;--sp6:32px;
  --rad-s:10px;--rad-m:14px;--rad-l:20px;--rad-xl:24px;--tap:44px;
  --fs-xs:12px;--fs-s:13.5px;--fs-m:15px;--fs-l:17px;--ease:cubic-bezier(.2,.7,.2,1)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:6px}
::selection{background:color-mix(in srgb,var(--accent) 35%,transparent)}
button,.btn,.chip,.fbb,.tabs a,.toc a,.toc button{-webkit-tap-highlight-color:transparent;transition:transform .12s var(--ease),background .15s,border-color .15s,color .15s}
button:active,.btn:active,.chip:active,.fbb:active{transform:scale(.97)}
/* header: same on every page, sticky and blurred on scrolling pages */
body:not(.app) .top{position:sticky;top:0;z-index:20;max-width:none;
  padding:calc(12px + env(safe-area-inset-top)) max(16px,calc((100% - 528px)/2)) 12px;
  background:color-mix(in srgb,var(--bg) 84%,transparent);backdrop-filter:saturate(1.6) blur(16px);-webkit-backdrop-filter:saturate(1.6) blur(16px);
  border-bottom:1px solid color-mix(in srgb,var(--line) 70%,transparent)}
.tabs a{min-height:32px;display:flex;align-items:center}
/* buttons and chips share sizes, corners and type */
.btn{height:48px;border-radius:var(--rad-m);font-size:var(--fs-m)}
.chip,.fbb{height:40px;border-radius:12px;padding:0 14px;font-size:var(--fs-s);font-weight:600;gap:7px}
.chip{background:var(--tile);border:1px solid var(--line);color:var(--detail)}
.savebtn{font-family:inherit;cursor:pointer}
.savebtn.on{color:var(--accent);border-color:var(--accent)}
.savebtn.on svg{fill:currentColor}
.fbb{background:transparent}
.chip.sm{height:34px;padding:0 11px;font-size:var(--fs-xs);border-radius:10px}
/* surfaces */
.card{border-radius:var(--rad-xl)}
.bg,.fresh{border-radius:var(--rad-l)}
.page .card{margin:var(--sp4) 0}
.body{padding:var(--sp4) 18px 20px;gap:var(--sp3)}
.extras,.fb{gap:var(--sp2)}
/* page titles and section labels */
.hero{padding:var(--sp5) 2px var(--sp2)}
.hero h1{font-size:32px;letter-spacing:-.015em}
.hero p{font-size:var(--fs-s);line-height:1.5}
.label{font-size:11.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin:var(--sp6) 2px var(--sp1)}
/* story image fallback: quiet tile with the topic's initial */
.media.noimg::after{content:attr(data-k);position:absolute;right:14px;top:-18px;font-family:var(--serif);font-weight:700;
  font-size:150px;line-height:1;color:color-mix(in srgb,var(--ink) 7%,transparent);pointer-events:none}
.media.noimg{background:linear-gradient(160deg,color-mix(in srgb,var(--accent) 9%,var(--img)),var(--img) 60%)}
/* empty and loading states */
.empty{padding:56px 20px;font-size:var(--fs-m);line-height:1.5}
.empty::before{content:"";display:block;width:44px;height:44px;margin:0 auto 14px;border-radius:50%;
  background:color-mix(in srgb,var(--accent) 16%,transparent);box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 40%,transparent)}
.skel{background:linear-gradient(90deg,var(--tile) 0%,var(--tile-open) 50%,var(--tile) 100%);background-size:200% 100%;animation:shimmer 1.3s linear infinite!important}
@keyframes shimmer{from{background-position:200% 0}to{background-position:-200% 0}}
.toast{border-radius:var(--rad-m);animation:pop .2s var(--ease)}
@keyframes pop{from{transform:translate(-50%,8px);opacity:0}to{transform:translate(-50%,0);opacity:1}}
.offline{position:fixed;bottom:calc(84px + env(safe-area-inset-bottom));left:50%;white-space:nowrap;transform:translateX(-50%);z-index:70;
  background:var(--tile);border:1px solid var(--line);color:var(--detail);font:600 12.5px var(--sans);padding:7px 12px;border-radius:999px;
  box-shadow:0 6px 18px rgba(0,0,0,.35)}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

CHEV = ("<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' "
        "aria-hidden='true'><path d='M6 9l6 6 6-6'/></svg>")
NEXT = ("<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' "
        "aria-hidden='true'><path d='M9 5l7 7-7 7'/></svg>")
BOOKMARK = ("<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
            "stroke-linejoin='round' aria-hidden='true'><path d='M6 3h12v18l-6-4-6 4z'/></svg>")


def save_btn(url: str, title: str, cls: str = "chip") -> str:
    return (f"<button type='button' class='{cls} savebtn' data-url='{e(url)}' data-title='{e(title)}'>"
            f"{BOOKMARK}<span>Save</span></button>")


ARCHIVE = ("<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
           "stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><rect x='3' y='4' width='18' height='4' rx='1'/>"
           "<path d='M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8M10 12h4'/></svg>")
ARROWUP = ("<svg width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' "
           "aria-hidden='true'><path d='M7 17L17 7M8 7h9v9'/></svg>")
SEARCH_ICON = ("<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' "
               "stroke-linecap='round' aria-hidden='true'><circle cx='11' cy='11' r='7'/><path d='M20 20l-4-4'/></svg>")
THUMB_UP = ("<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
            "stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><path d='M7 10v11H4V10zM7 10l4-8a3 3 0 0 1 3 3v4h5.5a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18 21H7'/></svg>")
THUMB_DOWN = ("<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
              "stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><path d='M17 14V3h3v11zM17 14l-4 8a3 3 0 0 1-3-3v-4H4.5a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 6 3h11'/></svg>")
PLAY = "<svg width='16' height='16' viewBox='0 0 24 24' fill='currentColor' aria-hidden='true'><path d='M7 4.5v15l13-7.5z'/></svg>"
PAUSE = "<svg width='16' height='16' viewBox='0 0 24 24' fill='currentColor' aria-hidden='true'><path d='M6 4h4v16H6zM14 4h4v16h-4z'/></svg>"
HEADPHONES = ("<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
              "stroke-linecap='round' aria-hidden='true'><path d='M3 18v-6a9 9 0 0 1 18 0v6'/><path d='M21 19a2 2 0 0 1-2 2h-1v-6h3zM3 19a2 2 0 0 0 2 2h1v-6H3z'/></svg>")
BOOK = ("<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
        "stroke-linecap='round' aria-hidden='true'><path d='M2 4h7a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H2zM22 4h-7a3 3 0 0 0-3 3v13a2 2 0 0 1 2-2h8z'/></svg>")
PREV = ("<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' "
        "aria-hidden='true'><path d='M15 5l-7 7 7 7'/></svg>")

# Article links open in a new tab, so the briefing stays where you left it.
NEWTAB = r"""document.querySelectorAll('a[href^="http"],a[data-orig]').forEach(a=>{a.target='_blank';a.rel='noopener'})"""

FEEDBACK_JS = r"""
(()=>{const repo=document.body.dataset.repo;const KEY='gh_token';
const toast=(html,ms=2600)=>{let t=document.querySelector('.toast');if(!t){t=document.createElement('div');t.className='toast';document.body.appendChild(t)}
 t.innerHTML=html;t.hidden=false;clearTimeout(t._h);t._h=setTimeout(()=>t.hidden=true,ms)};
const root=document.body.dataset.root||'';
const get=k=>{try{return localStorage.getItem(k)}catch(_){return null}}, set=(k,v)=>{try{v==null?localStorage.removeItem(k):localStorage.setItem(k,v)}catch(_){}};
document.querySelectorAll('.fb').forEach(box=>{const id='fb:'+(box.dataset.id||box.dataset.url),cur=get(id);
 box.querySelectorAll('.fbb').forEach(b=>{b.classList.toggle('on',b.dataset.act===cur);b.setAttribute('aria-pressed',b.dataset.act===cur)})});
document.addEventListener('click',async ev=>{const b=ev.target.closest('.fbb');if(!b)return;const box=b.closest('.fb');
 const token=get(KEY);if(!token){toast(`One-time setup needed. <a href="${root}settings.html">Set up feedback</a>`,6000);return}
 const id='fb:'+(box.dataset.id||box.dataset.url),prev=get(id),act=b.dataset.act;
 const send=async(a)=>{const item={url:box.dataset.url,topic:box.dataset.topic,source:box.dataset.source,title:box.dataset.title};
  const r=await fetch(`https://api.github.com/repos/${repo}/issues`,{method:'POST',headers:{Authorization:'Bearer '+token,
   Accept:'application/vnd.github+json','Content-Type':'application/json'},body:JSON.stringify({title:'feedback: '+a,body:JSON.stringify(item)})});
  if(!r.ok)throw new Error(r.status)};
 try{if(prev)await send('undo-'+prev);
  if(prev===act){set(id,null);toast('Removed')}else{await send(act);set(id,act);
   toast(act==='more'?'Got it. More like this from tomorrow':'Got it. Less like this from tomorrow')}
  box.querySelectorAll('.fbb').forEach(x=>{const on=x.dataset.act===get(id);x.classList.toggle('on',on);x.setAttribute('aria-pressed',on)});
 }catch(err){toast(`Couldn't send (${err.message}). <a href="${root}settings.html">Check setup</a>`,6000)}});
/* save for later from inside the briefing */
const norm=u=>{try{const x=new URL(u);return (x.hostname.replace(/^www\./,'')+x.pathname.replace(/\/+$/,'')).toLowerCase()}catch(_){return u}};
const mark=b=>{b.classList.add('on');b.querySelector('span').textContent='Saved'};
fetch(root+'saved.json',{cache:'no-store'}).then(r=>r.json()).then(list=>{const have=new Set(list.map(norm));
 document.querySelectorAll('.savebtn').forEach(b=>{if(have.has(norm(b.dataset.url))||get('saved:'+norm(b.dataset.url)))mark(b)})}).catch(()=>{
 document.querySelectorAll('.savebtn').forEach(b=>{if(get('saved:'+norm(b.dataset.url)))mark(b)})});
document.addEventListener('click',async ev=>{const b=ev.target.closest('.savebtn');if(!b)return;ev.preventDefault();ev.stopPropagation();
 if(b.classList.contains('on')){toast(`Already saved. <a href="${root}saved.html">Open Saved</a>`);return}
 const token=get(KEY);if(!token){toast(`One-time setup needed. <a href="${root}settings.html">Set up</a>`,6000);return}
 b.querySelector('span').textContent='Saving…';
 try{const r=await fetch(`https://api.github.com/repos/${repo}/issues`,{method:'POST',headers:{Authorization:'Bearer '+token,
   Accept:'application/vnd.github+json','Content-Type':'application/json'},body:JSON.stringify({title:'Save: '+(b.dataset.title||b.dataset.url).slice(0,120),body:b.dataset.url})});
  if(!r.ok)throw new Error(r.status);set('saved:'+norm(b.dataset.url),'1');mark(b);
  toast('Saved. It appears in Saved in a couple of minutes, with a summary and audio.',4500)}
 catch(err){b.querySelector('span').textContent='Save';toast(`Couldn't save (${err.message}). <a href="${root}settings.html">Check setup</a>`,6000)}},true);
const a=document.querySelector('.listen audio');if(a){const pb=document.querySelector('.listen .pb'),bar=document.querySelector('.listen .bar i'),
 sp=document.querySelector('.listen .sp'),lab=document.querySelector('.listen .lt small');const rates=[1,1.25,1.5,0.85];let ri=0;
 const fmt=s=>`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;
 pb.onclick=()=>{a.paused?a.play():a.pause()};a.onplay=()=>{pb.innerHTML=pb.dataset.pause;pb.setAttribute('aria-label','Pause')};
 a.onpause=()=>{pb.innerHTML=pb.dataset.play;pb.setAttribute('aria-label','Play')};
 a.ontimeupdate=()=>{if(a.duration){bar.style.width=(100*a.currentTime/a.duration)+'%';lab.textContent=fmt(a.currentTime)+' / '+fmt(a.duration);
  try{localStorage.setItem('audio:'+a.dataset.date,a.currentTime)}catch(_){}}};
 a.onloadedmetadata=()=>{const t=+get('audio:'+a.dataset.date);if(t&&t<a.duration-5)a.currentTime=t};
 sp.onclick=()=>{ri=(ri+1)%rates.length;a.playbackRate=rates[ri];sp.textContent=rates[ri]+'×'}}
})();
"""

JS = r"""
(()=>{const deck=document.querySelector('.deck');if(!deck)return;
const slides=[...deck.children],bars=[...document.querySelectorAll('.bars button')],
 num=document.querySelector('.status b'),prev=document.querySelector('[data-prev]'),
 next=document.querySelector('[data-next]'),orig=document.querySelector('[data-orig]'),n=slides.length,
 stories=slides.filter(s=>!s.dataset.label).length;
const go=i=>deck.scrollTo({left:Math.max(0,Math.min(n-1,i))*deck.clientWidth,behavior:'smooth'});
let cur=-1;const upd=()=>{const i=Math.round(deck.scrollLeft/deck.clientWidth);if(i===cur)return;cur=i;
 bars.forEach((b,k)=>b.classList.toggle('seen',k<=i));
 num.textContent=slides[i].dataset.label||`${i+1} of ${stories}`;
 prev.disabled=i===0;next.querySelector('span').textContent=i<n-2?'Next story':(i===n-2?'Finish':'Start over');
 const u=slides[i].dataset.url;orig.style.visibility=u?'visible':'hidden';if(u)orig.href=((document.body.dataset.root||'')+'read.html?u=')+encodeURIComponent(u)+(slides[i].dataset.audio?'&a='+encodeURIComponent(slides[i].dataset.audio):'');
 try{history.replaceState(null,'',i?`#${i+1}`:location.pathname)}catch(_){}};
deck.addEventListener('scroll',()=>requestAnimationFrame(upd),{passive:true});
prev.onclick=()=>go(cur-1);next.onclick=()=>go(cur<n-1?cur+1:0);
bars.forEach((b,k)=>b.onclick=()=>go(k));
document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>go(+b.dataset.go));
addEventListener('keydown',ev=>{if(ev.target.closest('input,textarea'))return;
 if(ev.key==='ArrowRight')go(cur+1);if(ev.key==='ArrowLeft')go(cur-1)});
addEventListener('resize',()=>{const c=cur;cur=-1;deck.scrollLeft=c*deck.clientWidth;upd()});
const h=parseInt(location.hash.slice(1));if(h>1){deck.scrollLeft=(h-1)*deck.clientWidth}
upd();})();
"""


def _domain(url: str) -> str:
    return urlsplit(url).netloc.removeprefix("www.")


def card(it: dict, root: str = "") -> str:
    """One story card: image, source, headline, takeaway, 3 expandable points."""
    img = (f"<img src='{e(it['image'])}' alt='' loading='lazy' referrerpolicy='no-referrer' "
           f"onerror=\"this.parentNode.classList.add('noimg');this.remove()\">") if it.get("image") else ""
    fav = f"https://www.google.com/s2/favicons?domain={e(_domain(it['url']))}&sz=64"
    pts = "".join(
        f"<details{' open' if n == 1 else ''}><summary><span class='n'>{n}</span><span>{e(b['point'])}</span>"
        f"{CHEV if b.get('detail') else ''}</summary>"
        + (f"<p>{e(b['detail'])}</p>" if b.get("detail") else "") + "</details>"
        for n, b in enumerate(it["bullets"], 1))
    room = f"<p class='room'>“{e(it['room_line'])}”</p>" if it.get("room_line") else ""
    # Backup if the original page has moved or vanished: Wayback Machine's latest snapshot
    fbdata = (f"data-id='{e(it.get('id', ''))}' data-url='{e(it['url'])}' data-topic='{e(it.get('topic', ''))}' "
              f"data-source='{e(it['source'])}' data-title='{e(it.get('headline') or it.get('title', ''))}'")
    feedback = (f"<div class='fb' {fbdata}><button type='button' class='fbb' data-act='more'>{THUMB_UP}<span>More like this</span></button>"
                f"<button type='button' class='fbb' data-act='less'>{THUMB_DOWN}<span>Less like this</span></button></div>")
    au = (it.get("audio") or {}).get("url", "")
    read_href = f"{root}read.html?u={e(quote(it['url'], safe=''))}" + (f"&amp;a={e(quote(au, safe=''))}" if au else "")
    read_chip = (f"<a class='chip' href='{read_href}'>{HEADPHONES if au else BOOK}<span>{'Read or listen' if au else 'Read'}</span></a>")
    archived = (f"<div class='extras'>{read_chip}{save_btn(it['url'], it.get('headline') or it.get('title', ''))}<a class='chip' href='https://wallhop.io/{e(it['url'])}'>"
                f"{ARCHIVE}<span>Archived copy</span></a><span class='hint'>if the link is broken</span></div>")
    initial = e((it.get("topic_name") or it.get("source") or "B")[:1].upper())
    return (f"<article class='card'><div class='scroll'>"
            f"<div class='media{'' if img else ' noimg'}' data-k='{initial}'>{img}<span class='pill'>{e(it.get('topic_name') or 'Story')}</span></div>"
            f"<div class='body'><div class='src'><img src='{fav}' alt='' referrerpolicy='no-referrer'>"
            f"{e(it['source'])} · {it['minutes']} min read</div>"
            f"<h1 class='head'><a href='{e(it['url'])}'>{e(it['headline'])}</a></h1>{room}"
            f"<div class='points'>{pts}</div>{feedback}{archived}</div></div></article>")


def shell(title: str, active: str, body: str, root: str = "", script: bool = False) -> str:
    tabs = "".join(f"<a href='{root}{href}' class='{'on' if active == k else ''}'>{label}</a>"
                   for k, label, href in (("today", "Today", "./"), ("saved", "Saved", "saved.html"),
                                          ("archive", "Archive", "archive/")))
    tabs += (f"<a href='{root}games.html' class='{'on' if active == 'games' else ''}' aria-label='Games'>"
             f"{_games().PUZZLE_ICON}</a>")
    tabs += (f"<a href='{root}search.html' class='{'on' if active == 'search' else ''}' aria-label='Search'>"
             f"{SEARCH_ICON}</a>")
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            "<meta name='theme-color' content='#0B1220'><meta name='apple-mobile-web-app-capable' content='yes'>"
            "<meta name='apple-mobile-web-app-status-bar-style' content='black-translucent'>"
            "<meta name='apple-mobile-web-app-title' content='Briefing'>"
            f"<link rel='apple-touch-icon' href='{root}apple-touch-icon.png'>"
            f"<link rel='manifest' href='{root}manifest.webmanifest'>"
            f"<title>{e(title)}</title>{FONTS}<style>{CSS}</style></head><body class='{'app' if script else ''}' data-repo='{e(_repo())}' data-root='{e(root)}' data-relay='{e(_relay_url())}'>"
            f"<header class='top'><a class='brand' href='{root}./'>Briefing<span>.</span></a>"
            f"<nav class='tabs'>{tabs}</nav></header>{body}"
            + (f"<script>{JS}</script>" if script else "") + f"<script>{NEWTAB}</script><script>{FEEDBACK_JS}</script><script>{_offline().REGISTER}</script></body></html>")


def section_of(it: dict) -> str:
    return it.get("section") or ("nyt" if "nytimes.com" in it.get("url", "") else "premium")


SECTIONS = {
    "nyt": ("The New York Times", "Today in the Times", "The best and most relevant Times stories today. Opens in your NYT app."),
    "premium": ("Premium picks", "From top publications", "Paywalled pieces worth opening with your subscription."),
}


def subs_slide(subs: list[dict], root: str = "", section: str = "premium") -> str:
    pill, title, sub = SECTIONS[section]
    rows = "".join(
        f"<div class='sub'><a class='subhit' href='{e(i['url'])}'><span class='src'>"
        + (e(i.get('topic_name', '')) if section == "nyt" else f"{e(i['source'])} · {e(i.get('topic_name', ''))}")
        + f"</span><strong>{e(i['headline'])}</strong><span class='tk'>{e(i.get('takeaway', ''))}</span></a>"
        f"<div class='subrow'><a class='open' href='{e(i['url'])}'>Open article {NEXT}</a>{save_btn(i['url'], i['headline'], 'chip sm')}"
        f"<a class='chip sm' href='https://wallhop.io/{e(i['url'])}'>{ARCHIVE}<span>Link broken?</span></a></div></div>"
        for i in subs)
    return (f"<section class='slide' data-url='' data-label='{e(pill)}'><article class='card'><div class='scroll'><div class='body'>"
            f"<span class='pill' style='align-self:flex-start'>{e(pill)}</span>"
            f"<h1 class='head'>{e(title)}</h1><p class='room' style='font-style:normal;font-family:var(--sans);font-size:14px'>{e(sub)}</p>"
            f"<div class='subs'>{rows}</div></div></div></article></section>")


def deep_slide(d: dict, root: str = "") -> str:
    img = (f"<img src='{e(d['image'])}' alt='' loading='lazy' referrerpolicy='no-referrer' onerror=\"this.remove()\">"
           if d.get("image") else "")
    pts = "".join(
        f"<details{' open' if n == 1 else ''}><summary><span class='n'>{n}</span><span>{e(p['point'])}</span>{CHEV}</summary>"
        f"<p>{e(p.get('detail', ''))}</p></details>" for n, p in enumerate(d["points"], 1))
    reading = [{"url": d["wiki_url"], "title": d["wiki_title"], "source": "Wikipedia"}] + (d.get("reading") or [])
    rows = "".join(f"<a href='{e(r['url'])}'><span class='k'>{ARROWUP}</span><span>{e(r['title'])}"
                   f"<small>{e(r['source'])}</small></span></a>" for r in reading)
    return (f"<section class='slide' data-url='{e(d['wiki_url'])}' data-label='Deep dive'><article class='card'><div class='scroll'>"
            f"<div class='media'>{img}<span class='pill'>Deep dive · {e(d.get('field', ''))}</span></div>"
            f"<div class='body'><div class='src'>{e(d.get('topic', ''))}</div>"
            f"<h1 class='head'>{e(d['headline'])}</h1>"
            + (f"<p class='room'>{e(d['why'])}</p>" if d.get("why") else "")
            + f"<div class='points'>{pts}</div>"
            f"<div class='label' style='margin:6px 0 0'>Go deeper</div>"
            f"<div class='toc'>{rows}</div>"
            f"<p class='foot' style='text-align:left;margin-top:4px'>Primer based on "
            f"<a href='{e(d['wiki_url'])}'>Wikipedia</a> (CC BY-SA).</p></div></div></article></section>")


def listen_bar(date: str) -> str:
    p = Path("data") / "audio" / f"{date}.json"
    if not p.exists():
        return ""
    m = json.loads(p.read_text())
    m["url"] = relay_audio(m["url"])
    return (f"<div class='listen'><button type='button' class='pb' aria-label='Play' data-play=\"{PLAY}\" data-pause=\"{PAUSE}\">{PLAY}</button>"
            f"<div class='lt'>Listen to today's briefing<small>{max(1, round(m['seconds'] / 60))} min</small>"
            f"<div class='bar'><i></i></div></div><button type='button' class='sp' aria-label='Playback speed'>1×</button>"
            f"<audio preload='none' data-date='{e(date)}' src='{e(m['url'])}'></audio></div>")


def relay_audio(url: str) -> str:
    """Stream release audio through the Cloudflare relay (GitHub serves it as a download iPhone won't play)."""
    try:
        import yaml
        relay = (yaml.safe_load(open("config.yaml")) or {}).get("relay_url", "")
    except Exception:
        relay = ""
    return f"{relay.rstrip('/')}/audio?url={quote(url, safe='')}" if relay and url else url


def deck(date: str, picks: list[dict], root: str = "", subs: list[dict] | None = None,
         smart: dict | None = None) -> str:
    d = dt.date.fromisoformat(date)
    n = len(picks)
    if not n:
        return "<main class='page'><p class='empty'>Nothing yet today.</p></main>"
    groups = [(sec, [i for i in subs or [] if section_of(i) == sec]) for sec in ("nyt", "premium")]
    groups = [(sec, items) for sec, items in groups if items]
    smart = smart or {}
    deep, evergreen = smart.get("deep"), smart.get("picks") or []
    total = n + (1 if deep else 0) + len(evergreen) + len(groups) + 1
    bars = "".join(f"<button type='button' aria-label='Slide {k + 1}'><i></i></button>" for k in range(total))
    slides = "".join(f"<section class='slide' data-url='{e(i['url'])}' data-audio='{e((i.get('audio') or {}).get('url', ''))}'>"
                     f"{card(i, root)}</section>" for i in picks)
    if deep:
        slides += deep_slide(deep, root)
    slides += "".join(f"<section class='slide' data-url='{e(i['url'])}' data-label='Get smarter'>{card(i, root)}</section>"
                      for i in evergreen)
    for sec, items in groups:
        slides += subs_slide(items, root, sec)
    mins = sum(i.get("minutes", 0) for i in picks)
    toc = "".join(f"<button type='button' data-go='{k}'><span class='k'>{k + 1}</span>"
                  f"<span>{e(i['headline'])}<small>{e(i['source'])} · {i['minutes']} min</small></span></button>"
                  for k, i in enumerate(picks))
    end = (f"<section class='slide end' data-label='All done'><article class='card'><div class='scroll'><div class='body'>"
           f"<div class='src'>{d.strftime('%A, %B')} {d.day}</div><h1>You're caught up.</h1>"
           f"<div class='src'>{n} stories · about {mins} min if you read them all</div>"
           f"<div class='toc'>{toc}</div>"
           f"<p class='foot'><a href='{root}epub/latest.epub'>Download as EPUB</a> · "
           f"<a href='{root}archive/'>Past briefings</a> · <a href='{root}highlights.html'>Highlights</a> · <a href='{root}podcast.html'>Podcast</a> · "
           f"<a href='{root}settings.html'>Settings</a></p></div></div></article></section>")
    return (f"<main class='reader'>{listen_bar(date)}<div class='bars'>{bars}</div>"
            f"<div class='status'><b>1 of {n}</b><span>{d.strftime('%a, %b')} {d.day}</span></div>"
            f"<div class='deck'>{slides}{end}</div>"
            f"<div class='actions'><button type='button' class='btn icon' data-prev aria-label='Previous story'>{PREV}</button>"
            f"<a class='btn' data-orig href='#'>Read</a>"
            f"<button type='button' class='btn primary' data-next><span>Next story</span>{NEXT}</button></div></main>")


READER_CSS = r"""
.rd{max-width:640px;margin:0 auto;padding:8px 18px 80px}
.rd .bar{display:flex;align-items:center;gap:10px;padding:10px 0 14px}
.rd .back{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:12px;border:1px solid var(--line);background:var(--tile)}
.rd .meta{font-size:12.5px;color:var(--muted);line-height:1.4}
.rd .meta b{color:var(--ink);font-weight:600}
.rd .badge{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--on-accent);background:var(--accent);padding:5px 9px;border-radius:6px}
.rd h1{font-family:var(--serif);font-weight:700;font-size:30px;line-height:1.15;letter-spacing:-.01em;margin:16px 0 8px}
.rd .by{font-size:14px;color:var(--muted);margin-bottom:22px}
.rd article{font-size:17.5px;line-height:1.72;color:var(--detail)}
.rd article p{margin:0 0 1.1em}
.rd article h2,.rd article h3{font-family:var(--serif);color:var(--ink);line-height:1.25;margin:1.6em 0 .5em}
.rd article h2{font-size:23px}.rd article h3{font-size:19px}
.rd article a{color:var(--accent);text-decoration:underline;text-underline-offset:3px}
.rd article img,.rd article video{max-width:100%;height:auto;border-radius:14px;display:block;margin:1.2em auto}
.rd article figure{margin:1.4em 0}.rd article figcaption{font-size:13px;color:var(--muted);margin-top:8px;line-height:1.5}
.rd article blockquote{margin:1.4em 0;padding:4px 0 4px 18px;border-left:3px solid var(--accent);font-family:var(--serif);font-style:italic;color:var(--ink)}
.rd article ul,.rd article ol{padding-left:1.3em}.rd article li{margin:.4em 0}
.rd article pre,.rd article code{font-size:14px;background:var(--tile);border-radius:8px}
.rd article pre{padding:12px;overflow:auto}
.rd article table{display:block;overflow-x:auto;border-collapse:collapse;font-size:14px}
.rd article td,.rd article th{border:1px solid var(--line);padding:6px 8px}
.rd .state{margin:40px 0;padding:22px;border-radius:20px;background:var(--card);text-align:center}
.rd .state h2{font-family:var(--serif);margin:0 0 8px;font-size:22px;color:var(--ink)}
.rd .state p{color:var(--muted);font-size:14.5px;line-height:1.55;margin:0 0 16px}
.rd .row{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}
.rd .row a{min-width:150px;padding:0 16px}
.rd .skel{height:14px;border-radius:7px;background:var(--tile);margin:12px 0;animation:pulse 1.2s ease-in-out infinite}
@keyframes pulse{50%{opacity:.45}}
.rd .end{display:flex;gap:10px;margin-top:30px;flex-wrap:wrap}
.rd .end a{flex:1;min-width:150px}
"""

READER_JS = r"""
(async()=>{
const $=s=>document.querySelector(s), u=new URLSearchParams(location.search).get('u')||'';
const show=(html)=>{$('#out').innerHTML=html};
const esc=t=>String(t||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
if(!/^https?:\/\//.test(u)){show(`<div class='state'><h2>No article link</h2><p>Open this from an "Archived copy" button.</p></div>`);return}
const host=new URL(u).hostname.replace(/^www\./,'');
$('#host').textContent=host; document.title='Archived · '+host;
const saveUrl='https://web.archive.org/save/'+u, rawLatest='https://web.archive.org/web/2/'+u;
let snap=null;
try{const r=await fetch('https://archive.org/wayback/available?url='+encodeURIComponent(u));const j=await r.json();snap=j?.archived_snapshots?.closest}catch(_){}
if(!snap||!snap.available){
  show(`<div class='state'><h2>Not archived yet</h2><p>The Internet Archive doesn't have a copy of this page. Some publishers block archiving, and new articles may not be captured yet.</p>
  <div class='row'><a class='btn primary' href='${esc(saveUrl)}' rel='noopener'>Ask the Archive to save it</a><a class='btn' href='${esc(u)}'>Try the original</a></div></div>`);return}
const ts=snap.timestamp, when=new Date(Date.UTC(+ts.slice(0,4),+ts.slice(4,6)-1,+ts.slice(6,8)));
$('#when').textContent='Saved '+when.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'});
const pageUrl=snap.url.replace(/^http:/,'https:'), clean=pageUrl.replace(/\/web\/(\d+)\//,'/web/$1id_/'),
  // if_ = the Archive's own copy with links kept inside the Archive but no toolbar.
  // (The raw id_ copy runs the site's original scripts, which can jump to the live site or its app.)
  framed=pageUrl.replace(/\/web\/(\d+)\//,'/web/$1if_/');
// If the Archive won't let us build a clean copy, go straight to its page without the toolbar.
const fallback=()=>{show(`<div class='state'><h2>Opening the archived page…</h2><p>Tip: tap <b>aA</b> in Safari's address bar, then <b>Show Reader</b>, for a clean view.</p></div>`);setTimeout(()=>location.replace(framed),900)};
try{
  const res=await fetch(clean); if(!res.ok) throw new Error(res.status);
  const doc=new DOMParser().parseFromString(await res.text(),'text/html');
  const base=doc.createElement('base');base.href=u;doc.head.prepend(base);
  const art=new Readability(doc).parse();
  if(!art||!art.content||art.textContent.trim().split(/\s+/).length<80) return fallback();
  const body=DOMPurify.sanitize(art.content,{FORBID_TAGS:['style','form','input','button','iframe'],FORBID_ATTR:['style','class','id','width','height']});
  const mins=Math.max(1,Math.round(art.textContent.trim().split(/\s+/).length/230));
  show(`<h1>${esc(art.title)}</h1><div class='by'>${esc([art.byline,art.siteName||host,mins+' min read'].filter(Boolean).join(' · '))}</div>
   <article>${body}</article>
   <div class='end'><a class='btn' href='${esc(pageUrl)}' rel='noopener'>View on the Archive</a><a class='btn primary' href='${esc(u)}'>Try the original</a></div>`);
  document.querySelectorAll('article a').forEach(a=>{a.rel='noopener';a.target='_blank'});
  document.querySelectorAll('article img').forEach(i=>{i.loading='lazy';i.referrerPolicy='no-referrer';i.onerror=()=>i.remove()});
}catch(_){fallback()}
})();
"""


def write_reader() -> None:
    import yaml
    from . import reader
    try:
        relay = (yaml.safe_load(open("config.yaml")) or {}).get("relay_url", "")
    except Exception:
        relay = ""
    reader.write_reader(relay)
    reader.write_highlights_page()


def write_all(cfg: dict, date: str, picks: list[dict], saved: list[dict], archive_dates: list[str],
              subs: list[dict] | None = None, smart: dict | None = None) -> None:
    (DOCS / "archive").mkdir(parents=True, exist_ok=True)
    nice = dt.date.fromisoformat(date).strftime("%A, %B %-d")
    (DOCS / "index.html").write_text(shell(f"Briefing — {nice}", "today", deck(date, picks, subs=subs, smart=smart), script=True))
    (DOCS / "archive" / f"{date}.html").write_text(
        shell(f"Briefing — {nice}", "archive", deck(date, picks, "../", subs, smart), root="../", script=True))
    rows = "".join(
        f"<a href='{d}.html'><span class='k'>›</span><span>{dt.date.fromisoformat(d).strftime('%A, %B %-d')}</span></a>"
        for d in sorted(archive_dates, reverse=True))
    (DOCS / "archive" / "index.html").write_text(shell(
        "Archive — Briefing", "archive",
        f"<main class='page'><section class='hero'><div class='kicker'>Past briefings</div><h1>Archive</h1></section>"
        f"<div class='toc'>{rows}</div></main>", root="../"))
    write_saved(saved)
    try:
        _games().write_pages(shell, date)
    except Exception as ex:
        import logging
        logging.getLogger(__name__).warning("couldn't write games pages: %s", ex)
    _offline().write_sw()
    write_reader()
    write_search_page()
    write_settings_page()
    write_podcast_page(_site())


def write_saved(saved: list[dict]) -> None:
    DOCS.mkdir(exist_ok=True)
    body = ("<main class='page'><section class='hero'><div class='kicker'>Your queue</div><h1>Saved</h1>"
            f"<p>{len(saved)} article{'s' if len(saved) != 1 else ''} saved for later</p></section>")
    body += "".join(card(i) for i in saved[:50]) or \
        "<p class='empty'>Nothing saved yet. Share a link to your Save shortcut and it'll show up here.</p>"
    (DOCS / "saved.html").write_text(shell("Saved — Briefing", "saved", body + "</main>"))
    (DOCS / "saved.json").write_text(json.dumps([s["url"] for s in saved]))


# ── search ─────────────────────────────────────────────────────────────
SEARCH_CSS = r"""
[hidden]{display:none!important}
.sbox{display:flex;gap:8px;margin:8px 0 6px}
.sbox input{flex:1;min-width:0;height:48px;border-radius:14px;border:1px solid var(--line);background:var(--tile);color:var(--ink);
  padding:0 14px;font:500 16px var(--sans);outline:none}
.sbox input:focus{border-color:var(--accent)}
.hint2{font-size:13px;color:var(--muted);margin:6px 2px 14px}
.res{display:flex;flex-direction:column}
.res a{display:block;padding:13px 2px;border-bottom:1px solid var(--line)}
.res .t{font-family:var(--serif);font-size:17px;line-height:1.3;color:var(--ink)}
.res .m{font-size:12px;color:var(--muted);margin-top:4px}
.res .m b{color:var(--accent);font-weight:600}
.res .x{font-size:13.5px;color:var(--detail);line-height:1.45;margin-top:4px}
.fresh{display:flex;flex-direction:column;gap:10px;margin:16px 0 4px;padding:16px;border-radius:18px;background:var(--card)}
.fresh h2{margin:0;font-family:var(--serif);font-size:19px}
.fresh p{margin:0;font-size:13.5px;line-height:1.5;color:var(--muted)}
.fresh .btn{flex:none}
.past a{display:flex;justify-content:space-between;gap:10px;padding:12px 2px;border-bottom:1px solid var(--line);font-size:15px}
.past a span{color:var(--muted);font-size:12px;white-space:nowrap}
.bg{margin:14px 0 4px;padding:16px;border-radius:18px;background:var(--card)}
.bg .src{margin-bottom:6px}
.bg p{margin:0;font-size:14.5px;line-height:1.6;color:var(--detail)}
.bg small{display:block;margin-top:8px;color:var(--muted);font-size:12px}
.bg small a{text-decoration:underline}
"""

SEARCH_JS = r"""
(()=>{const $=s=>document.querySelector(s), inp=$('#q'), out=$('#res'), fresh=$('#fresh'), stat=$('#stat');
const repo=document.body.dataset.repo;
const slug=q=>q.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,60)||'search';
const esc=t=>String(t||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let idx=null; const load=async()=>{if(!idx){try{idx=await (await fetch('search-index.json',{cache:'no-store'})).json()}catch(_){idx=[]}}return idx};
const fmt=d=>{try{return new Date(d+'T12:00:00Z').toLocaleDateString(undefined,{month:'short',day:'numeric'})}catch(_){return d}};
async function run(){const q=inp.value.trim();history.replaceState(null,'',q?'?q='+encodeURIComponent(q):location.pathname);
 if(!q){out.innerHTML='';fresh.hidden=true;return}
 const toks=q.toLowerCase().split(/\s+/).filter(w=>w.length>1);const data=await load();
 const hits=[];for(const r of data){const t=r.t.toLowerCase(),x=(r.x||'').toLowerCase();let ok=true,sc=0;
  for(const w of toks){const a=t.includes(w),b=x.includes(w);if(!a&&!b){ok=false;break}sc+=a?3:1}
  if(ok){sc+=r.g==='Briefing pick'||r.g==='Deep dive'?1:0;hits.push([sc,r])}}
 hits.sort((a,b)=>b[0]-a[0]||(b[1].d>a[1].d?1:-1));
 out.innerHTML=hits.length?hits.slice(0,40).map(([_,r])=>`<a href="${esc(r.u)}" target="_blank" rel="noopener"><div class="t">${esc(r.t)}</div>
  <div class="m">${r.g?`<b>${esc(r.g)}</b> · `:''}${esc(r.s)} · ${esc(fmt(r.d))}</div>${r.x?`<div class="x">${esc(r.x)}</div>`:''}</a>`).join('')
  :`<p class="hint2">Nothing in your briefing library yet. Try finding fresh articles.</p>`;
 fresh.hidden=false;$('#fq').textContent=q;
 $('#go').href=`https://github.com/${repo}/issues/new?title=${encodeURIComponent('search: '+q)}&body=${encodeURIComponent('Fresh search from your briefing. Tap Create/Submit; results appear in about 2 minutes.')}`;
 $('#go').onclick=()=>{try{localStorage.setItem('pendingSearch',JSON.stringify({q,s:slug(q),t:Date.now()}))}catch(_){};setTimeout(poll,1500)}}
let tm;inp.addEventListener('input',()=>{clearTimeout(tm);tm=setTimeout(run,200)});
$('#form').addEventListener('submit',ev=>{ev.preventDefault();run()});
async function poll(){let p;try{p=JSON.parse(localStorage.getItem('pendingSearch')||'null')}catch(_){}
 if(!p||Date.now()-p.t>15*60e3){stat.hidden=true;return}
 stat.hidden=false;
 try{const r=await fetch(`search/${p.s}.html`,{cache:'no-store',method:'HEAD'});
  if(r.ok){const meta=await (await fetch(`search/${p.s}.json`,{cache:'no-store'})).json().catch(()=>null);
   if(!meta||Date.parse(meta.when)>=p.t-120e3){stat.innerHTML=`Results for “${esc(p.q)}” are ready. <a class="btn primary" href="search/${p.s}.html">Open results</a>`;
    try{localStorage.removeItem('pendingSearch')}catch(_){};return}}}catch(_){}
 stat.innerHTML=`Searching for “${esc(p.q)}”… this takes about 2 minutes. You can leave this page open.`;setTimeout(poll,15000)}
const q0=new URLSearchParams(location.search).get('q');if(q0){inp.value=q0;run()}poll();})();
"""


def _past_searches() -> list[dict]:
    d = Path("data") / "searches"
    items = [json.loads(p.read_text()) for p in d.glob("*.json")] if d.exists() else []
    return sorted(items, key=lambda x: x.get("when", ""), reverse=True)


def _games():
    from . import games
    return games


def _offline():
    from . import offline
    return offline


def _relay_url() -> str:
    try:
        import yaml
        return (yaml.safe_load(open("config.yaml")) or {}).get("relay_url", "") or ""
    except Exception:
        return ""


def _site() -> str:
    owner, _, name = _repo().partition("/")
    return f"https://{owner.lower()}.github.io/{name}"


def _repo() -> str:
    import os
    return os.environ.get("GITHUB_REPOSITORY", "") or "scadams1111/briefing"


def write_search_page() -> None:
    past = _past_searches()[:30]
    rows = "".join(f"<a href='search/{e(x['slug'])}.html'>{e(x['q'])}<span>{len(x.get('results', []))} results · "
                   f"{e(x.get('when', '')[:10])}</span></a>" for x in past)
    body = ("<main class='page'><section class='hero'><div class='kicker'>Search</div><h1>Find articles</h1>"
            "<p>Search everything your briefing has collected, or find fresh articles on any topic.</p></section>"
            "<form id='form' class='sbox' role='search'><label for='q' class='sr' style='position:absolute;left:-9999px'>Search</label>"
            "<input id='q' type='search' placeholder='e.g. organoids, GLP-1, Roman roads' autocomplete='off' enterkeyhint='search'>"
            "</form>"
            "<div id='stat' class='fresh' hidden></div>"
            "<div id='fresh' class='fresh' hidden><h2>Find fresh articles on “<span id='fq'></span>”</h2>"
            "<p>Searches the news and your library, then the AI picks the best, most relevant pieces with three-point "
            "summaries. Opens GitHub: tap <b>Create</b>, then come back here. Ready in about 2 minutes.</p>"
            f"<a id='go' class='btn primary' href='#' target='_blank' rel='noopener'>{SEARCH_ICON}<span>Find fresh articles</span></a></div>"
            "<div id='res' class='res'></div>"
            + (f"<h3 class='label'>"
               f"Past searches</h3><div class='past'>{rows}</div>" if rows else "")
            + "</main>")
    page = shell("Search — Briefing", "search", body).replace("</style>", SEARCH_CSS + "</style>", 1)
    page = page.replace("</body>", f"<script>{SEARCH_JS}</script></body>")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "search.html").write_text(page)


def write_search_result(data: dict) -> Path:
    when = data.get("when", "")[:10]
    bg = data.get("background")
    body = (f"<main class='page'><section class='hero'><div class='kicker'>Search</div><h1>{e(data['q'])}</h1>"
            f"<p>{len(data['results'])} articles picked by relevance and quality · {e(when)}</p></section>")
    if bg:
        body += (f"<div class='bg'><div class='src'>Background · {e(bg['title'])}</div><p>{e(bg['text'])}</p>"
                 f"<small>From <a href='{e(bg['url'])}'>Wikipedia</a> (CC BY-SA)</small></div>")
    body += "".join(card(i, "../") for i in data["results"]) or \
        "<p class='empty'>No strong matches this time. Try different or broader words.</p>"
    body += "<p class='foot'><a href='../search.html'>New search</a></p></main>"
    page = shell(f"{data['q']} — Search", "search", body, root="../").replace("</style>", SEARCH_CSS + "</style>", 1)
    out = DOCS / "search"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{data['slug']}.html").write_text(page)
    (out / f"{data['slug']}.json").write_text(json.dumps({"q": data["q"], "when": data["when"]}))
    return out / f"{data['slug']}.html"


SETTINGS_JS = r"""
(()=>{const $=s=>document.querySelector(s),repo=document.body.dataset.repo,KEY='gh_token',st=$('#st');
const show=(m,ok)=>{st.textContent=m;st.style.color=ok?'var(--accent)':'var(--muted)'};
const cur=(()=>{try{return localStorage.getItem(KEY)}catch(_){return null}})();
show(cur?'Feedback is set up on this device.':'Not set up on this device yet.',!!cur);
$('#save').onclick=async()=>{const t=$('#tok').value.trim();if(!t){show('Paste your key first.');return}
 show('Checking…');try{const r=await fetch(`https://api.github.com/repos/${repo}`,{headers:{Authorization:'Bearer '+t,Accept:'application/vnd.github+json'}});
  if(!r.ok)throw new Error(r.status===401?'key not accepted':'error '+r.status);
  localStorage.setItem(KEY,t);$('#tok').value='';show('Saved. More / Less like this will work on this device.',true)}
 catch(err){show("Couldn't verify the key ("+err.message+"). Check it has Issues: Read and write for "+repo+".")}};
$('#rm').onclick=()=>{try{localStorage.removeItem(KEY)}catch(_){};show('Removed from this device.')};
})();
"""


def write_settings_page() -> None:
    repo = _repo()
    body = ("<main class='page'><section class='hero'><div class='kicker'>Settings</div><h1>Feedback setup</h1>"
            "<p>One time per device. Lets the More / Less like this buttons send your taps to the curator.</p></section>"
            "<div class='bg'><div class='src'>1 · Create a key on GitHub</div>"
            "<p>Tap the button, then: <b>Token name</b> Briefing feedback · <b>Expiration</b> 1 year · "
            f"<b>Repository access</b> Only select repositories → <b>{e(repo.split('/')[-1])}</b> · "
            "<b>Permissions</b> → Repository → <b>Issues: Read and write</b>. Tap <b>Generate token</b> and copy it.</p>"
            "<p style='margin-top:12px'><a class='btn primary' style='display:inline-flex;padding:0 16px' target='_blank' rel='noopener' "
            "href='https://github.com/settings/personal-access-tokens/new'>Create key on GitHub</a></p></div>"
            "<div class='bg'><div class='src'>2 · Paste it here</div>"
            "<form class='sbox' onsubmit='return false'><label for='tok' style='position:absolute;left:-9999px'>GitHub key</label>"
            "<input id='tok' type='password' placeholder='github_pat_…' autocomplete='off'></form>"
            "<div style='display:flex;gap:10px'><button id='save' type='button' class='btn primary'>Save</button>"
            "<button id='rm' type='button' class='btn'>Remove</button></div>"
            "<p id='st' style='margin-top:12px;font-size:14px'></p>"
            "<small>The key is stored only in this browser on this device. It is never put on the website. "
            "Your taps are recorded as short GitHub issues (visible in the repo) and applied each morning.</small></div></main>")
    page = shell("Settings — Briefing", "", body).replace("</style>", SEARCH_CSS + "</style>", 1)
    page = page.replace("</body>", f"<script>{SETTINGS_JS}</script></body>")
    (DOCS / "settings.html").write_text(page)


def write_podcast_page(site: str) -> None:
    feed = f"{site}/podcast.xml"
    body = ("<main class='page'><section class='hero'><div class='kicker'>Podcast</div><h1>Listen in your podcast app</h1>"
            "<p>Each morning's briefing, read aloud, about 9 minutes.</p></section>"
            "<div class='bg'><div class='src'>Apple Podcasts</div><p>Open <b>Podcasts</b> → <b>Library</b> → tap <b>…</b> "
            "(top right) → <b>Follow a Show by URL</b> → paste the address below.</p></div>"
            f"<div class='bg'><div class='src'>Feed address</div><p style='word-break:break-all'><b>{e(feed)}</b></p>"
            "<p style='margin-top:12px'><button type='button' class='btn primary' style='padding:0 16px' "
            f"onclick=\"navigator.clipboard.writeText('{e(feed)}').then(()=>this.textContent='Copied')\">Copy address</button></p></div></main>")
    (DOCS / "podcast.html").write_text(shell("Podcast — Briefing", "", body).replace("</style>", SEARCH_CSS + "</style>", 1))
