"""Games tab: today's puzzles on the web (tap to solve) and as e-reader pages in the EPUB."""
from __future__ import annotations

import datetime as dt
import html
import json
import logging
from pathlib import Path

from . import puzzles
from . import games_more as more

log = logging.getLogger(__name__)
e = html.escape
DATA = Path("data") / "games"
DOCS = Path("docs")

PUZZLE_ICON = ("<svg width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' "
               "stroke-linejoin='round' aria-hidden='true'><rect x='3' y='3' width='18' height='18' rx='3'/>"
               "<path d='M3 9h18M3 15h18M9 3v18M15 3v18'/></svg>")


def ensure(date: str, items: list[dict], llm=None, force: bool = False) -> dict | None:
    """Load today's puzzles, or make them (with the AI for the crossword if it's available)."""
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / f"{date}.json"
    if path.exists() and not force:
        g = json.loads(path.read_text())
        fresh = all(k in g for k in ("queens", "hive", "groups"))
        if fresh and (g.get("ai") or llm is None or not getattr(llm, "available", False)):
            return g
    try:
        g = puzzles.build(date, items, llm)
    except Exception as ex:
        log.exception("couldn't make today's puzzles: %s", ex)
        return json.loads(path.read_text()) if path.exists() else None
    path.write_text(json.dumps(g))
    for old in sorted(DATA.glob("20*.json"))[:-30]:
        old.unlink()
    return g


def load(date: str) -> dict | None:
    p = DATA / f"{date}.json"
    return json.loads(p.read_text()) if p.exists() else None


# ── web ───────────────────────────────────────────────────────────────────
CSS = r"""
[hidden]{display:none!important}
.seg{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none;background:var(--tile);padding:4px;border-radius:14px;margin:12px 0 14px;position:sticky;top:calc(env(safe-area-inset-top) + 56px);z-index:5}
.seg::-webkit-scrollbar{display:none}
.seg button{flex:none;white-space:nowrap;border:0;background:none;color:var(--muted);font:600 13px var(--sans);padding:9px 12px;border-radius:10px}
.seg button.on{background:var(--line);color:var(--ink)}
.seg button .ok{color:var(--accent);margin-left:3px}
.game h2{font-family:var(--serif);font-size:24px;margin:4px 2px 2px}
.game .gsub{color:var(--muted);font-size:13.5px;margin:0 2px 12px;line-height:1.45}
.gbtns{display:flex;gap:8px;margin:14px 0}
.gbtns .btn{height:42px;font-size:14px}
.gmsg{min-height:20px;font-size:14px;color:var(--muted);margin:2px 2px 8px}
.gmsg.win{color:var(--accent);font-weight:700}
.gmsg.bad{color:#F28B82}
/* crossword */
.xwrap{position:relative}
.xboard{display:grid;gap:2px;background:transparent;user-select:none;-webkit-user-select:none;touch-action:manipulation}
.xboard .blk{aspect-ratio:1}
.xboard .cell{aspect-ratio:1;background:var(--ink);color:#0B1220;border-radius:3px;position:relative;display:flex;align-items:center;justify-content:center}
.xboard .cell i{position:absolute;top:1px;left:2px;font:700 8px var(--sans);font-style:normal;color:#475569}
.xboard .cell b{font:700 clamp(12px,4.2vw,20px) var(--sans)}
.xboard .cell.hl{background:#CFE0FF}
.xboard .cell.cur{background:var(--accent)}
.xboard .cell.bad b{color:#C0392B}
.xboard .cell.rev b{color:#2563EB}
.kb{position:absolute;left:0;top:0;width:1px;height:1px;opacity:0;font-size:16px;border:0;padding:0}
.cbar{position:sticky;top:calc(env(safe-area-inset-top) + 112px);z-index:4;background:var(--card);border-radius:12px;padding:10px 12px;margin:0 0 10px;font-size:14.5px;line-height:1.35;min-height:20px}
.clues h3{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin:16px 2px 6px}
.clues ol{list-style:none;margin:0;padding:0}
.clues li{padding:8px 6px;border-radius:8px;font-size:14.5px;line-height:1.35;display:flex;gap:8px}
.clues li b{color:var(--muted);width:20px;flex:none;text-align:right}
.clues li.on{background:var(--tile)}
.clues li.done{color:var(--muted);text-decoration:line-through}
/* whodunit */
.cast{display:flex;flex-direction:column;gap:6px;margin:0 0 12px}
.cast div{font-size:14px;color:var(--detail)}
.cast b{color:var(--ink)}
.wclues{margin:0 0 14px;padding:0 0 0 28px}
.wclues li{margin:6px 0;font-size:15px;line-height:1.45}
.lg{border-collapse:collapse;margin:6px 0;user-select:none;-webkit-user-select:none}
.lg th{font:600 11.5px var(--sans);color:var(--detail);padding:3px 5px;text-align:right;white-space:nowrap}
.lg thead th{writing-mode:vertical-rl;transform:rotate(180deg);text-align:left;vertical-align:bottom;height:128px;padding:4px 2px}
.lg td{width:30px;height:30px;border:1px solid var(--line);text-align:center;font:700 15px var(--sans);color:var(--muted);background:var(--tile)}
.lg td.o{color:var(--accent);background:var(--tile-open)}
.lg td.gap{border:0;background:none}
.lg .thick-l{border-left:2px solid var(--muted)}
.lg .thick-t{border-top:2px solid var(--muted)}
.lgwrap{overflow-x:auto;margin:0 -4px;padding:0 4px}
.accuse{display:flex;flex-direction:column;gap:8px;margin:14px 0 0}
.accuse .btn{flex:none}
.accuse select{height:44px;border-radius:12px;border:1px solid var(--line);background:var(--tile);color:var(--ink);font:500 15px var(--sans);padding:0 10px}
/* murder map */
.mboard{display:grid;gap:0;border:2px solid var(--ink);border-radius:6px;overflow:hidden;user-select:none;-webkit-user-select:none;touch-action:manipulation}
.mboard div{aspect-ratio:1;position:relative;display:flex;align-items:center;justify-content:center;border:0 solid #0B1220}
.mboard .ri{position:absolute;top:2px;left:4px;font:700 9px var(--sans);color:rgba(11,18,32,.55)}
.mboard .f{font-size:22px;line-height:1;color:rgba(11,18,32,.7)}
.mboard .rug{background-image:repeating-linear-gradient(45deg,rgba(11,18,32,.16) 0 4px,transparent 4px 9px)}
.mboard .tok{width:64%;height:64%;border-radius:50%;background:#0B1220;color:var(--ink);font:800 clamp(13px,4.5vw,20px) var(--sans);display:flex;align-items:center;justify-content:center}
.mboard .tok.v{background:#7F1D1D}
.mboard .xm{font:800 20px var(--sans);color:rgba(11,18,32,.5)}
.mboard div.bad .tok{box-shadow:0 0 0 3px #F28B82}
.legend{display:flex;flex-wrap:wrap;gap:6px 12px;margin:10px 2px;font-size:13px;color:var(--detail)}
.legend span{display:flex;align-items:center;gap:6px}
.legend i{width:14px;height:14px;border-radius:4px;display:inline-block}
.tools{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.tools button{display:flex;align-items:center;gap:6px;height:38px;padding:0 12px;border-radius:999px;border:1px solid var(--line);background:none;color:var(--ink);font:600 13px var(--sans)}
.tools button b{width:22px;height:22px;border-radius:50%;background:var(--ink);color:var(--bg);display:flex;align-items:center;justify-content:center;font-size:12px}
.tools button.on{border-color:var(--accent);background:var(--tile)}
/* sudoku */
.sboard{display:grid;grid-template-columns:repeat(9,1fr);border:2px solid var(--ink);border-radius:6px;overflow:hidden;user-select:none;-webkit-user-select:none;touch-action:manipulation}
.sboard div{aspect-ratio:1;display:flex;align-items:center;justify-content:center;font:500 clamp(15px,5vw,22px) var(--sans);color:#7FB4FF;border-right:1px solid var(--line);border-bottom:1px solid var(--line);position:relative;background:var(--card)}
.sboard div.g{color:var(--ink);font-weight:700}
.sboard div.br{border-right:2px solid var(--ink)}
.sboard div.bb{border-bottom:2px solid var(--ink)}
.sboard div.peer{background:var(--tile)}
.sboard div.same{background:var(--tile-open)}
.sboard div.cur{background:#3A4A6B}
.sboard div.bad{color:#F28B82}
.sboard .nt{position:absolute;inset:2px;display:grid;grid-template-columns:repeat(3,1fr);font:600 8.5px var(--sans);color:var(--muted);text-align:center;align-items:center}
.pad{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin:12px 0}
.pad button{height:46px;border-radius:12px;border:1px solid var(--line);background:var(--tile);color:var(--ink);font:600 19px var(--sans)}
.pad button.mode.on{border-color:var(--accent);color:var(--accent)}
.pad button small{font-size:12px}
.past{margin-top:26px}
.past h3{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 2px 6px}
"""

