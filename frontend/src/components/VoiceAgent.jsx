import { useCallback, useMemo, useState } from 'react';
import { useConversation } from '@elevenlabs/react';
import { api } from '../lib/api.js';
import { resolveLatLngForTools, safeParseAnalysis } from '../lib/geo.js';

const AGENT_ID = import.meta.env.VITE_ELEVENLABS_AGENT_ID || '';

/**
 * Triage Agent (Agent 1) — the voice the user talks to.
 *
 * Client tools registered on the ElevenLabs dashboard agent (names must
 * match exactly — use any ONE of the aliases below for "find vets"):
 *
 *   - get_vision_analysis()
 *   - find_emergency_vet | find_emergency_vets | find_nearby_vets  → list vets (no dial)
 *   - auto_dial_vets({context?})
 *   - auto_dial_shelters({context?})
 *   - get_call_status({call_id})
 *
 * If the browser keeps asking for location: use HTTPS (or localhost), allow the
 * prompt once, OR set VITE_USE_DEMO_LOCATION=1 in frontend/.env to skip GPS entirely.
 */
export default function VoiceAgent({ sessionId, onCallResult }) {
  const [status, setStatus] = useState('idle'); // idle | connecting | active | speaking
  const [error, setError] = useState(null);

  const clientTools = useMemo(() => {
    /** List nearby vets — no outbound call. Multiple ElevenLabs tool ids → same handler. */
    const findEmergencyVetImpl = async (_params) => {
      try {
        const loc = await resolveLatLngForTools();
        const data = await api.findVets(loc.lat, loc.lng);
        return {
          results: (data.results || []).slice(0, 5),
          location_source: loc.source,
          ...(loc.note ? { location_note: loc.note } : {}),
        };
      } catch (err) {
        if (err?.code === 'INSECURE_CONTEXT') {
          return {
            error: 'insecure_context',
            details:
              'Open the app over HTTPS or localhost, or set VITE_USE_DEMO_LOCATION=1 in frontend/.env.',
          };
        }
        const code = err?.code;
        let details = String(err?.message || err);
        if (code === 1) details = 'Location permission denied — allow location, or set VITE_USE_DEMO_LOCATION=1 for demos.';
        else if (code === 2) details = 'Position unavailable.';
        else if (code === 3) details = 'Location request timed out.';
        return { error: 'find_emergency_vet_failed', details };
      }
    };

    return {
      get_vision_analysis: async () => {
        try {
          const data = await api.getObservations(sessionId);
          const parsed = safeParseAnalysis(data.analysis);
          return {
            severity: data.severity,
            frame_count: data.frame_count,
            ...(parsed || { raw: data.analysis }),
          };
        } catch (err) {
          return { error: 'no vision data yet', details: String(err) };
        }
      },

      find_emergency_vet: findEmergencyVetImpl,
      find_emergency_vets: findEmergencyVetImpl,
      find_nearby_vets: findEmergencyVetImpl,

      auto_dial_vets: async ({ context } = {}) => {
        try {
          const loc = await resolveLatLngForTools();
          const data = await api.autoDialVet({
            lat: loc.lat,
            lng: loc.lng,
            context,
            session_id: sessionId,
          });
          // Record locally for the Results page
          if (data.call_id) {
            onCallResult?.({
              kind: 'vet',
              call_id: data.call_id,
              status: data.status,
              placeName: data.place?.name,
              placePhone: data.place?.phone,
              placeAddress: data.place?.address,
            });
          }
          return {
            ...data,
            location_source: loc.source,
            ...(loc.note ? { location_note: loc.note } : {}),
          };
        } catch (err) {
          return { error: 'auto-dial vet failed', details: String(err?.message || err) };
        }
      },

      auto_dial_shelters: async ({ context } = {}) => {
        try {
          const loc = await resolveLatLngForTools();
          const data = await api.autoDialShelter({
            lat: loc.lat,
            lng: loc.lng,
            context,
            session_id: sessionId,
          });
          if (data.call_id) {
            onCallResult?.({
              kind: 'foster',
              call_id: data.call_id,
              status: data.status,
              placeName: data.place?.name,
              placePhone: data.place?.phone,
              placeAddress: data.place?.address,
            });
          }
          return {
            ...data,
            location_source: loc.source,
            ...(loc.note ? { location_note: loc.note } : {}),
          };
        } catch (err) {
          return { error: 'auto-dial shelter failed', details: String(err?.message || err) };
        }
      },

      get_call_status: async ({ call_id }) => {
        try {
          return await api.getCallStatus(call_id);
        } catch (err) {
          return { error: 'status check failed', details: String(err) };
        }
      },
    };
  }, [sessionId, onCallResult]);

  const conversation = useConversation({
    clientTools,
    onUnhandledClientToolCall: (call) => {
      console.warn(
        '[PawGuard] ElevenLabs requested a client tool that is not implemented:',
        call?.tool_name,
        call
      );
    },
    onConnect: () => setStatus('active'),
    onDisconnect: () => setStatus('idle'),
    onError: (e) => {
      console.error('voice agent error', e);
      setError(e?.message || 'Voice agent error');
    },
    onModeChange: (mode) => {
      if (mode?.mode === 'speaking') setStatus('speaking');
      else if (mode?.mode === 'listening') setStatus('active');
    },
  });

  const start = useCallback(async () => {
    if (!AGENT_ID) {
      setError('Missing VITE_ELEVENLABS_AGENT_ID');
      return;
    }
    setError(null);
    setStatus('connecting');
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      await conversation.startSession({
        agentId: AGENT_ID,
        dynamicVariables: { session_id: sessionId },
      });
    } catch (err) {
      console.error(err);
      setError(err?.message || 'Could not start voice');
      setStatus('idle');
    }
  }, [conversation, sessionId]);

  const stop = useCallback(async () => {
    try {
      await conversation.endSession();
    } finally {
      setStatus('idle');
    }
  }, [conversation]);

  const isActive = status === 'active' || status === 'speaking';

  let title;
  let subtitle;
  if (error) {
    title = 'Voice unavailable';
    subtitle = error;
  } else if (status === 'connecting') {
    title = 'Connecting…';
    subtitle = 'Setting up your AI vet assistant.';
  } else if (status === 'speaking') {
    title = 'PawGuard is speaking';
    subtitle = 'Listen up — tap to interrupt.';
  } else if (status === 'active') {
    title = 'Listening…';
    subtitle = 'Describe what you see. Tap to end.';
  } else {
    title = 'Talk to PawGuard';
    subtitle = 'Tap the mic to start a voice conversation.';
  }

  return (
    <section className="card voice-card" aria-live="polite">
      <div className="voice-info">
        <span className="voice-title">{title}</span>
        <span className={`voice-sub ${error ? 'error' : ''}`}>{subtitle}</span>
      </div>
      <button
        type="button"
        onClick={isActive ? stop : start}
        className={`voice-btn ${isActive ? 'active' : ''} ${
          status === 'speaking' ? 'speaking' : ''
        }`}
        aria-label={isActive ? 'End conversation' : 'Start conversation'}
      >
        <span className="ring" />
        {isActive ? '■' : '🎙'}
      </button>
    </section>
  );
}
