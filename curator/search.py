"""Search.

1. Instant: docs/search-index.json holds everything the briefing has collected
   (recent candidates, past picks, the explainer library); search.html filters it
   in the browser.
2. Fresh: `python -m curator search "<query>"` (run by the Search workflow when you
   open an issue titled "search: ...") finds new articles on the topic, has the AI
   pick the best and most relevant, and writes docs/search/<slug>.html.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import logging
import re
import time
import urllib.parse as up
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .extract import fetch_article, is_english
from .llm import LLM
from .sources import Candidate, _parse_feed, domain, normalize_url
from .summarize import summarize

log = logging.getLogger("curator")
DATA, DOCS = Path("data"), Path("docs")
POOL = DATA / "pool.json"
e = html.escape


def slug(q: str) -> str:
    """Must match slug() in the search page's JavaScript."""
    return re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")[:60] or "search"


# ── the rolling pool of everything collected ──────────────────────────
def remember_pool(cands: list[Candidate], date: str, keep_days: int = 21) -> None:
    pool = json.loads(POOL.read_text()) if POOL.exists() else []
    have = {p["u"] for p in pool}
    for c in cands:
        key = normalize_url(c.url)
        if key in have or not c.title:
            continue
        have.add(key)
        pool.append({"u": c.url, "t": c.title, "s": c.source, "x": " ".join(c.summary.split()[:40]),
                     "d": date, "k": c.topic})
    cutoff = (dt.date.fromisoformat(date) - dt.timedelta(days=keep_days)).isoformat()
    pool = [p for p in pool if p["d"] >= cutoff]
    DATA.mkdir(exist_ok=True)
    POOL.write_text(json.dumps(pool, separators=(",", ":")))


def build_index(topic_names: dict) -> None:
    """docs/search-index.json: compact records the search page filters in the browser."""
    out, seen = [], set()

    def add(u, t, s, x, d, tag=""):
        k = normalize_url(u)
        if k in seen or not t:
            return
        seen.add(k)
        out.append({"u": u, "t": t, "s": s, "x": x[:220], "d": d, "g": tag})

    for f in sorted((DATA / "days").glob("????-??-??.json"), reverse=True):
        for i in json.loads(f.read_text()):
            pts = " ".join(b.get("point", "") for b in i.get("bullets", []))
            add(i["url"], i.get("headline") or i["title"], i["source"], pts, f.stem, "Briefing pick")
    for f in sorted((DATA / "days").glob("????-??-??-smarter.json"), reverse=True):
        sm = json.loads(f.read_text())
        for i in sm.get("picks", []):
            add(i["url"], i.get("headline") or i["title"], i["source"],
                " ".join(b.get("point", "") for b in i.get("bullets", [])), f.stem[:10], "Get smarter")
        d = sm.get("deep")
        if d:
            add(d["wiki_url"], "Deep dive: " + d["headline"], "Wikipedia",
                " ".join(p["point"] for p in d["points"]), f.stem[:10], "Deep dive")
    pool = json.loads(POOL.read_text()) if POOL.exists() else []
    for p in sorted(pool, key=lambda p: p["d"], reverse=True):
        add(p["u"], p["t"], p["s"], p.get("x", ""), p["d"], topic_names.get(p.get("k", ""), ""))
    lib = DATA / "library.json"
    for x in (json.loads(lib.read_text()) if lib.exists() else []):
        when = dt.datetime.fromtimestamp(x.get("published") or x.get("added") or time.time()).date().isoformat()
        add(x["url"], x["title"], x["source"], x.get("summary", ""), when, "Explainer")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "search-index.json").write_text(json.dumps(out, separators=(",", ":")))


# ── fresh search ───────────────────────────────────────────────────────
RANK = """Someone searched for: "{q}"

Score each candidate 0-10: how relevant it is to that search AND how good it is to read
(original reporting, real analysis, clear explanation, strong writing). Penalize press releases,
thin news rewrites, listicles, promos, and duplicates of the same story.

Return JSON: {{"scores": [{{"id": <int>, "score": <number>}}]}}

CANDIDATES:
{items}
"""


