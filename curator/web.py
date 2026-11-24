"""The web reading experience: a clean, Matter-style briefing page."""
from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

DOCS = Path("docs")
e = html.escape

CSS = r"""
:root{
  --bg:#F7F5F0; --card:#FFFFFF; --ink:#16140F; --muted:#77736A; --faint:#A8A399;
  --line:#E9E5DC; --chip:#EFEBE3; --accent:#E8572A; --accent-soft:#FCE9E1;
  --shadow:0 1px 2px rgba(22,20,15,.04),0 8px 24px rgba(22,20,15,.06);
  --serif:"New York",ui-serif,"Iowan Old Style","Charter","Georgia",serif;
  --sans:-apple-system,BlinkMacSystemFont,"SF Pro Text","Inter","Segoe UI",system-ui,sans-serif;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0F0E0C; --card:#1A1916; --ink:#F1EEE7; --muted:#9C978C; --faint:#6E6A62;
  --line:#2A2824; --chip:#24221E; --accent:#FF7A4D; --accent-soft:#3A2219;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.25);
}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
.wrap{max-width:680px;margin:0 auto;padding:0 18px 80px}

/* top bar */
.bar{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 82%,transparent);
  backdrop-filter:saturate(1.6) blur(16px);-webkit-backdrop-filter:saturate(1.6) blur(16px);border-bottom:1px solid var(--line)}
.bar .wrap{display:flex;align-items:center;justify-content:space-between;height:54px;padding-bottom:0}
.brand{font-family:var(--serif);font-weight:700;font-size:20px;letter-spacing:-.01em}
.brand span{color:var(--accent)}
.tabs{display:flex;gap:4px;background:var(--chip);padding:3px;border-radius:999px}
.tabs a{font-size:13px;font-weight:600;padding:6px 12px;border-radius:999px;color:var(--muted)}
.tabs a.on{background:var(--card);color:var(--ink);box-shadow:0 1px 3px rgba(0,0,0,.08)}

/* hero */
.hero{padding:30px 0 6px}
.kicker{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.hero h1{font-family:var(--serif);font-size:38px;line-height:1.08;letter-spacing:-.02em;margin:6px 0 8px;font-weight:700}
.hero p{margin:0;color:var(--muted);font-size:15px}

/* topic chips */
.chips{display:flex;gap:8px;overflow-x:auto;padding:18px 0 6px;margin:0 -18px;padding-left:18px;padding-right:18px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;border:1px solid var(--line);background:var(--card);color:var(--muted);font:600 13px var(--sans);
  padding:7px 13px;border-radius:999px;cursor:pointer;transition:all .15s}
.chip.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}

/* cards */
.card{background:var(--card);border-radius:20px;box-shadow:var(--shadow);margin:18px 0;overflow:hidden;
  animation:rise .5s both}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.thumb{display:block;aspect-ratio:16/9;background:var(--chip);overflow:hidden}
.thumb img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .6s}
.card:hover .thumb img{transform:scale(1.02)}
.body{padding:18px 20px 20px}
.meta{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted);font-weight:500}
.meta img{width:18px;height:18px;border-radius:5px;background:var(--chip)}
.meta .dot{color:var(--faint)}
.topic{margin-left:auto;font-size:11px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);
  background:var(--accent-soft);padding:3px 8px;border-radius:6px;white-space:nowrap}
.card h2{font-family:var(--serif);font-size:23px;line-height:1.22;letter-spacing:-.01em;margin:10px 0 0;font-weight:700}
.card.lead h2{font-size:28px}
.room{font-family:var(--serif);font-style:italic;color:var(--muted);font-size:16.5px;line-height:1.5;
  margin:12px 0 0;padding-left:14px;border-left:3px solid var(--accent)}

/* key points */
.points{list-style:none;margin:16px 0 0;padding:0;border-top:1px solid var(--line)}
.points li{border-bottom:1px solid var(--line)}
.points details>summary{list-style:none;display:flex;gap:12px;align-items:flex-start;padding:13px 0;cursor:pointer;
  font-size:15.5px;line-height:1.45;font-weight:500}
.points details>summary::-webkit-details-marker{display:none}
.num{flex:none;width:24px;height:24px;border-radius:50%;background:var(--chip);color:var(--ink);font:700 12px/24px var(--sans);text-align:center;margin-top:1px;transition:all .2s}
.chev{flex:none;margin-left:auto;margin-top:3px;width:18px;height:18px;color:var(--faint);transition:transform .25s}
details[open] .num{background:var(--accent);color:#fff}
details[open] .chev{transform:rotate(180deg)}
.detail{padding:0 0 16px 36px;font-family:var(--serif);font-size:16.5px;line-height:1.65;color:var(--ink);opacity:.92;
  animation:fade .3s ease}
@keyframes fade{from{opacity:0;transform:translateY(-4px)}to{opacity:.92;transform:none}}

.foot{display:flex;align-items:center;gap:10px;margin-top:16px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;gap:6px;font-weight:600;font-size:14px;padding:9px 15px;border-radius:999px;
  background:var(--ink);color:var(--bg)}
.why{font-size:13.5px;line-height:1.5;color:var(--muted);margin-top:14px;padding:10px 12px;background:var(--chip);border-radius:12px}
.why b{color:var(--ink);font-weight:600}

.section{font-size:12px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--faint);margin:34px 0 -4px}
.empty{color:var(--muted);text-align:center;padding:60px 0}
.archive a{display:flex;justify-content:space-between;padding:16px 4px;border-bottom:1px solid var(--line);font-family:var(--serif);font-size:19px}
.archive a span{color:var(--faint);font-family:var(--sans);font-size:14px}
footer{text-align:center;color:var(--faint);font-size:12px;margin-top:40px}
footer a{text-decoration:underline}
.hide{display:none}
"""

