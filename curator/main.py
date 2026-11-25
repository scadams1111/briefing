"""Entry points: `python -m curator daily` and `python -m curator save <url>`."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import re
from pathlib import Path

import yaml

from . import render
from .extract import extract_all, fetch_article, is_english
from .llm import LLM
from .rank import dedupe_titles, final_score, heuristic, is_premium, llm_rank, select, shortlist
from .sources import Candidate, collect, domain, normalize_url
from .summarize import summarize

log = logging.getLogger("curator")
DATA = Path("data")
STATE = DATA / "state.json"


def load_cfg() -> dict:
    return yaml.safe_load(Path("config.yaml").read_text())


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"seen": {}, "saved": []}


def save_state(st: dict) -> None:
    DATA.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(st, indent=1))


def profile(cfg: dict) -> str:
    return os.environ.get("READER_PROFILE", "").strip() or cfg["profile"]


def today() -> str:
    # Pacific date, since the job runs in the early morning there
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=8)).date().isoformat()


def make_item(c_url, title, source, topic, topic_name, text, summ, **extra) -> dict:
    words = len(text.split())
    return {"id": hashlib.sha1(normalize_url(c_url).encode()).hexdigest()[:12], "url": c_url,
            "title": title, "headline": summ.get("headline") or title, "source": source,
            "topic": topic, "topic_name": topic_name, "words": words,
            "minutes": max(1, round(words / 230)), "bullets": summ["bullets"],
            "room_line": summ.get("room_line", ""),
            "ai": summ.get("ai", False), **extra}


def last_picks() -> list[dict]:
    days = sorted((DATA / "days").glob("????-??-??.json"))
    return json.loads(days[-1].read_text()) if days else []


def load_subs(date: str) -> list[dict]:
    p = DATA / "days" / f"{date}-subs.json"
    return json.loads(p.read_text()) if p.exists() else []


SUB_PROMPT = """Reader (private; never mention them, their job or their life): {profile}

From only this headline and summary, write JSON:
{{"headline": "plain, specific headline, max 14 words",
  "takeaway": "one sentence on what the piece is about and why it matters, max 30 words"}}
Write in English. Use only what's given; don't invent details.

