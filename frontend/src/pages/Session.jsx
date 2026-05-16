import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useCamera } from '../hooks/useCamera.js';
import { useVisionLoop } from '../hooks/useVisionLoop.js';
import { api } from '../lib/api.js';
import Camera from '../components/Camera.jsx';
import StatusPanel from '../components/StatusPanel.jsx';
import VoiceAgent from '../components/VoiceAgent.jsx';
import BottomNav from '../components/BottomNav.jsx';

export default function Session() {
  const navigate = useNavigate();
  const { state: routeState } = useLocation();
  const autoStart = !!routeState?.autoStart;
  const [sessionId, setSessionId] = useState(null);
  const [bootError, setBootError] = useState(null);
  const [cameraOpen, setCameraOpen] = useState(true);
  const callResultsRef = useRef([]);

  const { videoRef, state: cameraState, captureFrame } = useCamera({
    facingMode: 'environment',
    enabled: cameraOpen,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.startVisionSession();
        if (!cancelled) setSessionId(data.session_id);
      } catch (err) {
        if (!cancelled) {
          setBootError(
            'Backend unreachable — start the FastAPI server or check VITE_API_BASE.'
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const { observation, frameCount } = useVisionLoop({
    sessionId,
    captureFrame,
    active: cameraOpen && cameraState.status === 'ready' && !!sessionId,
  });

  const upsertCallResult = useCallback((result) => {
    const existingIndex = callResultsRef.current.findIndex(
      (r) => r.call_id && r.call_id === result.call_id
    );
    if (existingIndex >= 0) {
      callResultsRef.current = callResultsRef.current.map((r, i) =>
        i === existingIndex ? { ...r, ...result } : r
      );
      return;
    }
    callResultsRef.current = [...callResultsRef.current, result];
  }, []);

  const handleCallResult = useCallback(
    (result) => {
      upsertCallResult(result);
    },
    [upsertCallResult]
  );

  const handleCareArranged = useCallback(
    (result) => {
      upsertCallResult(result);
      sessionStorage.setItem(
        'pawguard:lastSession',
        JSON.stringify({
          sessionId,
          observation,
          callResults: callResultsRef.current,
          arrangedResult: result,
          endedAt: Date.now(),
        })
      );
      navigate('/results', { replace: true });
    },
    [navigate, observation, sessionId, upsertCallResult]
  );

  function exit() {
    sessionStorage.setItem(
      'pawguard:lastSession',
      JSON.stringify({
        sessionId,
        observation,
        callResults: callResultsRef.current,
        endedAt: Date.now(),
      })
    );
    navigate('/results');
  }

  return (
    <div className="app-shell">
      <main className="page session-page stack">
        <header className="session-top">
          <button
            className="icon-btn"
            type="button"
            onClick={exit}
            aria-label="End rescue"
          >
            ←
          </button>
          <h2>Live triage</h2>
          <div className="live-chip">
            <span className="dot" />
            Live
          </div>
        </header>

        {bootError && <div className="banner error">{bootError}</div>}

        <Camera
          videoRef={videoRef}
          status={cameraState.status}
          isOpen={cameraOpen}
          frameCount={frameCount}
          onToggle={() => setCameraOpen((v) => !v)}
        />

        <StatusPanel
          observation={observation}
          frameCount={frameCount}
          cameraOpen={cameraOpen}
        />

        {sessionId ? (
          <VoiceAgent
            sessionId={sessionId}
            autoStart={autoStart}
            onCallResult={handleCallResult}
            onCareArranged={handleCareArranged}
          />
        ) : (
          <div className="card placeholder-text">Setting up your session…</div>
        )}

        <button className="btn btn-ghost btn-block" type="button" onClick={exit}>
          End rescue & see summary
        </button>
      </main>

      <BottomNav />
    </div>
  );
}
