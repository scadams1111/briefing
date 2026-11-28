"""A small wiki over everything you've been briefed on.

Every story carries a few `tags`: the people, places, organizations, cases, events and ideas it's
about, named by their English Wikipedia titles. From those we build:
- docs/wiki/<slug>.html   one page per topic: a short Wikipedia summary, every story of yours that
                          mentions it, and related topics (ones that keep showing up alongside it)
- docs/wiki/index.html    all topics A–Z, searchable
- on each story card:     topic chips, inline links in the text, and related stories from your archive
"""
from __future__ import annotations

import datetime as dt
import html
import json
import logging
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

log = logging.getLogger(__name__)
e = html.escape
DATA = Path("data")
DOCS = Path("docs")
CACHE = DATA / "wiki.json"

TAG_PROMPT = """For each numbered article below, list 3-6 specific people, organizations, places, historical events,
criminal cases or ideas it is centrally about. Use each one's exact English Wikipedia article title
(e.g. "Federal Reserve", "Zodiac Killer", "Battle of Hastings", "CRISPR gene editing"). Skip vague
words ("Technology", "Health", "United States" unless central). Return JSON: {{"tags": {{"1": ["..."], "2": [...]}}}}

{articles}"""


def slug(tag: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")[:80] or "topic"


def clean_tags(tags) -> list[str]:
    out, seen = [], set()
    for t in tags or []:
        t = re.sub(r"\s+", " ", str(t)).strip().strip(".")
        if 2 < len(t) <= 60 and slug(t) not in seen:
            seen.add(slug(t))
            out.append(t)
    return out[:6]


STOP = set("""The A An And Or But If In On At Of For To From By With Without As Is Are Was Were Be This That These Those
It Its They Their We Our You Your He She His Her Why How What When Where Who Which New One Two Three Four Five
Mr Ms Mrs Dr After Before Over Under Into About Than Then Also Not No Yes Here There Some Many Most More Less
January February March April May June July August September October November December Monday Tuesday Wednesday
Thursday Friday Saturday Sunday""".split())


def guess_tags(it: dict) -> list[str]:
    """No-AI fallback: proper-noun phrases from the headline and points."""
    text = " ".join([it.get("headline", "")] + [b.get("point", "") for b in it.get("bullets", [])])
    found = Counter()
    for m in re.finditer(r"\b([A-Z][a-zA-Z'’\-]+(?:\s+(?:of\s+|the\s+|de\s+)?[A-Z][a-zA-Z'’\-]+){1,3})\b", text):
        words = m.group(1).split()
        while words and words[0] in STOP:
            words = words[1:]
        if len(words) >= 2 and not all(w in STOP for w in words):
            found[" ".join(words)] += 1
    return [t for t, _ in found.most_common(4)]


def tags_of(it: dict) -> list[str]:
    return clean_tags(it.get("tags"))   # AI tags only; guesses from headlines were too noisy


# ── corpus ────────────────────────────────────────────────────────────────
def corpus(saved: list[dict]) -> list[dict]:
    items, seen = [], set()
    for p in sorted((DATA / "days").glob("????-??-??.json"), reverse=True):
        try:
            day = json.loads(p.read_text())
        except Exception:
            continue
        for it in day:
            if it.get("id") and it["id"] not in seen:
                seen.add(it["id"])
                items.append({**it, "_date": p.stem})
    for s in saved:
        if s.get("id") and s["id"] not in seen:
            seen.add(s["id"])
            items.append({**s, "_date": (s.get("saved_at") or "")[:10], "_saved": True})
    return items


def backfill(llm, limit: int = 60) -> int:
    """Tag past stories that don't have AI tags yet (a few batched calls per morning)."""
    if llm is None or not getattr(llm, "available", False):
        return 0
    done = 0
    for p in sorted((DATA / "days").glob("????-??-??.json"), reverse=True):
        day = json.loads(p.read_text())
        todo = [it for it in day if not it.get("tags")]
        if not todo:
            continue
        for i in range(0, len(todo), 10):
            batch = todo[i:i + 10]
            arts = "\n".join(f"{n}. {it['headline']} ({it['source']}): " + " ".join(b['point'] for b in it.get('bullets', []))
                             for n, it in enumerate(batch, 1))
            res = llm.json(TAG_PROMPT.format(articles=arts)) or {}
            got = res.get("tags") or {}
            for n, it in enumerate(batch, 1):
                t = clean_tags(got.get(str(n)))
                if t:
                    it["tags"] = t
                    done += 1
        p.write_text(json.dumps(day, indent=1))
        if done >= limit:
            break
    log.info("tagged %d past stories", done)
    return done


# ── Wikipedia summaries (cached; fetched in the morning run) ─────────────
def load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except Exception:
        return {}


def fetch_summaries(tags: list[str], limit: int = 200) -> None:
    import requests
    cache = load_cache()
    todo = [t for t in tags if slug(t) not in cache][:limit]
    for t in todo:
        try:
            r = requests.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(t.replace(" ", "_"), safe=""),
                             headers={"User-Agent": "BriefingWiki/1.0 (personal reading app)"}, timeout=10)
            if r.status_code == 404:
                cache[slug(t)] = {"missing": True}
                continue
            j = r.json()
            if j.get("type") == "disambiguation":
                cache[slug(t)] = {"missing": True}
                continue
            cache[slug(t)] = {"title": j.get("title", t), "extract": (j.get("extract") or "")[:700],
                              "desc": j.get("description", ""),
                              "url": (j.get("content_urls") or {}).get("desktop", {}).get("page", "")}
        except Exception as ex:
            log.info("wiki summary failed for %s: %s", t, ex)
            break  # offline or rate-limited; try again tomorrow
    CACHE.write_text(json.dumps(cache, indent=0, sort_keys=True))


