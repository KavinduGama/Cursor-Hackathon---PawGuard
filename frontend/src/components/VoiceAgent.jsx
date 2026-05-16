import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useConversation } from '@elevenlabs/react';
import { api } from '../lib/api.js';
import { resolveLatLngForTools, safeParseAnalysis } from '../lib/geo.js';
import MicIcon from './MicIcon.jsx';

const AGENT_ID = import.meta.env.VITE_ELEVENLABS_AGENT_ID || '';

/**
 * Triage Agent (Agent 1) — the voice the user talks to.
 *
 * Client tools registered on the ElevenLabs dashboard agent (names must
 * match exactly — use any ONE of the aliases below for "find vets"):
 *
 *   - get_vision_analysis()
 *   - find_emergency_vet | find_emergency_vets | find_nearby_vets  → list vets (no dial)
 *   - find_foster_care                 → list foster/shelters (no dial)
 *   - auto_dial_vets({context?})       → combined find+call sequential loop
 *   - auto_dial_fosters({context?})    → combined find+call sequential loop
 *   - call_vets_sequentially({places, context?})     → call a pre-selected list
 *   - call_shelters_sequentially({places, context?}) → call a pre-selected list
 *   - get_call_status({call_id})       → manual progress check (the watcher pushes
 *                                        updates automatically, so the agent does
 *                                        NOT need to poll this).
 *
 * The auto_dial_* tools return immediately with a `call_id`; the agent should
 * keep talking to the user. A background watcher in this component polls
 * /api/calls/{call_id}/status every few seconds and pushes a
 * `sendUserMessage()` into the live conversation each time a new attempt
 * completes (and on the final result), so the agent actively narrates
 * progress.
 *
 * If the browser keeps asking for location: use HTTPS (or localhost), allow the
 * prompt once, OR set VITE_USE_DEMO_LOCATION=1 in frontend/.env to skip GPS entirely.
 */
