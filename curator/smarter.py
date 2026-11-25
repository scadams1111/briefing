"""'Get smarter': a daily deep dive on one topic (rotating across fields) plus a
couple of evergreen explainers from publications that age well.

- The deep-dive primer is written only from the topic's Wikipedia article
  (CC BY-SA, credited on the page), so its facts are grounded.
- Further reading comes from a growing library of explainers collected from
  evergreen feeds every day (data/library.json).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import random
import re
import time
from pathlib import Path
from urllib.parse import quote

from .extract import fetch_article, is_english
from .llm import LLM
from .sources import Candidate, _parse_feed, get, normalize_url, strip_html
from .summarize import summarize

log = logging.getLogger("curator")
DATA = Path("data")
LIB = DATA / "library.json"
WIKI = "https://en.wikipedia.org"

TOPIC_PROMPT = """Pick today's "get smarter" deep-dive topic for a curious, well-educated reader.

Field: {field}
Topics used recently (don't repeat or pick near-duplicates): {recent}

Choose ONE specific, concrete topic in this field that a smart non-specialist would genuinely be
smarter for understanding: a big idea, mechanism, phenomenon, historical turning point, or concept
that explains a lot about the world. It should be evergreen (not tied to this week's news) and have
a solid English Wikipedia article. Prefer things with surprising depth over trivia.

Return JSON: {{"topic": "short name", "wikipedia_title": "exact English Wikipedia article title",
"hook": "one sentence on why it's worth knowing, max 25 words"}}
"""

PRIMER_PROMPT = """Write a primer that makes a smart non-specialist genuinely understand this topic.
Use ONLY facts from the source text below (Wikipedia). Plain language; define jargon.
Never mention the reader. Write in English.

Topic: {topic}

SOURCE TEXT:
{text}

Return JSON:
{{"headline": "engaging, specific title for the primer, max 12 words",
  "why": "two sentences on why this matters and where it shows up in the world",
  "points": [{{"point": "a key idea, max 22 words", "detail": "80-140 words explaining it with specifics from the text"}}]
}}
Exactly 5 points, building from basics to deeper insight.
"""

READING_PROMPT = """Deep-dive topic: {topic}

Below are candidate articles from high-quality publications. Pick up to 4 that would most deepen
someone's understanding of THIS topic (directly about it, or closely related and illuminating).
Skip anything only loosely related. It's fine to pick none.

Return JSON: {{"ids": [<int>, ...]}}

CANDIDATES:
{items}
"""

EVERGREEN_PROMPT = """Score each article 0-10 for how much it would make a curious, well-educated reader
smarter in a lasting way: explains a mechanism, big idea or history clearly; durable rather than
newsy; excellent writing. Penalize news, listicles, promos, personal-diary posts, and thin pieces.

Return JSON: {{"scores": [{{"id": <int>, "score": <number>}}]}}

CANDIDATES:
{items}
"""


# ── library of evergreen articles ─────────────────────────────────────
def load_library() -> list[dict]:
    return json.loads(LIB.read_text()) if LIB.exists() else []


def grow_library(cfg: dict, lib: list[dict]) -> tuple[list[dict], dict]:
    """Add new items from evergreen feeds (any age) to the library."""
    sm = cfg.get("smarter") or {}
    have = {normalize_url(x["url"]) for x in lib}
    health = {}
    for f in sm.get("evergreen_feeds") or []:
        url, name = (f, None) if isinstance(f, str) else (f["url"], f.get("name"))
        try:
            items = _parse_feed(url, {"id": "smarter"}, 1.0, name)
            health[url] = f"ok ({len(items)})"
        except Exception as ex:
            health[url] = f"error: {type(ex).__name__}"
            continue
        for c in items:
            key = normalize_url(c.url)
            if key in have or not c.title:
                continue
            have.add(key)
            lib.append({"url": c.url, "title": c.title, "source": c.source,
                        "summary": c.summary[:500], "published": c.published,
                        "added": time.time(), "shown": None})
    lib.sort(key=lambda x: x.get("added", 0), reverse=True)
    return lib[: int(sm.get("library_size", 2000))], health


def _items_list(items: list[dict]) -> str:
    return "\n".join(f"[{i}] ({x['source']}) {x['title']}\n    {' '.join(x.get('summary', '').split()[:45])}"
                     for i, x in enumerate(items))


def _tokens(s: str) -> set[str]:
    stop = {"the", "and", "for", "with", "that", "this", "from", "what", "how", "why", "are", "was", "about"}
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 3 and w not in stop}


# ── Wikipedia ──────────────────────────────────────────────────────────
def wiki_article(title: str) -> dict | None:
    """Return {title, url, text, image} for a Wikipedia article (following search if needed)."""
    def query(t):
        r = get(f"{WIKI}/w/api.php", params={
            "action": "query", "format": "json", "redirects": 1, "prop": "extracts|pageimages|info",
            "explaintext": 1, "exsectionformat": "plain", "inprop": "url", "pithumbsize": 1000, "titles": t}).json()
        pages = list((r.get("query") or {}).get("pages", {}).values())
        p = pages[0] if pages else {}
        if not p or "missing" in p or not p.get("extract"):
            return None
        return {"title": p["title"], "url": p.get("fullurl") or f"{WIKI}/wiki/{quote(p['title'])}",
                "text": p["extract"], "image": (p.get("thumbnail") or {}).get("source", "")}
    try:
        art = query(title)
        if art:
            return art
        hits = get(f"{WIKI}/w/api.php", params={"action": "opensearch", "format": "json",
                                                 "limit": 1, "search": title}).json()
        return query(hits[1][0]) if len(hits) > 1 and hits[1] else None
    except Exception as ex:
        log.warning("wikipedia lookup failed for %s: %s", title, ex)
        return None


def _clean_wiki(text: str) -> str:
    # drop trailing reference-ish sections
    text = re.split(r"\n(?:See also|References|Notes|Further reading|External links|Bibliography)\n", text)[0]
    return text[:14000]


# ── build today's section ─────────────────────────────────────────────
def build(cfg: dict, st: dict, llm: LLM, who: str, date: str) -> dict:
    sm = cfg.get("smarter") or {}
    if not sm.get("enabled", True):
        return {}
    lib, health = grow_library(cfg, load_library())
    out: dict = {"date": date, "deep": None, "picks": []}
    recent = st.setdefault("smarter_topics", [])[-60:]
    fields = sm.get("fields") or ["Science"]
    day_no = dt.date.fromisoformat(date).toordinal()
    field = fields[day_no % len(fields)]

    # 1) deep dive
    if llm.available:
        pick = llm.json(TOPIC_PROMPT.format(field=field, recent=", ".join(recent) or "none")) or {}
        art = wiki_article(pick.get("wikipedia_title") or pick.get("topic") or "") if pick else None
        if art and len(art["text"].split()) > 400:
            primer = llm.json(PRIMER_PROMPT.format(topic=art["title"], text=_clean_wiki(art["text"]))) or {}
            points = [p for p in primer.get("points", []) if isinstance(p, dict) and p.get("point")][:5]
            if points:
                # further reading from the library
                topic_toks = _tokens(art["title"] + " " + pick.get("topic", "") + " " + art["text"][:1500])
                scored = sorted(lib, key=lambda x: len(topic_toks & _tokens(x["title"] + " " + x.get("summary", ""))),
                                reverse=True)[:30]
                scored = [x for x in scored if topic_toks & _tokens(x["title"] + " " + x.get("summary", ""))]
                reading = []
                if scored:
                    res = llm.json(READING_PROMPT.format(topic=art["title"], items=_items_list(scored))) or {}
                    for i in res.get("ids", [])[:4]:
                        try:
                            x = scored[int(i)]
                            reading.append({"url": x["url"], "title": x["title"], "source": x["source"]})
                        except (ValueError, IndexError, TypeError):
                            pass
                out["deep"] = {"field": field, "topic": pick.get("topic") or art["title"],
                               "hook": pick.get("hook", ""), "headline": primer.get("headline") or art["title"],
                               "why": primer.get("why", ""), "points": points, "image": art["image"],
                               "wiki_title": art["title"], "wiki_url": art["url"], "reading": reading}
                recent.append(pick.get("topic") or art["title"])
                st["smarter_topics"] = recent[-60:]

    # 2) mixed bag: unrelated evergreen explainers, full three-point cards
    n = int(sm.get("evergreen_picks", 2))
    seen = set(st["seen"])
    used_reading = {normalize_url(r["url"]) for r in (out["deep"] or {}).get("reading", [])}
    pool = [x for x in lib if not x.get("shown") and normalize_url(x["url"]) not in seen
            and normalize_url(x["url"]) not in used_reading]
    random.Random(date).shuffle(pool)
    pool = pool[:30]
    if pool and n:
        if llm.available:
            res = llm.json(EVERGREEN_PROMPT.format(items=_items_list(pool))) or {}
            sc = {}
            for s in res.get("scores", []):
                try:
                    sc[int(s["id"])] = float(s["score"])
                except (KeyError, ValueError, TypeError):
                    pass
            order = sorted(range(len(pool)), key=lambda i: sc.get(i, 0), reverse=True)
        else:
            order = list(range(len(pool)))
        for i in order:
            if len(out["picks"]) >= n:
                break
            x = pool[i]
            if any(p["source"] == x["source"] for p in out["picks"]):
                continue
            try:
                text, meta = fetch_article(x["url"])
            except Exception:
                continue
            if len(text.split()) < cfg.get("min_words", 600) or not is_english(text):
                continue
            summ = summarize(x["title"], x["source"], text, llm, who)
            out["picks"].append({
                "id": hashlib.sha1(normalize_url(x["url"]).encode()).hexdigest()[:12], "url": x["url"],
                "title": x["title"], "headline": summ.get("headline") or x["title"], "source": x["source"],
                "topic": "smarter", "topic_name": "Get smarter", "words": len(text.split()),
                "minutes": max(1, round(len(text.split()) / 230)), "bullets": summ["bullets"],
                "room_line": summ.get("room_line", ""), "ai": summ.get("ai", False),
                "image": meta.get("image") or "", "date": date})
            x["shown"] = date
            st["seen"][normalize_url(x["url"])] = date
    for r in (out["deep"] or {}).get("reading", []):
        for x in lib:
            if normalize_url(x["url"]) == normalize_url(r["url"]):
                x["shown"] = date
    DATA.mkdir(exist_ok=True)
    LIB.write_text(json.dumps(lib, indent=0))
    out["health"] = health
    return out