JS = r"""
(()=>{const G=JSON.parse(document.getElementById('gdata').textContent);
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const K=k=>'game:'+G.date+':'+k;
const load=(k,d)=>{try{const v=JSON.parse(localStorage.getItem(K(k)));return v==null?d:v}catch(_){return d}};
const save=(k,v)=>{try{localStorage.setItem(K(k),JSON.stringify(v))}catch(_){}};
const msg=(id,t,c)=>{const m=$('#'+id+' .gmsg');m.textContent=t;m.className='gmsg'+(c?' '+c:'')};
const won=id=>{const b=$(`.seg [data-g="${id}"]`);if(b&&!b.querySelector('.ok'))b.insertAdjacentHTML('beforeend','<span class="ok">✓</span>')};
const twice=(btn,fn)=>{btn.onclick=()=>{if(btn.dataset.arm){delete btn.dataset.arm;btn.textContent=btn.dataset.l;fn()}else{btn.dataset.l=btn.textContent;btn.dataset.arm=1;btn.textContent='Tap again';setTimeout(()=>{if(btn.dataset.arm){delete btn.dataset.arm;btn.textContent=btn.dataset.l}},2500)}}};
const segs=$$('.seg button');
const show=id=>{segs.forEach(b=>b.classList.toggle('on',b.dataset.g===id));$$('.game').forEach(s=>s.hidden=s.id!==id);try{localStorage.setItem('lastGame',id)}catch(_){}};
segs.forEach(b=>b.onclick=()=>{show(b.dataset.g);scrollTo({top:0})});
let first=location.hash.slice(1);try{first=first||localStorage.getItem('lastGame')}catch(_){}
show(segs.some(b=>b.dataset.g===first)?first:segs[0].dataset.g);
const on=segs.find(b=>b.classList.contains('on'));on&&on.scrollIntoView({inline:'center',block:'nearest'});

/* ── crossword ── */
(()=>{const X=G.crossword,R=X.rows,C=X.cols,S=X.solution,board=$('#xw .xboard'),inp=$('#xw .kb');
let st=load('xw',{}),rev=load('xwrev',{});const ce={};
X.entries.forEach((en,i)=>{for(let k=0;k<en.answer.length;k++){const r=en.d=='A'?en.r:en.r+k,c=en.d=='A'?en.c+k:en.c;(ce[r+','+c]=ce[r+','+c]||{})[en.d]=i}});
const nums={};X.entries.forEach(en=>nums[en.r+','+en.c]=en.n);
board.style.gridTemplateColumns=`repeat(${C},1fr)`;let h='';
for(let r=0;r<R;r++)for(let c=0;c<C;c++){const k=r+','+c;h+=S[r][c]=='.'?'<div class="blk"></div>':`<div class="cell" data-k="${k}">${nums[k]?`<i>${nums[k]}</i>`:''}<b></b></div>`}
board.innerHTML=h;const cel=k=>board.querySelector(`[data-k="${k}"]`);
const cells=i=>{const en=X.entries[i];return [...en.answer].map((_,k)=>en.d=='A'?en.r+','+(en.c+k):(en.r+k)+','+en.c)};
const sol=k=>{const [r,c]=k.split(',').map(Number);return S[r][c]};
let cur=null,dir='A';const ent=()=>{const m=ce[cur];return m[dir]!=null?m[dir]:m[dir=='A'?'D':'A']};
function paint(){$$('.cell',board).forEach(el=>{const k=el.dataset.k;el.querySelector('b').textContent=st[k]||'';el.classList.remove('cur','hl','bad');el.classList.toggle('rev',!!rev[k])});
 $$('#xw .clues li').forEach(li=>{const i=+li.dataset.i;li.classList.toggle('done',cells(i).every(k=>st[k]));li.classList.remove('on')});
 if(cur){const i=ent(),en=X.entries[i];dir=en.d;cells(i).forEach(k=>cel(k).classList.add('hl'));cel(cur).classList.add('cur');
  $('#xw .cbar').innerHTML=`<b>${en.n} ${en.d=='A'?'Across':'Down'}</b> · ${en.clue.replace(/[<&]/g,'')}`;
  const li=$(`#xw .clues li[data-i="${i}"]`);li&&li.classList.add('on')}
 save('xw',st);const all=Object.keys(ce);
 if(all.every(k=>st[k]===sol(k))){msg('xw',Object.keys(rev).length?'Complete.':'Solved! Nicely done.','win');won('xw')}}
function go(k){cur=k;paint();inp.value=' ';inp.focus({preventScroll:true})}
board.onclick=ev=>{const el=ev.target.closest('.cell');if(!el)return;const k=el.dataset.k;
 if(k===cur){const m=ce[k];if(m.A!=null&&m.D!=null)dir=dir=='A'?'D':'A'}else{const m=ce[k];if(m[dir]==null)dir=m.A!=null?'A':'D'}go(k)};
$$('#xw .clues li').forEach(li=>li.onclick=()=>{const i=+li.dataset.i;dir=X.entries[i].d;const cs=cells(i);go(cs.find(k=>!st[k])||cs[0]);board.scrollIntoView({block:'nearest'})});
function step(d){const cs=cells(ent()),j=cs.indexOf(cur)+d;if(j>=0&&j<cs.length)cur=cs[j]}
function type(ch){if(!cur)return;if(rev[cur]){step(1);paint();return}st[cur]=ch;msg('xw','');step(1);paint()}
function back(){if(!cur)return;if(st[cur]&&!rev[cur]){delete st[cur]}else{step(-1);if(!rev[cur])delete st[cur]}paint()}
inp.addEventListener('input',()=>{const v=inp.value;if(v.length<1)back();else{const ch=v.slice(-1).toUpperCase();if(/[A-Z]/.test(ch))type(ch)}inp.value=' '});
inp.addEventListener('keydown',ev=>{if(ev.key==='Backspace'&&inp.value===''){ev.preventDefault();back()}
 const mv={ArrowRight:[0,1],ArrowLeft:[0,-1],ArrowDown:[1,0],ArrowUp:[-1,0]}[ev.key];
 if(mv&&cur){ev.preventDefault();let [r,c]=cur.split(',').map(Number);for(;;){r+=mv[0];c+=mv[1];if(r<0||c<0||r>=R||c>=C)break;if(ce[r+','+c]){dir=mv[0]?'D':'A';cur=r+','+c;break}}paint()}});
$('#xw .chk').onclick=()=>{let n=0;for(const k in st)if(st[k]!==sol(k)){cel(k).classList.add('bad');n++}msg('xw',n?`${n} square${n>1?'s':''} wrong.`:'Everything so far is right.',n?'bad':'')};
$('#xw .rvw').onclick=()=>{if(!cur){msg('xw','Tap a square first.');return}cells(ent()).forEach(k=>{if(st[k]!==sol(k)){st[k]=sol(k);rev[k]=1}});save('xwrev',rev);paint()};
twice($('#xw .rva'),()=>{for(const k in ce){if(st[k]!==sol(k)){st[k]=sol(k);rev[k]=1}}save('xwrev',rev);paint()});
twice($('#xw .clr'),()=>{st={};rev={};save('xwrev',rev);msg('xw','');paint()});
paint();})();

/* ── whodunit ── */
(()=>{const W=G.whodunit,n=W.size,t=$('#wd .lg');let st=load('wd',{});
const cyc={'':'x','x':'o','o':''};
function set(k,v){if(v)st[k]=v;else delete st[k]}
t.onclick=ev=>{const td=ev.target.closest('td[data-k]');if(!td)return;const k=td.dataset.k,v=cyc[st[k]||''];set(k,v);
 if(v==='o'){const [g,a,b]=k.split(':');for(let j=0;j<n;j++){if(j!=+b&&!st[`${g}:${a}:${j}`])st[`${g}:${a}:${j}`]='x';if(j!=+a&&!st[`${g}:${j}:${b}`])st[`${g}:${j}:${b}`]='x'}}
 paint()};
function paint(){$$('td[data-k]',t).forEach(td=>{const v=st[td.dataset.k]||'';td.textContent=v==='x'?'✕':v==='o'?'●':'';td.className=td.className.replace(/\bo\b/,'').trim()+(v==='o'?' o':'')});save('wd',st)}
twice($('#wd .clr'),()=>{st={};paint();msg('wd','')});
$('#wd .acc').onclick=()=>{const w=+$('#wd .who').value,x=+$('#wd .what').value,y=+$('#wd .where').value;
 if(w<0||x<0||y<0){msg('wd','Choose a suspect, a weapon and a place.');return}
 const s=W.solution,ok=w===s.killer&&x===s.weapon[s.killer]&&y===W.crime_place;
 if(ok){msg('wd',`Case closed: ${W.suspects[w].name}, with the ${W.weapons[x]}, in the ${W.places[y]}.`,'win');won('wd');save('wdwon',1)}
 else msg('wd',w===s.killer?'Right suspect, but the details are off.':'Not quite. Check your grid against the clues.','bad')};
$('#wd .rv').onclick=()=>{const s=W.solution;msg('wd',`It was ${W.suspects[s.killer].name}, with the ${W.weapons[s.weapon[s.killer]]}, in the ${W.places[W.crime_place]}.`)};
if(load('wdwon',0))won('wd');paint()})();

/* ── murder map ── */
(()=>{const M=G.murdermap,n=M.n,b=$('#mm .mboard');let st=load('mm',{}),tool=M.people[0].initial;
const COL=['#F6C9A8','#B9D8F2','#C8E6B8','#E8C4E8','#F2E3A2','#BFE3DD'];
const fur={};M.furniture.forEach(f=>fur[f.r+','+f.c]=f.t);
b.style.gridTemplateColumns=`repeat(${n},1fr)`;let h='';
for(let r=0;r<n;r++)for(let c=0;c<n;c++){const rm=M.room[r][c],bw=[r>0&&M.room[r-1][c]!==rm?3:0,c<n-1&&M.room[r][c+1]!==rm?3:0,r<n-1&&M.room[r+1][c]!==rm?3:0,c>0&&M.room[r][c-1]!==rm?3:0];
 const f=fur[r+','+c];h+=`<div data-k="${r},${c}" class="${f==='rug'?'rug':''}" style="background-color:${COL[rm]};border-width:${bw.map(x=>x/2+'px').join(' ')}"><span class="ri">${M.rooms[rm][0]}</span>${f==='plant'?'<span class="f">♣</span>':f==='table'?'<span class="f">▬</span>':''}</div>`}
b.innerHTML=h;
$('#mm .tools').onclick=ev=>{const bt=ev.target.closest('button');if(!bt)return;tool=bt.dataset.t;$$('#mm .tools button').forEach(x=>x.classList.toggle('on',x===bt))};
b.onclick=ev=>{const d=ev.target.closest('[data-k]');if(!d)return;const k=d.dataset.k,f=fur[k];if(f==='plant'||f==='table'){msg('mm','Nobody can stand on a '+f+'.');return}
 if(tool==='erase')delete st[k];else if(tool==='x')st[k]=st[k]==='x'?undefined:'x';else{if(st[k]===tool)delete st[k];else{for(const q in st)if(st[q]===tool)delete st[q];st[k]=tool}}
 for(const q in st)if(st[q]===undefined)delete st[q];msg('mm','');paint()};
function paint(){$$('[data-k]',b).forEach(d=>{const v=st[d.dataset.k];d.classList.remove('bad');d.querySelectorAll('.tok,.xm').forEach(x=>x.remove());
 if(v==='x')d.insertAdjacentHTML('beforeend','<span class="xm">✕</span>');else if(v)d.insertAdjacentHTML('beforeend',`<span class="tok${v==='V'?' v':''}">${v}</span>`)});save('mm',st)}
const where=i=>M.solution.pos[i].join(',');
$('#mm .chk').onclick=()=>{let wrong=0,missing=0;M.people.forEach((p,i)=>{const k=Object.keys(st).find(q=>st[q]===p.initial);if(!k)missing++;else if(k!==where(i)){wrong++;b.querySelector(`[data-k="${k}"]`).classList.add('bad')}});
 if(!wrong&&!missing){msg('mm',`Solved! ${M.people[M.solution.killer].name} was alone with the victim in the ${M.rooms[M.room[M.solution.pos[M.victim][0]][M.solution.pos[M.victim][1]]]}.`,'win');won('mm');save('mmwon',1)}
 else msg('mm',wrong?`${wrong} ${wrong>1?'people are':'person is'} in the wrong spot.`:`${missing} still to place.`,wrong?'bad':'')};
twice($('#mm .rv'),()=>{st={};M.people.forEach((p,i)=>st[where(i)]=p.initial);paint();msg('mm',`${M.people[M.solution.killer].name} did it.`)});
twice($('#mm .clr'),()=>{st={};paint();msg('mm','')});
if(load('mmwon',0))won('mm');paint()})();

/* ── sudoku ── */
(()=>{const P=G.sudoku.puzzle,S=G.sudoku.solution,b=$('#sd .sboard');let st=load('sd',{v:{},n:{}}),cur=-1,notes=false;
let h='';for(let i=0;i<81;i++){const r=Math.floor(i/9),c=i%9;h+=`<div data-i="${i}" class="${P[i]!=='0'?'g ':''}${c%3==2&&c<8?'br ':''}${r%3==2&&r<8?'bb':''}"></div>`}b.innerHTML=h;
const val=i=>P[i]!=='0'?P[i]:(st.v[i]||'');
function paint(){const cv=cur>=0?val(cur):'';$$('[data-i]',b).forEach(d=>{const i=+d.dataset.i,r=Math.floor(i/9),c=i%9,v=val(i);
 d.classList.remove('peer','same','cur','bad');
 if(cur>=0){const R=Math.floor(cur/9),C=cur%9;if(r===R||c===C||(Math.floor(r/3)===Math.floor(R/3)&&Math.floor(c/3)===Math.floor(C/3)))d.classList.add('peer');if(cv&&v===cv)d.classList.add('same');if(i===cur)d.classList.add('cur')}
 d.innerHTML=v?v:(st.n[i]?`<span class="nt">${[1,2,3,4,5,6,7,8,9].map(k=>`<span>${st.n[i].includes(k)?k:''}</span>`).join('')}</span>`:'')});
 save('sd',st);if([...Array(81).keys()].every(i=>val(i)===S[i])){msg('sd','Solved! Well played.','win');won('sd')}}
b.onclick=ev=>{const d=ev.target.closest('[data-i]');if(!d)return;cur=+d.dataset.i;paint()};
function put(k){if(cur<0||P[cur]!=='0')return;if(k==='del'){delete st.v[cur];delete st.n[cur]}
 else if(notes){if(st.v[cur])return;const s=st.n[cur]||'';st.n[cur]=s.includes(k)?s.replace(k,''):s+k}
 else{st.v[cur]=st.v[cur]===k?undefined:k;if(!st.v[cur])delete st.v[cur];delete st.n[cur]}msg('sd','');paint()}
$('#sd .pad').onclick=ev=>{const bt=ev.target.closest('button');if(!bt)return;if(bt.dataset.k==='mode'){notes=!notes;bt.classList.toggle('on',notes);bt.innerHTML=notes?'✎<small> on</small>':'✎';return}put(bt.dataset.k)};
document.addEventListener('keydown',ev=>{if($('#sd').hidden)return;if(/^[1-9]$/.test(ev.key))put(ev.key);if(ev.key==='Backspace')put('del')});
$('#sd .era').onclick=()=>put('del');
$('#sd .chk').onclick=()=>{let n=0;for(const i in st.v)if(st.v[i]!==S[i]){b.querySelector(`[data-i="${i}"]`).classList.add('bad');n++}msg('sd',n?`${n} wrong.`:'No mistakes so far.',n?'bad':'')};
twice($('#sd .rv'),()=>{for(let i=0;i<81;i++)if(P[i]==='0')st.v[i]=S[i];paint()});
twice($('#sd .clr'),()=>{st={v:{},n:{}};paint();msg('sd','')});
paint()})();
})();
"""