Headline: {title}
Summary: {summary}
"""


def subscriber_picks(cfg: dict, st: dict, llm: LLM, who: str, date: str, feeds: list,
                     previews: list | None, n: int, section: str, per_section: int = 1,
                     per_source: int = 2) -> list[dict]:
    """Headline-only picks (paywalled): the NYT column, and Premium picks from other top publications."""
    if n <= 0 or (not feeds and not previews):
        return []
    topics = [{"id": f"sub{k}", "name": f.get("topic", "Subscriber"), "weight": 1.0,
               "feeds": [{"url": f["url"], "name": f.get("name"), "weight": 1.0}]} for k, f in enumerate(feeds)]
    cands = []
    if topics:
        cands, _ = collect({"topics": topics, "lookback_hours": cfg["lookback_hours"], "hackernews": {}},
                           set(st["seen"]))
    names = {t["id"]: t["name"] for t in topics}
    topic_names = {t["id"]: t["name"] for t in cfg["topics"]}
    for c in previews or []:                  # paywalled previews from the main feeds
        names[c.topic] = topic_names.get(c.topic, c.topic)
        cands.append(c)
    for c in cands:
        c.text = c.summary          # headline feed only; never fetch the paywalled page
        c.words = len(c.text.split())
    heuristic(cands, {"topics": topics})
    cands = dedupe_titles(cands)
    pool = sorted(cands, key=lambda c: c.heuristic, reverse=True)[:30]
    llm_rank(pool, llm, who, names)
    chosen: list = []
    for c in sorted(pool, key=final_score, reverse=True):
        if len(chosen) >= n:
            break
        same_section = sum(1 for x in chosen if (x.source, names[x.topic]) == (c.source, names[c.topic]))
        same_source = sum(1 for x in chosen if x.source == c.source)
        if same_section >= per_section or same_source >= per_source:
            continue                # variety across sections and publications
        chosen.append(c)
    out = []
    for c in chosen:
        res = llm.json(SUB_PROMPT.format(profile=who, title=c.title, summary=c.summary[:600])) if llm.available else None
        res = res or {}
        out.append({"id": hashlib.sha1(normalize_url(c.url).encode()).hexdigest()[:12], "url": c.url,
                    "title": c.title, "headline": res.get("headline") or c.title,
                    "takeaway": res.get("takeaway") or c.summary[:220], "source": c.source,
                    "topic_name": names[c.topic], "date": date, "subscriber": True,
                    "section": section, "score": c.llm_score})
        st["seen"][normalize_url(c.url)] = date
    return out


def prune(st: dict, keep_days: int) -> None:
    cutoff = (dt.date.fromisoformat(today()) - dt.timedelta(days=keep_days)).isoformat()
    st["seen"] = {u: d for u, d in st["seen"].items() if d >= cutoff}
    st["saved"] = st["saved"][:200]
    for folder, pattern in ((DATA / "days", "*.json"), (render.DOCS / "archive", "20*.html"),
                            (render.DOCS / "epub", "briefing-*.epub")):
        for p in folder.glob(pattern):
            if re.search(r"\d{4}-\d{2}-\d{2}", p.name).group(0) < cutoff:
                p.unlink()


def daily() -> None:
    cfg = load_cfg()
    st = load_state()
    date = today()
    llm = LLM(cfg)
    who = profile(cfg)
    names = {t["id"]: t["name"] for t in cfg["topics"]}

    # Re-running on the same day rebuilds today's picks instead of skipping them
    st["seen"] = {u: d for u, d in st["seen"].items() if d != date}
    cands, health = collect(cfg, set(st["seen"]))
    log.info("collected %d candidates", len(cands))
    heuristic(cands, cfg)
    per = cfg.get("candidates_per_topic", 6)
    pool = shortlist(cands, cfg, per * 3)   # cheap first cut before fetching pages
    extract_all(pool)
    prem = tuple(cfg.get("premium_domains") or ())
    # paywalled stories from top publications: keep them for the premium slide
    previews = [c for c in pool if c.words < cfg["min_words"] and prem and is_premium(c.url, prem)
                and len(c.summary.split()) >= 15 and is_english(c.summary)]
    by_src: dict[str, list[int]] = {}
    for c in pool:
        by_src.setdefault(c.source, []).append(c.words)
    health_sources = {k: {"fetched": len(v), "full_text": sum(w >= cfg["min_words"] for w in v)}
                      for k, v in sorted(by_src.items())}
    pool = [c for c in pool if c.words >= cfg["min_words"] and is_english(c.text)]
    pool = dedupe_titles(pool)
    heuristic(pool, cfg)                    # recompute now that we know real length
    pool = shortlist(pool, cfg)             # best few per topic go to the AI
    log.info("%d candidates after extraction/dedupe", len(pool))
    llm_rank(pool, llm, who, names)
    picks = select(pool, cfg)

    items = []
    for c in picks:
        summ = summarize(c.title, c.source, c.text, llm, who)
        items.append(make_item(c.url, c.title, c.source, c.topic, names.get(c.topic, c.topic), c.text, summ,
                               date=date, score=c.llm_score,
                               image=c.extra.get("image", ""), author=c.extra.get("author", "")))
        st["seen"][normalize_url(c.url)] = date

    picked = {normalize_url(c.url) for c in picks}
    nyt_cfg, prem_cfg = cfg.get("nyt") or {}, cfg.get("premium") or {}
    # The New York Times column: best + most relevant from its section feeds
    subs = subscriber_picks(cfg, st, llm, who, date, nyt_cfg.get("feeds") or [], [],
                            int(nyt_cfg.get("picks", 5)), "nyt", per_section=2, per_source=99)
    # Premium picks: paywalled stories from other top publications (not NYT)
    subs += subscriber_picks(cfg, st, llm, who, date, [],
                             [c for c in previews if normalize_url(c.url) not in picked
                              and "nytimes.com" not in c.url],
                             int(prem_cfg.get("picks", 4)), "premium", per_section=1, per_source=2)
    new_saved = [s for s in st["saved"] if not s.get("delivered")]
    (DATA / "days").mkdir(parents=True, exist_ok=True)
    (DATA / "days" / f"{date}.json").write_text(json.dumps(items, indent=1))
    (DATA / "days" / f"{date}-subs.json").write_text(json.dumps(subs, indent=1))

    prune(st, cfg.get("keep_days", 30))
    publish(cfg, st, date, items, new_saved)
    for s in new_saved:
        s["delivered"] = True
        s["delivered_on"] = date
    (render.DOCS / "health.json").write_text(json.dumps(
        {"date": date, "llm": llm.available, "candidates": len(cands), "picked": len(items), "feeds": health,
         "sources": health_sources}, indent=1))
    (render.DOCS / ".nojekyll").touch()
    save_state(st)
    (DATA / "last_daily.txt").write_text(date)
    log.info("done: %d picks, %d saved items delivered", len(items), len(new_saved))


def publish(cfg: dict, st: dict, date: str, items: list[dict], new_saved: list[dict]) -> None:
    site = render.site_url(cfg)
    subs = load_subs(date)
    render.build_epub(cfg, date, items, new_saved, subs)
    archive = [p.stem for p in (render.DOCS / "archive").glob("20*.html")] + [date]
    render.web(cfg, date, items, st["saved"], sorted(set(archive)), subs)
    render.feeds(cfg, site, items, st["saved"], subs)
    render.opds(cfg, site)


def rerender() -> None:
    """Rebuild the site from today's saved data (after a design change), no fetching or AI."""
    cfg = load_cfg()
    st = load_state()
    days = sorted((DATA / "days").glob("????-??-??.json"))
    if not days:
        return
    date = days[-1].stem
    publish(cfg, st, date, json.loads(days[-1].read_text()),
            [s for s in st["saved"] if s.get("delivered_on") == date])
    log.info("re-rendered %s", date)


