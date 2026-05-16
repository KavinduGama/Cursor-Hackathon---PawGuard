# ElevenLabs Agent Dashboard Configuration

This file documents exactly what must be configured on the
[ElevenLabs Conversational AI dashboard](https://elevenlabs.io/app/conversational-ai)
for PawGuard to work end-to-end.

There are **three** agents. The triage agent runs in the browser; the vet and
foster agents make outbound phone calls from the backend.

---

## Agent 1 — Triage Agent (browser voice)

**Agent ID env var:** `VITE_ELEVENLABS_AGENT_ID` (frontend) /
`ELEVENLABS_TRIAGE_AGENT_ID` (backend — informational only, not used by code)

### System prompt (recommended)

The prompt must instruct the agent to follow this exact flow:

1. Greet the user and ask them to show the animal on camera.
2. Call `get_vision_analysis` to read what the camera AI sees.
3. Describe the animal's condition to the user based on the vision data.
4. If the animal needs veterinary help, tell the user you will find nearby
   vets. Call `auto_dial_vets` (optionally `find_emergency_vet` first to
   list them).
5. While vets are being called in the background, keep the user calm and
   informed. **Do NOT poll `get_call_status`** — contextual updates arrive
   automatically.
6. When a vet confirms availability, relay the details (name, wait time,
   address) and wrap up the session.

### Dynamic variables

| Variable     | Passed by frontend | Purpose                   |
|--------------|--------------------|---------------------------|
| `session_id` | Yes                | Links voice to the vision session |

### Client tools (names must match exactly)

Register these five client tools on the dashboard. The frontend implements
them; the agent invokes them by name.

| Tool name                      | Parameters          | What it does                                        |
|--------------------------------|---------------------|-----------------------------------------------------|
| `get_vision_analysis`          | *(none)*            | Returns the latest camera analysis (species, injuries, severity) |
| `find_emergency_vet`           | *(none)*            | Lists nearby vets with phone numbers — **no call is placed** |
| `auto_dial_vets`               | `context` (optional string) | Finds nearby vets and calls them one by one until one is available |
| `auto_dial_shelters`           | `context` (optional string) | Same as above but for foster/shelters |
| `call_vets_sequentially`       | `places` (array), `context` (optional string) | Calls a pre-selected list of vets one by one (from a prior `find_emergency_vet`) |
| `call_shelters_sequentially`   | `places` (array), `context` (optional string) | Same as above but for foster/shelters |
| `get_call_status`              | `call_id` (string)  | Manually checks call progress (rarely needed — watchers push updates) |

**Aliases:** `find_emergency_vets` and `find_nearby_vets` are also handled as
aliases for `find_emergency_vet`. You only need to register one of the three
on the dashboard.

**Split-flow vs combined-flow:** The agent can either use `auto_dial_vets`
(combined: find + call) or the two-step split flow:
1. Call `find_emergency_vet` to get a list of nearby vets
2. Present the list to the user
3. Call `call_vets_sequentially` with the `places` array from step 1

---

## Agent 2 — Vet Outbound Agent (phone call)

**Agent ID env var:** `ELEVENLABS_VET_AGENT_ID`

This agent makes outbound phone calls to veterinary clinics on behalf of
PawGuard. It receives dynamic variables from the backend.

### Dynamic variables (injected by backend)

| Variable     | Value                          |
|--------------|--------------------------------|
| `context`    | Description of the animal's condition |
| `place_name` | Name of the clinic being called |
| `agent_type` | `"vet"`                        |

### Recommended prompt behaviour

- Introduce itself as calling from PawGuard, an animal rescue service.
- Explain the situation using `context`.
- Ask if the clinic can see the animal urgently.
- Confirm availability, estimated wait time, and contact person.

### Evaluation criteria (optional but recommended)

Configure on the dashboard under **Evaluation Criteria**:

| Criterion  | Success condition                         |
|------------|-------------------------------------------|
| `available`| The clinic confirmed they can see the animal |

### Data collection (optional but recommended)

| Field          | Type    | Description                    |
|----------------|---------|--------------------------------|
| `wait_minutes` | integer | Estimated wait time in minutes |
| `contact_name` | string  | Person who answered            |
| `notes`        | string  | Any additional info            |

---

## Agent 3 — Foster Outbound Agent (phone call)

**Agent ID env var:** `ELEVENLABS_FOSTER_AGENT_ID`

Identical structure to the vet agent but for animal shelters / foster homes.

### Dynamic variables

Same as vet agent (`context`, `place_name`, `agent_type="foster"`).

### Recommended prompt behaviour

- Introduce itself as calling from PawGuard.
- Ask if the shelter can accept a rescued animal.
- Confirm availability and pickup/drop-off logistics.

### Evaluation criteria and data collection

Same fields as the vet agent (`available`, `wait_minutes`, `contact_name`,
`notes`).

---

## Verification checklist

- [ ] Triage agent ID in `frontend/.env` (`VITE_ELEVENLABS_AGENT_ID`) matches
      the agent on the dashboard
- [ ] Triage agent has all 5 client tools registered with the exact names above
- [ ] Triage agent system prompt follows the flow: vision → triage → find vets → call → report
- [ ] Vet agent ID in `backend/.env` (`ELEVENLABS_VET_AGENT_ID`) matches its dashboard agent
- [ ] Foster agent ID in `backend/.env` (`ELEVENLABS_FOSTER_AGENT_ID`) is set
      (currently placeholder `agent_xxx_foster` — **needs a real ID**)
- [ ] Phone number ID in `backend/.env` (`ELEVENLABS_PHONE_NUMBER_ID`) is a
      Twilio number registered in ElevenLabs
- [ ] Vet and foster agents accept `context`, `place_name`, `agent_type` as
      dynamic variables