JS_SAFE = JS.replace("</", "<\\/")


def _xw_html(x: dict) -> str:
    def clues(d):
        return "".join(f"<li data-i='{i}'><b>{en['n']}</b><span>{e(en['clue'])} ({len(en['answer'])})</span></li>"
                       for i, en in enumerate(x["entries"]) if en["d"] == d)
    return (f"<section class='game' id='xw'><h2>Crossword</h2><p class='gsub'>{e(x.get('theme') or '')}"
            f"{' · built from today’s stories' if x.get('theme') and x.get('theme') != 'Mixed bag' else ''}. "
            "Tap a square to type; tap it again to switch direction.</p>"
            "<div class='cbar'>Tap a square or a clue to start.</div>"
            "<div class='xwrap'><input class='kb' autocapitalize='characters' autocomplete='off' autocorrect='off' spellcheck='false' aria-label='Crossword input'>"
            "<div class='xboard'></div></div><div class='gmsg'></div>"
            "<div class='gbtns'><button class='btn chk'>Check</button><button class='btn rvw'>Reveal word</button>"
            "<button class='btn rva'>Reveal all</button><button class='btn clr'>Clear</button></div>"
            f"<div class='clues'><h3>Across</h3><ol>{clues('A')}</ol><h3>Down</h3><ol>{clues('D')}</ol></div></section>")


