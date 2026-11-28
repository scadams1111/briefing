"""Original daily puzzles, generated fresh each day (seeded by the date so re-runs match).

- crossword:  a criss-cross crossword; words come from the day's stories when the AI is
              available, otherwise from a built-in word bank.
- whodunit:   a logic-grid mystery (who, with what, where) with a unique solution.
- murdermap:  place everyone on a floor plan, one per row and column; the murderer is
              the only person alone in a room with the victim.
- sudoku:     classic 9x9, easier early in the week and harder at the weekend.
"""
from __future__ import annotations

import itertools
import random
import re

# ── crossword ─────────────────────────────────────────────────────────────
BANK = [
    ("ORBIT", "Path around a planet"), ("TIDE", "It comes in twice a day"), ("ECHO", "Sound that comes back"),
    ("ATLAS", "Book of maps"), ("OPERA", "Drama that's sung"), ("ANVIL", "Blacksmith's block"),
    ("GLACIER", "Slow river of ice"), ("NECTAR", "What bees are after"), ("ISLAND", "Land with water all around"),
    ("CANVAS", "Painter's surface"), ("VOLCANO", "Mountain that may erupt"), ("MAGNET", "It attracts iron"),
    ("ORCHID", "Elegant flower with many species"), ("PRISM", "It splits white light"), ("LANTERN", "Portable light"),
    ("HARBOR", "Safe place for ships"), ("COMPASS", "It points north"), ("RIDDLE", "Puzzle in words"),
    ("SONNET", "Fourteen-line poem"), ("CACTUS", "Desert plant with spines"), ("PEPPER", "Salt's partner"),
    ("BALLOT", "Vote on paper"), ("TREATY", "Agreement between nations"), ("CENSUS", "Official count of people"),
    ("ENZYME", "Protein that speeds a reaction"), ("GENOME", "An organism's full set of DNA"),
    ("NEURON", "Nerve cell"), ("VACCINE", "Shot that trains immunity"), ("PROTON", "Positive particle"),
    ("COMET", "Icy visitor with a tail"), ("NEBULA", "Cloud where stars are born"), ("QUARTZ", "Common crystal"),
    ("FOSSIL", "Ancient trace in rock"), ("DELTA", "Where a river fans out"), ("CANYON", "Deep gorge"),
    ("TUNDRA", "Treeless arctic plain"), ("MONSOON", "Seasonal rains"), ("OASIS", "Desert water source"),
    ("FALCON", "Fast bird of prey"), ("OTTER", "Playful river swimmer"), ("BEAVER", "Dam builder"),
    ("HERON", "Long-legged wading bird"), ("WALRUS", "Tusked sea mammal"), ("GECKO", "Lizard that walks up walls"),
    ("MAPLE", "Tree behind a famous syrup"), ("CEDAR", "Fragrant wood for chests"), ("ACORN", "Oak's seed"),
    ("BASIL", "Herb in pesto"), ("SAFFRON", "Costly spice from crocuses"), ("GINGER", "Spicy root"),
    ("WALNUT", "Nut with a brain-like look"), ("YEAST", "It makes bread rise"), ("BAGEL", "Boiled ring of bread"),
    ("CELLO", "Big string instrument played seated"), ("TEMPO", "Speed of a piece of music"),
    ("CHORUS", "Part everyone sings"), ("BALLET", "Dance on pointe"), ("SCRIPT", "Actors' text"),
    ("SEQUEL", "Part two"), ("MURAL", "Painting on a wall"), ("STATUE", "Sculpted figure"),
    ("ARCHIVE", "Collection of old records"), ("LEDGER", "Book of accounts"), ("AUDIT", "Check of the books"),
    ("MARGIN", "Space at a page's edge"), ("INDEX", "List at the back of a book"), ("FOOTNOTE", "Note at the bottom"),
    ("SENATE", "Upper chamber"), ("VETO", "Executive no"), ("QUORUM", "Enough members to vote"),
    ("TARIFF", "Tax on imports"), ("BUDGET", "Plan for spending"), ("ROBOT", "Machine that does tasks"),
    ("PIXEL", "Dot on a screen"), ("CIPHER", "Secret code"), ("SERVER", "Computer that hosts sites"),
    ("BATTERY", "It stores charge"), ("ROCKET", "It goes to space"), ("SATELLITE", "Moon, or man-made orbiter"),
    ("ANCHOR", "It keeps a ship in place"), ("PADDLE", "Canoe tool"), ("SUMMIT", "Mountain top"),
    ("TRAIL", "Hiking path"), ("CAMPFIRE", "Where s'mores happen"), ("KAYAK", "Narrow boat with a double paddle"),
    ("RELAY", "Race with a baton"), ("MARATHON", "Race of about 26 miles"), ("TROPHY", "Winner's cup"),
    ("PUZZLE", "Thing to solve"), ("CLUE", "Hint for a solver"), ("ALIBI", "Proof you were elsewhere"),
    ("MOTIVE", "Reason for a crime"), ("WITNESS", "Person who saw it"), ("VERDICT", "Jury's decision"),
    ("HAMMOCK", "Swinging bed"), ("PILLOW", "Bed rest for your head"), ("KETTLE", "It whistles when boiling"),
    ("TEAPOT", "Spouted vessel"), ("LADDER", "Climbing frame"), ("WINDOW", "Pane in a wall"),
    ("ISOTOPE", "Same element, different neutrons"), ("CATALYST", "Something that speeds change"),
    ("HABITAT", "Natural home"), ("MIGRATE", "Move with the seasons"), ("POLLEN", "Flower dust"),
    ("CORAL", "Reef builder"), ("PLANKTON", "Drifting ocean life"), ("TSUNAMI", "Giant sea wave"),
]

