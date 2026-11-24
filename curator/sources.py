"""Collect candidate articles from RSS feeds, news searches and Hacker News."""
from __future__ import annotations

import calendar
import logging
import re
import time
import urllib.parse as up
from dataclasses import dataclass, field

import feedparser
import requests

log = logging.getLogger("curator")
UA = "Mozilla/5.0 (compatible; PersonalBriefing/1.0; +https://github.com)"
TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$|ref_|cmpid|smid|source$)")


@dataclass
class Candidate:
    url: str
    title: str
    source: str
    topic: str
    published: float
    summary: str = ""
    source_weight: float = 1.0
    hn_points: int = 0
    text: str = ""
    words: int = 0
    heuristic: float = 0.0
    llm_score: float | None = None
    llm_reason: str = ""
    extra: dict = field(default_factory=dict)


def normalize_url(url: str) -> str:
    p = up.urlsplit(url.strip())
    q = [(k, v) for k, v in up.parse_qsl(p.query) if not TRACKING.match(k.lower())]
    path = p.path.rstrip("/") or "/"
    host = p.netloc.lower().removeprefix("www.")
    return up.urlunsplit(("https", host, path, up.urlencode(q), ""))


def domain(url: str) -> str:
    return up.urlsplit(url).netloc.lower().removeprefix("www.")


def strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", s).strip()


def get(url: str, **kw) -> requests.Response:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=25, **kw)
    r.raise_for_status()
    return r


def _entry_time(e) -> float:
    for key in ("published_parsed", "updated_parsed"):
        t = e.get(key)
        if t:
            return float(calendar.timegm(t))
    return time.time()


def _bing_target(link: str) -> str:
    """Bing news RSS links are redirects; pull the real article URL out."""
    if "bing.com" in link:
        qs = up.parse_qs(up.urlsplit(link).query)
        if "url" in qs:
            return qs["url"][0]
    return link


def _parse_feed(url: str, topic: dict, weight: float, name: str | None) -> list[Candidate]:
    parsed = feedparser.parse(get(url).content)
    src = name or strip_html(parsed.feed.get("title", "")) or domain(url)
    out = []
    for e in parsed.entries[:40]:
        link = _bing_target(e.get("link", ""))
        if not link.startswith("http"):
            continue
        content = ""
        if e.get("content"):
            content = e.content[0].get("value", "")
        out.append(Candidate(
            url=link,
            title=strip_html(e.get("title", "")),
            source=src if "bing.com" not in url else (e.get("source", {}).get("title") or domain(link)),
            topic=topic["id"],
            published=_entry_time(e),
            summary=strip_html(content or e.get("summary", "")),
            source_weight=weight,
        ))
    return out


def collect(cfg: dict, seen: set[str]) -> tuple[list[Candidate], dict]:
    health: dict[str, str] = {}
    found: dict[str, Candidate] = {}
    cutoff = time.time() - cfg["lookback_hours"] * 3600

    def add(c: Candidate):
        key = normalize_url(c.url)
        if key in seen or c.published < cutoff or not c.title:
            return
        prev = found.get(key)
        if prev is None or c.source_weight > prev.source_weight:
            if prev:
                c.hn_points = max(c.hn_points, prev.hn_points)
            found[key] = c

    for topic in cfg["topics"]:
        jobs = []
        for f in topic.get("feeds", []) or []:
            if isinstance(f, str):
                jobs.append((f, 1.0, None))
            else:
                jobs.append((f["url"], f.get("weight", 1.0), f.get("name")))
        for q in topic.get("searches", []) or []:
            jobs.append((f"https://www.bing.com/news/search?q={up.quote_plus(q)}&format=rss", 0.8, None))
        for url, w, name in jobs:
            try:
                items = _parse_feed(url, topic, w, name)
                health[url] = f"ok ({len(items)})"
                for c in items:
                    add(c)
            except Exception as ex:  # one dead feed shouldn't stop the run
                health[url] = f"error: {type(ex).__name__}: {str(ex)[:120]}"
                log.warning("feed failed %s: %s", url, ex)

    hn = cfg.get("hackernews", {})
    if hn.get("enabled"):
        try:
            hits = get("https://hn.algolia.com/api/v1/search",
                       params={"tags": "front_page", "hitsPerPage": 60}).json()["hits"]
            health["hackernews"] = f"ok ({len(hits)})"
            for h in hits:
                if not h.get("url"):
                    continue
                key = normalize_url(h["url"])
                pts = h.get("points") or 0
                if key in found:  # already in a feed: HN attention is a bonus
                    found[key].hn_points = max(found[key].hn_points, pts)
                elif pts >= hn.get("min_points", 150):
                    add(Candidate(url=h["url"], title=h.get("title", ""), source=domain(h["url"]),
                                  topic=hn.get("topic", "ai"), published=float(h.get("created_at_i") or time.time()),
                                  source_weight=0.9, hn_points=pts))
        except Exception as ex:
            health["hackernews"] = f"error: {ex}"

    return list(found.values()), health
