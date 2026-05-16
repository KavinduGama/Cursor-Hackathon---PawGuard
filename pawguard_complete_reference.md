# PawGuard AI - Complete Project Reference (Current)

> Last updated for the current codebase state (frontend teal theme + auto-dial flow).

---

## What PawGuard does

PawGuard is a mobile-first AI rescue assistant:

1. User opens the web app and starts a rescue session.
2. Camera frames stream continuously to the backend for Gemini analysis.
3. User talks to an ElevenLabs triage agent.
4. The triage agent reads cached vision results instantly via client tools.
5. For urgent cases, the app can auto-find and auto-call nearby vets/shelters.
6. Results are shown in the in-app rescue summary timeline.

---

## Architecture at a glance

```text
PHONE BROWSER (React + Vite PWA)
  - Camera feed + frame capture loop
  - ElevenLabs conversation session
  - Client tools: vision read, vet search, auto-dial, call status
  - Session summary persisted in sessionStorage
          |
          v
FASTAPI BACKEND
  - /api/vision      (Gemini session + cached observations)
  - /api/location    (Google Places vet/foster search)
  - /api/calls       (direct outbound call endpoints)
  - /api/auto-dial   (find + call in one step)
          |
          v
ELEVENLABS
  - Agent 1: user-facing triage
  - Agent 2: vet outbound caller
  - Agent 3: foster/shelter outbound caller
```

---

## Repo layout

```text
backend/
  app/
    main.py
    config.py
    models/schemas.py
    routers/
      vision.py
      location.py
      calls.py
      auto_dial.py
    services/
      gemini.py
      places.py
      elevenlabs.py
  requirements.txt
  .env.example

frontend/
  src/
    pages/
      Landing.jsx
      Session.jsx
      Results.jsx
    components/
      Camera.jsx
      StatusPanel.jsx
      VoiceAgent.jsx
      ResultCard.jsx
      BottomNav.jsx
      MicIcon.jsx
    hooks/
      useCamera.js
      useVisionLoop.js
    lib/
      api.js
      geo.js
    styles.css
  vite.config.js
  .env.example
```

---

## Frontend (current behavior)

### Routes

- `/` -> Landing page (PawGuard branded hero, mic teaser, how-it-works steps)
- `/session` -> Active rescue (camera + live status + voice controls)
- `/results` -> Rescue summary + call outcomes timeline

### Current UI theme

- Teal/mint token palette in `frontend/src/styles.css`
- Rounded mobile card layout
- Four-tab bottom nav:
  - Home (`/`)
  - Find Vets (`/session`)
  - Foster Help (`/results`)
  - Profile (disabled placeholder)

### Voice and tools wiring

`frontend/src/components/VoiceAgent.jsx` registers these client tools for the ElevenLabs triage agent:

- `get_vision_analysis()`
- `find_emergency_vet()`
- `find_emergency_vets()`
- `find_nearby_vets()`
- `auto_dial_vets({ context? })`
- `auto_dial_shelters({ context? })`
- `get_call_status({ call_id })`

Notes:

- `find_*vet*` aliases return nearby vets only (no outbound call).
- `auto_dial_*` performs combined find+call through backend `/api/auto-dial/*`.
- Call results are cached in memory during session and persisted to `sessionStorage` when exiting.

### Vision loop timing

From `useVisionLoop`:

- Frame capture upload interval: **2500 ms**
- Observation poll interval: **1500 ms**

This keeps perceived response fast while Gemini runs asynchronously in backend.

---

## Backend (current API)

### Core routes

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/vision/session/start` | Start/reuse vision session |
| POST | `/api/vision/analyze` | Send frame to Gemini, update cache |
| GET | `/api/vision/observations/{session_id}` | Read latest cached analysis |
| DELETE | `/api/vision/session/{session_id}` | End vision session |
| POST | `/api/location/vets` | Nearby veterinary places |
| POST | `/api/location/foster` | Nearby foster/shelter places |
| POST | `/api/calls/vet` | Direct vet outbound call |
| POST | `/api/calls/foster` | Direct foster outbound call |
| GET | `/api/calls/{call_id}/status` | Call status/details |
| POST | `/api/auto-dial/vet` | Find callable vet and dial |
| POST | `/api/auto-dial/shelter` | Find callable shelter and dial |
| GET | `/health` | Health check |

### Auto-dial behavior

`/api/auto-dial/*`:

1. Searches nearby places.
2. Picks the first result with a phone number.
3. Initiates outbound call via ElevenLabs.
4. Returns `call_id`, `status`, `agent_type`, and selected `place`.
5. Returns `status: "no_results"` if no callable place is found.

---

## Environment variables

### Backend (`backend/.env`)

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

ELEVENLABS_API_KEY=
ELEVENLABS_TRIAGE_AGENT_ID=
ELEVENLABS_VET_AGENT_ID=
ELEVENLABS_FOSTER_AGENT_ID=
ELEVENLABS_PHONE_NUMBER_ID=

GOOGLE_PLACES_API_KEY=

MOCK_VET_PHONE=
MOCK_VET_NAME=PetCare Veterinary Hospital - Nawala
MOCK_VET_ADDRESS=47 Nawala Road, Nawala, Sri Lanka

ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend.vercel.app
PORT=8000
LOG_LEVEL=info
```

### Frontend (`frontend/.env`)

```env
VITE_API_BASE=http://localhost:8000
VITE_ELEVENLABS_AGENT_ID=agent_xxx_triage

VITE_USE_DEMO_LOCATION=1
VITE_FALLBACK_TO_DEMO_LOCATION=1
VITE_DEMO_LAT=6.927079
VITE_DEMO_LNG=79.861243
```

---

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Open the Vite URL from your phone on the same network for camera testing.

---

## Build and deploy notes

- Frontend build command: `npm run build`
- Backend docs locally: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health`
- Intended hosting split:
  - Frontend: Vercel
  - Backend: Railway

Remember to add deployed frontend URL to backend `ALLOWED_ORIGINS`.

---

## Important implementation notes

- Camera stream uses `facingMode: 'environment'` (ideal back camera).
- Voice mic permission is requested separately by ElevenLabs session start.
- Results page re-fetches call status for each recorded `call_id`.
- `MOCK_VET_PHONE` can force vet search to a safe fake clinic for testing.
- If browser location is blocked or non-HTTPS, demo location fallback can keep tools functional.

---

## Known gaps / placeholders (current)

- `/profile` route is not implemented yet (nav item is disabled).
- PWA manifest in `vite.config.js` still uses older green theme colors and can be aligned to the current teal palette if desired.

---

## Current dependency snapshot

`backend/requirements.txt`:

- fastapi 0.115.5
- uvicorn[standard] 0.32.1
- python-dotenv 1.0.1
- google-genai 0.3.0
- httpx 0.27.2
- pydantic 2.9.2
- pydantic-settings 2.6.1
- elevenlabs 1.50.3
- python-multipart 0.0.12

---

This document intentionally reflects the **actual project state now**, including the new landing theme and the active auto-dial tool chain.
