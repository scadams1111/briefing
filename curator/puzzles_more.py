"""More daily puzzles: news quiz, groups, letter hive, cryptogram, word ladder, nonogram,
futoshiki and queens. All original, seeded by the date."""
from __future__ import annotations

import itertools
import random
import re
import string
from collections import deque
from functools import lru_cache
from pathlib import Path


@lru_cache(1)
def words() -> list[str]:
    """Common English words, most frequent first (word list: ENABLE ∩ wordfreq)."""
    return (Path(__file__).with_name("words.txt")).read_text().split()


# ── news quiz ─────────────────────────────────────────────────────────────
QUIZ_PROMPT = """Write a 5-question multiple-choice quiz on today's news briefing, for a well-read adult.
Stories:
{stories}

Return JSON: {{"questions": [{{"q": "question", "options": ["A", "B", "C", "D"], "answer": 0, "why": "one-sentence explanation"}}]}}
Rules: exactly 5 questions, each from a different story; 4 short, plausible options; "answer" is the index of the
correct option; test the substance (what happened, why it matters, a key number), not trivia like bylines; use only
facts stated in the stories above."""


def quiz(items: list[dict], llm, seed: str) -> dict | None:
    rng = random.Random("qz" + seed)
    if llm is not None and getattr(llm, "available", False) and items:
        stories = "\n".join(f"- {i['headline']} ({i['source']}): " + " ".join(
            f"{b['point']} {b.get('detail', '')}" for b in i.get("bullets", [])[:3])[:900] for i in items[:10])
        res = llm.json(QUIZ_PROMPT.format(stories=stories)) or {}
        qs = []
        for q in res.get("questions") or []:
            opts = [str(o) for o in q.get("options") or []]
            try:
                a = int(q.get("answer"))
            except Exception:
                continue
            if q.get("q") and len(opts) == 4 and 0 <= a < 4:
                qs.append({"q": str(q["q"]), "options": opts, "answer": a, "why": str(q.get("why", ""))})
        if len(qs) >= 4:
            return {"questions": qs[:5], "ai": True}
    # no AI: match headlines to publications
    srcs = sorted({i["source"] for i in items})
    if len(srcs) < 4:
        return None
    qs = []
    for it in rng.sample(items, min(5, len(items))):
        wrong = rng.sample([s for s in srcs if s != it["source"]], 3)
        opts = wrong + [it["source"]]
        rng.shuffle(opts)
        qs.append({"q": f"Which publication ran “{it['headline']}”?", "options": opts,
                   "answer": opts.index(it["source"]), "why": ""})
    return {"questions": qs, "ai": False}


