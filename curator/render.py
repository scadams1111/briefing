"""Write the outputs: web pages, RSS feeds (for KOReader), EPUB + OPDS catalog."""
from __future__ import annotations

import datetime as dt
import html
import os
from email.utils import format_datetime
from pathlib import Path

from ebooklib import epub

DOCS = Path("docs")
e = html.escape

CSS = """
body{font-family:Georgia,'Times New Roman',serif;max-width:40em;margin:0 auto;padding:1em 1.1em 3em;line-height:1.5;color:#111;background:#fff}
h1{font-size:1.6em;margin:.2em 0}
h2{font-size:1.2em;margin:.2em 0 .3em}
h3.section{margin-top:2em;border-bottom:2px solid #111;padding-bottom:.2em;text-transform:uppercase;letter-spacing:.06em;font-size:.95em}
a{color:#111}
.meta{font-size:.8em;text-transform:uppercase;letter-spacing:.05em;color:#555;margin:0}
.room{font-style:italic;margin:.3em 0 .6em}
.why{font-size:.9em;color:#444}
article{border-top:1px solid #bbb;padding:1em 0}
ol{padding-left:1.3em}
li{margin:.45em 0}
summary{cursor:pointer}
details p{margin:.4em 0 .8em;font-size:.95em}
nav{font-size:.9em;margin-bottom:1em}
.back{font-size:.85em}
"""


# ── web (see web.py for the design) ────────────────────────────────
def web(cfg: dict, date: str, picks: list[dict], saved: list[dict], archive_dates: list[str],
        subs: list[dict] | None = None) -> None:
    from . import web as w
    w.write_all(cfg, date, picks, saved, archive_dates, subs or [])


def saved_page(cfg: dict, saved: list[dict]) -> None:
    from . import web as w
    w.write_saved(saved)


# ── RSS (KOReader News Downloader) ─────────────────────────────────
def _rss(title: str, link: str, items: list[tuple[dict, str]]) -> str:
    now = format_datetime(dt.datetime.now(dt.timezone.utc))
    xs = []
    for it, content in items:
        when = it.get("saved_at") or it.get("date")
        pub = format_datetime(dt.datetime.fromisoformat(when).replace(tzinfo=dt.timezone.utc)) if when else now
        xs.append(f"<item><title>{e(it['headline'])}</title><link>{e(it['url'])}</link>"
                  f"<guid isPermaLink='false'>{e(it['id'])}</guid><pubDate>{pub}</pubDate>"
                  f"<description><![CDATA[{content}]]></description></item>")
    return (f"<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel><title>{e(title)}</title>"
            f"<link>{e(link)}</link><description>{e(title)}</description><lastBuildDate>{now}</lastBuildDate>"
            + "".join(xs) + "</channel></rss>")


def _brief_body(it: dict) -> str:
    s = f"<p><i>{e(it.get('topic_name', ''))} · {e(it['source'])} · {it['minutes']} min</i></p>"
    if it.get("room_line"):
        s += f"<p><i>“{e(it['room_line'])}”</i></p>"
    s += "<ol>" + "".join(f"<li><b>{e(b['point'])}</b></li>" for b in it["bullets"]) + "</ol><hr/>"
    for n, b in enumerate(it["bullets"], 1):
        s += f"<h3>{n}. {e(b['point'])}</h3><p>{e(b.get('detail', ''))}</p>"
    return s + f"<p>Original: {e(it['url'])}</p>"


def _sub_body(it: dict) -> str:
    return (f"<p><i>{e(it['source'])} · {e(it.get('topic_name', ''))} · subscriber article</i></p>"
            f"<p>{e(it.get('takeaway', ''))}</p><p>Read it on the publisher's site: {e(it['url'])}</p>")


def feeds(cfg: dict, site: str, picks: list[dict], saved: list[dict], subs: list[dict] | None = None) -> None:
    recent_saved = saved[:20]
    # 1) the briefing itself: bullets + expansions (KOReader: download_full_article = false)
    (DOCS / "briefing.xml").write_text(_rss(cfg["site_title"], site,
                                            [(i, _brief_body(i)) for i in picks + recent_saved]
                                            + [(i, _sub_body(i)) for i in subs or []]))
    # 2) plain links so KOReader fetches the full originals itself (download_full_article = true)
    (DOCS / "articles.xml").write_text(_rss(cfg["site_title"] + " — full articles", site,
                                            [(i, e(i.get("room_line") or i["headline"])) for i in picks + recent_saved]))