def _wd_html(w: dict) -> str:
    n = w["size"]
    sus = [s["name"] for s in w["suspects"]]
    cols = [x.title() for x in w["weapons"]] + [x.title() for x in w["places"]]
    head = "<tr><th></th>" + "".join(f"<th class='{'thick-l' if j == n else ''}'>{e(c)}</th>" for j, c in enumerate(cols)) + "</tr>"
    rows = ""
    for i, s in enumerate(sus):  # suspects × weapons | suspects × places
        rows += (f"<tr><th>{e(s)}</th>" + "".join(f"<td data-k='sw:{i}:{j}'></td>" for j in range(n))
                 + "".join(f"<td data-k='sl:{i}:{j}' class='{'thick-l' if j == 0 else ''}'></td>" for j in range(n)) + "</tr>")
    for i, p in enumerate(w["places"]):  # places × weapons
        rows += (f"<tr><th>{e(p.title())}</th>" + "".join(
            f"<td data-k='pw:{i}:{j}' class='{'thick-t' if i == 0 else ''}'></td>" for j in range(n))
                 + "".join("<td class='gap'></td>" for _ in range(n)) + "</tr>")
    opts = lambda xs, label: f"<option value='-1'>{label}</option>" + "".join(
        f"<option value='{i}'>{e(x)}</option>" for i, x in enumerate(xs))
    return (f"<section class='game' id='wd' hidden><h2>Whodunit</h2><p class='gsub'>{e(w['intro'])}</p>"
            "<div class='cast'>" + "".join(f"<div><b>{e(s['name'])}</b>, {e(s['about'])}</div>" for s in w["suspects"]) + "</div>"
            "<ol class='wclues'>" + "".join(f"<li>{e(c)}</li>" for c in w["clues"]) + "</ol>"
            "<p class='gsub'>Tap a box once for ✕ (ruled out), twice for ● (confirmed).</p>"
            f"<div class='lgwrap'><table class='lg'><thead>{head}</thead><tbody>{rows}</tbody></table></div>"
            "<div class='accuse'>"
            f"<select class='who'>{opts(sus, 'Who did it?')}</select>"
            f"<select class='what'>{opts(w['weapons'], 'With what?')}</select>"
            f"<select class='where'>{opts(w['places'], 'Where?')}</select>"
            "<button class='btn primary acc'>Make the accusation</button></div><div class='gmsg' style='margin-top:10px'></div>"
            "<div class='gbtns'><button class='btn rv'>Reveal</button><button class='btn clr'>Clear grid</button></div></section>")