# ── groups (find four groups of four) ────────────────────────────────────
GROUP_BANK = [
    ("Planets", "MARS VENUS SATURN MERCURY"), ("Chess pieces", "KING QUEEN BISHOP KNIGHT"),
    ("Shades of blue", "NAVY TEAL COBALT AZURE"), ("Card games", "BRIDGE POKER RUMMY HEARTS"),
    ("Coffee drinks", "LATTE MOCHA ESPRESSO CORTADO"), ("Trees", "OAK ELM BIRCH WILLOW"),
    ("Units of time", "SECOND MINUTE HOUR DECADE"), ("Pasta shapes", "PENNE FUSILLI ORZO RIGATONI"),
    ("Greek letters", "ALPHA DELTA SIGMA OMEGA"), ("Ballet terms", "PLIE JETE ARABESQUE PIROUETTE"),
    ("Clouds", "CIRRUS CUMULUS STRATUS NIMBUS"), ("Constellations", "ORION LYRA CYGNUS DRACO"),
    ("Poker words", "FLUSH BLUFF RAISE FOLD"), ("Tennis terms", "LOVE DEUCE ACE LET"),
    ("Things with keys", "PIANO KEYBOARD MAP LOCK"), ("Things with shells", "TURTLE SNAIL EGG TACO"),
    ("Musical tempos", "ADAGIO ALLEGRO LARGO PRESTO"), ("Bones", "FEMUR TIBIA ULNA RADIUS"),
    ("Herbs", "BASIL THYME SAGE DILL"), ("Gemstones", "RUBY EMERALD SAPPHIRE OPAL"),
    ("Dog breeds", "BEAGLE BOXER POODLE COLLIE"), ("Rivers", "NILE AMAZON DANUBE THAMES"),
    ("___ fish", "SWORD STAR CAT JELLY"), ("Fire ___", "WORKS PLACE FLY ALARM"),
    ("Sun ___", "FLOWER DIAL BURN RISE"), ("___ ball", "FOOT BASKET SNOW MEAT"),
    ("Anagrams of LISTEN", "SILENT ENLIST TINSEL INLETS"), ("Hidden animals", "SCATTER BEARD CRATER TOWEL"),
    ("Shakespeare plays", "HAMLET OTHELLO MACBETH TEMPEST"), ("Composers", "BACH MOZART HANDEL HAYDN"),
    ("Painters", "MONET DEGAS RENOIR MANET"), ("Elements", "IRON NEON ZINC GOLD"),
    ("Currencies", "EURO YEN RUPEE PESO"), ("Sailing words", "BOW STERN MAST KEEL"),
    ("Kinds of cheese", "BRIE FETA GOUDA EDAM"), ("Breads", "BAGUETTE FOCACCIA NAAN BRIOCHE"),
    ("Dances", "TANGO SALSA WALTZ RUMBA"), ("Weather words", "SLEET HAIL DRIZZLE FOG"),
    ("Moons", "TITAN EUROPA IO CALLISTO"), ("Instruments", "OBOE CELLO TUBA HARP"),
    ("Cell parts", "NUCLEUS RIBOSOME MEMBRANE VACUOLE"), ("Legal terms", "TORT LIEN WRIT BAIL"),
]

GROUPS_PROMPT = """Make a "find the four groups" word puzzle for a well-read adult.
Today's stories, for inspiration:
{stories}

Return JSON: {{"groups": [{{"name": "category", "words": ["W1","W2","W3","W4"]}}, ... 4 groups]}}
Rules: 4 groups of 4 single words (A-Z, no spaces); all 16 words different; difficulty rising from an easy group
to a tricky one (wordplay like "___ ball", hidden words or anagrams is welcome); one group may connect to today's
news; include one or two red herrings that seem to fit another group but have only one true home."""


def groups(items: list[dict], llm, seed: str) -> dict:
    rng = random.Random("gr" + seed)
    if llm is not None and getattr(llm, "available", False):
        stories = "\n".join(f"- {i['headline']}" for i in items[:10])
        res = llm.json(GROUPS_PROMPT.format(stories=stories)) or {}
        gs = []
        for g in res.get("groups") or []:
            ws = [re.sub(r"[^A-Z]", "", str(w).upper()) for w in g.get("words") or []]
            if g.get("name") and len(ws) == 4 and all(ws):
                gs.append({"name": str(g["name"]), "words": ws})
        if len(gs) == 4 and len({w for g in gs for w in g["words"]}) == 16:
            return {"groups": gs, "ai": True}
    while True:
        pick = rng.sample(GROUP_BANK, 4)
        gs = [{"name": n, "words": w.split()} for n, w in pick]
        if len({w for g in gs for w in g["words"]}) == 16:
            return {"groups": gs, "ai": False}


# ── letter hive ───────────────────────────────────────────────────────────
def hive(seed: str) -> dict:
    rng = random.Random("hv" + seed)
    ws = words()
    common = ws[:25000]
    pangrams = [w for w in common if len(set(w)) == 7 and "s" not in w]
    for _ in range(400):
        p = rng.choice(pangrams)
        letters = sorted(set(p))
        center = rng.choice(letters)
        ok = [w for w in ws[:30000] if len(w) >= 4 and center in w and set(w) <= set(letters)]
        if 18 <= len(ok) <= 55:
            outer = [c for c in letters if c != center]
            rng.shuffle(outer)
            pang = [w for w in ok if set(w) == set(letters)]
            score = lambda w: (1 if len(w) == 4 else len(w)) + (7 if w in pang else 0)
            return {"center": center.upper(), "outer": [c.upper() for c in outer],
                    "answers": sorted(w.upper() for w in ok), "pangrams": [w.upper() for w in pang],
                    "max": sum(score(w) for w in ok)}
    raise RuntimeError("no hive")


