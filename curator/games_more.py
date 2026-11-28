"""Web UI and EPUB pages for the extra puzzles (see puzzles_more.py)."""
from __future__ import annotations

import html
import json

e = html.escape
REG = ['#F6C9A8', '#B9D8F2', '#C8E6B8', '#E8C4E8', '#F2E3A2', '#BFE3DD', '#F4B6B6', '#D6CCF5', '#E3D2B4', '#C9D3DF']

CSS = r"""
/* quiz */
.qq{background:var(--card);border-radius:16px;padding:14px;margin:0 0 10px}
.qq p{margin:0 0 10px;font-size:15.5px;line-height:1.4;font-weight:600}
.qq button{display:block;width:100%;text-align:left;margin:6px 0 0;padding:11px 12px;border-radius:12px;border:1px solid var(--line);background:var(--tile);color:var(--ink);font:500 14.5px var(--sans)}
.qq button.right{border-color:#4ADE80;background:#12331F}
.qq button.wrong{border-color:#F28B82;background:#3A1A1A}
.qq .why{font-size:13.5px;color:var(--detail);margin-top:8px;line-height:1.45}
/* groups */
.gsolved{display:flex;flex-direction:column;gap:6px;margin-bottom:6px}
.gsolved div{border-radius:12px;padding:10px;text-align:center;color:#0B1220}
.gsolved b{display:block;font-size:13px;letter-spacing:.06em;text-transform:uppercase}
.gsolved span{font-size:14px}
.gtiles{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.gtiles button{height:64px;border-radius:12px;border:0;background:var(--tile);color:var(--ink);font:700 clamp(10px,3vw,13.5px) var(--sans);padding:2px;word-break:break-word}
.gtiles button.sel{background:var(--ink);color:var(--bg)}
.dots{font-size:13px;color:var(--muted);margin:10px 2px}
/* hive */
.hword{text-align:center;font:700 26px var(--sans);letter-spacing:.06em;min-height:36px;margin:6px 0}
.hword .c{color:var(--accent)}
.hex{position:relative;width:240px;height:236px;margin:6px auto}
.hex button{position:absolute;width:76px;height:66px;border:0;background:var(--tile);color:var(--ink);font:800 24px var(--sans);clip-path:polygon(25% 0,75% 0,100% 50%,75% 100%,25% 100%,0 50%)}
.hex button.c{background:var(--accent);color:var(--on-accent)}
.hfound{display:flex;flex-wrap:wrap;gap:6px 10px;font-size:14px;color:var(--detail);margin:10px 2px}
.hfound .pg{color:var(--accent);font-weight:700}
.hbar{height:6px;background:var(--tile);border-radius:3px;margin:6px 2px 2px;overflow:hidden}
.hbar i{display:block;height:100%;background:var(--accent)}
/* cryptogram */
.cg{display:flex;flex-wrap:wrap;gap:10px 12px;margin:10px 0;user-select:none;-webkit-user-select:none}
.cg .w{display:flex;gap:2px}
.cg .l{display:flex;flex-direction:column;align-items:center;width:clamp(18px,5.6vw,24px)}
.cg .l b{height:26px;width:100%;border-bottom:2px solid var(--muted);font:700 18px var(--sans);text-align:center;color:var(--ink)}
.cg .l small{font:600 11px var(--sans);color:var(--muted);margin-top:3px}
.cg .l.sel b{border-color:var(--accent);background:var(--tile)}
.cg .l.hint b{color:var(--accent)}
.cg .p{font:700 18px var(--sans);align-self:flex-start;padding-top:2px}
/* ladder */
.lad{display:flex;flex-direction:column;gap:8px;align-items:center;margin:10px 0}
.lad input,.lad div{width:180px;height:46px;border-radius:12px;border:1px solid var(--line);background:var(--tile);color:var(--ink);font:700 22px var(--sans);letter-spacing:.3em;text-align:center;text-transform:uppercase;display:flex;align-items:center;justify-content:center;padding:0}
.lad div{background:var(--card);border-color:transparent;color:var(--accent)}
.lad input.bad{border-color:#F28B82}
.lad input.good{border-color:#4ADE80}
/* nonogram */
.ngw{overflow-x:auto}
.ng{border-collapse:collapse;margin:6px auto;user-select:none;-webkit-user-select:none;touch-action:manipulation}
.ng td{width:28px;height:28px;padding:0;text-align:center;border:1px solid var(--line);background:var(--card)}
.ng td.f{background:var(--ink)}
.ng td.x::after{content:'✕';color:var(--muted);font-size:13px}
.ng td.r5{border-right:2px solid var(--muted)}
.ng td.b5{border-bottom:2px solid var(--muted)}
.ng th{font:600 11px var(--sans);color:var(--detail);padding:2px 4px}
.ng th.cc{vertical-align:bottom;line-height:1.25}
.ng th.rc{text-align:right;white-space:nowrap}
.mode2{display:flex;gap:6px;margin:8px 0}
.mode2 button{flex:1;height:40px;border-radius:12px;border:1px solid var(--line);background:none;color:var(--ink);font:600 14px var(--sans)}
.mode2 button.on{border-color:var(--accent);background:var(--tile)}
/* futoshiki */
.ft{display:grid;gap:0;margin:8px auto;max-width:360px;user-select:none;-webkit-user-select:none}
.ft .c{aspect-ratio:1;border-radius:10px;background:var(--card);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;font:600 24px var(--sans);color:#7FB4FF}
.ft .c.g{color:var(--ink);font-weight:800}
.ft .c.cur{background:#3A4A6B}
.ft .c.bad{color:#F28B82}
.ft .s{display:flex;align-items:center;justify-content:center;font:800 18px var(--sans);color:var(--accent)}
/* queens */
.qb{display:grid;border:2px solid var(--ink);border-radius:6px;overflow:hidden;user-select:none;-webkit-user-select:none;touch-action:manipulation}
.qb div{aspect-ratio:1;display:flex;align-items:center;justify-content:center;border:0 solid #0B1220;font:800 clamp(16px,5vw,24px) var(--sans);color:#0B1220}
.qb div.x{color:rgba(11,18,32,.45);font-size:15px}
.qb div.bad{color:#B91C1C}
"""