MM_COLORS = ['#F6C9A8', '#B9D8F2', '#C8E6B8', '#E8C4E8', '#F2E3A2', '#BFE3DD']


def _mm_html(m: dict) -> str:
    tools = "".join(f"<button data-t='{p['initial']}' class='{'on' if i == 0 else ''}'><b>{p['initial']}</b>"
                    f"{e(p['name'].split()[0] if i != m['victim'] else 'Victim')}</button>" for i, p in enumerate(m["people"]))
    tools += "<button data-t='x'><b>✕</b>Rule out</button><button data-t='erase'><b>⌫</b>Erase</button>"
    legend = "".join(f"<span><i style='background:{MM_COLORS[i]}'></i>{e(r)}</span>" for i, r in enumerate(m["rooms"]))
    legend += "<span>♣ plant</span><span>▬ table</span><span><i class='rug' style='background:#ddd;background-image:repeating-linear-gradient(45deg,#999 0 3px,transparent 3px 7px)'></i>rug</span>"
    cast = "".join(f"<div><b>{e(p['name'])}</b>, {e(p['about'])}</div>" for p in m["people"])
    return ("<section class='game' id='mm' hidden><h2>Murder map</h2>"
            f"<p class='gsub'>Place all {m['n']} people on the floor plan. Each row and each column holds exactly one person, "
            "and nobody stands on a plant or table (rugs are fine). The murderer is the only person alone in a room with the victim.</p>"
            f"<div class='cast'>{cast}</div><ol class='wclues'>" + "".join(f"<li>{e(c)}</li>" for c in m["clues"]) + "</ol>"
            f"<div class='tools'>{tools}</div><div class='mboard'></div><div class='legend'>{legend}</div><div class='gmsg'></div>"
            "<div class='gbtns'><button class='btn chk'>Check</button><button class='btn rv'>Reveal</button>"
            "<button class='btn clr'>Clear</button></div></section>")


