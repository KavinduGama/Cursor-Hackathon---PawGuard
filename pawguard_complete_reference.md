# 🐾 PawGuard AI — Complete Hackathon Reference

> AI animal rescue assistant. User shows injured animal on phone camera → AI diagnoses via voice → If critical, AI calls nearest vet automatically.

---

## 🎯 The Idea (Elevator Pitch)

"Open the app, point your camera at an injured animal, and talk to an AI vet assistant. It sees the animal through your camera, tells you what's wrong, and if it's serious — it **actually calls the nearest vet** to check availability, then reports back to you."

---

## 🏗️ Architecture Overview

```
📱 PHONE BROWSER (PWA)
├── Camera (back camera, always on)
├── Microphone (voice conversation)
├── ElevenLabs Widget (voice UI)
└── Frame sender (every 2s → backend)
        │
        ▼
🐍 FASTAPI BACKEND (Railway)
├── Vision Service (Gemini 2.0 Flash)
│   └── Always-watching: analyzes frames continuously
│       Caches latest analysis → instant read
├── Location Service (Google Places API)
│   └── Finds nearest vets / foster care
├── Call Manager (ElevenLabs API)
│   └── Spawns outbound call agents
└── Orchestrator
    └── Coordinates agents, manages state

        │
        ▼
🎙️ ELEVENLABS AGENTS
├── Agent 1: TRIAGE (talks to user, user-facing)
├── Agent 2: VET CALLER (calls vet clinics)
└── Agent 3: FOSTER FINDER (calls foster services)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | **Vite + React** (PWA) | Fast, simple, camera works on mobile browser |
| Backend | **FastAPI** (Python) | You know it, async, perfect for AI APIs |
| Voice AI | **ElevenLabs Conversational AI** | Hackathon sponsor, great quality |
| Outbound Calls | **ElevenLabs Voice Agents** | Can make real phone calls |
| Vision | **Gemini 2.0 Flash** | Free, fast, 1M token context for multi-frame |
| Location | **Google Places API** | Find nearby vets/foster care |
| Deploy Frontend | **Vercel** | Free, instant URL for demo |
| Deploy Backend | **Railway** | Free tier, always-on, no timeout limits |

---

## 🔑 API Keys Needed

| Service | Free? | Sign Up |
|---|---|---|
| ElevenLabs | ✅ Free tier | elevenlabs.io |
| Google Gemini | ✅ Free (15 RPM) | aistudio.google.com |
| Google Places | ✅ $200 free credit | console.cloud.google.com |
| OpenAI (optional, for 2nd opinion) | ❌ Pay-as-go | platform.openai.com |

---

## 👁️ Vision System — "Always Watching"

### The Key Concept
Vision runs **continuously in the background**, not on-demand. The voice agent never waits for vision — it reads pre-computed results instantly.

### How It Works

```
BACKGROUND LOOP (runs non-stop):
Camera → capture frame every 2s → POST to FastAPI → Gemini analyzes → cache result