# ── cryptogram ────────────────────────────────────────────────────────────
SAYINGS = [
    "A smooth sea never made a skilled sailor.", "The best time to plant a tree was twenty years ago. The second best time is now.",
    "Measure twice and cut once.", "Still waters run deep.", "Fortune favors the prepared mind.",
    "Curiosity is the engine of achievement.", "Little strokes fell great oaks.", "Well begun is half done.",
    "Every expert was once a beginner.", "The map is not the territory.",
]


def cryptogram(items: list[dict], seed: str) -> dict:
    rng = random.Random("cg" + seed)
    lines = [i["room_line"] for i in items if 40 <= len(i.get("room_line") or "") <= 170]
    text, src = (rng.choice(lines), "From today's briefing") if lines else (rng.choice(SAYINGS), "A saying")
    text = text.strip().strip("“”\"")
    up = string.ascii_uppercase
    while True:
        perm = list(up)
        rng.shuffle(perm)
        if all(a != b for a, b in zip(up, perm)):
            break
    key = dict(zip(up, perm))
    enc = "".join(key.get(ch, ch) for ch in text.upper())
    used = [c for c in dict.fromkeys(text.upper()) if c in up]
    hints = rng.sample(used, min(2, len(used)))
    return {"cipher": enc, "plain": text.upper(), "source": src,
            "hints": {key[h]: h for h in hints}}


# ── word ladder ───────────────────────────────────────────────────────────
def ladder(seed: str) -> dict:
    rng = random.Random("ld" + seed)
    four = [w for w in words() if len(w) == 4]
    common = four[:1400]
    allset = set(four)

    def nbrs(w, pool):
        for i in range(4):
            for c in string.ascii_lowercase:
                if c != w[i]:
                    x = w[:i] + c + w[i + 1:]
                    if x in pool:
                        yield x
    pool = set(common)
    for _ in range(300):
        start = rng.choice(common)
        prev = {start: None}
        dq = deque([start])
        while dq:
            w = dq.popleft()
            for x in nbrs(w, pool):
                if x not in prev:
                    prev[x] = w
                    dq.append(x)

        def path(t):
            p = [t]
            while prev[p[-1]]:
                p.append(prev[p[-1]])
            return p[::-1]
        far = [t for t in prev if len(path(t)) in (5, 6) and sum(a != b for a, b in zip(start, t)) == 4]
        if far:
            t = rng.choice(far)
            return {"start": start.upper(), "end": t.upper(), "solution": [w.upper() for w in path(t)],
                    "valid": sorted(w.upper() for w in allset)}
    raise RuntimeError("no ladder")


# ── nonogram ──────────────────────────────────────────────────────────────
ART = {
    "a teacup": ["..........", "..#.#.#...", "...#.#....", "..........", "#########.", "#.......##",
                 "#.......#.#", "#.......##", ".#.....#..", "..#####..."],
    "a house": ["....##....", "...####...", "..######..", ".########.", "##########", ".#......#.",
                ".#.##.##.#", ".#.##.##.#", ".#....##.#", ".########."],
    "a fish": ["..........", "...####...", "..######.#", ".#.######.", "#########.", "#########.",
               ".########.", "..######.#", "...####...", ".........."],
    "a heart": ["..........", ".###..###.", "##########", "##########", "##########", ".########.",
                "..######..", "...####...", "....##....", ".........."],
    "a key": ["..........", ".###......", "#...#.....", "#...######", "#...#.#.#.", ".###..#.#.",
              "..........", "..........", "..........", ".........."],
    "an umbrella": ["....##....", "..######..", ".########.", "##########", "#..#..#..#", "....#.....",
                    "....#.....", "....#.....", "....#..#..", ".....##..."],
    "a tree": ["....##....", "...####...", "..######..", ".########.", "..######..", ".########.",
               "##########", "....##....", "....##....", "...####..."],
    "a sailboat": ["....#.....", "....##....", "....###...", "....####..", "....#####.", "....#.....",
                   "##########", ".########.", "..######..", ".........."],
    "a mushroom": ["...####...", ".########.", "##.####.##", "##########", "##########", "...#..#...",
                   "...#..#...", "...#..#...", "...####...", ".........."],
    "a cat": ["#........#", "##......##", "#.######.#", "#........#", "#.#....#.#", "#........#",
              "#...##...#", ".#......#.", "..######..", ".........."],
    "a star": ["....##....", "....##....", "...####...", "##########", ".########.", "..######..",
               "..######..", ".###..###.", ".##....##.", "#........#"],
    "an anchor": ["....##....", "...#..#...", "....##....", "..######..", "....##....", "....##....",
                  "#...##...#", "##..##..##", ".########.", "...####..."],
}