def retry() -> None:
    """Catch-up run: redo today's summaries that missed out on the AI."""
    cfg = load_cfg()
    st = load_state()
    date = today()
    path = DATA / "days" / f"{date}.json"
    if not path.exists():
        log.info("no briefing for %s yet; nothing to retry", date)
        return
    items = json.loads(path.read_text())
    todo = [i for i in items if not i.get("ai")]
    saved_todo = [s for s in st["saved"] if not s.get("ai")][:10]
    if not todo and not saved_todo:
        log.info("all summaries already AI-written; nothing to do")
        return
    llm = LLM(cfg)
    if not llm.available:
        return
    who = profile(cfg)
    fixed = 0
    for it in todo + saved_todo:
        if not llm.available:
            break
        try:
            text, _ = fetch_article(it["url"])
        except Exception:
            continue
        summ = summarize(it["title"], it["source"], text, llm, who)
        if summ.get("ai"):
            it.update(headline=summ.get("headline") or it["title"], bullets=summ["bullets"],
                      room_line=summ.get("room_line", ""), ai=True)
            fixed += 1
    path.write_text(json.dumps(items, indent=1))
    save_state(st)
    if fixed:
        publish(cfg, st, date, items, [s for s in st["saved"] if s.get("delivered_on") == date])
    log.info("retry: upgraded %d of %d summaries", fixed, len(todo) + len(saved_todo))


def save(url: str) -> None:
    cfg = load_cfg()
    st = load_state()
    url = url.strip()
    if any(normalize_url(s["url"]) == normalize_url(url) for s in st["saved"]):
        log.info("already saved")
        return
    text, meta = "", {}
    try:
        text, meta = fetch_article(url)
    except Exception as ex:
        log.warning("couldn't fetch %s: %s", url, ex)
    title = (meta.get("title") or url).strip()
    source = meta.get("sitename") or domain(url)
    summ = summarize(title, source, text, LLM(cfg), profile(cfg))
    if not summ["bullets"]:
        summ["bullets"] = [{"point": "Couldn't read this page (paywall or blocked) — open the original.", "detail": ""}]
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    st["saved"].insert(0, make_item(url, title, source, "saved", "Saved", text, summ, saved_at=now, delivered=False,
                                     image=meta.get("image") or "", author=meta.get("author") or ""))
    save_state(st)
    site = render.site_url(cfg)
    render.saved_page(cfg, st["saved"])
    days = sorted((DATA / "days").glob("????-??-??.json"))
    render.feeds(cfg, site, last_picks(), st["saved"], load_subs(days[-1].stem) if days else [])
    log.info("saved: %s", title)


def find_url(s: str) -> str | None:
    m = re.search(r"https?://\S+", s or "")
    return m.group(0).rstrip(").,>]\"'") if m else None
