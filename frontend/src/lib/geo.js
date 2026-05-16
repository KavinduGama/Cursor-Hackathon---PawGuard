export function getCurrentPosition(options = {}) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation not supported on this device'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) => reject(err),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000, ...options }
    );
  });
}

const DEMO_LAT_DEFAULT = 6.927079; // Colombo — adjust via env
const DEMO_LNG_DEFAULT = 79.861243;

function envBool(v) {
  if (v == null || v === '') return false;
  const s = String(v).toLowerCase();
  return s === '1' || s === 'true' || s === 'yes';
}

function demoCoords() {
  const lat = Number(import.meta.env.VITE_DEMO_LAT ?? DEMO_LAT_DEFAULT);
  const lng = Number(import.meta.env.VITE_DEMO_LNG ?? DEMO_LNG_DEFAULT);
  return {
    lat: Number.isFinite(lat) ? lat : DEMO_LAT_DEFAULT,
    lng: Number.isFinite(lng) ? lng : DEMO_LNG_DEFAULT,
  };
}

/**
 * Resolves lat/lng for vet/shelter tools.
 *
 * - VITE_USE_DEMO_LOCATION=1 → never asks for GPS (hackathon / MOCK_VET_PHONE demos).
 * - Else tries GPS when page is secure context (HTTPS or localhost).
 * - VITE_FALLBACK_TO_DEMO_LOCATION=1 → if GPS fails or context insecure, uses demo coords.
 */
export async function resolveLatLngForTools() {
  if (envBool(import.meta.env.VITE_USE_DEMO_LOCATION)) {
    const { lat, lng } = demoCoords();
    return {
      lat,
      lng,
      source: 'demo_fixed',
      note: 'Using VITE_DEMO_LAT / VITE_DEMO_LNG (no GPS prompt).',
    };
  }

  const fallback = envBool(import.meta.env.VITE_FALLBACK_TO_DEMO_LOCATION);

  if (typeof window !== 'undefined' && !window.isSecureContext) {
    if (fallback) {
      const { lat, lng } = demoCoords();
      return {
        lat,
        lng,
        source: 'demo_fallback_insecure',
        note: 'Page is not HTTPS — using demo coordinates instead of GPS.',
      };
    }
    throw Object.assign(new Error('insecure_context'), {
      code: 'INSECURE_CONTEXT',
    });
  }

  try {
    const pos = await getCurrentPosition();
    return { ...pos, source: 'gps' };
  } catch (err) {
    if (fallback) {
      const { lat, lng } = demoCoords();
      return {
        lat,
        lng,
        source: 'demo_fallback_gps_error',
        note: `GPS unavailable (${String(err?.message || err)}); using demo coordinates.`,
      };
    }
    throw err;
  }
}

export function safeParseAnalysis(text) {
  if (text == null) return null;
  if (typeof text === 'object' && text !== null && !Array.isArray(text)) {
    return text;
  }
  if (typeof text !== 'string') return null;
  try {
    return JSON.parse(text);
  } catch {
    const match = text.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        return JSON.parse(match[0]);
      } catch {
        return null;
      }
    }
    return null;
  }
}

export function sessionIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get('sid');
}