VOICE AGENT (when user asks):
Agent calls get_vision_analysis → reads cache → responds instantly (~50ms)
```

### Why This Matters
- **Naive approach:** User asks → capture frame → send to Gemini → wait 2-3s → respond. Feels slow.
- **Our approach:** Gemini already analyzed 5+ frames before user even asks. Agent reads cache instantly. Feels magical.

### Gemini Chat Session = Memory
- We use a Gemini **chat session** (not single-shot)
- Gemini remembers ALL previous frames in the session
- It can say: "The swelling I noticed 30 seconds ago is worse now"
- 1M token context = 50+ frames = minutes of observation

---

## 🤖 Multi-Agent Architecture

### Why 3 Agents (Not 1)?
- Agent 1 talks to the USER on their phone
- Agent 2 makes a PHONE CALL to a vet clinic
- Agent 3 makes a PHONE CALL to foster care
- These are **physically separate conversations** — they MUST be separate agents

### Agent 1: Triage Agent
- **Type:** ElevenLabs Conversational AI (user-facing widget)
- **Personality:** Empathetic vet assistant, calm, knowledgeable
- **What it does:**
  1. Greets user, asks them to show the animal
  2. Reads vision analysis (from cache) to understand what it sees
  3. Guides user: "Can you show me the other side?"
  4. Assesses severity: CRITICAL / MODERATE / MILD
  5. If critical → triggers vet call (Agent 2)
  6. If mild → gives first aid guidance
  7. If user wants foster → triggers foster call (Agent 3)
  8. Reports back results from Agent 2/3

- **Client-Side Tools:**

| Tool Name | When Called | What It Does |
|---|---|---|
| `get_vision_analysis` | Agent needs to see | Reads cached Gemini analysis (instant) |
| `find_nearby_vets` | Critical case | Calls FastAPI → Google Places |
| `find_foster_care` | User requests | Calls FastAPI → Google Places |
| `call_vet` | Critical, vet found | Calls FastAPI → spawns Agent 2 |
| `call_foster` | Foster needed | Calls FastAPI → spawns Agent 3 |
| `get_call_status` | Checking on call | Gets Agent 2/3 result |

### Agent 2: Vet Caller Agent
- **Type:** ElevenLabs Outbound Call Agent
- **What it does:** Calls the vet clinic phone number
- **Conversation:** "Hi, I'm calling from PawGuard AI on behalf of someone who found an injured [animal]. [Describes condition]. Is there a vet available? How soon can they be seen?"
- **Reports back:** Available yes/no, wait time, vet name

### Agent 3: Foster Care Agent
- **Type:** ElevenLabs Outbound Call Agent
- **What it does:** Calls foster care services
- **Conversation:** Similar to Agent 2, but asks about foster availability, pickup options
- **Reports back:** Available yes/no, pickup available, requirements

---

## 📱 Frontend Structure (Vite + React)

### Pages
```
/              → Landing page (intro + "Start Rescue" button)
/session       → Main page (camera + voice + live status panel)
/results       → Summary (diagnosis, vet info, directions)
```

### Key Components
```
Camera.jsx        → Accesses back camera, displays feed, captures frames every 2s
VoiceAgent.jsx    → ElevenLabs Conversational AI widget + client-side tools
StatusPanel.jsx   → Shows what AI is seeing (live text updates)
ResultCard.jsx    → Shows vet/foster availability results
```

### Camera Access (Mobile Browser)
```javascript
// This works on mobile browsers — accesses BACK camera
const stream = await navigator.mediaDevices.getUserMedia({
  video: { facingMode: 'environment' },  // back camera
  audio: true
});
videoRef.current.srcObject = stream;
```

### Frame Capture (Every 2 Seconds)
```javascript
// Background loop — fires and forgets
setInterval(() => {
  const canvas = document.createElement('canvas');
  canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
  const base64 = canvas.toDataURL('image/jpeg', 0.7);
  
  fetch(`${API}/api/vision/analyze`, {
    method: 'POST',
    body: JSON.stringify({ session_id, frame: base64 })
  }); // no await — fire and forget
}, 2000);
```

### ElevenLabs Widget Setup
```javascript
import { useConversation } from '@11labs/react';

const conversation = useConversation({
  agentId: 'your-agent-id',
  clientTools: {
    get_vision_analysis: async () => {
      const res = await fetch(`${API}/api/vision/observations/${sessionId}`);
      return (await res.json()).analysis;  // instant cache read
    },
    find_nearby_vets: async () => {
      const pos = await getCurrentPosition();
      const res = await fetch(`${API}/api/location/vets`, {
        method: 'POST',
        body: JSON.stringify({ lat: pos.lat, lng: pos.lng })
      });
      return await res.json();
    },
    call_vet: async ({ vet_phone, animal_info }) => {
      const res = await fetch(`${API}/api/calls/vet`, {
        method: 'POST',
        body: JSON.stringify({ phone: vet_phone, context: animal_info })
      });
      return await res.json();
    }
  }
});
```

---

## 🐍 Backend Structure (FastAPI)

### Project Layout
```
backend/
├── app/
│   ├── main.py           # FastAPI app, CORS, startup
│   ├── config.py          # env vars (API keys)
│   ├── routers/
│   │   ├── vision.py      # /api/vision/* endpoints
│   │   ├── location.py    # /api/location/* endpoints
│   │   └── calls.py       # /api/calls/* endpoints
│   ├── services/
│   │   ├── gemini.py      # Gemini chat session manager
│   │   ├── places.py      # Google Places client
│   │   └── elevenlabs.py  # Outbound call manager
│   └── models/
│       └── schemas.py     # Pydantic models
└── requirements.txt
```

### API Endpoints

```
# Vision
POST /api/vision/analyze           → Receive frame, send to Gemini, cache result
POST /api/vision/session/start     → Start new Gemini chat session
GET  /api/vision/observations/{id} → Get latest cached analysis (INSTANT)

# Location
POST /api/location/vets            → Find nearby vets (Google Places)
POST /api/location/foster          → Find nearby foster care

# Calls
POST /api/calls/vet                → Spawn Agent 2, call a vet
POST /api/calls/foster             → Spawn Agent 3, call foster
GET  /api/calls/{call_id}/status   → Check call result
```

### Vision Service (The Cache Pattern)
```python
# In-memory cache
vision_sessions: dict[str, dict] = {}

@router.post("/analyze")
async def analyze(request: FrameRequest):
    session = vision_sessions[request.session_id]
    
    # Send frame to Gemini chat (remembers previous frames)
    response = await session["chat"].send_message([
        {"mime_type": "image/jpeg", "data": request.frame},
        "What animals/injuries do you see? Any changes?"
    ])
    
    # Cache it — voice agent reads this instantly
    session["latest"] = response.text
    session["frame_count"] += 1
    return {"status": "ok"}

