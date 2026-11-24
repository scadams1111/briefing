import logging
import sys

from .main import daily, find_url, retry, save

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

if len(sys.argv) < 2 or sys.argv[1] not in ("daily", "retry", "save"):
    sys.exit("usage: python -m curator daily | retry | save <url or text containing a url>")

if sys.argv[1] == "daily":
    daily()
elif sys.argv[1] == "retry":
    retry()
else:
    url = find_url(" ".join(sys.argv[2:]))
    if not url:
        sys.exit("no URL found")
    save(url)
