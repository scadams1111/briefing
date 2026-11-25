"""'More like this' / 'Less like this'.

Buttons on the site open a GitHub issue titled "feedback: more|less|undo-more|undo-less"
(sent from your browser with a key that's stored only on your phone). Each morning
the daily run reads those issues, adjusts topic/source weights in data/prefs.json,
remembers the liked/disliked headlines for the AI ranker, and closes the issues.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import requests

log = logging.getLogger("curator")
PREFS = Path("data") / "prefs.json"
DELTA = {"more": (0.07, 0.10), "less": (-0.08, -0.15)}   # (topic, source) nudges per tap
TOPIC_RANGE, SOURCE_RANGE = (0.5, 1.6), (0.4, 1.8)


def load() -> dict:
    p = json.loads(PREFS.read_text()) if PREFS.exists() else {}
    p.setdefault("topic", {})
    p.setdefault("source", {})
    p.setdefault("liked", [])
    p.setdefault("disliked", [])
    return p


def _clamp(v: float, lo_hi: tuple) -> float:
    return round(max(lo_hi[0], min(lo_hi[1], v)), 3)


def apply(prefs: dict, action: str, item: dict) -> None:
    undo = action.startswith("undo-")
    base = action.removeprefix("undo-")
    if base not in DELTA:
        return
    dt, ds = DELTA[base]
    sign = -1 if undo else 1
    topic, source, title = item.get("topic") or "", item.get("source") or "", (item.get("title") or "")[:160]
    if topic and topic not in ("saved", "search"):
        prefs["topic"][topic] = _clamp(prefs["topic"].get(topic, 1.0) + sign * dt, TOPIC_RANGE)
    if source:
        prefs["source"][source] = _clamp(prefs["source"].get(source, 1.0) + sign * ds, SOURCE_RANGE)
    lst = prefs["liked" if base == "more" else "disliked"]
    if undo:
        if title in lst:
            lst.remove(title)
    elif title and title not in lst:
        lst.append(title)
        del lst[:-40]                       # keep the 40 most recent


def collect() -> int:
    """Read open feedback issues (yours only), apply them, close them. Returns how many."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if not repo or not token:
        return 0
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/issues", headers=h, timeout=20,
                         params={"state": "open", "per_page": 100, "sort": "created", "direction": "asc"})
        r.raise_for_status()
        issues = [i for i in r.json() if "pull_request" not in i and i["title"].startswith("feedback:")]
    except Exception as ex:
        log.warning("couldn't read feedback: %s", ex)
        return 0
    prefs, n = load(), 0
    for i in issues:
        if i.get("author_association") == "OWNER":
            action = i["title"].split(":", 1)[1].strip().split()[0] if ":" in i["title"] else ""
            m = re.search(r"\{.*\}", i.get("body") or "", re.S)
            try:
                item = json.loads(m.group(0)) if m else {}
            except json.JSONDecodeError:
                item = {}
            apply(prefs, action, item)
            n += 1
        try:
            requests.patch(i["url"], headers=h, json={"state": "closed", "state_reason": "completed"}, timeout=20)
        except Exception:
            pass
    if n:
        PREFS.parent.mkdir(exist_ok=True)
        PREFS.write_text(json.dumps(prefs, indent=1))
        log.info("applied %d feedback taps", n)
    return n


def prompt_text(prefs: dict) -> str:
    liked, disliked = prefs.get("liked", [])[-15:], prefs.get("disliked", [])[-15:]
    if not liked and not disliked:
        return ""
    s = ("\nREADER FEEDBACK (stories they asked for more or less of; generalize to similar topics, "
         "angles and sources, but don't over-fit):\n")
    if liked:
        s += "More like: " + "; ".join(liked) + "\n"
    if disliked:
        s += "Less like: " + "; ".join(disliked) + "\n"
    return s