def _clue(line):
    return [len(m) for m in re.findall(r"#+", "".join("#" if x else "." for x in line))] or [0]


def _line_options(clue, n):
    if clue == [0]:
        return [[0] * n]
    out = []

    def rec(i, pos, acc):
        if i == len(clue):
            out.append(acc + [0] * (n - len(acc)))
            return
        rest = sum(clue[i + 1:]) + len(clue) - i - 1
        for s in range(pos, n - rest - clue[i] + 1):
            rec(i + 1, s + clue[i] + 1, acc + [0] * (s - len(acc)) + [1] * clue[i] + ([0] if i < len(clue) - 1 else []))
    rec(0, 0, [])
    return [o[:n] for o in out]


def _nono_solve(rows, cols, known):
    R, C = len(rows), len(cols)
    g = [[known.get((r, c), -1) for c in range(C)] for r in range(R)]
    ro = [_line_options(cl, C) for cl in rows]
    co = [_line_options(cl, R) for cl in cols]
    changed = True
    while changed:
        changed = False
        for r in range(R):
            ro[r] = [o for o in ro[r] if all(g[r][c] in (-1, o[c]) for c in range(C))]
            for c in range(C):
                vals = {o[c] for o in ro[r]}
                if len(vals) == 1 and g[r][c] == -1:
                    g[r][c] = vals.pop(); changed = True
        for c in range(C):
            co[c] = [o for o in co[c] if all(g[r][c] in (-1, o[r]) for r in range(R))]
            for r in range(R):
                vals = {o[r] for o in co[c]}
                if len(vals) == 1 and g[r][c] == -1:
                    g[r][c] = vals.pop(); changed = True
    return g


def nonogram(seed: str) -> dict:
    rng = random.Random("ng" + seed)
    name = rng.choice(sorted(ART))
    art = [row.ljust(10, ".")[:10] for row in ART[name]]
    sol = [[1 if ch == "#" else 0 for ch in row] for row in art]
    rows = [_clue(r) for r in sol]
    cols = [_clue([sol[r][c] for r in range(10)]) for c in range(10)]
    known = {}
    while True:
        g = _nono_solve(rows, cols, known)
        unk = [(r, c) for r in range(10) for c in range(10) if g[r][c] == -1]
        if not unk:
            break
        r, c = rng.choice(unk)
        known[(r, c)] = sol[r][c]
    return {"rows": rows, "cols": cols, "solution": ["".join(map(str, r)) for r in sol], "picture": name,
            "givens": [[r, c, v] for (r, c), v in known.items()]}


# ── futoshiki ─────────────────────────────────────────────────────────────
def _latin(n, rng):
    base = list(range(1, n + 1))
    rows = [base[i:] + base[:i] for i in range(n)]
    rng.shuffle(rows)
    cols = list(range(n))
    rng.shuffle(cols)
    sym = base[:]
    rng.shuffle(sym)
    return [[sym[r[c] - 1] for c in cols] for r in rows]


def _futo_count(n, givens, ineq, limit=2):
    g = [[givens.get((r, c), 0) for c in range(n)] for r in range(n)]
    cells = [(r, c) for r in range(n) for c in range(n) if not g[r][c]]
    cons = {}
    for (a, b) in ineq:  # value(a) < value(b)
        cons.setdefault(a, []).append((b, 1))
        cons.setdefault(b, []).append((a, -1))

    def ok(r, c, v):
        if v in g[r] or any(g[i][c] == v for i in range(n)):
            return False
        for (q, s) in cons.get((r, c), []):
            w = g[q[0]][q[1]]
            if w and ((s == 1 and not v < w) or (s == -1 and not v > w)):
                return False
        return True
    cnt = 0

    def rec(i):
        nonlocal cnt
        if i == len(cells):
            cnt += 1
            return
        r, c = cells[i]
        for v in range(1, n + 1):
            if ok(r, c, v):
                g[r][c] = v
                rec(i + 1)
                g[r][c] = 0
                if cnt >= limit:
                    return
    rec(0)
    return cnt