# ── the graph ─────────────────────────────────────────────────────────────
class Wiki:
    def __init__(self, items: list[dict]):
        self.items = items
        self.tags: dict[str, list[str]] = {}          # item id -> tags
        self.name: dict[str, str] = {}               # slug -> display name
        self.where: dict[str, list[dict]] = defaultdict(list)
        self.co: dict[str, Counter] = defaultdict(Counter)
        for it in items:
            ts = tags_of(it)
            self.tags[it["id"]] = ts
            for t in ts:
                s = slug(t)
                self.name.setdefault(s, t)
                self.where[s].append(it)
            for a in ts:
                for b in ts:
                    if a != b:
                        self.co[slug(a)][slug(b)] += 1
        # word vectors for "related stories"
        docs = {it["id"]: self._words(it) for it in items}
        df = Counter(w for ws in docs.values() for w in set(ws))
        n = max(1, len(docs))
        self.vec = {}
        for i, ws in docs.items():
            tf = Counter(ws)
            v = {w: c * math.log(n / df[w]) for w, c in tf.items() if df[w] < n * .3}
            norm = math.sqrt(sum(x * x for x in v.values())) or 1
            self.vec[i] = {w: x / norm for w, x in v.items()}

    @staticmethod
    def _words(it):
        text = " ".join([it.get("headline", "")] + [b.get("point", "") + " " + b.get("detail", "") for b in it.get("bullets", [])])
        return [w for w in re.findall(r"[a-z][a-z\-]{3,}", text.lower())]

    def related(self, it: dict, k: int = 3) -> list[dict]:
        mine, vt = {slug(t) for t in self.tags.get(it["id"], [])}, self.vec.get(it["id"], {})
        scored = []
        for o in self.items:
            if o["id"] == it["id"] or o.get("url") == it.get("url"):
                continue
            shared = len(mine & {slug(t) for t in self.tags.get(o["id"], [])})
            vo = self.vec.get(o["id"], {})
            cos = sum(x * vo.get(w, 0) for w, x in vt.items())
            s = shared * .35 + cos
            if s > .18:
                scored.append((s, o))
        scored.sort(key=lambda x: -x[0])
        return [o for _, o in scored[:k]]

    def has_page(self, tag: str) -> bool:
        return slug(tag) in self.where


WIKI: Wiki | None = None


def prepare(saved: list[dict]) -> Wiki:
    global WIKI
    WIKI = Wiki(corpus(saved))
    return WIKI


