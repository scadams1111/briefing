"""Offline support: a service worker that saves the day's briefing on your phone.

- Pages (Today, Saved, Search, Archive, the reader...) load from the network when
  there's signal, and from the saved copy when there isn't.
- Fonts, icons and the reader's libraries are saved once and reused.
- Story photos and each story's reader text (fetched through your relay) are saved
  ahead of time whenever you open Today with a connection, so Read works offline too.
"""
from __future__ import annotations

import json
import time

from . import web as w

SW = r"""
const VERSION = 'briefing-%(version)s';
const PAGES = VERSION + '-pages', ASSETS = 'briefing-assets-v1', ARTICLES = 'briefing-articles-v1';
const CORE = %(core)s;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(PAGES).then(c => Promise.allSettled(CORE.map(u => c.add(new Request(u, {cache: 'reload'}))))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('briefing-') && k.endsWith('-pages') && k !== PAGES)
    .map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

const isAsset = u => /fonts\.(googleapis|gstatic)\.com|cdn\.jsdelivr\.net|google\.com\/s2\/favicons/.test(u.href) ||
  /\.(png|jpe?g|webp|gif|svg|woff2?|css|webmanifest)$/i.test(u.pathname);

async function networkFirst(req, cacheName, timeoutMs = 4000) {
  const cache = await caches.open(cacheName);
  try {
    const res = await Promise.race([fetch(req), new Promise((_, rej) => setTimeout(() => rej('timeout'), timeoutMs))]);
    if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone());
    return res;
  } catch (_) {
    return (await cache.match(req)) || (await cache.match(req, {ignoreSearch: true})) ||
      new Response("<!doctype html><meta name=viewport content='width=device-width'><body style='background:#0B1220;color:#EAF0FA;font:16px system-ui;padding:40px'>Offline, and this page wasn't saved yet. Open Today once with signal to save the day's briefing.</body>",
        {status: 503, headers: {'Content-Type': 'text/html'}});
  }
}
async function cacheFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  if (hit) return hit;
  try {
    const res = await fetch(req);
    if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone());
    return res;
  } catch (_) { return Response.error(); }
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || req.headers.get('range')) return;          // audio streams pass straight through
  const u = new URL(req.url);
  if (u.hostname.endsWith('workers.dev') && u.pathname === '/audio') return;
  if (u.hostname.endsWith('workers.dev')) { e.respondWith(networkFirst(req, ARTICLES, 8000)); return; }   // reader text
  if (u.hostname === 'api.github.com' || u.hostname.endsWith('archive.org') || u.hostname.includes('dictionaryapi')) return;
  if (u.origin === location.origin && (req.mode === 'navigate' || /\.(html|json|xml)$/.test(u.pathname) || u.pathname.endsWith('/'))) {
    e.respondWith(networkFirst(req, PAGES)); return;
  }
  if (isAsset(u) || req.destination === 'image' || req.destination === 'font' || req.destination === 'style' || req.destination === 'script') {
    e.respondWith(cacheFirst(req, ASSETS)); return;
  }
});

// Today page asks us to save its photos and each story's reader text ahead of time.
self.addEventListener('message', e => {
  const d = e.data || {};
  if (d.type !== 'warm') return;
  e.waitUntil((async () => {
    const assets = await caches.open(ASSETS), arts = await caches.open(ARTICLES);
    for (const u of d.assets || []) { try { if (!(await assets.match(u))) { const r = await fetch(u, {mode: 'no-cors'}); await assets.put(u, r); } } catch (_) {} }
    for (const u of d.articles || []) { try { if (!(await arts.match(u))) { const r = await fetch(u); if (r.ok) await arts.put(u, r); } } catch (_) {} }
    // keep the article cache from growing forever: newest ~80 entries
    const keys = await arts.keys(); for (const k of keys.slice(0, Math.max(0, keys.length - 80))) await arts.delete(k);
  })());
});
"""

REGISTER = r"""
(()=>{if(!('serviceWorker' in navigator))return;const root=document.body.dataset.root||'';
navigator.serviceWorker.register(root+'sw.js').then(reg=>{
 const warm=()=>{const sw=navigator.serviceWorker.controller||reg.active;if(!sw||!navigator.onLine)return;
  const relay=document.body.dataset.relay||'';
  const assets=[...document.querySelectorAll('img[src]')].map(i=>i.src).filter(s=>/^https?:/.test(s));
  const articles=relay?[...document.querySelectorAll('.slide[data-url]')].map(s=>s.dataset.url).filter(Boolean)
    .map(u=>relay.replace(/\/$/,'')+'/?url='+encodeURIComponent(u)):[];
  const pages=['','saved.html','games.html','search.html','archive/','highlights.html','read.html','search-index.json'].map(p=>new URL(root+p,location.href).href);
  sw.postMessage({type:'warm',assets:[...assets,...pages],articles})};
 if(document.querySelector('.deck'))(navigator.serviceWorker.ready.then(()=>setTimeout(warm,2500)));
}).catch(()=>{});
const badge=()=>{let b=document.querySelector('.offline');if(navigator.onLine){if(b)b.remove();return}
 if(!b){b=document.createElement('div');b.className='offline';b.textContent='Offline · saved copy';document.body.appendChild(b)}};
addEventListener('online',badge);addEventListener('offline',badge);badge();})();
"""

OFFLINE_CSS = """
.offline{position:fixed;bottom:calc(84px + env(safe-area-inset-bottom));left:50%;white-space:nowrap;transform:translateX(-50%);z-index:70;
  background:var(--tile);border:1px solid var(--line);color:var(--detail);font:600 12.5px var(--sans);padding:7px 12px;border-radius:999px;
  box-shadow:0 6px 18px rgba(0,0,0,.35)}
"""


def write_sw() -> None:
    core = ["./", "index.html", "saved.html", "games.html", "search.html", "archive/", "highlights.html", "read.html", "settings.html",
            "manifest.webmanifest", "apple-touch-icon.png", "icon-192.png", "icon-512.png", "search-index.json"]
    (w.DOCS / "sw.js").write_text(SW % {"version": time.strftime("%Y%m%d%H%M"), "core": json.dumps(core)})
