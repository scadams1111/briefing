"""Audio briefing: the AI writes a spoken script of today's briefing, a neural
voice reads it, and the MP3 is published as a GitHub Release asset (so audio
never bloats the repo). docs/podcast.xml lists recent episodes for any podcast app.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import html
import json
import logging
import os
from email.utils import format_datetime
from pathlib import Path

from .llm import LLM

log = logging.getLogger("curator")
DATA, DOCS, BUILD = Path("data") / "audio", Path("docs"), Path("build") / "audio"
e = html.escape

SCRIPT_PROMPT = """Write the script for a spoken morning news briefing of about {minutes} minutes
({words} words) for one listener, read by a single host.

Style: warm, smart and conversational, like a great public-radio host. Plain spoken English:
no markdown, headings, bullet points, URLs, emoji or stage directions. Spell out abbreviations
the first time if they'd be unclear when heard. Use smooth transitions. Never mention the
listener's job, employer or personal life. Use ONLY the facts provided; attribute opinions.

Structure:
1. A short greeting with the date ({date}) and a one-sentence preview of the top stories.
2. Each main story in order: a hook, the key points woven into natural speech, and why it matters.
3. If there is a deep dive, a "today's deep dive" segment explaining the topic simply.
4. If there are New York Times picks, a quick "also worth a look in the Times" round-up, one sentence each.
5. A brief sign-off.

Return JSON: {{"script": "the full script as plain text, paragraphs separated by blank lines"}}