WORD_RE = re.compile(r"^[A-Z]{3,10}$")


def _try_layout(words: list[tuple[str, str]], rng: random.Random, max_size: int = 13):
    grid: dict[tuple[int, int], str] = {}
    placed = []

    def fits(w, r, c, d):
        dr, dc = (0, 1) if d == "A" else (1, 0)
        cross = 0
        if grid.get((r - dr, c - dc)) or grid.get((r + dr * len(w), c + dc * len(w))):
            return -1
        for i, ch in enumerate(w):
            rr, cc = r + dr * i, c + dc * i
            g = grid.get((rr, cc))
            if g:
                if g != ch:
                    return -1
                cross += 1
            else:  # a new letter must not touch other letters sideways
                if grid.get((rr + dc, cc + dr)) or grid.get((rr - dc, cc - dr)):
                    return -1
        if cross == len(w):
            return -1
        cells = list(grid) + [(r + dr * i, c + dc * i) for i in range(len(w))]
        rs, cs = [x for x, _ in cells], [y for _, y in cells]
        if max(rs) - min(rs) >= max_size or max(cs) - min(cs) >= max_size:
            return -1
        return cross

    def put(w, r, c, d, clue):
        dr, dc = (0, 1) if d == "A" else (1, 0)
        for i, ch in enumerate(w):
            grid[(r + dr * i, c + dc * i)] = ch
        placed.append({"answer": w, "clue": clue, "r": r, "c": c, "d": d})

    first, *rest = words
    put(first[0], 0, 0, "A", first[1])
    for _ in range(2):  # second pass picks up words that didn't fit early on
        for w, clue in list(rest):
            best = None
            for (r0, c0), ch in list(grid.items()):
                for i, wc in enumerate(w):
                    if wc != ch:
                        continue
                    for d in "AD":
                        r, c = (r0, c0 - i) if d == "A" else (r0 - i, c0)
                        x = fits(w, r, c, d)
                        if x > 0:
                            key = (x, rng.random())
                            if best is None or key > best[0]:
                                best = (key, r, c, d)
            if best:
                put(w, best[1], best[2], best[3], clue)
                rest.remove((w, clue))
    return grid, placed