def _sd_html(s: dict) -> str:
    pad = "".join(f"<button data-k='{k}'>{k}</button>" for k in range(1, 10)) + \
        "<button data-k='mode' class='mode' aria-label='Pencil notes'>✎</button>"
    return ("<section class='game' id='sd' hidden><h2>Sudoku</h2>"
            f"<p class='gsub'>{s['givens']} clues. Fill every row, column and box with 1–9. ✎ switches to pencil notes.</p>"
            f"<div class='sboard'></div><div class='pad'>{pad}</div>"
            "<div class='gmsg'></div><div class='gbtns'><button class='btn chk'>Check</button>"
            "<button class='btn era'>Erase</button><button class='btn rv'>Reveal</button><button class='btn clr'>Clear</button></div></section>")


def page_body(g: dict, root: str, past: list[str]) -> str:
    nice = dt.date.fromisoformat(g["date"]).strftime("%A, %B %-d")
    extra = more.sections(g)
    order = [("qz", "Quiz"), ("gr", "Groups"), ("xw", "Crossword"), ("hv", "Hive"), ("wd", "Whodunit"), ("mm", "Map"),
             ("cg", "Cryptogram"), ("ld", "Ladder"), ("sd", "Sudoku"), ("ft", "Futoshiki"), ("qn", "Queens"), ("ng", "Nonogram")]
    order = [(k, l) for k, l in order if k in extra or k in ("xw", "wd", "mm", "sd")]
    seg = "".join(f"<button data-g='{k}'>{label}</button>" for k, label in order)
    keys = ("date", "crossword", "whodunit", "murdermap", "sudoku", "quiz", "groups", "hive", "cryptogram", "ladder",
            "nonogram", "futoshiki", "queens")
    data = json.dumps({k: g[k] for k in keys if k in g}).replace("</", "<\\/")
    extra_html = "".join(f"<section class='game' id='{k}' hidden>{v}</section>" for k, v in extra.items())
    past_html = ""
    if past:
        past_html = ("<div class='past'><h3>Past puzzles</h3><div class='toc'>" + "".join(
            f"<a href='{root}games/{d}.html'><span class='k'>›</span><span>{dt.date.fromisoformat(d).strftime('%A, %B %-d')}</span></a>"
            for d in past) + "</div></div>")
    return (f"<style>{CSS}{more.CSS}</style><main class='page'><section class='hero'><div class='kicker'>Games · {e(nice)}</div>"
            "<h1>Puzzles</h1><p>New puzzles every morning. They're also at the end of your Kobo briefing.</p></section>"
            f"<div class='seg'>{seg}</div>"
            + _xw_html(g["crossword"]) + _wd_html(g["whodunit"]) + _mm_html(g["murdermap"]) + _sd_html(g["sudoku"])
            + extra_html + past_html + KOBO_CARD.format(root=root) + f"</main><script type='application/json' id='gdata'>{data}</script>"
            f"<script>{JS_SAFE}</script><script>{more.JS_SAFE}</script>")