TODAY'S MATERIAL (JSON):
{material}
"""


def _material(items: list[dict], smart: dict, subs: list[dict]) -> str:
    m = {"stories": [{"headline": i["headline"], "source": i["source"], "takeaway": i.get("room_line", ""),
                      "points": [{"point": b["point"], "detail": " ".join(b.get("detail", "").split()[:90])}
                                 for b in i["bullets"]]} for i in items]}
    d = (smart or {}).get("deep")
    if d:
        m["deep_dive"] = {"topic": d["topic"], "why": d.get("why", ""),
                          "points": [{"point": p["point"], "detail": p.get("detail", "")} for p in d["points"]]}
    nyt = [s for s in subs or [] if s.get("section") == "nyt" or "nytimes.com" in s.get("url", "")]
    if nyt:
        m["nyt"] = [{"headline": s["headline"], "takeaway": s.get("takeaway", "")} for s in nyt]
    return json.dumps(m, ensure_ascii=False)


def _fallback_script(date_nice: str, items: list[dict]) -> str:
    parts = [f"Good morning. Here's your briefing for {date_nice}."]
    for k, i in enumerate(items, 1):
        parts.append(f"Story {k}, from {i['source']}: {i['headline']}.")
        parts += [b["point"] for b in i["bullets"]]
    parts.append("That's the briefing. Have a good day.")
    return "\n\n".join(parts)


async def _speak(text: str, out: Path, voice: str, rate: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def make(cfg: dict, date: str, items: list[dict], smart: dict, subs: list[dict], llm: LLM) -> dict | None:
    ac = cfg.get("audio") or {}
    if not ac.get("enabled", True) or not items:
        return None
    minutes = int(ac.get("minutes", 9))
    nice = dt.date.fromisoformat(date).strftime("%A, %B %-d")
    script = None
    if llm.available:
        res = llm.json(SCRIPT_PROMPT.format(minutes=minutes, words=minutes * 150, date=nice,
                                            material=_material(items, smart, subs))) or {}
        script = (res.get("script") or "").strip() or None
    script = script or _fallback_script(nice, items)
    BUILD.mkdir(parents=True, exist_ok=True)
    out = BUILD / f"briefing-{date}.mp3"
    try:
        asyncio.run(_speak(script, out, ac.get("voice", "en-US-AndrewMultilingualNeural"), ac.get("rate", "+4%")))
    except Exception as ex:
        log.warning("main voice failed (%s); trying the backup voice", ex)
        try:
            from gtts import gTTS
            gTTS(script, lang="en", tld="us").save(str(out))
        except Exception as ex2:
            log.warning("backup voice failed too: %s", ex2)
            return None
    try:
        from mutagen.mp3 import MP3
        seconds = int(MP3(str(out)).info.length)
    except Exception:
        seconds = len(script.split()) * 60 // 150
    repo = os.environ.get("GITHUB_REPOSITORY", "scadams1111/briefing")
    queue_upload(f"audio-{date}", out)
    meta = {"date": date, "title": f"Briefing — {nice}", "file": out.name, "bytes": out.stat().st_size,
            "seconds": seconds, "url": f"https://github.com/{repo}/releases/download/audio-{date}/{out.name}",
            "summary": "; ".join(i["headline"] for i in items[:5])}
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"{date}.json").write_text(json.dumps(meta, indent=1))
    (DATA / f"{date}.txt").write_text(script)
    log.info("audio briefing: %d min, %d KB", seconds // 60, meta["bytes"] // 1024)
    return meta


def load(date: str) -> dict | None:
    p = DATA / f"{date}.json"
    return json.loads(p.read_text()) if p.exists() else None


def podcast_feed(cfg: dict, site: str, keep: int = 14) -> None:
    eps = sorted((json.loads(p.read_text()) for p in DATA.glob("????-??-??.json")),
                 key=lambda m: m["date"], reverse=True)[:keep] if DATA.exists() else []
    for p in DATA.glob("????-??-??.*") if DATA.exists() else []:
        if p.stem not in {m["date"] for m in eps}:
            p.unlink()
    title = cfg.get("site_title", "The Daily Briefing")
    items = "".join(
        f"<item><title>{e(m['title'])}</title><description>{e(m.get('summary', ''))}</description>"
        f"<enclosure url='{e(m['url'])}' length='{m['bytes']}' type='audio/mpeg'/>"
        f"<guid isPermaLink='false'>briefing-audio-{m['date']}</guid>"
        f"<pubDate>{format_datetime(dt.datetime.fromisoformat(m['date'] + 'T12:00:00+00:00'))}</pubDate>"
        f"<itunes:duration>{m['seconds']}</itunes:duration><itunes:explicit>false</itunes:explicit></item>"
        for m in eps)
    DOCS.mkdir(exist_ok=True)
    (DOCS / "podcast.xml").write_text(
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<rss version='2.0' xmlns:itunes='http://www.itunes.com/dtds/podcast-1.0.dtd'><channel>"
        f"<title>{e(title)}</title><link>{e(site)}/</link><language>en-us</language>"
        "<description>A personal daily briefing, read aloud.</description>"
        "<itunes:author>Briefing</itunes:author><itunes:explicit>false</itunes:explicit>"
        f"<itunes:image href='{e(site)}/podcast-cover.jpg'/><itunes:category text='News'/>"
        f"{items}</channel></rss>")


# ── per-article audio ──────────────────────────────────────────────────
def queue_upload(tag: str, path: Path) -> None:
    """The workflow uploads every file listed here to the named GitHub release."""
    BUILD.mkdir(parents=True, exist_ok=True)
    with open(BUILD / "upload.txt", "a") as f:
        f.write(f"{tag}\t{path}\n")


def _article_script(it: dict, text: str, max_words: int) -> str:
    words = text.split()
    body = text if len(words) <= max_words else " ".join(words[:max_words]) + \
        " ... That's where this reading ends. The full article continues on the original site."
    return f"{it.get('headline') or it.get('title')}. From {it.get('source', '')}.\n\n{body}"


async def _speak_many(jobs: list[tuple[str, Path]], voice: str, rate: str, conc: int = 4) -> None:
    import edge_tts
    sem = asyncio.Semaphore(conc)

    async def one(text, out):
        async with sem:
            for attempt in range(2):
                try:
                    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))
                    return
                except Exception as ex:
                    log.warning("article audio failed (%s), attempt %d", ex, attempt + 1)
                    if out.exists():
                        out.unlink()
    await asyncio.gather(*(one(t, o) for t, o in jobs))


def make_articles(cfg: dict, items: list[dict], texts: dict, tag: str) -> int:
    """Give each item an 'audio' entry {url, seconds} by reading its full text aloud."""
    ac = cfg.get("audio") or {}
    if not ac.get("articles", True):
        return 0
    repo = os.environ.get("GITHUB_REPOSITORY", "scadams1111/briefing")
    BUILD.mkdir(parents=True, exist_ok=True)
    jobs, todo = [], []
    for it in items:
        text = texts.get(it["id"], "")
        if len(text.split()) < 150:
            continue
        out = BUILD / f"art-{it['id']}.mp3"
        jobs.append((_article_script(it, text, int(ac.get("article_max_words", 4500))), out))
        todo.append((it, out))
    if not jobs:
        return 0
    try:
        asyncio.run(_speak_many(jobs, ac.get("voice", "en-US-AndrewMultilingualNeural"), ac.get("rate", "+4%")))
    except Exception as ex:
        log.warning("article audio failed: %s", ex)
        return 0
    n = 0
    for it, out in todo:
        if not out.exists() or out.stat().st_size < 2000:
            continue
        try:
            from mutagen.mp3 import MP3
            secs = int(MP3(str(out)).info.length)
        except Exception:
            secs = 0
        it["audio"] = {"url": f"https://github.com/{repo}/releases/download/{tag}/{out.name}", "seconds": secs}
        queue_upload(tag, out)
        n += 1
    log.info("article audio: %d of %d articles", n, len(items))
    return n
