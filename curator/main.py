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
from .extract import extract_all, fetch_article
from .llm import LLM
from .rank import dedupe_titles, heuristic, llm_rank, select, shortlist
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
            "room_line": summ.get("room_line", ""), "why_for_you": summ.get("why_for_you", ""),
            "ai": summ.get("ai", False), **extra}


def last_picks() -> list[dict]:
    days = sorted((DATA / "days").glob("*.json"))
    return json.loads(days[-1].read_text()) if days else []


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
    pool = [c for c in pool if c.words >= cfg["min_words"]]
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
                               date=date, score=c.llm_score, reason=c.llm_reason,
                               image=c.extra.get("image", ""), author=c.extra.get("author", "")))
        st["seen"][normalize_url(c.url)] = date

    new_saved = [s for s in st["saved"] if not s.get("delivered")]
    (DATA / "days").mkdir(parents=True, exist_ok=True)
    (DATA / "days" / f"{date}.json").write_text(json.dumps(items, indent=1))

    prune(st, cfg.get("keep_days", 30))
    publish(cfg, st, date, items, new_saved)
    for s in new_saved:
        s["delivered"] = True
        s["delivered_on"] = date
    (render.DOCS / "health.json").write_text(json.dumps(
        {"date": date, "llm": llm.available, "candidates": len(cands), "picked": len(items), "feeds": health}, indent=1))
    (render.DOCS / ".nojekyll").touch()
    save_state(st)
    log.info("done: %d picks, %d saved items delivered", len(items), len(new_saved))


def publish(cfg: dict, st: dict, date: str, items: list[dict], new_saved: list[dict]) -> None:
    site = render.site_url(cfg)
    render.build_epub(cfg, date, items, new_saved)
    archive = [p.stem for p in (render.DOCS / "archive").glob("20*.html")] + [date]
    render.web(cfg, date, items, st["saved"], sorted(set(archive)))
    render.feeds(cfg, site, items, st["saved"])
    render.opds(cfg, site)


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
                      room_line=summ.get("room_line", ""), why_for_you=summ.get("why_for_you", ""), ai=True)
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
    render.feeds(cfg, site, last_picks(), st["saved"])
    log.info("saved: %s", title)


def find_url(s: str) -> str | None:
    m = re.search(r"https?://\S+", s or "")
    return m.group(0).rstrip(").,>]\"'") if m else None
