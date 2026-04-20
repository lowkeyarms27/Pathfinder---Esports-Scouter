# Pathfinder — Esports Talent Scouting Platform

> AI-powered talent intelligence for competitive esports. Upload a VOD, get a full stylistic profile and pro-player comparison in seconds.

---

## What It Does

Pathfinder analyzes gameplay footage using a multi-agent AI pipeline to produce a **stylistic DNA profile** for any player, then matches them against a library of 60+ professional players with real tournament data. It answers the question: *"Who does this player play like, and what are they worth?"*

### Core Features

- **VOD Analysis** — Upload a single clip or 2–3 clips for averaged multi-clip profiling
- **15-Dimension Style Vector** — Aggression, clutch rate, reaction speed, utility priority, flank frequency, and 10 more
- **Pro Twin Matching** — Cosine similarity against 60 enriched pro archetypes (sixstats.cc tournament data)
- **Market Value Estimate** — Illustrative salary range based on stylistic profile
- **Discover Page** — Browse, filter, and search 8 mock pro players across R6 Siege and Valorant
- **Watchlist** — Track players of interest across sessions
- **Player Profiles** — Radar chart, bar chart, match history, analyst traits

---

## Architecture

### 4-Agent AI Pipeline

```
VOD Upload
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  OBSERVER  — 9 parallel ML sensors                  │
│  • Gemini Vision    • Twelve Labs (Pegasus)          │
│  • YOLO Detection   • Whisper Audio Transcription    │
│  • HUD OCR          • Player Tracker (ByteTrack)     │
│  • Audio Events     • CLIP Concepts                  │
│  • Spatial AI                                        │
└────────────────────────┬────────────────────────────┘
                         │  raw event log
                         ▼
┌─────────────────────────────────────────────────────┐
│  PROFILER  — builds 15-dim style vector              │
│  Aggregates sensor output into normalized floats     │
│  for each dimension (0.0 – 1.0)                     │
└────────────────────────┬────────────────────────────┘
                         │  style_vector
                         ▼
┌─────────────────────────────────────────────────────┐
│  TWIN AGENT  — pro match via cosine similarity       │
│  • Per-pro dimension masking (real vs template data) │
│  • Event-count confidence weighting                  │
│  • Display score normalized 0–100 across library     │
└────────────────────────┬────────────────────────────┘
                         │  pro_match, alternatives
                         ▼
┌─────────────────────────────────────────────────────┐
│  VALUE CRITIC  — market value heuristic              │
│  • Salary range estimate (illustrative)              │
│  • Risk tier + acquisition recommendation            │
│  • Confidence scales with data quality               │
└─────────────────────────────────────────────────────┘
```

### Pro Archetype Library

- **60 pros** across NAL, EUL, Brazil League, and APAC
- **Real tournament data** scraped from sixstats.cc — up to 62 events per player
- **15 style dimensions** populated from actual match stats where available
- **Validation**: 94% self-match accuracy, 100% role@1 on pros with ≥5 events

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11, SQLite |
| Vision AI | Google Gemini 1.5 Flash, Twelve Labs Pegasus |
| Computer Vision | YOLOv8 (Ultralytics), ByteTrack, EasyOCR |
| Audio | OpenAI Whisper, Librosa |
| Embeddings | CLIP (OpenAI via HuggingFace Transformers) |
| Matching | scikit-learn cosine similarity |
| Frontend | React 19, Vite, React Router v6, Recharts |
| Styling | CSS Modules (no UI framework) |
| Data | sixstats.cc, Liquipedia scraper |

---

## Project Structure

