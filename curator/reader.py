"""Reader view with highlights and notes.

read.html?u=<article url>            live article via your Cloudflare relay; falls back
                                      to an Internet Archive copy, then to the original
read.html?u=<article url>&src=archive  archive copy first

Pages are fetched and cleaned in your browser (through the relay, which only serves
your site); nothing from the article is stored on the website. Highlights and notes
are saved in this browser and can be sent to Obsidian or copied as Markdown.
highlights.html lists everything you've highlighted on this device.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import web as w

e = w.e

HL_CSS = r"""
[hidden]{display:none!important}
.rd article mark{background:color-mix(in srgb,var(--accent) 32%,transparent);color:var(--ink);border-radius:3px;padding:0 1px;cursor:pointer}
.rd article mark.note{box-shadow:inset 0 -2px 0 var(--accent)}
.hlbar{position:fixed;left:50%;bottom:calc(18px + env(safe-area-inset-bottom));transform:translateX(-50%);display:flex;gap:6px;
  padding:6px;border-radius:14px;background:var(--ink);box-shadow:0 10px 30px rgba(0,0,0,.45);z-index:40}
.hlbar button{white-space:nowrap;border:0;border-radius:10px;padding:10px 14px;font:700 14px var(--sans);background:transparent;color:var(--bg)}
.hlbar button.hl{background:var(--accent);color:var(--on-accent)}
.notes{margin-top:34px;padding:16px;border-radius:18px;background:var(--card)}
.notes h2{font-family:var(--serif);font-size:20px;margin:0 0 10px;color:var(--ink)}
.notes .n{padding:10px 0;border-bottom:1px solid var(--line)}
.notes .n:last-of-type{border-bottom:0}
.notes blockquote{margin:0;padding-left:12px;border-left:3px solid var(--accent);font-family:var(--serif);font-size:15.5px;line-height:1.55;color:var(--ink)}
.notes .nt{margin-top:6px;font-size:14px;color:var(--detail)}
.notes .acts{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.notes .acts .btn{flex:1;min-width:140px}
.notes .empty2{font-size:14px;color:var(--muted);margin:0}
.via{font-size:12px;color:var(--muted);margin-top:4px}
.via a{text-decoration:underline}
"""

READER_JS = r"""
(async()=>{
const $=s=>document.querySelector(s), P=new URLSearchParams(location.search), u=P.get('u')||'', want=P.get('src')||'live';
const RELAY=document.body.dataset.relay||'', root=document.body.dataset.root||'';
const show=html=>{$('#out').innerHTML=html};
const esc=t=>String(t||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
if(!/^https?:\/\//.test(u)){show(`<div class='state'><h2>No article link</h2><p>Open this from a story's Read button.</p></div>`);return}
const host=new URL(u).hostname.replace(/^www\./,'');$('#host').textContent=host;document.title='Read · '+host;
const viaRelay=x=>RELAY?RELAY+'?url='+encodeURIComponent(x):x;
async function grab(url){const r=await fetch(viaRelay(url));if(!r.ok)throw new Error('HTTP '+r.status);return await r.text()}
function parse(html,base){const doc=new DOMParser().parseFromString(html,'text/html');const b=doc.createElement('base');b.href=base;doc.head.prepend(b);
 const a=new Readability(doc).parse();if(!a||!a.content)return null;const words=a.textContent.trim().split(/\s+/).length;return words<150?null:{...a,words}}
async function live(){try{return parse(await grab(u),u)}catch(_){return null}}
let snapUrl=null,snapWhen=null;
async function archived(){try{const j=await (await fetch('https://archive.org/wayback/available?url='+encodeURIComponent(u))).json();
 const s=j?.archived_snapshots?.closest;if(!s||!s.available)return null;snapUrl=s.url.replace(/^http:/,'https:');snapWhen=s.timestamp;
 const raw=snapUrl.replace(/\/web\/(\d+)\//,'/web/$1id_/');return parse(await grab(raw),u)}catch(_){return null}}
let art=null,src='';
if(want==='archive'){art=await archived();src=art?'archive':'';if(!art){art=await live();src=art?'live':''}}
else{art=await live();src=art?'live':'';if(!art){art=await archived();src=art?'archive':''}}
const when=ts=>ts?new Date(Date.UTC(+ts.slice(0,4),+ts.slice(4,6)-1,+ts.slice(6,8))).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}):'';
if(!art){$('#when').textContent='Not available';
 show(`<div class='state'><h2>Couldn't open a clean copy</h2><p>The site may be paywalled or blocking readers, and there's no usable archived copy.</p>
 <div class='row'><a class='btn primary' href='${esc(u)}' target='_blank' rel='noopener'>Open the original</a>${snapUrl?`<a class='btn' href='${esc(snapUrl)}' target='_blank' rel='noopener'>Archive page</a>`:''}</div></div>`);return}
$('#when').textContent=src==='archive'?'Archived copy · '+when(snapWhen):'Reader view';
const body=DOMPurify.sanitize(art.content,{FORBID_TAGS:['style','form','input','button','iframe','script'],FORBID_ATTR:['style','class','id','width','height']});
const mins=Math.max(1,Math.round(art.words/230)), title=art.title||host;
show(`<h1>${esc(title)}</h1><div class='by'>${esc([art.byline,art.siteName||host,mins+' min read'].filter(Boolean).join(' · '))}</div>
 <article id='art'>${body}</article>
 <div class='notes' id='notes'></div>
 <div class='end'><a class='btn' href='${esc(u)}' target='_blank' rel='noopener'>Open original</a>${src==='archive'&&snapUrl?`<a class='btn' href='${esc(snapUrl)}' target='_blank' rel='noopener'>View on the Archive</a>`:''}</div>
 <p class='via'>Tip: select text to highlight it or add a note. <a href='${root}highlights.html'>All highlights</a></p>`);
document.querySelectorAll('#art a').forEach(a=>{a.target='_blank';a.rel='noopener'});
document.querySelectorAll('#art img').forEach(i=>{i.loading='lazy';i.referrerPolicy='no-referrer';i.onerror=()=>i.remove()});

// ── highlights & notes (saved in this browser) ──
const A=$('#art'), KEY='hl:'+u, INDEX='hl:index';
const load=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'[]')}catch(_){return[]}};
const save=list=>{try{localStorage.setItem(KEY,JSON.stringify(list));const ix=JSON.parse(localStorage.getItem(INDEX)||'{}');
 if(list.length)ix[u]={title,host,at:Date.now(),n:list.length};else delete ix[u];localStorage.setItem(INDEX,JSON.stringify(ix))}catch(_){}};
const nodes=()=>{const t=document.createTreeWalker(A,NodeFilter.SHOW_TEXT);const a=[];let n;while(n=t.nextNode())a.push(n);return a};
function wrap(start,end,h){let pos=0;for(const n of nodes()){const len=n.data.length,s=Math.max(start-pos,0),e2=Math.min(end-pos,len);
 if(s<e2){let x=n;if(s>0)x=x.splitText(s);if(e2-s<x.data.length)x.splitText(e2-s);const m=document.createElement('mark');m.dataset.h=h.id;
  if(h.note)m.className='note';x.parentNode.insertBefore(m,x);m.appendChild(x)}pos+=len;if(pos>=end)break}}
function locate(h){const txt=A.textContent;if(txt.slice(h.start,h.end)===h.text)return[h.start,h.end];const i=txt.indexOf(h.text);return i<0?null:[i,i+h.text.length]}
function paint(){const list=load();A.querySelectorAll('mark').forEach(m=>{m.replaceWith(...m.childNodes)});A.normalize();
 for(const h of list){const at=locate(h);if(at)wrap(at[0],at[1],h)}renderNotes(list)}
function md(list){let s=`# ${title}\n\nSource: ${u}\nSaved: ${new Date().toISOString().slice(0,10)}\n\n`;
 for(const h of list){s+=`> ${h.text.replace(/\n+/g,' ')}\n`;if(h.note)s+=`\n${h.note}\n`;s+='\n'}return s}
function renderNotes(list){const box=$('#notes');
 if(!list.length){box.innerHTML=`<h2>Highlights</h2><p class='empty2'>Select any text in the article to highlight it or add a note.</p>`;return}
 box.innerHTML=`<h2>Highlights (${list.length})</h2>`+list.map(h=>`<div class='n'><blockquote>${esc(h.text)}</blockquote>${h.note?`<div class='nt'>${esc(h.note)}</div>`:''}</div>`).join('')+
 `<div class='acts'><a class='btn primary' id='obs' href='#'>Send to Obsidian</a><button type='button' class='btn' id='cp'>Copy Markdown</button></div>`;
 const name=('Briefing/'+title).replace(/[\\/:*?"<>|#^\[\]]+/g,' ').replace('Briefing ','Briefing/').slice(0,120);
 $('#obs').href='obsidian://new?file='+encodeURIComponent(name)+'&content='+encodeURIComponent(md(list))+'&overwrite=true';
 $('#cp').onclick=async()=>{try{await navigator.clipboard.writeText(md(list));$('#cp').textContent='Copied'}catch(_){$('#cp').textContent='Copy failed'}}}
const bar=document.createElement('div');bar.className='hlbar';bar.hidden=true;
bar.innerHTML=`<button type='button' class='hl' data-a='hl'>Highlight</button><button type='button' data-a='note'>Add note</button>`;document.body.appendChild(bar);
let pending=null;
function current(){const s=getSelection();if(!s||s.isCollapsed||!s.rangeCount)return null;const r=s.getRangeAt(0);
 if(!A.contains(r.commonAncestorContainer))return null;const text=r.toString().trim();if(text.length<3)return null;
 const pre=document.createRange();pre.selectNodeContents(A);pre.setEnd(r.startContainer,r.startOffset);
 let start=pre.toString().length;const raw=r.toString();start+=raw.indexOf(text);return{start,end:start+text.length,text:text.slice(0,1500)}}
document.addEventListener('selectionchange',()=>{pending=current();bar.hidden=!pending});
bar.addEventListener('pointerdown',ev=>ev.preventDefault());
bar.addEventListener('click',ev=>{const b=ev.target.closest('button');if(!b||!pending)return;let note='';
 if(b.dataset.a==='note'){note=prompt('Your note')||'';if(!note)return}
 const list=load();list.push({id:Date.now().toString(36),...pending,note,at:Date.now()});list.sort((a,b)=>a.start-b.start);save(list);
 getSelection().removeAllRanges();bar.hidden=true;pending=null;paint()});
A.addEventListener('click',ev=>{const m=ev.target.closest('mark');if(!m||!getSelection().isCollapsed)return;const list=load(),h=list.find(x=>x.id===m.dataset.h);if(!h)return;
 const v=prompt('Edit the note, or clear it and tap OK to keep the highlight. Cancel does nothing. Type DELETE to remove the highlight.',h.note||'');
 if(v===null)return;if(v.trim().toUpperCase()==='DELETE')list.splice(list.indexOf(h),1);else h.note=v.trim();save(list);paint()});
paint();
})();
"""

HIGHLIGHTS_JS = r"""
(()=>{const box=document.querySelector('#list');const esc=t=>String(t||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let ix={};try{ix=JSON.parse(localStorage.getItem('hl:index')||'{}')}catch(_){}
const items=Object.entries(ix).sort((a,b)=>b[1].at-a[1].at);
if(!items.length){box.innerHTML="<p class='empty'>No highlights yet. Open any story with Read, select text, and tap Highlight.</p>";return}
let all='# Briefing highlights\n\n';
box.innerHTML=items.map(([u,m])=>{let list=[];try{list=JSON.parse(localStorage.getItem('hl:'+u)||'[]')}catch(_){}
 all+=`## ${m.title}\n\nSource: ${u}\n\n`+list.map(h=>`> ${h.text.replace(/\n+/g,' ')}\n`+(h.note?`\n${h.note}\n`:'')).join('\n')+'\n';
 return `<div class='bg'><div class='src'>${esc(m.host)} · ${new Date(m.at).toLocaleDateString()}</div>
 <a href='read.html?u=${encodeURIComponent(u)}'><strong style='font-family:var(--serif);font-size:18px'>${esc(m.title)}</strong></a>
 ${list.map(h=>`<p style='margin-top:10px;border-left:3px solid var(--accent);padding-left:10px'>${esc(h.text)}</p>${h.note?`<small>${esc(h.note)}</small>`:''}`).join('')}</div>`}).join('');
const cp=document.querySelector('#cpall');cp.hidden=false;cp.onclick=async()=>{try{await navigator.clipboard.writeText(all);cp.textContent='Copied'}catch(_){cp.textContent='Copy failed'}};
})();
"""


def write_reader(relay: str = "") -> None:
    body = ("<main class='rd'><div class='bar'><a class='back' href='javascript:history.back()' aria-label='Back'>"
            f"{w.PREV}</a><div class='meta'><span class='badge'>Reader</span><br>"
            "<b id='host'></b> · <span id='when'>Loading…</span></div></div>"
            "<div id='out'><div class='skel' style='height:30px;width:85%'></div><div class='skel' style='width:40%'></div>"
            "<div class='skel'></div><div class='skel'></div><div class='skel' style='width:92%'></div><div class='skel'></div>"
            "<div class='skel' style='width:70%'></div></div></main>")
    page = ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            "<meta name='theme-color' content='#0B1220'><meta name='referrer' content='no-referrer'>"
            f"<link rel='apple-touch-icon' href='apple-touch-icon.png'>"
            f"<title>Reader</title>{w.FONTS}<style>{w.CSS}{w.READER_CSS}{HL_CSS}</style>"
            "<script src='https://cdn.jsdelivr.net/npm/@mozilla/readability@0.5.0/Readability.js'></script>"
            "<script src='https://cdn.jsdelivr.net/npm/dompurify@3.1.6/dist/purify.min.js'></script>"
            f"</head><body data-relay='{e(relay)}' data-root=''>{body}<script>{READER_JS}</script></body></html>")
    w.DOCS.mkdir(exist_ok=True)
    (w.DOCS / "read.html").write_text(page)


def write_highlights_page() -> None:
    body = ("<main class='page'><section class='hero'><div class='kicker'>Your notes</div><h1>Highlights</h1>"
            "<p>Everything you've highlighted in the reader on this device.</p></section>"
            "<p><button id='cpall' type='button' class='btn primary' style='padding:0 16px' hidden>Copy all as Markdown</button></p>"
            "<div id='list'></div></main>")
    page = w.shell("Highlights — Briefing", "", body).replace("</style>", w.SEARCH_CSS + "</style>", 1)
    (w.DOCS / "highlights.html").write_text(page.replace("</body>", f"<script>{HIGHLIGHTS_JS}</script></body>"))