# ── bits used inside story cards ─────────────────────────────────────────
def reader_href(it: dict, root: str) -> str:
    au = (it.get("audio") or {}).get("url", "")
    return f"{root}read.html?u={quote(it['url'], safe='')}" + (f"&a={quote(au, safe='')}" if au else "")


def link_text(text_escaped: str, it: dict, root: str) -> str:
    """Turn the first mention of each of the story's topics into a link to its page."""
    if not WIKI:
        return text_escaped
    out = text_escaped
    for t in sorted(WIKI.tags.get(it.get("id", ""), []), key=len, reverse=True):
        name = e(t)
        i = out.find(name)
        if i < 0 or "<a " in out[max(0, i - 60):i]:
            continue
        out = out[:i] + f"<a class='wl' href='{root}wiki/{slug(t)}.html'>{name}</a>" + out[i + len(name):]
    return out


def card_extras(it: dict, root: str) -> str:
    if not WIKI or not it.get("id"):
        return ""
    ts = WIKI.tags.get(it["id"]) or tags_of(it)
    chips = "".join(f"<a class='tchip' href='{root}wiki/{slug(t)}.html'>{e(t)}</a>" for t in ts if WIKI.has_page(t))
    rel = WIKI.related(it)
    rel_html = "".join(
        f"<a class='rel' href='{e(reader_href(o, root))}'><span>{e(o['source'])} · {e(_nice(o.get('_date', '')))}</span>"
        f"<b>{e(o['headline'])}</b></a>" for o in rel)
    out = ""
    if chips:
        out += f"<div class='tchips'><span class='tl'>Topics</span>{chips}</div>"
    if rel_html:
        out += f"<div class='rels'><span class='tl'>Related in your briefing</span>{rel_html}</div>"
    return out


def _nice(d: str) -> str:
    try:
        return dt.date.fromisoformat(d).strftime("%b %-d")
    except Exception:
        return ""


CSS = r"""
a.wl{color:inherit;text-decoration:underline;text-decoration-color:var(--accent);text-decoration-thickness:1.5px;text-underline-offset:3px}
.tchips{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:14px 0 4px}
.tl{font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700;margin-right:4px;width:100%}
.tchip{display:inline-flex;align-items:center;height:32px;padding:0 11px;border-radius:999px;background:var(--tile);border:1px solid var(--line);color:var(--ink);font-size:13px;font-weight:600}
.rels{display:flex;flex-direction:column;gap:6px;margin:14px 0 4px}
.rel{display:block;padding:10px 12px;border-radius:12px;background:var(--tile);border:1px solid var(--line)}
.rel span{display:block;font-size:12px;color:var(--muted);margin-bottom:2px}
.rel b{font-size:14.5px;line-height:1.35;color:var(--ink);font-weight:600}
.wk .lead{background:var(--card);border-radius:18px;padding:16px;margin:0 0 18px}
.wk .lead p{margin:0 0 8px;font-size:15.5px;line-height:1.55;color:var(--detail)}
.wk .lead small{color:var(--muted);font-size:12.5px}
.wk .lead small a{text-decoration:underline}
.wk h3{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);margin:22px 2px 8px}
.wk .story{background:var(--card);border-radius:16px;padding:14px;margin:0 0 10px}
.wk .story .m{font-size:12.5px;color:var(--muted)}
.wk .story b{display:block;font-size:16px;line-height:1.35;margin:3px 0 6px;color:var(--ink)}
.wk .story p{margin:0 0 10px;font-size:14px;line-height:1.5;color:var(--detail)}
.wk .story .acts{display:flex;gap:8px;flex-wrap:wrap}
.wk [hidden]{display:none!important}
.wk .az{display:flex;flex-wrap:wrap;gap:6px}
.wk input.find{width:100%;height:46px;border-radius:14px;border:1px solid var(--line);background:var(--tile);color:var(--ink);font:500 16px var(--sans);padding:0 14px;margin:0 0 14px;box-sizing:border-box}
.wk .tchip i{font-style:normal;color:var(--muted);margin-left:6px;font-weight:500}
"""