CHEV = "<svg class='chev' viewBox='0 0 20 20' fill='none' stroke='currentColor' stroke-width='2'><path d='M5 7.5l5 5 5-5'/></svg>"
ARROW = "<svg width='14' height='14' viewBox='0 0 20 20' fill='none' stroke='currentColor' stroke-width='2.2'><path d='M7 13l6-6M8 7h5v5'/></svg>"

JS = """
document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click',()=>{
  document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on',x===c));
  const t=c.dataset.t;
  document.querySelectorAll('.card').forEach(k=>k.classList.toggle('hide',t!=='all'&&k.dataset.t!==t));
}));
"""


def _domain(url: str) -> str:
    from urllib.parse import urlsplit
    return urlsplit(url).netloc.removeprefix("www.")


def card(it: dict, lead: bool = False, delay: int = 0) -> str:
    img = ""
    if it.get("image"):
        img = (f"<a class='thumb' href='{e(it['url'])}'><img src='{e(it['image'])}' alt='' loading='lazy' "
               f"referrerpolicy='no-referrer' onerror=\"this.parentNode.remove()\"></a>")
    fav = f"https://www.google.com/s2/favicons?domain={e(_domain(it['url']))}&sz=64"
    pts = "".join(
        f"<li><details><summary><span class='num'>{n}</span><span>{e(b['point'])}</span>{CHEV}</summary>"
        f"<div class='detail'>{e(b.get('detail', ''))}</div></details></li>"
        for n, b in enumerate(it["bullets"], 1) if b.get("detail")) or "".join(
        f"<li><details><summary><span class='num'>{n}</span><span>{e(b['point'])}</span></summary></details></li>"
        for n, b in enumerate(it["bullets"], 1))
    room = f"<p class='room'>{e(it['room_line'])}</p>" if it.get("room_line") else ""
    why = f"<div class='why'><b>Why for you</b> · {e(it['why_for_you'])}</div>" if it.get("why_for_you") else ""
    return (f"<article class='card{' lead' if lead else ''}' data-t='{e(it.get('topic', ''))}' style='animation-delay:{delay}ms'>{img}"
            f"<div class='body'><div class='meta'><img src='{fav}' alt='' referrerpolicy='no-referrer'>"
            f"<span>{e(it['source'])}</span><span class='dot'>·</span><span>{it['minutes']} min</span>"
            f"<span class='topic'>{e(it.get('topic_name', ''))}</span></div>"
            f"<h2><a href='{e(it['url'])}'>{e(it['headline'])}</a></h2>{room}"
            f"<ol class='points'>{pts}</ol>"
            f"{why}<div class='foot'><a class='btn' href='{e(it['url'])}'>Read original {ARROW}</a></div></div></article>")