KOBO_CARD = ("<div class='past'><h3>Play on your Kobo</h3><div class='fresh' style='display:block;padding:16px;border-radius:18px;background:var(--card)'>"
             "<p class='gsub' style='margin:0 0 10px'>Tap to solve all of these in KOReader. One-time setup, on a computer:</p>"
             "<ol style='margin:0;padding-left:20px;font-size:14px;line-height:1.6;color:var(--detail)'>"
             "<li>Download the <a href='{root}kobo/briefinggames.koplugin.zip' style='text-decoration:underline'>Briefing puzzles plugin</a> and unzip it.</li>"
             "<li>Plug in your Kobo and copy the <b>briefinggames.koplugin</b> folder into <b>.adds/koreader/plugins</b>. "
             "(.adds is a hidden folder; on a Mac press Cmd+Shift+. to see it.)</li>"
             "<li>Eject, then restart KOReader.</li>"
             "<li>Open the top menu → Tools (🛠) → <b>Briefing puzzles</b>. It downloads the day's puzzles over Wi-Fi.</li></ol></div></div>")


def write_pages(shell, date: str) -> None:
    g = load(date)
    days = sorted((p.stem for p in DATA.glob("20*.json")), reverse=True)
    if not g and days:
        g = load(days[0])
    if not g:
        return
    (DOCS / "games").mkdir(parents=True, exist_ok=True)
    past = [d for d in days if d != g["date"]][:14]
    (DOCS / "games.html").write_text(shell("Games — Briefing", "games", page_body(g, "", past)))
    (DOCS / "games" / "today.json").write_text(json.dumps(g))   # for the Kobo plugin
    _kobo_zip()
    for d in days[:15]:
        gd = load(d)
        if gd:
            (DOCS / "games" / f"{d}.html").write_text(
                shell(f"Games — {d}", "games", page_body(gd, "../", [x for x in days if x != d][:14]), root="../"))


def _kobo_zip() -> None:
    """Package the KOReader plugin so it can be downloaded from the site."""
    import zipfile
    src = Path("kobo") / "briefinggames.koplugin"
    if not src.exists():
        return
    out = DOCS / "kobo"
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out / "briefinggames.koplugin.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(src.glob("*.lua")):
            info = zipfile.ZipInfo(f"briefinggames.koplugin/{p.name}", (2026, 1, 1, 0, 0, 0))
            z.writestr(info, p.read_bytes())


# ── e-reader (EPUB) ───────────────────────────────────────────────────────
EPUB_CSS = """
table.g{border-collapse:collapse;margin:.6em auto}
table.g td{border:1px solid #000;width:1.7em;height:1.7em;text-align:center;vertical-align:middle;padding:0;font-size:.95em;position:relative}
table.g td.b{background:#000}
table.g td.n{vertical-align:top;text-align:left;font-size:.55em;padding:1px 2px;line-height:1}
table.g td.e{border:0}
table.s td{width:1.9em;height:1.9em;font-size:1.05em;font-weight:bold}
table.s td.r{border-right:3px solid #000}
table.s td.d{border-bottom:3px solid #000}
table.m td{width:2.6em;height:2.6em;font-size:.8em}
p.clue{margin:.25em 0}
ol.cl li{margin:.3em 0}
.small{font-size:.85em}
"""


def _xw_grid(x, filled=False):
    nums = {(en["r"], en["c"]): en["n"] for en in x["entries"]}
    rows = ""
    for r, line in enumerate(x["solution"]):
        rows += "<tr>"
        for c, ch in enumerate(line):
            if ch == ".":
                rows += "<td class='e'></td>"
            elif filled:
                rows += f"<td>{ch}</td>"
            else:
                rows += f"<td class='n'>{nums.get((r, c), '')}</td>"
        rows += "</tr>"
    return f"<table class='g'>{rows}</table>"