# ── pages ─────────────────────────────────────────────────────────────────
def write_pages(shell) -> None:
    if not WIKI:
        return
    out = DOCS / "wiki"
    out.mkdir(parents=True, exist_ok=True)
    cache = load_cache()
    keep = set()
    for s, items in WIKI.where.items():
        name = WIKI.name[s]
        info = cache.get(s) or {}
        wurl = info.get("url") or "https://en.wikipedia.org/wiki/" + quote(name.replace(" ", "_"))
        lead = ""
        if info.get("extract"):
            lead = (f"<div class='lead'><p>{e(info['extract'])}</p><small>From Wikipedia · "
                    f"<a href='{e(wurl)}'>Read the full article</a></small></div>")
        else:
            lead = f"<div class='lead'><small><a href='{e(wurl)}'>Look up {e(name)} on Wikipedia</a></small></div>"
        stories = "".join(
            f"<div class='story'><span class='m'>{e(it['source'])} · {e(_nice(it.get('_date', '')))}{' · Saved' if it.get('_saved') else ''}</span>"
            f"<b>{e(it['headline'])}</b><p>{e((it.get('bullets') or [{}])[0].get('point', ''))}</p><div class='acts'>"
            f"<a class='chip' href='{e(reader_href(it, '../'))}'><span>Read</span></a>"
            f"<a class='chip' href='{e(it['url'])}'><span>Original</span></a></div></div>"
            for it in sorted(items, key=lambda x: x.get("_date", ""), reverse=True))
        co = [c for c, _ in WIKI.co[s].most_common(12) if c in WIKI.where]
        rel = "".join(f"<a class='tchip' href='{c}.html'>{e(WIKI.name[c])}</a>" for c in co)
        desc = f"<p>{e(info['desc'][:1].upper() + info['desc'][1:])}</p>" if info.get("desc") else ""
        body = (f"<style>{CSS}</style><main class='page wk'><section class='hero'><div class='kicker'>"
                f"<a href='index.html'>Topics</a></div><h1>{e(name)}</h1>{desc}</section>{lead}"
                f"<h3>In your briefing · {len(items)}</h3>{stories}"
                + (f"<h3>Related topics</h3><div class='az'>{rel}</div>" if rel else "") + "</main>")
        (out / f"{s}.html").write_text(shell(f"{name} — Briefing", "archive", body, root="../"))
        keep.add(f"{s}.html")
    names = sorted(WIKI.where, key=lambda s: WIKI.name[s].lower())
    top = sorted(WIKI.where, key=lambda s: -len(WIKI.where[s]))[:16]
    chip = lambda s: f"<a class='tchip' href='{s}.html' data-n='{e(WIKI.name[s].lower())}'>{e(WIKI.name[s])}<i>{len(WIKI.where[s])}</i></a>"
    body = (f"<style>{CSS}</style><main class='page wk'><section class='hero'><div class='kicker'>Wiki</div><h1>Topics</h1>"
            "<p>Every person, place, case and idea from your briefings, linked together.</p></section>"
            "<input class='find' type='search' placeholder='Find a topic' aria-label='Find a topic'>"
            f"<h3>Most mentioned</h3><div class='az top'>{''.join(chip(s) for s in top)}</div>"
            f"<h3>A–Z · {len(names)}</h3><div class='az all'>{''.join(chip(s) for s in names)}</div></main>"
            "<script>document.querySelector('.find').addEventListener('input',ev=>{const q=ev.target.value.toLowerCase().trim();"
            "document.querySelector('.top').parentNode.querySelectorAll('h3')[0].hidden=!!q;document.querySelector('.top').hidden=!!q;"
            "document.querySelectorAll('.all .tchip').forEach(a=>a.hidden=q&&!a.dataset.n.includes(q))})</script>")
    (out / "index.html").write_text(shell("Topics — Briefing", "archive", body, root="../"))
    (out / "index.json").write_text(json.dumps([{"s": s, "n": WIKI.name[s], "c": len(WIKI.where[s])} for s in names]))
    keep |= {"index.html", "index.json"}
    for p in out.glob("*.html"):
        if p.name not in keep:
            p.unlink()