def shell(title: str, active: str, body: str, root: str = "", script: bool = False) -> str:
    tabs = "".join(f"<a href='{root}{href}' class='{'on' if active == k else ''}'>{label}</a>"
                   for k, label, href in (("today", "Today", "./"), ("saved", "Saved", "saved.html"),
                                          ("archive", "Archive", "archive/")))
    return (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            f"<meta name='theme-color' content='#F7F5F0' media='(prefers-color-scheme: light)'>"
            f"<meta name='theme-color' content='#0F0E0C' media='(prefers-color-scheme: dark)'>"
            f"<meta name='apple-mobile-web-app-capable' content='yes'>"
            f"<title>{e(title)}</title><style>{CSS}</style></head><body>"
            f"<header class='bar'><div class='wrap'><a class='brand' href='{root}./'>Briefing<span>.</span></a>"
            f"<nav class='tabs'>{tabs}</nav></div></header><main class='wrap'>{body}</main>"
            + (f"<script>{JS}</script>" if script else "") + "</body></html>")


def today_body(date: str, picks: list[dict], root: str = "") -> str:
    d = dt.date.fromisoformat(date)
    mins = sum(i.get("minutes", 0) for i in picks)
    topics = []
    for i in picks:
        if (i.get("topic"), i.get("topic_name")) not in topics:
            topics.append((i.get("topic"), i.get("topic_name")))
    chips = "<button class='chip on' data-t='all'>All</button>" + "".join(
        f"<button class='chip' data-t='{e(t)}'>{e(n)}</button>" for t, n in topics)
    body = (f"<section class='hero'><div class='kicker'>{d.strftime('%A')}</div>"
            f"<h1>{d.strftime('%B')} {d.day}</h1>"
            f"<p>{len(picks)} stories worth your time · about {mins} min of reading</p></section>"
            f"<div class='chips'>{chips}</div>")
    body += "".join(card(i, lead=(n == 0), delay=min(n, 6) * 60) for n, i in enumerate(picks)) or \
        "<p class='empty'>Nothing yet today.</p>"
    body += f"<footer>Curated every morning · <a href='{root}epub/latest.epub'>Download as EPUB</a></footer>"
    return body


def write_all(cfg: dict, date: str, picks: list[dict], saved: list[dict], archive_dates: list[str]) -> None:
    (DOCS / "archive").mkdir(parents=True, exist_ok=True)
    nice = dt.date.fromisoformat(date).strftime("%A, %B %-d")
    (DOCS / "index.html").write_text(shell(f"Briefing — {nice}", "today", today_body(date, picks), script=True))
    (DOCS / "archive" / f"{date}.html").write_text(
        shell(f"Briefing — {nice}", "archive", today_body(date, picks, "../"), root="../", script=True))
    rows = "".join(
        f"<a href='{d}.html'>{dt.date.fromisoformat(d).strftime('%A, %B %-d')}<span>›</span></a>"
        for d in sorted(archive_dates, reverse=True))
    (DOCS / "archive" / "index.html").write_text(shell(
        "Archive", "archive", f"<section class='hero'><div class='kicker'>Past briefings</div><h1>Archive</h1></section>"
        f"<div class='archive'>{rows}</div>", root="../"))
    write_saved(saved)


def write_saved(saved: list[dict]) -> None:
    DOCS.mkdir(exist_ok=True)
    body = ("<section class='hero'><div class='kicker'>Your queue</div><h1>Saved</h1>"
            f"<p>{len(saved)} article{'s' if len(saved) != 1 else ''} saved for later</p></section>")
    body += "".join(card(i, delay=min(n, 6) * 60) for n, i in enumerate(saved[:50])) or \
        "<p class='empty'>Nothing saved yet. Share a link to your Save shortcut and it'll appear here.</p>"
    (DOCS / "saved.html").write_text(shell("Saved — Briefing", "saved", body))
