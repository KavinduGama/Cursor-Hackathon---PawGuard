const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

async function jsonFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${path} ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  startVisionSession: (sessionId) =>
    jsonFetch('/api/vision/session/start', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId || null }),
    }),

  analyzeFrame: (sessionId, frameDataUrl) =>
    fetch(`${API_BASE}/api/vision/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, frame: frameDataUrl }),
      keepalive: true,
    }).then((res) => {
      if (!res.ok) {
        console.warn(`[PawGuard] analyzeFrame failed: ${res.status}`);
      }
      return res;
    }),

  getObservations: (sessionId) =>
    jsonFetch(`/api/vision/observations/${sessionId}`),

  /** Nearby vets only (no outbound call). Used by `find_emergency_vet`. */
  findVets: (lat, lng, radius_m = 5000) =>
    jsonFetch('/api/location/vets', {
      method: 'POST',
      body: JSON.stringify({ lat, lng, radius_m }),
    }),

  /** Nearby foster/shelters only (no outbound call). Used by `find_foster_care`. */
  findFoster: (lat, lng, radius_m = 8000) =>
    jsonFetch('/api/location/foster', {
      method: 'POST',
      body: JSON.stringify({ lat, lng, radius_m }),
    }),

  // ── Combined "find + call" tools used by the triage agent ────────────
  autoDialVet: ({ lat, lng, context, session_id }) =>
    jsonFetch('/api/auto-dial/vet', {
      method: 'POST',
      body: JSON.stringify({ lat, lng, context, session_id }),
    }),

  autoDialShelter: ({ lat, lng, context, session_id }) =>
    jsonFetch('/api/auto-dial/shelter', {
      method: 'POST',
      body: JSON.stringify({ lat, lng, context, session_id }),
    }),

  /** Call a pre-selected list of places one by one (split-flow). */
  dialList: ({ kind, places, context, session_id }) =>
    jsonFetch('/api/calls/dial-list', {
      method: 'POST',
      body: JSON.stringify({ kind, places, context, session_id }),
    }),

  getCallStatus: (callId) => jsonFetch(`/api/calls/${callId}/status`),
};

export const API_BASE_URL = API_BASE;