def crossword(words: list[tuple[str, str]], seed: str, theme: str = "", extra: list | None = None) -> dict:
    rng = random.Random("xw" + seed)
    main_n = len(words)
    words = [(w.upper(), c) for w, c in list(words) + list(extra or []) if WORD_RE.match(w.upper())]
    seen, uniq = set(), []
    for w, c in words:
        if w not in seen:
            seen.add(w)
            uniq.append((w, c))
    best = None
    for _ in range(60):
        a, b = uniq[:main_n], uniq[main_n:]
        rng.shuffle(a)
        rng.shuffle(b)
        pool = sorted((a + b)[:16], key=lambda x: -len(x[0]) + rng.random() * 3)
        grid, placed = _try_layout(pool, rng)
        rs, cs = [r for r, _ in grid], [c for _, c in grid]
        area = (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)
        crosses = sum(len(p["answer"]) for p in placed) - len(grid)
        score = (min(len(placed), 12), crosses, -area)
        if best is None or score > best[0]:
            best = (score, grid, placed)
    _, grid, placed = best
    placed = placed[:14]
    r0, c0 = min(r for r, _ in grid), min(c for _, c in grid)
    for p in placed:
        p["r"] -= r0
        p["c"] -= c0
    rows = max(p["r"] + (len(p["answer"]) if p["d"] == "D" else 1) for p in placed)
    cols = max(p["c"] + (len(p["answer"]) if p["d"] == "A" else 1) for p in placed)
    sol = [["" for _ in range(cols)] for _ in range(rows)]
    for p in placed:
        for i, ch in enumerate(p["answer"]):
            r, c = (p["r"], p["c"] + i) if p["d"] == "A" else (p["r"] + i, p["c"])
            sol[r][c] = ch
    starts = sorted({(p["r"], p["c"]) for p in placed})
    num = {s: k for k, s in enumerate(starts, 1)}
    for p in placed:
        p["n"] = num[(p["r"], p["c"])]
    placed.sort(key=lambda p: (p["d"], p["n"]))
    return {"rows": rows, "cols": cols, "solution": ["".join(ch or "." for ch in row) for row in sol],
            "entries": placed, "theme": theme}


CROSSWORD_PROMPT = """You are writing a small daily crossword for a well-read adult, themed on today's news briefing.
Today's stories:
{stories}

Return JSON: {{"theme": "a 2-5 word title", "words": [{{"answer": "WORD", "clue": "clue"}}, ... 16 items]}}
Rules:
- answers: single common English words or well-known proper nouns, 3-10 letters, A-Z only (no spaces, hyphens or digits)
- about half the answers should connect to today's stories; the rest can be general vocabulary
- clues: classic crossword style, under 12 words, fair and gettable, never containing the answer or its root
- vary lengths; include several 4-6 letter words so the grid interlocks well
"""


def crossword_words(items: list[dict], llm) -> tuple[list[tuple[str, str]], str]:
    if llm is not None and getattr(llm, "available", False):
        stories = "\n".join(f"- {i['headline']}: " + "; ".join(b['point'] for b in i.get('bullets', [])[:2])
                            for i in items[:10])
        res = llm.json(CROSSWORD_PROMPT.format(stories=stories)) or {}
        out = []
        for x in res.get("words") or []:
            a = re.sub(r"[^A-Z]", "", str(x.get("answer", "")).upper())
            clue = str(x.get("clue", "")).strip()
            if WORD_RE.match(a) and clue and a.lower() not in clue.lower():
                out.append((a, clue))
        if len(out) >= 9:
            return out, str(res.get("theme") or "Today's news")[:40]
    return [], ""


# ── whodunit (logic grid) ─────────────────────────────────────────────────
SUSPECTS = [
    ("Ada Finch", "a nervous botanist"), ("Basil Rook", "the family solicitor"), ("Cora Vane", "a retired opera singer"),
    ("Desmond Pike", "the groundskeeper"), ("Edith Marsh", "a rival novelist"), ("Felix Orme", "the nephew with debts"),
    ("Greta Holm", "the cook"), ("Hugo Starling", "a visiting astronomer"), ("Iris Quell", "the private secretary"),
    ("Jasper Lowe", "a chess champion"), ("Klara Wynn", "the chauffeur"), ("Leo Tamsin", "the butler"),
    ("Mabel Croft", "a vicar's widow"), ("Nils Barrow", "an art dealer"), ("Opal Reyes", "a famous chemist"),
    ("Percy Dunmore", "an aging war correspondent"),
]
VICTIMS = ["Lord Ambrose Pell", "Dame Winifred Crane", "Professor Otto Brack", "Madame Celeste Varga",
           "Sir Reginald Thorn", "Baroness Ida Lusk", "Captain Silas Merrow", "Countess Vera Lindqvist"]