```
Pathfinder/
├── backend/
│   ├── agents/
│   │   ├── observer.py        # 9 parallel ML sensors
│   │   ├── profiler.py        # style vector builder
│   │   ├── twin_agent.py      # cosine similarity matching
│   │   ├── value_critic.py    # market value heuristic
│   │   └── orchestrator.py    # pipeline coordinator
│   ├── ml/
│   │   ├── yolo_analyzer.py
│   │   ├── ocr_analyzer.py
│   │   ├── whisper_transcriber.py
│   │   ├── audio_analyzer.py
│   │   ├── clip_analyzer.py
│   │   └── player_tracker.py
│   ├── scrapers/
│   │   ├── sixstats.py        # real tournament stats
│   │   ├── liquipedia.py      # pro archetype builder
│   │   └── tracker_network.py
│   ├── routes/
│   │   └── scouting.py        # REST API endpoints
│   ├── database.py            # SQLite + pro_archetypes table
│   └── main.py                # FastAPI app
├── frontend-react/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Discover.jsx       # hero search + player grid
│   │   │   ├── PlayerProfile.jsx  # full profile with charts
│   │   │   ├── Watchlist.jsx      # tracked players
│   │   │   └── ScoutPlayer.jsx    # VOD upload + live pipeline
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── PlayerCard.jsx
│   │   │   ├── Pipeline.jsx       # live agent step tracker
│   │   │   ├── RadarChart.jsx     # SVG 15-dim radar
│   │   │   ├── ProMatchCard.jsx
│   │   │   └── ValueCard.jsx
│   │   ├── context/
│   │   │   └── WatchlistContext.jsx
│   │   └── data/
│   │       └── mockData.js        # 8 mock pro players
│   └── package.json
├── data/
│   └── pro_archetypes.json    # cached pro library
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- API keys: Google Gemini, Twelve Labs (optional — graceful fallback)

### Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set environment variables
export GEMINI_API_KEY=your_key_here
export TWELVELABS_API_KEY=your_key_here   # optional

# Start the API server
cd Pathfinder
python -m backend.main
# → http://localhost:8001
```

### Frontend

```bash
cd frontend-react
npm install
npm run dev
# → http://localhost:5174
```

The frontend proxies `/api` requests to the backend automatically via Vite config.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/scout` | Upload single clip + player handle |
| `POST` | `/api/scout/multi` | Upload 2–5 clips for multi-clip profiling |
| `GET` | `/api/scout/{session_id}/status` | Poll analysis status |
| `GET` | `/api/scout/{session_id}/log` | Stream live agent log |
| `GET` | `/api/scout/{session_id}/results` | Get full scouting report |

### Request (single clip)

```bash
curl -X POST http://localhost:8001/api/scout \
  -F "clip=@gameplay.mp4" \
  -F "player_handle=YourHandle" \
  -F "game=r6siege" \
  -F "team=Team Name"
```

### Response

```json
{
  "player_handle": "YourHandle",
  "archetype": "Entry Fragger",
  "style_vector": {
    "aggression": 0.87,
    "reaction_speed": 0.91,
    "entry_success_rate": 0.78,
    ...
  },
  "pro_match": {
    "handle": "Beaulo",
    "team": "Spacestation Gaming",
    "role": "Entry Fragger"
  },
  "display_score": 83.4,
  "similarity_score": 71.2,
  "market_value": 45000,
  "market_value_low": 32000,
  "market_value_high": 59000,
  "sensors_active": 7,
  "sensors_total": 9
}
```

---

## Style Dimensions

| Dimension | Description |
|---|---|
| `aggression` | Frequency of proactive, aggressive plays |
| `reaction_speed` | Speed of response to enemy contact |
| `entry_success_rate` | Win rate on site entry duels |
| `clutch_rate` | Performance in low-HP / outnumbered scenarios |
| `first_duel_rate` | How often the player takes the first fight |
| `trade_efficiency` | Ability to trade kills effectively |
| `utility_priority` | How much the player invests in utility |
| `utility_enable_rate` | How often utility creates kills for teammates |
| `site_presence` | Time spent holding/near bomb site |
| `info_play_rate` | Frequency of information-gathering plays |
| `calm_under_pressure` | Composure in high-stakes moments |
| `comms_density` | Callout and communication activity |
| `flank_frequency` | How often the player takes off-angle routes |
| `position_variance` | Unpredictability of positioning |
| `operator_diversity` | Breadth of operator/agent pool |

---

## Scraping Pro Data

```bash
# Rebuild Liquipedia pro archetypes
python -m backend.scrapers.liquipedia --all