# ── EPUB + OPDS ────────────────────────────────────────────────────
def _x(title: str, fname: str, body: str, css) -> epub.EpubHtml:
    ch = epub.EpubHtml(title=title, file_name=fname, lang="en")
    ch.content = f"<html><head><title>{e(title)}</title></head><body>{body}</body></html>"
    ch.add_item(css)
    return ch


def build_epub(cfg: dict, date: str, picks: list[dict], saved: list[dict], subs: list[dict] | None = None) -> Path:
    nice = dt.date.fromisoformat(date).strftime("%a %b %-d")
    book = epub.EpubBook()
    book.set_identifier(f"briefing-{date}")
    book.set_title(f"Briefing — {nice}")
    book.set_language("en")
    book.add_author(cfg["site_title"])
    css = epub.EpubItem(uid="css", file_name="style.css", media_type="text/css", content=CSS)
    book.add_item(css)

    allitems = [("Today", picks), ("Saved for later", saved)]
    chapters, contents = [], f"<h1>Briefing</h1><p class='meta'>{nice}</p>"
    n = 0
    for section, items in allitems:
        if not items:
            continue
        contents += f"<h3 class='section'>{e(section)}</h3>"
        for it in items:
            n += 1
            f = f"a{n:02d}.xhtml"
            # contents: headline + the 3 points, each linking to its expansion
            pts = "".join(f"<li><a href='{f}#b{k}'>{e(b['point'])}</a></li>" for k, b in enumerate(it["bullets"], 1))
            contents += (f"<p class='meta'>{e(it.get('topic_name', ''))} · {e(it['source'])}</p>"
                         f"<h2><a href='{f}'>{e(it['headline'])}</a></h2><ol>{pts}</ol>")
            body = (f"<p class='meta'>{e(it.get('topic_name', ''))} · {e(it['source'])} · {it['minutes']} min</p>"
                    f"<h1>{e(it['headline'])}</h1>")
            if it.get("room_line"):
                body += f"<p class='room'>“{e(it['room_line'])}”</p>"
            for k, b in enumerate(it["bullets"], 1):
                body += (f"<h2 id='b{k}'>{k}. {e(b['point'])}</h2><p>{e(b.get('detail', ''))}</p>")
            if it.get("why_for_you"):
                body += f"<p class='why'>Why for you: {e(it['why_for_you'])}</p>"
            body += (f"<p class='back'>Full article: {e(it['url'])}</p>"
                     f"<p class='back'><a href='contents.xhtml'>↩ Back to contents</a></p>")
            chapters.append(_x(it["headline"], f, body, css))
    if subs:
        contents += "<h3 class='section'>From your subscriptions</h3>"
        for it in subs:
            contents += (f"<p class='meta'>{e(it['source'])} · {e(it.get('topic_name', ''))}</p>"
                         f"<h2>{e(it['headline'])}</h2><p>{e(it.get('takeaway', ''))}</p>"
                         f"<p class='back'>Read on your phone: {e(it['url'])}</p>")
    toc_ch = _x("Contents", "contents.xhtml", contents, css)
    for ch in [toc_ch, *chapters]:
        book.add_item(ch)
    book.toc = [epub.Link("contents.xhtml", "Contents", "contents"), *chapters]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = [toc_ch, *chapters]

    out = DOCS / "epub"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"briefing-{date}.epub"
    epub.write_epub(str(path), book)
    (out / "latest.epub").write_bytes(path.read_bytes())
    return path


def opds(cfg: dict, site: str) -> None:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = ""
    for p in sorted((DOCS / "epub").glob("briefing-*.epub"), reverse=True):
        d = p.stem.removeprefix("briefing-")
        entries += (f"<entry><title>Briefing — {d}</title><id>urn:briefing:{d}</id><updated>{d}T12:00:00Z</updated>"
                    f"<link rel='http://opds-spec.org/acquisition' href='{site}/epub/{p.name}' type='application/epub+zip'/></entry>")
    (DOCS / "opds.xml").write_text(
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<feed xmlns='http://www.w3.org/2005/Atom' xmlns:opds='http://opds-spec.org/2010/catalog'>"
        f"<id>urn:briefing:catalog</id><title>{e(cfg['site_title'])}</title><updated>{now}</updated>"
        f"<link rel='self' href='{site}/opds.xml' type='application/atom+xml;profile=opds-catalog;kind=acquisition'/>"
        f"{entries}</feed>")


def site_url(cfg: dict) -> str:
    if cfg.get("site_url"):
        return cfg["site_url"].rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner.lower()}.github.io/{name}"
    return "http://localhost:8000"