def _wiki_background(q: str) -> dict | None:
    from .smarter import get
    try:
        hits = get("https://en.wikipedia.org/w/api.php", params={
            "action": "opensearch", "format": "json", "limit": 1, "search": q}).json()
        if len(hits) < 2 or not hits[1]:
            return None
        t = hits[1][0]
        r = get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{up.quote(t)}").json()
        if r.get("type") == "disambiguation" or not r.get("extract"):
            return None
        return {"title": r.get("title", t), "text": r["extract"],
                "url": (r.get("content_urls") or {}).get("mobile", {}).get("page") or f"https://en.wikipedia.org/wiki/{up.quote(t)}"}
    except Exception:
        return None


def run(q: str, cfg: dict, who: str, n: int = 6) -> Path:
    q = " ".join(q.split())[:120]
    s = slug(q)
    llm = LLM(cfg)
    cands: dict[str, Candidate] = {}
    for query in (q, f"{q} analysis"):
        url = f"https://www.bing.com/news/search?q={up.quote_plus(query)}&format=rss"
        try:
            for c in _parse_feed(url, {"id": "search"}, 1.0, None):
                cands.setdefault(normalize_url(c.url), c)
        except Exception as ex:
            log.warning("news search failed: %s", ex)
    # things already collected
    idx = json.loads((DOCS / "search-index.json").read_text()) if (DOCS / "search-index.json").exists() else []
    toks = {w for w in re.findall(r"[a-z0-9]+", q.lower()) if len(w) > 2}
    def hit(r):
        text = (r["t"] + " " + r.get("x", "")).lower()
        return sum(w in text for w in toks)
    for r in sorted((r for r in idx if hit(r) >= max(1, len(toks) // 2 + (len(toks) > 1))), key=hit, reverse=True)[:20]:
        cands.setdefault(normalize_url(r["u"]), Candidate(url=r["u"], title=r["t"], source=r["s"], topic="search",
                                                          published=time.time(), summary=r.get("x", "")))
    pool = list(cands.values())[:40]

    def grab(c):
        try:
            c.text, meta = fetch_article(c.url)
            c.extra["image"] = meta.get("image") or ""
            if meta.get("sitename") and "bing" in c.source.lower():
                c.source = meta["sitename"]
        except Exception:
            c.text = ""
        c.words = len(c.text.split())
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(grab, pool))
    pool = [c for c in pool if c.words >= 350 and is_english(c.text)]
    if llm.available and pool:
        items = "\n".join(f"[{i}] ({c.source}, {c.words} words) {c.title}\n    {' '.join(c.text.split()[:80])}"
                          for i, c in enumerate(pool))
        res = llm.json(RANK.format(q=q, items=items)) or {}
        for x in res.get("scores", []):
            try:
                pool[int(x["id"])].llm_score = float(x["score"])
            except (KeyError, ValueError, IndexError, TypeError):
                pass
    pool.sort(key=lambda c: (c.llm_score if c.llm_score is not None else 0, c.words), reverse=True)
    chosen, per_src = [], {}
    for c in pool:
        if len(chosen) >= n:
            break
        if c.llm_score is not None and c.llm_score < 5:
            continue
        if per_src.get(c.source, 0) >= 2:
            continue
        per_src[c.source] = per_src.get(c.source, 0) + 1
        chosen.append(c)
    results = []
    for c in chosen:
        summ = summarize(c.title, c.source, c.text, llm, who)
        results.append({"id": hashlib.sha1(normalize_url(c.url).encode()).hexdigest()[:12], "url": c.url,
                        "title": c.title, "headline": summ.get("headline") or c.title, "source": c.source,
                        "topic": "search", "topic_name": "Search", "minutes": max(1, round(c.words / 230)),
                        "bullets": summ["bullets"], "room_line": summ.get("room_line", ""),
                        "image": c.extra.get("image", ""), "ai": summ.get("ai", False)})
    data = {"q": q, "slug": s, "when": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
            "background": _wiki_background(q), "results": results}
    (DATA / "searches").mkdir(parents=True, exist_ok=True)
    (DATA / "searches" / f"{s}.json").write_text(json.dumps(data, indent=1))
    from . import web
    path = web.write_search_result(data)
    web.write_search_page()
    log.info("search %r: %d results -> %s", q, len(results), path)
    return path