# Enrich with real sixstats tournament stats
python -m backend.scrapers.sixstats --max-events 200

# Validate matching accuracy
python -m backend.tools.validate_matching --min-events 5
```

---

## Design System

- **Background**: `#080808` pure black
- **Surface**: `#0f0f0f` / `#141414`
- **Accent**: `#00ff88` neon green
- **Font**: DM Sans (body) + DM Mono (numbers)
- **Styling**: CSS Modules — no UI framework

---

## Limitations

- Market value estimates are **illustrative only** — derived from stylistic similarity, not real transfer market data
- Style vectors from Gemini (amateur VODs) vs sixstats (pro tournament data) use different measurement methods, which affects match accuracy
- Many pro players don't have Liquipedia pages under their common alias, limiting archetype library coverage
- Sensor accuracy depends on video quality — minimum 720p recommended

---

## Games Supported

- Rainbow Six Siege (full sensor suite)
- Valorant (partial — UI sensor calibration in progress)

---

## What I Learned Building This

### Web Scraping at Scale
I scraped three different data sources — Liquipedia, sixstats.cc, and tracker.gg — each with completely different structures, rate limits, and anti-bot measures. This taught me that scraping is mostly about patience and reading the network tab, not clever code. The real skill is figuring out which endpoint the site actually uses versus what the docs say, and building in delays that don't get you banned (2.5s for Liquipedia, 3s for tracker.gg).

### Cosine Similarity for Matching
The Twin Agent compares a scouted player's 15-dimensional style vector against pro archetypes using cosine similarity. Before this I'd only heard of it in theory. Implementing it from scratch — normalising vectors, taking dot products, handling edge cases like zero vectors — made it concrete. I also learned why raw similarity scores aren't enough: two players with identical mechanics but different roles shouldn't match, which is why I added a 15% role-match bonus on top of the similarity score.

### Multi-Dimensional Feature Vectors
The Profiler produces a 15-dimensional "Stylistic DNA" vector covering things like aggression, utility discipline, positioning, clutch tendencies. The hard part wasn't the math — it was deciding what the 15 dimensions should be. I had to think about what actually differentiates a roamer from an anchor at a deep level, then translate that into things an AI can measure from a VOD. Feature design is a domain knowledge problem first, and a technical problem second.

### Why Agent Role Separation Matters
Early versions had one AI doing everything — watch the VOD, find mistakes, compare to pros, give a verdict. The output was generic. Splitting into Observer → Profiler → Twin → Value Critic, where each agent has a single job and a strict output format, produced dramatically better results. Each agent can be prompted and tuned independently. The Observer just logs events. It doesn't evaluate them — that's the Profiler's job. Separation of concerns applies to AI agents just as much as software modules.

### CSS Modules Design System
Pathfinder started with Tailwind and I rebuilt the UI in CSS Modules with a dark design system (pure black background, neon green accent, DM Sans + DM Mono fonts). I learned what a design token actually is — `--accent: #00ff88` used everywhere means one change updates the whole UI. I also learned why Tailwind and CSS Modules can coexist in the same build without conflict, and when each is the right tool.

### Windows Subprocess Environment Variables
The backend kept failing with `GEMINI_API_KEY not set` even after the `.env` was loaded. The root cause was that `uvicorn --reload` spawns child processes that don't inherit the parent's environment variables on Windows the same way Linux does. The fix was loading `.env` at the very top of both `main.py` and `orchestrator.py` as a failsafe, and running uvicorn *without* `--reload` in production. Environment variable inheritance is platform-specific behaviour I'd never had to think about before.

### Scouting "By Reward" vs "By Mistake"
The conceptual insight that drove the whole project: every other esports AI tool finds what players do wrong. Pathfinder finds what they do exceptionally well and matches it to a professional style. This reframing changed every design decision — the prompts, the output format, what the Profiler measures. I learned that the most important engineering decision is often the framing of the problem, not the implementation of the solution.