WEAPONS = ["letter opener", "poisoned teacup", "fireplace poker", "garden shears", "silk scarf", "bronze bust",
           "cricket bat", "hatpin", "vial of arsenic", "heavy atlas", "walking cane", "champagne bottle"]
PLACES = ["observatory", "boathouse", "wine cellar", "chapel", "greenhouse", "gallery", "attic", "music room",
          "orangery", "gun room"]


def whodunit(seed: str, size: int = 3) -> dict:
    rng = random.Random("wd" + seed)
    sus = rng.sample(SUSPECTS, size)
    wea = rng.sample(WEAPONS, size)
    pla = rng.sample(PLACES, size)
    sw = list(range(size)); rng.shuffle(sw)
    sl = list(range(size)); rng.shuffle(sl)
    cands = [(a, b) for a in itertools.permutations(range(size)) for b in itertools.permutations(range(size))]

    def truth(f, a, b):
        k, x, y, pos = f
        if k == "SW":
            v = a[x] == y
        elif k == "SL":
            v = b[x] == y
        else:  # WL: whoever had weapon x was in place y
            v = b[a.index(x)] == y
        return v == pos

    facts = []
    for s in range(size):
        for j in range(size):
            facts.append(("SW", s, j, sw[s] == j))
            facts.append(("SL", s, j, sl[s] == j))
            facts.append(("WL", s, j, sl[sw.index(s)] == j))
    rng.shuffle(facts)
    facts.sort(key=lambda f: f[3] and rng.random() < .7)  # favour "not" clues; they make it a puzzle
    chosen, live = [], cands
    for f in facts:
        nxt = [c for c in live if truth(f, *c)]
        if len(nxt) < len(live):
            chosen.append(f)
            live = nxt
        if len(live) == 1:
            break
    for f in chosen[:]:  # drop clues that turned out to be unnecessary
        rest = [g for g in chosen if g is not f]
        if sum(all(truth(g, *c) for g in rest) for c in cands) == 1:
            chosen = rest
    crime = rng.randrange(size)
    killer = sl.index(crime)
    name = lambda s: sus[s][0]

    def text(f):
        k, x, y, pos = f
        if k == "SW":
            return rng.choice([f"{name(x)} had the {wea[y]}.", f"The {wea[y]} was in {name(x)}'s hands."]) if pos else \
                rng.choice([f"{name(x)} never touched the {wea[y]}.", f"{name(x)} did not have the {wea[y]}."])
        if k == "SL":
            return rng.choice([f"{name(x)} spent the evening in the {pla[y]}.", f"{name(x)} was in the {pla[y]}."]) if pos else \
                rng.choice([f"{name(x)} was never in the {pla[y]}.", f"Nobody saw {name(x)} in the {pla[y]}."])
        return f"The {wea[x]} turned up in the {pla[y]}." if pos else f"The {wea[x]} was not in the {pla[y]}."

    victim = rng.choice(VICTIMS)
    return {"size": size, "victim": victim,
            "suspects": [{"name": n, "about": a} for n, a in sus], "weapons": wea, "places": pla,
            "clues": [text(f) for f in chosen], "crime_place": crime,
            "intro": f"{victim} has been found dead in the {pla[crime]}. Each suspect had one weapon and was in one place; "
                     f"no two shared either. Work out who had what, and where, then name the killer.",
            "solution": {"weapon": sw, "place": sl, "killer": killer}}


# ── murder map (place everyone on the floor plan) ────────────────────────
ROOMS = ["Kitchen", "Library", "Parlor", "Study", "Hall", "Garden"]


