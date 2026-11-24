# The Daily Briefing

A free, self-running reading curator. Every morning it:

1. Pulls new articles from ~45 hand-picked feeds, topic searches and the Hacker News front page
2. Drops short items and duplicate coverage of the same story
3. Has a free AI model score the shortlist for writing quality and relevance to you
4. Picks ~10 (max 2 per topic, at least 1 lighter read)
5. Writes **3 key points** per article, a **longer expansion of each point**, and a one-line "say this in the room" takeaway
6. Publishes it as a web page, RSS feeds for KOReader, and an EPUB for your Kobo

You can also **save any link** from your phone and it gets the same treatment.

Total cost: $0 (GitHub Actions + GitHub Pages + Gemini's free tier).

---

## Setup (about 30 minutes, once)

### 1. Put the code on GitHub
1. Create a free account at github.com if you don't have one.
2. New repository → name it `briefing` → **Public** (free GitHub Pages requires public) → Create.
3. Upload all these files ("uploading an existing file", drag the folder contents in). Make sure the `.github` folder comes along. Some uploaders hide dot-folders, and if so, create `.github/workflows/daily.yml` and `save.yml` by hand with "Add file → Create new file".

### 2. Get a free Gemini key
1. Go to aistudio.google.com → **Get API key** → Create.
2. In your repo: **Settings → Secrets and variables → Actions → New repository secret**
   - Name `GEMINI_API_KEY`, value = the key.

> No key? It still runs, just with plain ranking and the article's lead sentences as bullets.

### 3. Tell it who you are (private)
Add a second secret, **`READER_PROFILE`**. This stays private even though the repo is public. Suggested text (edit freely):

```
DVM, PhD, DACLAM; associate director in laboratory animal medicine at a contract
research vivarium in San Diego. Cares about: animal research policy (NIH/FDA,
NAMs, welfare regulation, IACUC), biotech and pharma (especially San Diego),
AI and what it changes in science and work, major science and medicine, the
economy, world affairs. Exploring starting a consulting business, so interested
in entrepreneurship and leadership. Parent of two young boys. Enjoys hiking,
fishing, 3D printing, photography, astrophotography, and great longform essays.
Wants to be the well-read person in the room: substance over hype, and the
pieces smart people will be talking about.
```

### 4. Turn on the website
**Settings → Pages** → Source: *Deploy from a branch* → Branch: `main`, folder: `/docs` → Save.
Your briefing will live at `https://YOUR-USERNAME.github.io/briefing/`.

### 5. Run it once
**Actions** tab → enable workflows if asked → **Daily briefing** → **Run workflow**.
Takes ~5–10 min. After that it runs by itself every morning (~4–5am Pacific).
Check `https://YOUR-USERNAME.github.io/briefing/health.json` to see which feeds worked.

---

## Reading on the Kobo Libra 2

Kobo's own software can't fetch feeds, so install **KOReader**, a free reader that runs alongside it (you choose which to open). Follow the Kobo guide on the KOReader GitHub wiki ("Installation on Kobo devices").

Then in KOReader:

**Daily briefing as articles.** Tools → **News downloader** → Settings → Edit news feeds → add:

| Feed | Setting |
|---|---|
| `https://YOUR-USERNAME.github.io/briefing/briefing.xml` | Download full article: **off** (it holds the bullets + expansions) |
| `https://YOUR-USERNAME.github.io/briefing/articles.xml` | Download full article: **on** (KOReader fetches each original in full) |

Tap **Sync news feeds** each morning on Wi-Fi.

**Daily EPUB.** Search (magnifier) → **OPDS catalog** → `+` → URL `https://YOUR-USERNAME.github.io/briefing/opds.xml`. Each day's briefing appears as a book. Inside, the contents page lists every article's 3 points. Tap a point to jump to its expansion, and use "Back to contents" to return.

> The full article text isn't republished on your public site (that would be copying other people's work). KOReader's `articles.xml` feed downloads originals straight from the publishers instead, the same as opening them in a browser. Paywalled sites only give their preview.

---

## Saving links from your iPhone ("save for later")

Saving works by opening a GitHub issue with the link. It's processed in ~1 minute and shows up on `saved.html`, in both feeds, and in the next morning's EPUB under **Saved for later**. Only issues **you** open are processed.

**Easiest:** GitHub mobile app → your repo → Issues → New → paste the link as the title.

**One tap from the Share sheet (iOS Shortcut):**
1. github.com → Settings → Developer settings → **Fine-grained tokens** → Generate. Repository access: only `briefing`. Permissions: **Issues: Read and write**. Copy the token.
2. Shortcuts app → new shortcut → turn on **Show in Share Sheet** (accepts URLs, Safari web pages).
3. Add action **Get Contents of URL**:
   - URL: `https://api.github.com/repos/YOUR-USERNAME/briefing/issues`
   - Method: **POST**
   - Headers: `Authorization` = `Bearer YOUR-TOKEN`, `Accept` = `application/vnd.github+json`
   - Request Body: JSON, key `title` (Text) = *Shortcut Input*
4. Name it "Save to Briefing". Now Share → Save to Briefing from Safari, Chrome, Mail, anywhere.

> Heads up: the repo is public, so your saved links (issue titles) are visible to anyone who looks. The summaries are too. Your profile and key are not.

---

## Tuning

Everything is in `config.yaml`:
- **Topics:** change `weight` (higher = more likely to be picked), add or remove feeds, add `searches:` for niche subjects.
- **Volume:** `daily_picks`, `max_per_topic`, `min_light_picks`.
- **Dead feeds:** see `docs/health.json` after a run; delete lines that show `error`.
- **AI model:** if all models in `llm.models` fail (Google renames them often), copy a current *Flash* model name from AI Studio and put it first.

## Files
```
config.yaml            your topics, feeds and settings
curator/               the code (sources → extract → rank → summarize → render)
.github/workflows/     daily run + save-a-link
docs/                  the published site, feeds, EPUBs (generated)
data/                  memory of what you've seen and saved (generated)
```

Run locally: `pip install -r requirements.txt && python -m curator daily`, then open `docs/index.html`.
