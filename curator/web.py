"""The web reading experience: 'Midnight' story cards. One story per screen,
swipe or tap Next to move through the day's briefing."""
from __future__ import annotations

import datetime as dt
import html
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
.top{max-width:560px;margin:0 auto;padding:14px 16px 0;display:flex;align-items:center;justify-content:space-between;gap:12px}
.brand{font-family:var(--serif);font-weight:700;font-size:21px;letter-spacing:-.01em}
.brand span{color:var(--accent)}
.tabs{display:flex;gap:2px;background:var(--tile);padding:3px;border-radius:999px}
.tabs a{font-size:13px;font-weight:600;padding:7px 12px;border-radius:999px;color:var(--muted)}
.tabs a.on{background:var(--line);color:var(--ink)}

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
.extras{display:flex;align-items:center;gap:10px;padding-top:4px}
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
"""

CHEV = ("<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' "
        "aria-hidden='true'><path d='M6 9l6 6 6-6'/></svg>")
NEXT = ("<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' "
        "aria-hidden='true'><path d='M9 5l7 7-7 7'/></svg>")
ARCHIVE = ("<svg width='15' height='15' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' "
           "stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><rect x='3' y='4' width='18' height='4' rx='1'/>"
           "<path d='M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8M10 12h4'/></svg>")
PREV = ("<svg width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.4' "
        "aria-hidden='true'><path d='M15 5l-7 7 7 7'/></svg>")

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
 const u=slides[i].dataset.url;orig.style.visibility=u?'visible':'hidden';if(u)orig.href=u;
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
           f"onerror=\"this.remove()\">") if it.get("image") else ""
    fav = f"https://www.google.com/s2/favicons?domain={e(_domain(it['url']))}&sz=64"
    pts = "".join(
        f"<details{' open' if n == 1 else ''}><summary><span class='n'>{n}</span><span>{e(b['point'])}</span>"
        f"{CHEV if b.get('detail') else ''}</summary>"
        + (f"<p>{e(b['detail'])}</p>" if b.get("detail") else "") + "</details>"
        for n, b in enumerate(it["bullets"], 1))
    room = f"<p class='room'>“{e(it['room_line'])}”</p>" if it.get("room_line") else ""
    # Backup if the original page has moved or vanished: Wayback Machine's latest snapshot
    archived = (f"<div class='extras'><a class='chip' href='https://wallhop.io/{e(it['url'])}'>"
                f"{ARCHIVE}<span>Archived copy</span></a><span class='hint'>if the link is broken</span></div>")
    return (f"<article class='card'><div class='scroll'>"
            f"<div class='media'>{img}<span class='pill'>{e(it.get('topic_name') or 'Story')}</span></div>"
            f"<div class='body'><div class='src'><img src='{fav}' alt='' referrerpolicy='no-referrer'>"
            f"{e(it['source'])} · {it['minutes']} min read</div>"
            f"<h1 class='head'><a href='{e(it['url'])}'>{e(it['headline'])}</a></h1>{room}"
            f"<div class='points'>{pts}</div>{archived}</div></div></article>")


def shell(title: str, active: str, body: str, root: str = "", script: bool = False) -> str:
    tabs = "".join(f"<a href='{root}{href}' class='{'on' if active == k else ''}'>{label}</a>"
                   for k, label, href in (("today", "Today", "./"), ("saved", "Saved", "saved.html"),
                                          ("archive", "Archive", "archive/")))
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            "<meta name='theme-color' content='#0B1220'><meta name='apple-mobile-web-app-capable' content='yes'>"
            "<meta name='apple-mobile-web-app-status-bar-style' content='black-translucent'>"
            f"<title>{e(title)}</title>{FONTS}<style>{CSS}</style></head><body>"
            f"<header class='top'><a class='brand' href='{root}./'>Briefing<span>.</span></a>"
            f"<nav class='tabs'>{tabs}</nav></header>{body}"
            + (f"<script>{JS}</script>" if script else "") + "</body></html>")


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
        f"<div class='subrow'><a class='open' href='{e(i['url'])}'>Open article {NEXT}</a>"
        f"<a class='chip sm' href='https://wallhop.io/{e(i['url'])}'>{ARCHIVE}<span>Link broken?</span></a></div></div>"
        for i in subs)
    return (f"<section class='slide' data-url='' data-label='{e(pill)}'><article class='card'><div class='scroll'><div class='body'>"
            f"<span class='pill' style='align-self:flex-start'>{e(pill)}</span>"
            f"<h1 class='head'>{e(title)}</h1><p class='room' style='font-style:normal;font-family:var(--sans);font-size:14px'>{e(sub)}</p>"
            f"<div class='subs'>{rows}</div></div></div></article></section>")


def deck(date: str, picks: list[dict], root: str = "", subs: list[dict] | None = None) -> str:
    d = dt.date.fromisoformat(date)
    n = len(picks)
    if not n:
        return "<main class='page'><p class='empty'>Nothing yet today.</p></main>"
    groups = [(sec, [i for i in subs or [] if section_of(i) == sec]) for sec in ("nyt", "premium")]
    groups = [(sec, items) for sec, items in groups if items]
    bars = "".join(f"<button type='button' aria-label='Story {k + 1}'><i></i></button>"
                   for k in range(n + 1 + len(groups)))
    slides = "".join(f"<section class='slide' data-url='{e(i['url'])}'>{card(i, root)}</section>" for i in picks)
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
           f"<a href='{root}archive/'>Past briefings</a></p></div></div></article></section>")
    return (f"<main class='reader'><div class='bars'>{bars}</div>"
            f"<div class='status'><b>1 of {n}</b><span>{d.strftime('%a, %b')} {d.day}</span></div>"
            f"<div class='deck'>{slides}{end}</div>"
            f"<div class='actions'><button type='button' class='btn icon' data-prev aria-label='Previous story'>{PREV}</button>"
            f"<a class='btn' data-orig href='#'>Read original</a>"
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
    """A Midnight-styled reader for Internet Archive copies. The archived page is
    fetched and cleaned in the reader's own browser; nothing is stored on the site."""
    body = ("<main class='rd'><div class='bar'><a class='back' href='javascript:history.back()' aria-label='Back'>"
            f"{PREV}</a><div class='meta'><span class='badge'>{ARCHIVE} Archived copy</span><br>"
            "<b id='host'></b> · <span id='when'>Looking it up…</span></div></div>"
            "<div id='out'><div class='skel' style='height:30px;width:85%'></div><div class='skel' style='width:40%'></div>"
            "<div class='skel'></div><div class='skel'></div><div class='skel' style='width:92%'></div><div class='skel'></div>"
            "<div class='skel' style='width:70%'></div></div></main>")
    page = ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            "<meta name='theme-color' content='#0B1220'><meta name='referrer' content='no-referrer'>"
            f"<title>Archived copy</title>{FONTS}<style>{CSS}{READER_CSS}</style>"
            "<script src='https://cdn.jsdelivr.net/npm/@mozilla/readability@0.5.0/Readability.js'></script>"
            "<script src='https://cdn.jsdelivr.net/npm/dompurify@3.1.6/dist/purify.min.js'></script>"
            f"</head><body>{body}<script>{READER_JS}</script></body></html>")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "read.html").write_text(page)