JS = r"""
(()=>{const G=JSON.parse(document.getElementById('gdata').textContent);
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
const K=k=>'game:'+G.date+':'+k;
const load=(k,d)=>{try{const v=JSON.parse(localStorage.getItem(K(k)));return v==null?d:v}catch(_){return d}};
const save=(k,v)=>{try{localStorage.setItem(K(k),JSON.stringify(v))}catch(_){}};
const msg=(id,t,c)=>{const m=$('#'+id+' .gmsg');if(m){m.textContent=t;m.className='gmsg'+(c?' '+c:'')}};
const won=id=>{const b=$(`.seg [data-g="${id}"]`);if(b&&!b.querySelector('.ok'))b.insertAdjacentHTML('beforeend','<span class="ok">✓</span>')};
const twice=(btn,fn)=>{if(!btn)return;btn.onclick=()=>{if(btn.dataset.arm){delete btn.dataset.arm;btn.textContent=btn.dataset.l;fn()}else{btn.dataset.l=btn.textContent;btn.dataset.arm=1;btn.textContent='Tap again';setTimeout(()=>{if(btn.dataset.arm){delete btn.dataset.arm;btn.textContent=btn.dataset.l}},2500)}}};
const esc=t=>String(t).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const shuffle=a=>{for(let i=a.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[a[i],a[j]]=[a[j],a[i]]}return a};

/* quiz */
if(G.quiz)(()=>{const Q=G.quiz.questions,box=$('#qz .qlist');let st=load('qz',{});
function paint(){box.innerHTML=Q.map((q,i)=>{const a=st[i];return `<div class="qq"><p>${i+1}. ${esc(q.q)}</p>${q.options.map((o,j)=>`<button data-q="${i}" data-o="${j}" class="${a==null?'':j===q.answer?'right':j===a?'wrong':''}">${esc(o)}</button>`).join('')}${a!=null&&q.why?`<div class="why">${esc(q.why)}</div>`:''}</div>`}).join('');
 const n=Object.keys(st).length,s=Q.filter((q,i)=>st[i]===q.answer).length;
 if(n===Q.length){msg('qz',`You scored ${s} out of ${Q.length}.`,'win');won('qz')}else msg('qz',n?`${s} of ${n} so far.`:'');save('qz',st)}
box.onclick=ev=>{const b=ev.target.closest('button');if(!b)return;const i=+b.dataset.q;if(st[i]!=null)return;st[i]=+b.dataset.o;paint()};
twice($('#qz .clr'),()=>{st={};paint()});paint()})();

/* groups */
if(G.groups)(()=>{const GR=G.groups.groups;let st=load('gr',{found:[],miss:0,order:null}),sel=[];
const all=GR.flatMap(g=>g.words);if(!st.order)st.order=shuffle(all.slice());
const COL=['#F2E3A2','#C8E6B8','#B9D8F2','#E8C4E8'];
function paint(){const left=st.order.filter(w=>!st.found.some(i=>GR[i].words.includes(w)));
 $('#gr .gsolved').innerHTML=st.found.map(i=>`<div style="background:${COL[i]}"><b>${esc(GR[i].name)}</b><span>${GR[i].words.join(', ')}</span></div>`).join('');
 $('#gr .gtiles').innerHTML=left.map(w=>`<button data-w="${w}" class="${sel.includes(w)?'sel':''}">${w}</button>`).join('');
 $('#gr .dots').textContent=st.found.length===4?'':'Mistakes left: '+'● '.repeat(Math.max(0,4-st.miss));
 if(st.found.length===4){msg('gr',st.miss?`Solved with ${st.miss} mistake${st.miss>1?'s':''}.`:'Perfect! No mistakes.','win');won('gr')}save('gr',st)}
$('#gr .gtiles').onclick=ev=>{const b=ev.target.closest('button');if(!b)return;const w=b.dataset.w;sel=sel.includes(w)?sel.filter(x=>x!==w):sel.length<4?[...sel,w]:sel;paint()};
$('#gr .sub4').onclick=()=>{if(sel.length<4){msg('gr','Pick four words.');return}
 const i=GR.findIndex(g=>sel.every(w=>g.words.includes(w)));
 if(i>=0){st.found.push(i);sel=[];msg('gr','')}else{st.miss++;const close=GR.some(g=>sel.filter(w=>g.words.includes(w)).length===3);msg('gr',st.miss>=4?'Out of mistakes. Keep going, or reveal.':close?'One away…':'Not a group.','bad')}paint()};
$('#gr .shuf').onclick=()=>{shuffle(st.order);paint()};$('#gr .desel').onclick=()=>{sel=[];paint()};
twice($('#gr .rv'),()=>{st.found=[0,1,2,3].filter(i=>!st.found.includes(i)).reduce((a,i)=>[...a,i],st.found);paint()});
twice($('#gr .clr'),()=>{st={found:[],miss:0,order:shuffle(all.slice())};sel=[];msg('gr','');paint()});paint()})();

/* hive */
if(G.hive)(()=>{const H=G.hive,A=new Set(H.answers),P=new Set(H.pangrams);let st=load('hv',{f:[]}),cur='',outer=H.outer.slice();
const pts=w=>(w.length===4?1:w.length)+(P.has(w)?7:0);
const RANKS=[[0,'Beginner'],[.05,'Getting going'],[.15,'Solid'],[.3,'Good'],[.45,'Great'],[.6,'Amazing'],[.8,'Genius']];
const POS=[[82,0],[164,46],[164,136],[82,170],[0,136],[0,46]];
function hex(){$('#hv .hex').innerHTML=`<button class="c" data-l="${H.center}" style="left:82px;top:85px">${H.center}</button>`+outer.map((l,i)=>`<button data-l="${l}" style="left:${POS[i][0]}px;top:${POS[i][1]}px">${l}</button>`).join('')}
function paint(){$('#hv .hword').innerHTML=[...cur].map(c=>c===H.center?`<span class="c">${c}</span>`:c).join('')||'&nbsp;';
 const sc=st.f.reduce((a,w)=>a+pts(w),0),fr=sc/H.max;let rk='';for(const [t,n] of RANKS)if(fr>=t)rk=n;
 $('#hv .hsc').textContent=`${rk} · ${sc} points · ${st.f.length} of ${H.answers.length} words`;$('#hv .hbar i').style.width=Math.min(100,fr*100)+'%';
 $('#hv .hfound').innerHTML=st.f.slice().sort().map(w=>`<span class="${P.has(w)?'pg':''}">${w}</span>`).join('');
 if(st.f.length===H.answers.length){msg('hv','Every word found!','win');won('hv')}save('hv',st)}
function enter(){const w=cur;cur='';if(w.length<4)msg('hv','Too short.','bad');else if(!w.includes(H.center))msg('hv','Missing the center letter.','bad');
 else if(st.f.includes(w))msg('hv','Already found.');else if(!A.has(w))msg('hv','Not in the word list.','bad');
 else{st.f.push(w);msg('hv',P.has(w)?'Pangram! +'+pts(w):'+'+pts(w),P.has(w)?'win':'');if(fr()>=.45)won('hv')}paint()}
const fr=()=>st.f.reduce((a,w)=>a+pts(w),0)/H.max;
$('#hv .hex').onclick=ev=>{const b=ev.target.closest('button');if(b){cur+=b.dataset.l;paint()}};
$('#hv .del').onclick=()=>{cur=cur.slice(0,-1);paint()};$('#hv .ent').onclick=enter;$('#hv .shuf').onclick=()=>{shuffle(outer);hex()};
document.addEventListener('keydown',ev=>{if($('#hv').hidden)return;const k=ev.key.toUpperCase();if(k==='ENTER')enter();else if(k==='BACKSPACE'){cur=cur.slice(0,-1);paint()}else if(/^[A-Z]$/.test(k)&&(k===H.center||outer.includes(k))){cur+=k;paint()}});
twice($('#hv .rv'),()=>{$('#hv .hfound').innerHTML=H.answers.map(w=>`<span class="${P.has(w)?'pg':''}" style="${st.f.includes(w)?'':'opacity:.5'}">${w}</span>`).join('')});
if(fr()>=.45)won('hv');hex();paint()})();

/* cryptogram */
if(G.cryptogram)(()=>{const C=G.cryptogram,box=$('#cg .cg'),inp=$('#cg .kb');let st=load('cg',{}),cur=null;
const hint=C.hints;for(const k in hint)st[k]=hint[k];
box.innerHTML=C.cipher.split(' ').map(w=>`<span class="w">${[...w].map(ch=>/[A-Z]/.test(ch)?`<span class="l${hint[ch]?' hint':''}" data-c="${ch}"><b></b><small>${ch}</small></span>`:`<span class="p">${esc(ch)}</span>`).join('')}</span>`).join('');
function paint(){$$('.l',box).forEach(l=>{l.querySelector('b').textContent=st[l.dataset.c]||'';l.classList.toggle('sel',l.dataset.c===cur)});save('cg',st);
 const out=[...C.cipher].map(ch=>/[A-Z]/.test(ch)?(st[ch]||'_'):ch).join('');if(out===C.plain){msg('cg','Decoded!','win');won('cg')}}
box.onclick=ev=>{const l=ev.target.closest('.l');if(!l||hint[l.dataset.c])return;cur=l.dataset.c;paint();inp.value=' ';inp.focus({preventScroll:true})};
inp.addEventListener('input',()=>{const v=inp.value;if(cur){if(v.length<1)delete st[cur];else{const ch=v.slice(-1).toUpperCase();if(/[A-Z]/.test(ch)){for(const k in st)if(st[k]===ch&&!hint[k])delete st[k];st[cur]=ch;
 const ks=[...new Set([...C.cipher].filter(c=>/[A-Z]/.test(c)))];const i=ks.indexOf(cur);cur=ks.slice(i+1).concat(ks.slice(0,i)).find(k=>!st[k])||cur}}}inp.value=' ';msg('cg','');paint()});
$('#cg .chk').onclick=()=>{const map={};[...C.cipher].forEach((c,i)=>{if(/[A-Z]/.test(c))map[c]=C.plain[i]});let n=0;for(const k in st)if(st[k]!==map[k]){delete st[k];n++}paint();msg('cg',n?`Cleared ${n} wrong letter${n>1?'s':''}.`:'All correct so far.',n?'bad':'')};
twice($('#cg .rv'),()=>{[...C.cipher].forEach((c,i)=>{if(/[A-Z]/.test(c))st[c]=C.plain[i]});paint()});
twice($('#cg .clr'),()=>{st={};for(const k in hint)st[k]=hint[k];paint();msg('cg','')});paint()})();

/* word ladder */
if(G.ladder)(()=>{const L=G.ladder,V=new Set(L.valid),n=L.solution.length-2,box=$('#ld .lad');let st=load('ld',[]);
box.innerHTML=`<div>${L.start}</div>`+Array.from({length:n},(_,i)=>`<input maxlength="4" data-i="${i}" autocapitalize="characters" autocomplete="off" autocorrect="off" spellcheck="false" enterkeyhint="next">`).join('')+`<div>${L.end}</div>`;
const ins=$$('input',box);ins.forEach((x,i)=>x.value=st[i]||'');
const diff=(a,b)=>[...a].filter((c,i)=>c!==b[i]).length;
function check(){let prev=L.start,ok=true;st=ins.map(x=>x.value.toUpperCase());save('ld',st);
 ins.forEach(x=>{const w=x.value.toUpperCase();x.classList.remove('bad','good');if(w.length<4){ok=false;return}if(V.has(w)&&diff(prev,w)===1){x.classList.add('good');prev=w}else{x.classList.add('bad');ok=false}});
 if(ok&&diff(prev,L.end)===1){msg('ld','Solved!','win');won('ld')}else msg('ld','')}
ins.forEach((x,i)=>{x.addEventListener('input',()=>{check();if(x.value.length===4&&ins[i+1])ins[i+1].focus()})});
twice($('#ld .rv'),()=>{ins.forEach((x,i)=>x.value=L.solution[i+1]);check()});
twice($('#ld .clr'),()=>{ins.forEach(x=>x.value='');check()});check()})();

/* nonogram */
if(G.nonogram)(()=>{const N=G.nonogram,R=N.rows.length,C=N.cols.length,S=N.solution,t=$('#ng .ng');let st=load('ng',{}),mode='f';
const giv={};N.givens.forEach(([r,c,v])=>giv[r+','+c]=v?'f':'x');Object.assign(st,giv);
let h='<tr><th></th>'+N.cols.map(cl=>`<th class="cc">${cl.join('<br>')}</th>`).join('')+'</tr>';
for(let r=0;r<R;r++)h+=`<tr><th class="rc">${N.rows[r].join(' ')}</th>`+Array.from({length:C},(_,c)=>`<td data-k="${r},${c}" class="${c%5==4&&c<C-1?'r5 ':''}${r%5==4&&r<R-1?'b5':''}"></td>`).join('')+'</tr>';t.innerHTML=h;
function paint(){$$('td',t).forEach(td=>{const v=st[td.dataset.k];td.classList.toggle('f',v==='f');td.classList.toggle('x',v==='x')});save('ng',st);
 let ok=true;for(let r=0;r<R;r++)for(let c=0;c<C;c++)if((st[r+','+c]==='f')!==(S[r][c]==='1'))ok=false;
 if(ok){msg('ng',`Solved! It's ${N.picture}.`,'win');won('ng')}}
t.onclick=ev=>{const td=ev.target.closest('td');if(!td||giv[td.dataset.k])return;const k=td.dataset.k;st[k]=st[k]===mode?undefined:mode;if(!st[k])delete st[k];msg('ng','');paint()};
$$('#ng .mode2 button').forEach(b=>b.onclick=()=>{mode=b.dataset.m;$$('#ng .mode2 button').forEach(x=>x.classList.toggle('on',x===b))});
$('#ng .chk').onclick=()=>{let n=0;for(const k in st){const [r,c]=k.split(',').map(Number);if((st[k]==='f')!==(S[r][c]==='1')){n++}}msg('ng',n?`${n} square${n>1?'s':''} wrong.`:'No mistakes so far.',n?'bad':'')};
twice($('#ng .rv'),()=>{st={};for(let r=0;r<R;r++)for(let c=0;c<C;c++)if(S[r][c]==='1')st[r+','+c]='f';paint()});
twice($('#ng .clr'),()=>{st=Object.assign({},giv);paint();msg('ng','')});paint()})();

/* futoshiki */
if(G.futoshiki)(()=>{const F=G.futoshiki,n=F.n,S=F.solution,b=$('#ft .ft');let st=load('ft',{}),cur=null;
const giv={};F.givens.forEach(([r,c,v])=>giv[r+','+c]=String(v));
const sym={};F.less.forEach(([a,b2,c,d])=>{if(a===c)sym[`h${a},${Math.min(b2,d)}`]=b2<d?'<':'>';else sym[`v${Math.min(a,c)},${b2}`]=a<c?'∧':'∨'});
b.style.gridTemplateColumns=Array.from({length:2*n-1},(_,i)=>i%2?'22px':'1fr').join(' ');let h='';
for(let R=0;R<2*n-1;R++)for(let C=0;C<2*n-1;C++){const r=R>>1,c=C>>1;
 if(R%2==0&&C%2==0)h+=`<div class="c${giv[r+','+c]?' g':''}" data-k="${r},${c}"></div>`;
 else if(R%2==0)h+=`<div class="s">${sym['h'+r+','+c]||''}</div>`;else if(C%2==0)h+=`<div class="s" style="height:22px">${sym['v'+r+','+c]||''}</div>`;else h+='<div></div>'}
b.innerHTML=h;const val=k=>giv[k]||st[k]||'';
function paint(){$$('.c',b).forEach(d=>{d.textContent=val(d.dataset.k);d.classList.toggle('cur',d.dataset.k===cur);d.classList.remove('bad')});save('ft',st);
 let ok=true;for(let r=0;r<n;r++)for(let c=0;c<n;c++)if(val(r+','+c)!==S[r][c])ok=false;if(ok){msg('ft','Solved!','win');won('ft')}}
b.onclick=ev=>{const d=ev.target.closest('.c');if(!d||giv[d.dataset.k])return;cur=d.dataset.k;paint()};
$('#ft .pad').innerHTML=Array.from({length:n},(_,i)=>`<button data-k="${i+1}">${i+1}</button>`).join('')+'<button data-k="del">⌫</button>';
$('#ft .pad').style.gridTemplateColumns=`repeat(${n+1},1fr)`;
$('#ft .pad').onclick=ev=>{const bt=ev.target.closest('button');if(!bt||!cur)return;if(bt.dataset.k==='del')delete st[cur];else st[cur]=bt.dataset.k;msg('ft','');paint()};
$('#ft .chk').onclick=()=>{let m=0;for(const k in st){const [r,c]=k.split(',').map(Number);if(st[k]!==S[r][c]){b.querySelector(`[data-k="${k}"]`).classList.add('bad');m++}}msg('ft',m?`${m} wrong.`:'No mistakes so far.',m?'bad':'')};
twice($('#ft .rv'),()=>{for(let r=0;r<n;r++)for(let c=0;c<n;c++)st[r+','+c]=S[r][c];paint()});
twice($('#ft .clr'),()=>{st={};paint();msg('ft','')});paint()})();

/* queens */
if(G.queens)(()=>{const Qn=G.queens,n=Qn.n,R=Qn.regions,b=$('#qn .qb');let st=load('qn',{});
const COL=__COLORS__;b.style.gridTemplateColumns=`repeat(${n},1fr)`;let h='';
for(let r=0;r<n;r++)for(let c=0;c<n;c++){const g=R[r][c],bw=[r>0&&R[r-1][c]!==g?3:0,c<n-1&&R[r][c+1]!==g?3:0,r<n-1&&R[r+1][c]!==g?3:0,c>0&&R[r][c-1]!==g?3:0];
 h+=`<div data-k="${r},${c}" style="background:${COL[g]};border-width:${bw.map(x=>x/2+'px').join(' ')}"></div>`}b.innerHTML=h;
function paint(){const qs=Object.keys(st).filter(k=>st[k]==='q').map(k=>k.split(',').map(Number));
 $$('[data-k]',b).forEach(d=>{const v=st[d.dataset.k];d.textContent=v==='q'?'♛':v==='x'?'✕':'';d.className=v==='x'?'x':'';});
 const bad=new Set();qs.forEach((a,i)=>qs.forEach((q,j)=>{if(i<j&&(a[0]===q[0]||a[1]===q[1]||R[a[0]][a[1]]===R[q[0]][q[1]]||(Math.abs(a[0]-q[0])<=1&&Math.abs(a[1]-q[1])<=1))){bad.add(a+'');bad.add(q+'')}}));
 bad.forEach(k=>{const d=b.querySelector(`[data-k="${k}"]`);d&&d.classList.add('bad')});save('qn',st);
 if(qs.length===n&&!bad.size){msg('qn','Solved!','win');won('qn')}else msg('qn',bad.size?'Two crowns clash.':'',bad.size?'bad':'')}
b.onclick=ev=>{const d=ev.target.closest('[data-k]');if(!d)return;const k=d.dataset.k;st[k]=!st[k]?'x':st[k]==='x'?'q':undefined;if(!st[k])delete st[k];paint()};
twice($('#qn .rv'),()=>{st={};Qn.solution.forEach((c,r)=>st[r+','+c]='q');paint()});
twice($('#qn .clr'),()=>{st={};paint()});paint()})();
})();
""".replace("__COLORS__", json.dumps(REG))
JS_SAFE = JS.replace("</", "<\\/")


