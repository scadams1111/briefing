import logging
import sys

from .main import daily, find_url, save

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

if len(sys.argv) < 2 or sys.argv[1] not in ("daily", "save"):
    sys.exit("usage: python -m curator daily | save <url or text containing a url>")

if sys.argv[1] == "daily":
    daily()
else:
    url = find_url(" ".join(sys.argv[2:]))
    if not url:
        sys.exit("no URL found")
    save(url)