def _mm_grid(m, filled=False):
    sym = {"plant": "♣", "table": "▬", "rug": "≈"}
    fur = {(f["r"], f["c"]): f["t"] for f in m["furniture"]}
    who = {tuple(p): m["people"][i]["initial"] for i, p in enumerate(m["solution"]["pos"])} if filled else {}
    room, n = m["room"], m["n"]
    rows = ""
    for r in range(n):
        rows += "<tr>"
        for c in range(n):
            rm = room[r][c]
            bw = [r == 0 or room[r - 1][c] != rm, c == n - 1 or room[r][c + 1] != rm,
                  r == n - 1 or room[r + 1][c] != rm, c == 0 or room[r][c - 1] != rm]
            style = "border-width:" + " ".join("3px" if x else "1px" for x in bw)
            inner = f"<b>{who[(r, c)]}</b><br/>" if (r, c) in who else ""
            rows += (f"<td style='{style}'>{inner}<span class='small'>{e(m['rooms'][rm][0])}"
                     f"{' ' + sym[fur[(r, c)]] if (r, c) in fur else ''}</span></td>")
        rows += "</tr>"
    return f"<table class='g m'>{rows}</table>"


def _sd_grid(s, filled=False):
    src = s["solution"] if filled else s["puzzle"]
    rows = ""
    for r in range(9):
        rows += "<tr>" + "".join(
            f"<td class='{'r' if c in (2, 5) else ''} {'d' if r in (2, 5) else ''}'>{src[r * 9 + c] if src[r * 9 + c] != '0' else ''}</td>"
            for c in range(9)) + "</tr>"
    return f"<table class='g s'>{rows}</table>"


def epub_pages(g: dict) -> list[tuple[str, str, str]]:
    """(title, filename, body) for each puzzle page and the answers page."""
    x, w, m, s = g["crossword"], g["whodunit"], g["murdermap"], g["sudoku"]
    back = "<p class='back'><a href='contents.xhtml'>↩ Back to contents</a> · <a href='g_answers.xhtml'>Answers</a></p>"
    cl = lambda d: "".join(f"<p class='clue'><b>{en['n']}.</b> {e(en['clue'])} ({len(en['answer'])})</p>"
                           for en in x["entries"] if en["d"] == d)
    pages = [
        ("Crossword", "g_xw.xhtml",
         f"<p class='meta'>Puzzles · Crossword</p><h1>{e(x.get('theme') or 'Crossword')}</h1>{_xw_grid(x)}"
         f"<h2>Across</h2>{cl('A')}<h2>Down</h2>{cl('D')}{back}"),
        ("Whodunit", "g_wd.xhtml",
         f"<p class='meta'>Puzzles · Whodunit</p><h1>Whodunit</h1><p>{e(w['intro'])}</p>"
         "<h2>Suspects</h2>" + "".join(f"<p class='clue'><b>{e(su['name'])}</b>, {e(su['about'])}</p>" for su in w["suspects"])
         + f"<p class='small'>Weapons: {e(', '.join(w['weapons']))}<br/>Places: {e(', '.join(w['places']))}</p>"
         "<h2>Clues</h2><ol class='cl'>" + "".join(f"<li>{e(c)}</li>" for c in w["clues"]) + f"</ol>{back}"),
        ("Murder map", "g_mm.xhtml",
         "<p class='meta'>Puzzles · Murder map</p><h1>Murder map</h1>"
         f"<p class='small'>Place all {m['n']} people. One per row and one per column; nobody stands on a plant (♣) or table (▬); "
         "rugs (≈) are fine. The murderer is the only person alone in a room with the victim.</p>"
         f"{_mm_grid(m)}<p class='small'>Rooms: " + ", ".join(f"{r[0]} = {e(r)}" for r in m["rooms"]) + "</p>"
         "<h2>People</h2>" + "".join(f"<p class='clue'><b>{e(p['initial'])}</b> · {e(p['name'])}, {e(p['about'])}</p>" for p in m["people"])
         + "<h2>Clues</h2><ol class='cl'>" + "".join(f"<li>{e(c)}</li>" for c in m["clues"]) + f"</ol>{back}"),
        ("Sudoku", "g_sd.xhtml",
         f"<p class='meta'>Puzzles · Sudoku</p><h1>Sudoku</h1><p class='small'>{s['givens']} clues.</p>{_sd_grid(s)}{back}"),
    ]
    extra_pages, extra_ans = more.epub_pages(g)
    pages = extra_pages[:2] + pages + extra_pages[2:]
    sol = w["solution"]
    k = sol["killer"]
    table = "".join(f"<p class='clue'>{e(su['name'])}: {e(w['weapons'][sol['weapon'][i]])}, {e(w['places'][sol['place'][i]])}</p>"
                    for i, su in enumerate(w["suspects"]))
    mk = m["solution"]["killer"]
    pages.append(("Puzzle answers", "g_answers.xhtml",
                  "<p class='meta'>Puzzles</p><h1>Answers</h1>"
                  f"<h2>Crossword</h2>{_xw_grid(x, True)}"
                  f"<h2>Whodunit</h2><p><b>{e(w['suspects'][k]['name'])}</b>, with the {e(w['weapons'][sol['weapon'][k]])}, "
                  f"in the {e(w['places'][w['crime_place']])}.</p>{table}"
                  f"<h2>Murder map</h2>{_mm_grid(m, True)}<p><b>{e(m['people'][mk]['name'])}</b> did it.</p>"
                  f"<h2>Sudoku</h2>{_sd_grid(s, True)}{extra_ans}"
                  "<p class='back'><a href='contents.xhtml'>↩ Back to contents</a></p>"))
    return pages
