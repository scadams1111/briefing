import logging
import sys

from .main import daily, find_url, rerender, retry, save, search

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

if len(sys.argv) < 2 or sys.argv[1] not in ("daily", "retry", "render", "save", "search"):
    sys.exit("usage: python -m curator daily | retry | render | save <url> | search <words> <url or text containing a url>")

if sys.argv[1] == "daily":
    daily()
elif sys.argv[1] == "search":
    q = " ".join(sys.argv[2:]).strip()
    if q.lower().startswith("search:"):
        q = q[7:].strip()
    if not q:
        sys.exit("no search words")
    search(q)
elif sys.argv[1] == "render":
    rerender()
elif sys.argv[1] == "retry":
    retry()
else:
    url = find_url(" ".join(sys.argv[2:]))
    if not url:
        sys.exit("no URL found")
    save(url)