export default function VoiceAgent({
  sessionId,
  autoStart = false,
  onCallResult,
  onCareArranged,
}) {
  const [status, setStatus] = useState('idle'); // idle | connecting | active | speaking
  const [error, setError] = useState(null);

  // Ref to the live conversation object so watcher closures always see the
  // latest one without re-running their setTimeout chain.
  const conversationRef = useRef(null);
  // Map<call_id, { lastIndex: number, terminal: boolean, timer: any }>
  const watchersRef = useRef(new Map());
  // Guards the one-shot auto-start when arriving from Landing.
  const autoStartedRef = useRef(false);
  const autoExitTimerRef = useRef(null);

  const stopWatcher = useCallback((callId) => {
    const w = watchersRef.current.get(callId);
    if (w?.timer) clearTimeout(w.timer);
    watchersRef.current.delete(callId);
  }, []);

  const stopAllWatchers = useCallback(() => {
    for (const [, w] of watchersRef.current) {
      if (w?.timer) clearTimeout(w.timer);
    }
    watchersRef.current.clear();
  }, []);

  const pushToConversation = useCallback((text) => {
    const conv = conversationRef.current;
    if (!conv?.sendUserMessage) return;
    try {
      conv.sendUserMessage(
        `[SYSTEM UPDATE — do not repeat verbatim, summarise naturally to the user] ${text}`
      );
    } catch (e) {
      console.warn('[PawGuard] sendUserMessage failed', e);
    }
  }, []);

  const startWatcher = useCallback(
    (callId, kind) => {
      if (!callId || watchersRef.current.has(callId)) return;
      const state = { lastIndex: -1, terminal: false, timer: null };
      watchersRef.current.set(callId, state);

      const tick = async () => {
        if (state.terminal) return;
        try {
          const data = await api.getCallStatus(callId);
          const attempts = Array.isArray(data.attempts) ? data.attempts : [];

          // Announce any newly-completed attempts. `available` is tri-state:
          //   true  -> definitively available (push success update)
          //   false -> definitively unavailable (push "trying next")
          //   null  -> unknown — stay silent and let the terminal update speak
          for (let i = state.lastIndex + 1; i < attempts.length; i++) {
            const a = attempts[i];
            if (a.available === true) {
              const wait =
                a.wait_minutes != null ? `~${a.wait_minutes} min wait` : 'available';
              const who = a.contact_name ? `${a.contact_name} at ` : '';
              pushToConversation(
                [
                  `Auto-dial update (${kind}):`,
                  `${who}${a.place_name} confirmed — ${wait}.`,
                  a.notes || '',
                ]
                  .join(' ')
                  .trim()
              );
            } else if (a.available === false) {
              const reason = a.status === 'failed' ? 'call failed' : a.status;
              pushToConversation(
                `Auto-dial update (${kind}): ${a.place_name} unavailable (${reason}). Trying next.`
              );
            }
            state.lastIndex = i;
          }

          // Terminal events.
          if (data.status === 'completed' && data.successful_place) {
            const sp = data.successful_place;
            const who = data.contact_name ? `${data.contact_name} at ` : '';
            const wait =
              data.wait_minutes != null
                ? `Estimated wait ~${data.wait_minutes} minutes.`
                : '';
            pushToConversation(
              [
                `Auto-dial finished (${kind}):`,
                `${who}${sp.name} can take the animal.`,
                wait,
                sp.phone ? `Phone: ${sp.phone}.` : '',
                sp.address ? `Address: ${sp.address}.` : '',
                data.notes || '',
              ]
                .join(' ')
                .trim()
            );
            const arrangedResult = {
              kind,
              call_id: callId,
              status: data.status,
              available: true,
              wait_minutes: data.wait_minutes,
              contact_name: data.contact_name,
              notes: data.notes,
              summary: data.summary,
              placeName: sp.name,
              placePhone: sp.phone,
              placeAddress: sp.address,
              placeLat: sp.lat,
              placeLng: sp.lng,
            };
            onCallResult?.(arrangedResult);

            if (!autoExitTimerRef.current) {
              autoExitTimerRef.current = setTimeout(async () => {
                try {
                  await conversationRef.current?.endSession?.();
                } catch (err) {
                  console.warn('[PawGuard] voice auto-end failed', err);
                } finally {
                  autoExitTimerRef.current = null;
                  onCareArranged?.(arrangedResult);
                }
              }, 6000);
            }
            state.terminal = true;
          } else if (data.status === 'exhausted' || data.status === 'failed') {
            pushToConversation(
              `Auto-dial finished (${kind}): ${data.status} after ${attempts.length} attempt(s). ${
                data.notes || 'No place confirmed availability.'
              }`
            );
            state.terminal = true;
          }
        } catch (err) {
          // Transient errors are fine — keep polling.
        }

        if (!state.terminal) {
          state.timer = setTimeout(tick, 3000);
        } else {
          watchersRef.current.delete(callId);
        }
      };

      state.timer = setTimeout(tick, 1000);
    },
    [onCallResult, onCareArranged, pushToConversation]
  );

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

      find_foster_care: async (_params) => {
        try {
          const loc = await resolveLatLngForTools();
          const data = await api.findFoster(loc.lat, loc.lng);
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
          return { error: 'find_foster_care_failed', details: String(err?.message || err) };
        }
      },

      // ── Non-blocking sequential auto-dial ──────────────────────────────
      // Returns immediately with status="in_progress". A background watcher
      // (in this component) polls /api/calls/{call_id}/status and pushes a
      // sendUserMessage() each time a new attempt completes, plus a
      // final update when one place is reached or the loop is exhausted.
      auto_dial_vets: async ({ context } = {}) => {
        try {
          const loc = await resolveLatLngForTools();
          const data = await api.autoDialVet({
            lat: loc.lat,
            lng: loc.lng,
            context,
            session_id: sessionId,
          });
          if (data.call_id) {
            onCallResult?.({
              kind: 'vet',
              call_id: data.call_id,
              status: data.status,
              placeName: data.place?.name,
              placePhone: data.place?.phone,
              placeAddress: data.place?.address,
            });
            startWatcher(data.call_id, 'vet');
          }
          return {
            status: data.status,
            call_id: data.call_id,
            total_attempts_planned: data.total_attempts_planned ?? null,
            location_source: loc.source,
            ...(loc.note ? { location_note: loc.note } : {}),
            message:
              "Started calling vets one by one in the background. Keep the conversation going with the user — you'll receive a [SYSTEM UPDATE] message the moment any clinic answers or all calls are exhausted. Summarise it naturally when it arrives. Do NOT poll get_call_status.",
          };
        } catch (err) {
          return { error: 'auto_dial_vet_failed', details: String(err?.message || err) };
        }
      },

      auto_dial_fosters: async ({ context } = {}) => {
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
            startWatcher(data.call_id, 'foster');
          }
          return {
            status: data.status,
            call_id: data.call_id,
            total_attempts_planned: data.total_attempts_planned ?? null,
            location_source: loc.source,
            ...(loc.note ? { location_note: loc.note } : {}),
            message:
              "Started calling foster/shelters one by one in the background. Keep the conversation going with the user — you'll receive a [SYSTEM UPDATE] message the moment any place answers or all calls are exhausted. Summarise it naturally when it arrives. Do NOT poll get_call_status.",
          };
        } catch (err) {
          return { error: 'auto_dial_shelter_failed', details: String(err?.message || err) };
        }
      },

      // ── Split-flow: call a pre-selected list without re-searching ─────
      // The agent can call find_emergency_vet first, show the user the list,
      // then invoke call_vets_sequentially with the places array it received.
      call_vets_sequentially: async ({ places, context } = {}) => {
        try {
          if (!Array.isArray(places) || places.length === 0) {
            return {
              error: 'no_places',
              details:
                'Provide a "places" array (from find_emergency_vet results) to call.',
            };
          }
          const data = await api.dialList({
            kind: 'vet',
            places,
            context,
            session_id: sessionId,
          });
          if (data.call_id) {
            onCallResult?.({
              kind: 'vet',
              call_id: data.call_id,
              status: data.status,
              placeName: data.place?.name,
              placePhone: data.place?.phone,
              placeAddress: data.place?.address,
            });
            startWatcher(data.call_id, 'vet');
          }
          return {
            status: data.status,
            call_id: data.call_id,
            total_attempts_planned: data.total_attempts_planned ?? null,
            message:
              "Started calling the listed vets one by one. You'll receive [SYSTEM UPDATE] messages automatically. Summarise them naturally. Do NOT poll get_call_status.",
          };
        } catch (err) {
          return {
            error: 'call_vets_sequentially_failed',
            details: String(err?.message || err),
          };
        }
      },

      call_shelters_sequentially: async ({ places, context } = {}) => {
        try {
          if (!Array.isArray(places) || places.length === 0) {
            return {
              error: 'no_places',
              details:
                'Provide a "places" array (from find results) to call.',
            };
          }
          const data = await api.dialList({
            kind: 'foster',
            places,
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
            startWatcher(data.call_id, 'foster');
          }
          return {
            status: data.status,
            call_id: data.call_id,
            total_attempts_planned: data.total_attempts_planned ?? null,
            message:
              "Started calling the listed shelters one by one. You'll receive [SYSTEM UPDATE] messages automatically. Summarise them naturally. Do NOT poll get_call_status.",
          };
        } catch (err) {
          return {
            error: 'call_shelters_sequentially_failed',
            details: String(err?.message || err),
          };
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
  }, [sessionId, onCallResult, startWatcher]);

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

  // Keep the ref pointing at the latest conversation so the watcher's setTimeout
  // chain always uses the live object.
  useEffect(() => {
    conversationRef.current = conversation;
  }, [conversation]);

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
    stopAllWatchers();
    try {
      await conversation.endSession();
    } finally {
      setStatus('idle');
    }
  }, [conversation, stopAllWatchers]);

  // One-shot auto-start when arriving from Landing with `autoStart` route state.
  useEffect(() => {
    if (
      autoStart &&
      sessionId &&
      status === 'idle' &&
      !error &&
      AGENT_ID &&
      !autoStartedRef.current
    ) {
      autoStartedRef.current = true;
      start();
    }
  }, [autoStart, sessionId, status, error, start]);

  // Clear all watchers on unmount so timers don't leak.
  useEffect(() => {
    return () => {
      if (autoExitTimerRef.current) clearTimeout(autoExitTimerRef.current);
      stopAllWatchers();
    };
  }, [stopAllWatchers]);

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
    title = '';
    subtitle = '';
  }

  const showIdleHero = !error && status === 'idle';

  return (
    <section className="card voice-card voice-card--center" aria-live="polite">
      <button
        type="button"
        onClick={isActive ? stop : start}
        className={`voice-btn ${isActive ? 'active' : ''} ${
          status === 'speaking' ? 'speaking' : ''
        }`}
        aria-label={isActive ? 'End conversation' : 'Start conversation'}
      >
        <span className="ring" />
        {isActive ? (
          <span className="mic-icon mic-icon-stop" aria-hidden />
        ) : (
          <span className="mic-icon">
            <MicIcon size={34} />
          </span>
        )}
      </button>
      <div className="voice-info">
        {showIdleHero ? (
          <>
            <span className="voice-title">
              Tap to talk to{' '}
              <span className="voice-accent-name">PawGuard</span>
            </span>
            <span className="voice-sub">
              Describe what you see after you tap the mic.
            </span>
          </>
        ) : (
          <>
            {title ? <span className="voice-title">{title}</span> : null}
            <span className={`voice-sub ${error ? 'error' : ''}`}>{subtitle}</span>
          </>
        )}
      </div>
    </section>
  );
}