def _btns(*names):
    lab = {"chk": "Check", "rv": "Reveal", "clr": "Clear"}
    return "<div class='gbtns'>" + "".join(f"<button class='btn {n}'>{lab[n]}</button>" for n in names) + "</div>"


def sections(g: dict) -> dict:
    out = {}
    if g.get("quiz"):
        out["qz"] = ("<h2>News quiz</h2><p class='gsub'>Five questions on today's briefing. One tap per answer.</p>"
                     "<div class='qlist'></div><div class='gmsg'></div>" + _btns("clr"))
    if g.get("groups"):
        out["gr"] = ("<h2>Groups</h2><p class='gsub'>Find four groups of four. Pick four words, then Submit. Four mistakes allowed.</p>"
                     "<div class='gsolved'></div><div class='gtiles'></div><div class='dots'></div><div class='gmsg'></div>"
                     "<div class='gbtns'><button class='btn shuf'>Shuffle</button><button class='btn desel'>Deselect</button>"
                     "<button class='btn primary sub4'>Submit</button></div>" + _btns("rv", "clr"))
    if g.get("hive"):
        out["hv"] = ("<h2>Letter hive</h2><p class='gsub'>Make words of 4+ letters using the center letter at least once. "
                     "Letters can repeat. A word using all seven is a pangram.</p>"
                     "<div class='hsc gsub' style='margin-bottom:0'></div><div class='hbar'><i></i></div>"
                     "<div class='hword'></div><div class='hex'></div><div class='gmsg' style='text-align:center'></div>"
                     "<div class='gbtns'><button class='btn del'>Delete</button><button class='btn shuf'>Shuffle</button>"
                     "<button class='btn primary ent'>Enter</button></div><div class='hfound'></div>" + _btns("rv"))
    if g.get("cryptogram"):
        out["cg"] = ("<h2>Cryptogram</h2><p class='gsub'>Each letter stands for another. Tap a letter, then type what you think it is. "
                     f"{e(g['cryptogram']['source'])}.</p><div class='xwrap'><input class='kb' autocapitalize='characters' "
                     "autocomplete='off' autocorrect='off' spellcheck='false' aria-label='Letter'><div class='cg'></div></div>"
                     "<div class='gmsg'></div>" + _btns("chk", "rv", "clr"))
    if g.get("ladder"):
        L = g["ladder"]
        out["ld"] = (f"<h2>Word ladder</h2><p class='gsub'>Get from {L['start']} to {L['end']} by changing one letter at a time. "
                     "Every rung must be a real word.</p><div class='lad'></div><div class='gmsg'></div>" + _btns("rv", "clr"))
    if g.get("nonogram"):
        out["ng"] = ("<h2>Nonogram</h2><p class='gsub'>The numbers give the runs of filled squares in each row and column, in order. "
                     "Fill squares to reveal a picture.</p><div class='mode2'><button data-m='f' class='on'>■ Fill</button>"
                     "<button data-m='x'>✕ Mark empty</button></div><div class='ngw'><table class='ng'></table></div>"
                     "<div class='gmsg'></div>" + _btns("chk", "rv", "clr"))
    if g.get("futoshiki"):
        n = g["futoshiki"]["n"]
        out["ft"] = (f"<h2>Futoshiki</h2><p class='gsub'>Fill each row and column with 1–{n}. Signs between squares "
                     "show which number is bigger.</p><div class='ft'></div><div class='pad'></div><div class='gmsg'></div>"
                     + _btns("chk", "rv", "clr"))
    if g.get("queens"):
        n = g["queens"]["n"]
        out["qn"] = (f"<h2>Queens</h2><p class='gsub'>Place {n} crowns: one in each row, column and colored region. "
                     "No two crowns may touch, even diagonally. Tap once for ✕, twice for ♛.</p>"
                     "<div class='qb'></div><div class='gmsg'></div>" + _btns("rv", "clr"))
    return out


