"""Pull clean article text so the AI can judge and summarize it."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

import trafilatura

from .sources import Candidate, get

log = logging.getLogger("curator")


def fetch_article(url: str) -> tuple[str, dict]:
    """Return (text, metadata) for a URL. Text is '' if extraction fails."""
    html = get(url).text
    text = trafilatura.extract(html, include_comments=False, include_tables=False,
                               favor_precision=True) or ""
    meta = {}
    m = trafilatura.extract_metadata(html)
    if m:
        meta = {"title": m.title, "sitename": m.sitename, "date": m.date, "author": m.author,
                "image": getattr(m, "image", None) or ""}
    return text, meta


def _one(c: Candidate) -> None:
    try:
        c.text, meta = fetch_article(c.url)
        c.extra["image"] = meta.get("image") or ""
        c.extra["author"] = meta.get("author") or ""
    except Exception as ex:
        log.info("extract failed %s: %s", c.url, ex)
        c.text = ""
    if len(c.text.split()) < len(c.summary.split()):
        c.text = c.summary  # paywalled or blocked: fall back to the feed's own text
    c.words = len(c.text.split())


EN = set("""the and of to in is that for it with as was on are be by this have from at not but
they his her which you we an or has their will been were would its more said can about
who what when there than also one into after over new how our some these out many most""".split())


def is_english(text: str) -> bool:
    """Cheap check: in English prose, common English words make up a big share of words."""
    words = [w.lower().strip(".,;:!?\"'()“”’") for w in text.split()[:400]]
    if len(words) < 40:
        return True  # too little to judge
    return sum(w in EN for w in words) / len(words) >= 0.18


def extract_all(cands: list[Candidate], workers: int = 8) -> None:
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(_one, cands))
