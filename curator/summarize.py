"""Turn an article into: headline, 3 key points, an expansion of each, and a
one-line 'say this in the room' takeaway."""
from __future__ import annotations

import re

from .llm import LLM

PROMPT = """You write a personal reading briefing for one reader.

READER: {profile}

ARTICLE
Title: {title}
Source: {source}
Text:
{text}

Return JSON exactly like:
{{
  "headline": "plain, specific headline, max 14 words",
  "bullets": [
    {{"point": "a key takeaway, concrete, max 28 words",
      "detail": "120-200 words expanding this point with the article's specifics: names, numbers, evidence, caveats"}}
  ],
  "room_line": "one sentence the reader could say in conversation that shows they grasp why this matters",
  "tags": ["3-6 people, organizations, places, events, criminal cases or ideas the article is centrally about, each as its exact English Wikipedia article title"]
}}
Rules: never mention the reader, their job, employer or personal life; the reader profile is only to judge
what matters, and this text is published. Write everything in English, even if the article is in another language.
Exactly 3 bullets, ordered by importance. Use only facts from the article.
No hype. If it's an opinion piece, attribute the claims to the author.
"""

SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“])")


def _clip(s: str, words: int) -> str:
    w = s.split()
    return s if len(w) <= words else " ".join(w[:words]) + "…"


def extractive(title: str, text: str) -> dict:
    """No-AI fallback: lead sentences as points, their paragraphs as details."""
    paras = [p.strip() for p in text.split("\n") if len(p.split()) >= 25] or [text]
    bullets = []
    for i in range(min(3, len(paras))):
        first = SENT.split(paras[i])[0]
        detail = " ".join(paras[i:i + 2])
        bullets.append({"point": _clip(first, 30), "detail": _clip(detail, 200)})
    return {"headline": title, "bullets": bullets, "room_line": ""}


def summarize(title: str, source: str, text: str, llm: LLM, profile: str) -> dict:
    out = None
    if llm.available and text:
        out = llm.json(PROMPT.format(profile=profile, title=title, source=source, text=text[:14000]))
    ai = True
    if not out or not isinstance(out.get("bullets"), list) or not out["bullets"]:
        out = extractive(title, text)
        ai = False
    out["ai"] = ai
    out["bullets"] = [b for b in out["bullets"] if isinstance(b, dict) and b.get("point")][:3]
    out.setdefault("headline", title)
    out.setdefault("room_line", "")
    out.pop("why_for_you", None)
    from .wiki import clean_tags
    out["tags"] = clean_tags(out.get("tags")) if ai else []
    return out