# ── EPUB ──────────────────────────────────────────────────────────────────
def _region_table(reg, label, extra=lambda r, c: ""):
    n = len(reg)
    rows = ""
    for r in range(n):
        rows += "<tr>"
        for c in range(n):
            g = reg[r][c]
            bw = [r == 0 or reg[r - 1][c] != g, c == n - 1 or reg[r][c + 1] != g,
                  r == n - 1 or reg[r + 1][c] != g, c == 0 or reg[r][c - 1] != g]
            rows += (f"<td style='border-width:{' '.join('3px' if x else '1px' for x in bw)}'>"
                     f"<span class='small'>{label(g)}</span>{extra(r, c)}</td>")
        rows += "</tr>"
    return f"<table class='g'>{rows}</table>"


def epub_pages(g: dict) -> tuple[list[tuple[str, str, str]], str]:
    """Puzzle pages plus an HTML chunk for the answers page."""
    back = "<p class='back'><a href='contents.xhtml'>↩ Back to contents</a> · <a href='g_answers.xhtml'>Answers</a></p>"
    pages, ans = [], ""
    if g.get("quiz"):
        Q = g["quiz"]["questions"]
        body = "<p class='meta'>Puzzles</p><h1>News quiz</h1>" + "".join(
            f"<p><b>{i}. {e(q['q'])}</b></p><p class='small'>" + "<br/>".join(f"{'ABCD'[j]}. {e(o)}" for j, o in enumerate(q["options"])) + "</p>"
            for i, q in enumerate(Q, 1))
        pages.append(("News quiz", "g_qz.xhtml", body + back))
        ans += "<h2>News quiz</h2>" + "".join(
            f"<p class='clue'>{i}. {'ABCD'[q['answer']]}: {e(q['options'][q['answer']])}"
            + (f" <span class='small'>({e(q['why'])})</span>" if q.get("why") else "") + "</p>" for i, q in enumerate(Q, 1))
    if g.get("groups"):
        ws = sorted(w for gr in g["groups"]["groups"] for w in gr["words"])
        rows = "".join("<tr>" + "".join(f"<td style='width:5.5em'>{w}</td>" for w in ws[i:i + 4]) + "</tr>" for i in range(0, 16, 4))
        pages.append(("Groups", "g_gr.xhtml", "<p class='meta'>Puzzles</p><h1>Groups</h1>"
                      "<p class='small'>Sort these 16 words into four groups of four.</p>"
                      f"<table class='g'>{rows}</table>{back}"))
        ans += "<h2>Groups</h2>" + "".join(f"<p class='clue'><b>{e(gr['name'])}:</b> {', '.join(gr['words'])}</p>"
                                           for gr in g["groups"]["groups"])
    if g.get("hive"):
        H = g["hive"]
        pages.append(("Letter hive", "g_hv.xhtml", "<p class='meta'>Puzzles</p><h1>Letter hive</h1>"
                      f"<p style='font-size:1.6em;text-align:center;letter-spacing:.3em'><b>[{H['center']}]</b> {' '.join(H['outer'])}</p>"
                      f"<p class='small'>Make words of 4+ letters that use {H['center']} at least once; letters can repeat. "
                      f"There are {len(H['answers'])} words, including {len(H['pangrams'])} that use all seven letters.</p>{back}"))
        ans += f"<h2>Letter hive</h2><p class='small'>{', '.join(H['answers'])}<br/>Pangrams: {', '.join(H['pangrams'])}</p>"
    if g.get("cryptogram"):
        C = g["cryptogram"]
        hints = ", ".join(f"{k} = {v}" for k, v in C["hints"].items())
        pages.append(("Cryptogram", "g_cg.xhtml", "<p class='meta'>Puzzles</p><h1>Cryptogram</h1>"
                      "<p class='small'>Each letter stands for a different letter.</p>"
                      f"<p style='font-size:1.25em;letter-spacing:.15em;line-height:1.8'>{e(C['cipher'])}</p>"
                      f"<p class='small'>Hints: {e(hints)}</p>{back}"))
        ans += f"<h2>Cryptogram</h2><p>{e(C['plain'])}</p>"
    if g.get("ladder"):
        L = g["ladder"]
        rungs = "".join("<p style='text-align:center;letter-spacing:.4em'>_ _ _ _</p>" for _ in L["solution"][1:-1])
        pages.append(("Word ladder", "g_ld.xhtml", "<p class='meta'>Puzzles</p><h1>Word ladder</h1>"
                      "<p class='small'>Change one letter at a time; every step must be a real word.</p>"
                      f"<p style='text-align:center;font-size:1.4em'><b>{L['start']}</b></p>{rungs}"
                      f"<p style='text-align:center;font-size:1.4em'><b>{L['end']}</b></p>{back}"))
        ans += f"<h2>Word ladder</h2><p>{' → '.join(L['solution'])}</p>"
    if g.get("nonogram"):
        N = g["nonogram"]
        giv = {(r, c): v for r, c, v in N["givens"]}
        head = "<tr><td class='e'></td>" + "".join(f"<td class='e small' style='vertical-align:bottom'>{'<br/>'.join(map(str, cl))}</td>" for cl in N["cols"]) + "</tr>"

        def grid(filled):
            body = ""
            for r in range(len(N["rows"])):
                body += f"<tr><td class='e small' style='text-align:right;white-space:nowrap'>{' '.join(map(str, N['rows'][r]))}&#160;</td>"
                for c in range(len(N["cols"])):
                    v = N["solution"][r][c] == "1" if filled else giv.get((r, c))
                    body += "<td class='b'></td>" if v == 1 or v is True else (
                        "<td>·</td>" if v == 0 and not filled else "<td></td>")
                body += "</tr>"
            return f"<table class='g'>{head}{body}</table>"
        pages.append(("Nonogram", "g_ng.xhtml", "<p class='meta'>Puzzles</p><h1>Nonogram</h1>"
                      "<p class='small'>Numbers are the runs of filled squares in each row and column, in order.</p>"
                      f"{grid(False)}{back}"))
        ans += f"<h2>Nonogram</h2><p>It's {e(N['picture'])}.</p>{grid(True)}"
    if g.get("futoshiki"):
        F = g["futoshiki"]
        n = F["n"]
        giv = {(r, c): v for r, c, v in F["givens"]}
        sym = {}
        for a, b, c, d in F["less"]:
            if a == c:
                sym[("h", a, min(b, d))] = "&lt;" if b < d else "&gt;"
            else:
                sym[("v", min(a, c), b)] = "∧" if a < c else "∨"

        def grid(filled):
            rows = ""
            for R in range(2 * n - 1):
                rows += "<tr>"
                for C in range(2 * n - 1):
                    r, c = R // 2, C // 2
                    if R % 2 == 0 and C % 2 == 0:
                        v = F["solution"][r][c] if filled else giv.get((r, c), "")
                        rows += f"<td><b>{v}</b></td>"
                    elif R % 2 == 0:
                        rows += f"<td class='e'>{sym.get(('h', r, c), '')}</td>"
                    elif C % 2 == 0:
                        rows += f"<td class='e'>{sym.get(('v', r, c), '')}</td>"
                    else:
                        rows += "<td class='e'></td>"
                rows += "</tr>"
            return f"<table class='g s'>{rows}</table>"
        pages.append(("Futoshiki", "g_ft.xhtml", "<p class='meta'>Puzzles</p><h1>Futoshiki</h1>"
                      f"<p class='small'>Fill each row and column with 1–{n}; the signs show which neighbor is bigger.</p>"
                      f"{grid(False)}{back}"))
        ans += f"<h2>Futoshiki</h2>{grid(True)}"
    if g.get("queens"):
        Q = g["queens"]
        lab = lambda k: "ABCDEFGHIJ"[k]
        pages.append(("Queens", "g_qn.xhtml", "<p class='meta'>Puzzles</p><h1>Queens</h1>"
                      f"<p class='small'>Place {Q['n']} crowns: one per row, column and lettered region; no two may touch, even diagonally.</p>"
                      f"{_region_table(Q['regions'], lab)}{back}"))
        ans += "<h2>Queens</h2>" + _region_table(Q["regions"], lab, lambda r, c: " ♛" if Q["solution"][r] == c else "")
    return pages, ans
