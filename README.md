# PawGuard AI

AI animal-rescue assistant. Point your phone at an injured animal, talk to an
AI vet via voice, and if it's serious the app **autonomously calls the nearest
vet clinic** — then reports back.

```
📱 PWA (Vite + React)            🐍 FastAPI backend            🎙 ElevenLabs
─────────────────────            ──────────────────            ─────────────
Camera + Mic ─────┐              vision/  (Gemini chat)         Agent 1 (triage)
ElevenLabs widget │  HTTPS ───►  location/(Google Places)  ◄──► Agent 2 (vet caller)
Frame loop (2.5s) ┘              calls/   (outbound calls)      Agent 3 (foster)
```

---

## Project layout

```
backend/         FastAPI app (Railway-ready)
  app/
    main.py                 CORS + router mounting
    config.py               env-var settings
    routers/                vision / location / calls endpoints
    services/
      gemini.py             Gemini 2.0 Flash chat session + in-memory cache
      places.py             Google Places (New) — searchNearby
      elevenlabs.py         Outbound call manager + status polling
    models/schemas.py       Pydantic request/response models
  requirements.txt
  .env.example
  Procfile / railway.json

frontend/        Vite + React PWA (Vercel-ready)
  src/
    pages/                  Landing, Session, Results
    components/             Camera, StatusPanel, VoiceAgent, ResultCard
    hooks/                  useCamera, useVisionLoop
    lib/                    api client, geo helpers
  vite.config.js            PWA + dev server
  .env.example
```

---

## Quick start (local)

### 1. Backend

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate     # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env       # macOS/Linux: cp .env.example .env
# Edit .env and fill in at least GEMINI_API_KEY to unlock vision.
# Everything else has a graceful "demo mode" fallback.

uvicorn app.main:app --reload --port 8000
```

Health-check: <http://localhost:8000/health>

### 2. Frontend

```bash
cd frontend
npm install

copy .env.example .env       # macOS/Linux: cp .env.example .env
# Set VITE_ELEVENLABS_AGENT_ID to your triage agent id.

npm run dev
```

Open the printed `http://192.168.x.x:5173` URL **on your phone** (same Wi-Fi)
to test the back camera. iOS/desktop browsers will fall back to the front
camera if no environment-facing camera is available.

> Browsers only grant camera + mic on **HTTPS** or **localhost**. For
> on-device testing use `ngrok http 5173` (or deploy to Vercel) to get HTTPS.

---

## API surface

| Method | Path                               | Purpose                                   |
| ------ | ---------------------------------- | ----------------------------------------- |
| POST   | `/api/vision/session/start`        | Start a Gemini chat session               |
| POST   | `/api/vision/analyze`              | Send a frame, update cache                |
| GET    | `/api/vision/observations/{id}`    | **Instant** cached analysis for the agent |
| POST   | `/api/location/vets`               | Nearby veterinary clinics                 |
| POST   | `/api/location/foster`             | Nearby foster / shelters                  |
| POST   | `/api/calls/vet`                   | Spawn outbound vet call (Agent 2)         |
| POST   | `/api/calls/foster`                | Spawn outbound foster call (Agent 3)     |
| GET    | `/api/calls/{call_id}/status`      | Result + summary of the call             |

Interactive docs: <http://localhost:8000/docs>

---

## ElevenLabs agent setup

You need **three** agents in the [ElevenLabs dashboard](https://elevenlabs.io/app/conversational-ai):

### Agent 1 — Triage (user-facing widget)

- **Type:** Conversational AI (web widget)
- **First message:** "Hi, I'm PawGuard. Show me the animal you found — I can see through your camera. Move slowly so I get a good look."
- **System prompt:** calm vet assistant. Triage severity → call vets when CRITICAL → offer foster.
- **Client tools** (names must match exactly):

  | Tool                  | Parameters                                  | Notes                                |
  | --------------------- | ------------------------------------------- | ------------------------------------ |
  | `get_vision_analysis` | _none_                                      | Returns the cached Gemini JSON       |
  | `find_nearby_vets`    | _none_                                      | Browser geo + Google Places          |
  | `find_foster_care`    | _none_                                      | Same, for foster                     |
  | `call_vet`            | `phone` (string), `name` (string), `context` (string) | Spawns Agent 2          |
  | `call_foster`         | `phone`, `name`, `context`                  | Spawns Agent 3                       |
  | `get_call_status`     | `call_id` (string)                          | Reads the call's result              |

  All six are registered client-side in `frontend/src/components/VoiceAgent.jsx`.

### Agent 2 — Vet Caller (outbound phone)

- **Type:** Conversational AI with **Twilio outbound** enabled
- **Dynamic variables:** `context`, `place_name`, `agent_type`
- **First message:** "Hi, this is PawGuard AI calling on behalf of someone who just found an injured animal nearby. {{context}} — do you have a vet who can see it now, and what's your earliest available time?"
- **Evaluation criteria:** add boolean `available` + free-text `wait_time` so the triage agent can report back specifics.

### Agent 3 — Foster Caller (outbound phone)

Identical wiring to Agent 2, but pitched for foster orgs:
"Hi, this is PawGuard AI — we have a rescued animal that needs temporary foster. {{context}}. Can you take it, and how soon can pickup happen?"

Drop the three agent IDs into `backend/.env` and the triage ID into `frontend/.env`.

---

## Demo mode (no API keys)

The backend degrades gracefully when keys are missing so you can demo the flow
end-to-end before everything is wired up:

| Missing key                 | Behaviour                                                |
| --------------------------- | -------------------------------------------------------- |
| `GEMINI_API_KEY`            | `/analyze` will 500 — vision **requires** Gemini         |
| `GOOGLE_PLACES_API_KEY`     | Returns 3 fake nearby places near the caller's location  |
| `ELEVENLABS_*` (call agents)| Simulates a 3-second call that "succeeds" with demo data |

---

## Deployment

### Backend → Railway

1. Push `backend/` to GitHub
2. New Railway project → Deploy from repo, set the root to `backend/`
3. Add all variables from `.env.example` in the Railway dashboard
4. Railway uses `Procfile` / `railway.json` automatically (uvicorn on `$PORT`)
5. Note the public URL (e.g. `https://pawguard-api.up.railway.app`) — that's
   your `VITE_API_BASE` for the frontend

### Frontend → Vercel

1. Push `frontend/` to GitHub
2. Import into Vercel, framework preset = **Vite**
3. Env vars: `VITE_API_BASE` and `VITE_ELEVENLABS_AGENT_ID`
4. Deploy — Vercel auto-serves the PWA over HTTPS, so camera + mic work on phone

Add the Vercel URL to `ALLOWED_ORIGINS` in the backend env, redeploy backend.

---

## How the "always-watching vision" works

```
Camera ─► every 2.5s ─► POST /vision/analyze ─► Gemini chat (same session)
                                                       │
                                                       ▼
                                          Update vision_sessions[sid].latest
                                                       │
                              ◄───────── GET /vision/observations/{sid}
              StatusPanel polls every 1.5s         (instant cache read)
                                                       ▲
                                              Triage agent reads this
                                              via the `get_vision_analysis`
                                              client tool — never waits on
                                              Gemini itself.
```

Because the agent reads the cache (not Gemini directly), responses feel
instantaneous even though deep visual analysis is happening continuously in
the background. Gemini's chat session retains every previous frame, so it
can naturally compare across time ("the bleeding has slowed since 30 s ago").

---

## License

MIT — built for the ElevenLabs hackathon.