def _regions(rng, n, k):
    while True:
        owner = {}
        seeds = rng.sample([(r, c) for r in range(n) for c in range(n)], k)
        for i, s in enumerate(seeds):
            owner[s] = i
        while len(owner) < n * n:
            r, c = rng.choice(list(owner))
            nb = [(r + dr, c + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            nb = [p for p in nb if 0 <= p[0] < n and 0 <= p[1] < n and p not in owner]
            if nb:
                owner[rng.choice(nb)] = owner[(r, c)]
        sizes = [list(owner.values()).count(i) for i in range(k)]
        if min(sizes) >= 3:
            return [[owner[(r, c)] for c in range(n)] for r in range(n)]


def murdermap(seed: str, n: int = 5) -> dict:
    rng = random.Random("mm" + seed)
    for _attempt in range(200):
        k = rng.choice([4, 4, 5])
        room = _regions(rng, n, k)
        cells = [(r, c) for r in range(n) for c in range(n)]
        furn = {}
        for p in rng.sample(cells, rng.randint(3, 5)):
            furn[p] = rng.choice(["table", "plant"])
        for p in rng.sample([x for x in cells if x not in furn], 2):
            furn[p] = "rug"
        blocked = {p for p, t in furn.items() if t != "rug"}
        perms = [p for p in itertools.permutations(range(n)) if all((r, p[r]) not in blocked for r in range(n))]
        if len(perms) < 6:
            continue
        cast = rng.sample(SUSPECTS, n - 1)
        while len({s[0][0] for s in cast}) < n - 1:
            cast = rng.sample(SUSPECTS, n - 1)
        victim = rng.choice([v for v in VICTIMS if v.split()[-1][0] not in {s[0][0] for s in cast}] or VICTIMS)
        people = [c[0] for c in cast] + [victim]   # index n-1 is the victim
        V = n - 1

        def rule_ok(pos):  # victim shares a room with exactly one person
            vr = room[pos[V][0]][pos[V][1]]
            return sum(room[pos[i][0]][pos[i][1]] == vr for i in range(n) if i != V) == 1

        configs = []
        for p in perms:
            for order in itertools.permutations(range(n)):  # order[row] = person
                pos = [None] * n
                for r, who in enumerate(order):
                    pos[who] = (r, p[r])
                if rule_ok(pos):
                    configs.append(tuple(pos))
        if len(configs) < 2:
            continue
        sol = rng.choice(configs)
        rm = lambda q: room[q[0]][q[1]]

        def near(q, kind):
            return any(furn.get((q[0] + dr, q[1] + dc)) == kind for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))

        facts = []
        for i in range(n):
            q = sol[i]
            facts += [("room", i, rm(q), True)]
            facts += [("room", i, j, False) for j in range(k) if j != rm(q)]
            facts += [("row", i, q[0], True), ("col", i, q[1], True)]
            for kind in ("plant", "table"):
                if any(t == kind for t in furn.values()):
                    facts.append(("near", i, kind, near(q, kind)))
            if "rug" in furn.values():
                facts.append(("rug", i, None, furn.get(q) == "rug"))
        rng.shuffle(facts)
        facts.sort(key=lambda f: {"room": 0, "near": 0, "rug": 1, "row": 2, "col": 2}[f[0]] + rng.random() * 1.6)

        def ok(f, pos):
            kd, i, v, t = f
            q = pos[i]
            if kd == "room":
                x = rm(q) == v
            elif kd == "row":
                x = q[0] == v
            elif kd == "col":
                x = q[1] == v
            elif kd == "near":
                x = near(q, v)
            else:
                x = furn.get(q) == "rug"
            return x == t

        chosen, live = [], configs
        for f in facts:
            nxt = [c for c in live if ok(f, c)]
            if len(nxt) < len(live):
                chosen.append(f)
                live = nxt
            if len(live) == 1:
                break
        if len(live) != 1:
            continue
        for f in chosen[:]:
            rest = [g for g in chosen if g is not f]
            if sum(all(ok(g, c) for g in rest) for c in configs) == 1:
                chosen = rest
        if len(chosen) > 9:
            continue
        names = rng.sample(ROOMS, k)
        ordn = ["first", "second", "third", "fourth", "fifth", "sixth"]

        def text(f):
            kd, i, v, t = f
            who = people[i]
            if kd == "room":
                return f"{who} was in the {names[v]}." if t else f"{who} was not in the {names[v]}."
            if kd == "row":
                return f"{who} was in the {ordn[v]} row from the top."
            if kd == "col":
                return f"{who} was in the {ordn[v]} column from the left."
            if kd == "near":
                return f"{who} was right beside a {v}." if t else f"{who} was nowhere near a {v}."
            return f"{who} was standing on a rug." if t else f"{who} was not standing on a rug."

        killer = next(i for i in range(n) if i != V and rm(sol[i]) == rm(sol[V]))
        return {"n": n, "rooms": names, "room": room,
                "furniture": [{"r": r, "c": c, "t": t} for (r, c), t in sorted(furn.items())],
                "people": [{"name": p, "initial": p.split()[0][0] if i != V else "V", "about": (cast[i][1] if i != V else "the victim")}
                           for i, p in enumerate(people)],
                "victim": V, "clues": [text(f) for f in chosen],
                "solution": {"pos": [list(q) for q in sol], "killer": killer}}
    raise RuntimeError("couldn't build a murder map")


# ── sudoku ────────────────────────────────────────────────────────────────
def _solve(b, limit=2):
    """Count solutions up to `limit` (b is a flat list of 81 ints, 0 = empty)."""
    try:
        i = b.index(0)
    except ValueError:
        return 1
    r, c = divmod(i, 9)
    used = set(b[r * 9:r * 9 + 9]) | set(b[c::9]) | {
        b[(r // 3 * 3 + y) * 9 + c // 3 * 3 + x] for y in range(3) for x in range(3)}
    n = 0
    for v in range(1, 10):
        if v not in used:
            b[i] = v
            n += _solve(b, limit - n)
            b[i] = 0
            if n >= limit:
                break
    return n


def _fill(b, rng):
    try:
        i = b.index(0)
    except ValueError:
        return True
    r, c = divmod(i, 9)
    used = set(b[r * 9:r * 9 + 9]) | set(b[c::9]) | {
        b[(r // 3 * 3 + y) * 9 + c // 3 * 3 + x] for y in range(3) for x in range(3)}
    vals = [v for v in range(1, 10) if v not in used]
    rng.shuffle(vals)
    for v in vals:
        b[i] = v
        if _fill(b, rng):
            return True
    b[i] = 0
    return False


def sudoku(seed: str, clues: int = 32) -> dict:
    rng = random.Random("sd" + seed)
    full = [0] * 81
    _fill(full, rng)
    puz = full[:]
    order = list(range(81))
    rng.shuffle(order)
    for i in order:
        if sum(1 for v in puz if v) <= clues:
            break
        j = 80 - i  # remove in symmetric pairs
        keep = puz[i], puz[j]
        puz[i] = puz[j] = 0
        if _solve(puz[:]) != 1:
            puz[i], puz[j] = keep
    return {"puzzle": "".join(str(v) for v in puz), "solution": "".join(str(v) for v in full),
            "givens": sum(1 for v in puz if v)}


# ── the day's set ─────────────────────────────────────────────────────────
def build(date: str, items: list[dict], llm=None) -> dict:
    import datetime as dt
    wd = dt.date.fromisoformat(date).weekday()  # Mon=0 … Sun=6
    words, theme = crossword_words(items, llm)
    rng = random.Random("bank" + date)
    bank = BANK[:]
    rng.shuffle(bank)
    xw = crossword(words, date, theme or "Mixed bag", extra=bank[:12] if words else bank[:24])
    return {"date": date, "ai": bool(words),
            "crossword": xw,
            "whodunit": whodunit(date, 3 if wd < 3 else 4),
            "murdermap": murdermap(date),
            "sudoku": sudoku(date, [38, 36, 34, 32, 30, 28, 27][wd])}