@router.get("/observations/{session_id}")
async def get_observations(session_id: str):
    # Voice agent calls this — instant read from cache
    return {"analysis": vision_sessions[session_id]["latest"]}
```

### Requirements.txt
```
fastapi
uvicorn
python-dotenv
google-genai
openai
httpx
pydantic
```

---

## 🚀 Deployment

### Frontend → Vercel
```bash
cd frontend
npm run build
# Connect GitHub repo to Vercel, auto-deploys
# Or: npx vercel --prod
```

### Backend → Railway
```bash
cd backend
# Connect GitHub repo to Railway
# Set env vars in Railway dashboard
# Railway auto-detects Python + runs uvicorn
```

### Environment Variables
```
# Backend (.env)
GEMINI_API_KEY=xxx
ELEVENLABS_API_KEY=xxx
GOOGLE_PLACES_API_KEY=xxx
OPENAI_API_KEY=xxx  # optional
ELEVENLABS_TRIAGE_AGENT_ID=xxx
ELEVENLABS_VET_AGENT_ID=xxx
ELEVENLABS_FOSTER_AGENT_ID=xxx
```

---

## 🎬 User Flows

### Flow 1: Critical Case
```
1. User opens pawguard.vercel.app on phone
2. Grants camera + mic permission
3. AI: "Hi! I'm PawGuard. Show me the animal you found."
4. User points phone at injured dog
5. (Background: frames sent to Gemini every 2s)
6. AI: "I can see a dog with a swollen leg. Move closer?"
7. User moves camera
8. AI: "This looks critical — swelling and a wound. 
        I'm finding the nearest vet."
9. (Finds PetCare Clinic, 1.2 miles away)
10. AI: "I'm calling PetCare Clinic now. Keep the dog calm."
11. (Agent 2 calls the vet, has conversation)
12. AI: "Dr. Smith can see the dog in 15 minutes at 
         123 Main St. Want directions?"
```

### Flow 2: Non-Critical + Foster
```
1-5. Same as above
6. AI: "This cat has minor skin irritation. Not critical.
        Clean with warm water, no human meds."
7. User: "Can you find foster care?"
8. (Agent 3 calls foster service)
9. AI: "Happy Paws Foster can take the cat. They can 
        pick up in 30 minutes."
```

---

## ⏱️ 18-Hour Build Schedule

| Phase | What | Hours | Total |
|---|---|---|---|
| 1 | Vite + FastAPI project setup | 1h | 1h |
| 2 | Camera UI + frame capture | 1.5h | 2.5h |
| 3 | Gemini vision service + cache | 1.5h | 4h |
| 4 | ElevenLabs Triage Agent setup | 2h | 6h |
| 5 | Client-side tools (vision↔voice bridge) | 1.5h | 7.5h |
| 6 | Google Places (find vets/foster) | 1h | 8.5h |
| 7 | Outbound call agents (vet + foster) | 2.5h | 11h |
| 8 | FastAPI orchestrator | 1.5h | 12.5h |
| 9 | UI polish + PWA | 1.5h | 14h |
| 10 | Testing + bugs | 2h | 16h |
| 11 | Demo + presentation | 2h | 18h |

---

## 💡 Key Decisions & Why

| Decision | Why |
|---|---|
| **PWA, not native app** | No app store needed, judges just open a URL |
| **Vite, not Next.js** | No SSR needed, camera/mic are client-only, simpler |
| **Gemini, not GPT-4o** | Free tier, faster, 1M context for multi-frame memory |
| **Always-watching vision** | Instant voice responses, no waiting for analysis |
| **Multi-agent, not single** | Outbound calls are separate phone lines by nature |
| **FastAPI orchestrator** | Simple coordination, not full A2A protocol (overkill) |
| **Vercel + Railway** | Both free, split frontend/backend cleanly |

---

## 🏆 What Will Impress Judges

1. **"Show the animal"** → AI sees through camera and describes injuries
2. **"Move around it"** → AI guides user like a real vet, tracks changes across angles
3. **"This is critical"** → AI autonomously decides to call a vet
4. **Actual phone call happens** → Agent calls vet, has real conversation 🤯
5. **Reports back** → "Dr. Smith can see you in 15 min"
6. **Multi-agent architecture** → Sophisticated, production-ready design
7. **Works on any phone** → Just a URL, instant demo

---

## ⚠️ Hackathon Tips

- **Demo with a stuffed animal or photo** if no real injured animal available
- **Set up a simulated vet number** (your own Twilio number with an AI receptionist) for the call demo
- **Test on your phone** early — don't wait until demo day
- **Record a backup video** in case live demo has network issues
- **Mention future improvements:** YOLOv8 pre-filtering, A2A protocol, native app, real vet directory integration