def write_all(cfg: dict, date: str, picks: list[dict], saved: list[dict], archive_dates: list[str],
              subs: list[dict] | None = None) -> None:
    (DOCS / "archive").mkdir(parents=True, exist_ok=True)
    nice = dt.date.fromisoformat(date).strftime("%A, %B %-d")
    (DOCS / "index.html").write_text(shell(f"Briefing — {nice}", "today", deck(date, picks, subs=subs), script=True))
    (DOCS / "archive" / f"{date}.html").write_text(
        shell(f"Briefing — {nice}", "archive", deck(date, picks, "../", subs), root="../", script=True))
    rows = "".join(
        f"<a href='{d}.html'><span class='k'>›</span><span>{dt.date.fromisoformat(d).strftime('%A, %B %-d')}</span></a>"
        for d in sorted(archive_dates, reverse=True))
    (DOCS / "archive" / "index.html").write_text(shell(
        "Archive — Briefing", "archive",
        f"<main class='page'><section class='hero'><div class='kicker'>Past briefings</div><h1>Archive</h1></section>"
        f"<div class='toc'>{rows}</div></main>", root="../"))
    write_saved(saved)
    write_reader()


def write_saved(saved: list[dict]) -> None:
    DOCS.mkdir(exist_ok=True)
    body = ("<main class='page'><section class='hero'><div class='kicker'>Your queue</div><h1>Saved</h1>"
            f"<p>{len(saved)} article{'s' if len(saved) != 1 else ''} saved for later</p></section>")
    body += "".join(card(i) for i in saved[:50]) or \
        "<p class='empty'>Nothing saved yet. Share a link to your Save shortcut and it'll show up here.</p>"
    (DOCS / "saved.html").write_text(shell("Saved — Briefing", "saved", body + "</main>"))