def futoshiki(seed: str, n: int = 5) -> dict:
    rng = random.Random("ft" + seed)
    sol = _latin(n, rng)
    pairs = [((r, c), (r, c + 1)) for r in range(n) for c in range(n - 1)] + \
            [((r, c), (r + 1, c)) for r in range(n - 1) for c in range(n)]
    rng.shuffle(pairs)
    ineq = []
    for a, b in pairs[: n * 2]:
        ineq.append((a, b) if sol[a[0]][a[1]] < sol[b[0]][b[1]] else (b, a))
    givens = {}
    cells = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(cells)
    extra = iter(pairs[n * 2:])
    while _futo_count(n, givens, ineq) != 1:
        nxt = next(extra, None)
        if nxt and rng.random() < .6:
            a, b = nxt
            ineq.append((a, b) if sol[a[0]][a[1]] < sol[b[0]][b[1]] else (b, a))
        else:
            r, c = cells.pop()
            givens[(r, c)] = sol[r][c]
    for k in list(givens):  # remove givens that aren't needed
        v = givens.pop(k)
        if _futo_count(n, givens, ineq) != 1:
            givens[k] = v
    return {"n": n, "givens": [[r, c, v] for (r, c), v in givens.items()],
            "less": [[a[0], a[1], b[0], b[1]] for a, b in ineq], "solution": ["".join(map(str, r)) for r in sol]}


# ── queens ────────────────────────────────────────────────────────────────
def _queens_count(n, reg, limit=2):
    cnt = 0
    cols, regs = set(), set()

    def rec(r, prev):
        nonlocal cnt
        if r == n:
            cnt += 1
            return
        for c in range(n):
            if c in cols or reg[r][c] in regs or (prev is not None and abs(prev - c) <= 1):
                continue
            cols.add(c); regs.add(reg[r][c])
            rec(r + 1, c)
            cols.discard(c); regs.discard(reg[r][c])
            if cnt >= limit:
                return
    rec(0, None)
    return cnt


def queens(seed: str, n: int = 8) -> dict:
    rng = random.Random("qn" + seed)
    for _ in range(4000):
        while True:
            p = list(range(n))
            rng.shuffle(p)
            if all(abs(p[i] - p[i + 1]) > 1 for i in range(n - 1)):
                break
        reg = [[-1] * n for _ in range(n)]
        for r in range(n):
            reg[r][p[r]] = r
        front = [(r, p[r]) for r in range(n)]
        filled = n
        while filled < n * n:
            r, c = rng.choice(front)
            nb = [(r + a, c + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))
                  if 0 <= r + a < n and 0 <= c + b < n and reg[r + a][c + b] < 0]
            if not nb:
                front.remove((r, c))
                continue
            q = rng.choice(nb)
            reg[q[0]][q[1]] = reg[r][c]
            front.append(q)
            filled += 1
        if _queens_count(n, reg) == 1:
            return {"n": n, "regions": reg, "solution": p}
    raise RuntimeError("no queens")


def build_more(date: str, items: list[dict], llm=None) -> dict:
    out = {}
    for k, fn in (("quiz", lambda: quiz(items, llm, date)), ("groups", lambda: groups(items, llm, date)),
                  ("hive", lambda: hive(date)), ("cryptogram", lambda: cryptogram(items, date)),
                  ("ladder", lambda: ladder(date)), ("nonogram", lambda: nonogram(date)),
                  ("futoshiki", lambda: futoshiki(date)), ("queens", lambda: queens(date))):
        try:
            v = fn()
            if v:
                out[k] = v
        except Exception as ex:  # one puzzle failing never takes down the rest
            import logging
            logging.getLogger(__name__).warning("%s failed: %s", k, ex)
    return out
