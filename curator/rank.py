"""Score, shortlist and pick the day's articles."""
from __future__ import annotations

import logging
import math
import re
import time
from urllib.parse import urlsplit

from .llm import LLM
from .sources import Candidate

log = logging.getLogger("curator")

RANK_PROMPT = """You pick what one reader should read today.

READER: {profile}

Score each candidate 0-10 for whether this reader should read it today.
Reward: excellent writing; original reporting or real analysis; durable insight;
stories informed people will be discussing; relevance to the reader's interests.
Penalize: press releases, listicles, thin rewrites of wire news, product promos,
clickbait, and duplicate coverage of the same story (score only the best version high).

Return JSON: {{"scores": [{{"id": <int>, "score": <number>}}]}}

CANDIDATES:
{items}
"""


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 3}


def is_premium(url: str, domains: tuple) -> bool:
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    return any(host == d or host.endswith("." + d) for d in domains)


def dedupe_titles(cands: list[Candidate]) -> list[Candidate]:
    """Drop near-identical headlines (same story from several outlets)."""
    kept: list[Candidate] = []
    for c in sorted(cands, key=lambda c: (c.source_weight, c.words), reverse=True):
        t = _tokens(c.title)
        if any(t and len(t & _tokens(k.title)) / len(t | _tokens(k.title)) > 0.6 for k in kept):
            continue
        kept.append(c)
    return kept


def heuristic(cands: list[Candidate], cfg: dict) -> None:
    tw = {t["id"]: t.get("weight", 1.0) for t in cfg["topics"]}
    prem = tuple(cfg.get("premium_domains") or ())
    bonus = float(cfg.get("premium_bonus", 0.0))
    now = time.time()
    for c in cands:
        age_h = max(0.0, (now - c.published) / 3600)
        c.heuristic = (
            c.source_weight * tw.get(c.topic, 1.0)
            + min(c.words, 4000) / 2000          # longer, more substantial pieces
            + math.log1p(c.hn_points) / 3         # people are talking about it
            - age_h / 48                          # freshness
            + (bonus if prem and is_premium(c.url, prem) else 0.0)
        )


def shortlist(cands: list[Candidate], cfg: dict, per: int | None = None) -> list[Candidate]:
    per = per or cfg.get("candidates_per_topic", 6)
    out: list[Candidate] = []
    for t in cfg["topics"]:
        mine = sorted((c for c in cands if c.topic == t["id"]), key=lambda c: c.heuristic, reverse=True)
        out.extend(mine[:per])
    return out


def llm_rank(cands: list[Candidate], llm: LLM, profile: str, topic_names: dict) -> None:
    if not llm.available:
        return
    for start in range(0, len(cands), 30):
        batch = cands[start:start + 30]
        lines = []
        for i, c in enumerate(batch):
            excerpt = " ".join(c.text.split()[:110])
            lines.append(f"[{i}] ({topic_names.get(c.topic, c.topic)} | {c.source} | {c.words} words) "
                         f"{c.title}\n    {excerpt}")
        res = llm.json(RANK_PROMPT.format(profile=profile, items="\n".join(lines)))
        for s in (res or {}).get("scores", []):
            try:
                c = batch[int(s["id"])]
                c.llm_score = float(s["score"])
                c.llm_reason = str(s.get("reason", ""))
            except (KeyError, ValueError, IndexError, TypeError):
                continue


def final_score(c: Candidate) -> float:
    # The AI's judgement dominates; the heuristic breaks ties / fills gaps.
    return (c.llm_score * 1.0 + c.heuristic * 0.3) if c.llm_score is not None else c.heuristic


def select(cands: list[Candidate], cfg: dict) -> list[Candidate]:
    n = cfg["daily_picks"]
    cap = cfg.get("max_per_topic", 2)
    light = {t["id"] for t in cfg["topics"] if t.get("kind") == "light"}
    ranked = sorted(cands, key=final_score, reverse=True)
    picks: list[Candidate] = []
    count: dict[str, int] = {}

    def take(c):
        picks.append(c)
        count[c.topic] = count.get(c.topic, 0) + 1

    for c in ranked:  # reserve the lighter reads first
        if sum(1 for p in picks if p.topic in light) >= cfg.get("min_light_picks", 1):
            break
        if c.topic in light:
            take(c)
    for c in ranked:
        if len(picks) >= n:
            break
        if c not in picks and count.get(c.topic, 0) < cap:
            take(c)
    # keep core stories on top, light reads at the end
    return sorted(picks, key=lambda c: (c.topic in light, -final_score(c)))
