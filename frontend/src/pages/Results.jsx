import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import ResultCard from '../components/ResultCard.jsx';
import BottomNav from '../components/BottomNav.jsx';

const SEVERITY_LABEL = {
  CRITICAL: 'Critical',
  MODERATE: 'Moderate',
  MILD: 'Mild',
  UNKNOWN: 'Observed',
};

export default function Results() {
  const navigate = useNavigate();
  const [enriched, setEnriched] = useState([]);

  const last = useMemo(() => {
    try {
      const raw = sessionStorage.getItem('pawguard:lastSession');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    if (!last?.callResults?.length) return;
    let cancelled = false;
    (async () => {
      const results = await Promise.all(
        last.callResults.map(async (r) => {
          if (!r.call_id) return r;
          try {
            const status = await api.getCallStatus(r.call_id);
            return { ...r, ...status };
          } catch {
            return r;
          }
        })
      );
      if (!cancelled) setEnriched(results);
    })();
    return () => {
      cancelled = true;
    };
  }, [last]);

  if (!last) {
    return (
      <div className="app-shell">
        <main className="page stack">
          <header className="header-row">
            <button
              className="icon-btn"
              onClick={() => navigate('/')}
              aria-label="Back"
            >
              ←
            </button>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 800 }}>Rescues</h2>
            <div style={{ width: 40 }} />
          </header>

          <div className="card" style={{ textAlign: 'center', padding: '2rem 1rem' }}>
            <div style={{ fontSize: '3rem' }}>🐾</div>
            <h3 style={{ margin: '0.5rem 0 0.25rem' }}>No rescue session yet</h3>
            <p className="card-meta">
              Start a rescue and your case summary will appear here.
            </p>
            <button
              className="btn btn-primary"
              style={{ marginTop: '1rem' }}
              onClick={() => navigate('/session')}
            >
              🐾 Begin a rescue
            </button>
          </div>
        </main>
        <BottomNav />
      </div>
    );
  }

  const parsed = last.observation?.parsed;
  const severity = (last.observation?.severity || 'UNKNOWN').toUpperCase();
  const results = enriched.length ? enriched : last.callResults || [];

  const endedAt = last.endedAt
    ? new Date(last.endedAt).toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '—';

  const callPlaced = results.length > 0;
  const callCompleted = results.some(
    (r) => (r.status || '').toLowerCase() === 'completed'
  );

  const timeline = [
    { title: 'Rescue reported', sub: endedAt, state: 'done' },
    {
      title: 'Triage complete',
      sub: parsed
        ? `${parsed.animal || 'Animal'} — ${SEVERITY_LABEL[severity] || severity}`
        : 'Awaiting vision data',
      state: parsed ? 'done' : 'active',
    },
    {
      title: 'Vet / foster contacted',
      sub: callPlaced
        ? `${results.length} call${results.length === 1 ? '' : 's'} placed`
        : 'No call placed',
      state: callPlaced ? 'done' : 'pending',
    },
    {
      title: 'Care arranged',
      sub: callCompleted
        ? 'Confirmed by the clinic'
        : callPlaced
        ? 'Waiting for response'
        : 'Pending',
      state: callCompleted ? 'done' : callPlaced ? 'active' : 'pending',
    },
  ];

  return (
    <div className="app-shell">
      <main className="page stack">
        <header className="header-row">
          <button
            className="icon-btn"
            onClick={() => navigate('/')}
            aria-label="Back"
          >
            ←
          </button>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 800 }}>Rescue summary</h2>
          <button className="icon-btn" aria-label="Share">
            ↗
          </button>
        </header>

        <section className="case-hero">
          {severity === 'CRITICAL' && (
            <span className="urgent-badge">Urgent</span>
          )}
          <h2>{parsed?.animal || 'Unknown animal'}</h2>
          <div className="case-desc">
            {parsed?.guidance ||
              (parsed?.visible_injuries?.length
                ? `Visible: ${parsed.visible_injuries.join(', ')}`
                : 'Triage completed by PawGuard AI.')}
          </div>

          <div className="case-meta-grid">
            <div className="item">
              Severity
              <strong>{SEVERITY_LABEL[severity] || severity}</strong>
            </div>
            <div className="item">
              Ended
              <strong>{endedAt}</strong>
            </div>
          </div>
        </section>

        <div className="card">
          <div className="card-title-row">
            <span className="card-title">Rescue progress</span>
            <span className="card-meta">Every update brings hope 💚</span>
          </div>
          <div className="timeline">
            {timeline.map((step, i) => (
              <div key={i} className={`timeline-step ${step.state}`}>
                <div className={`marker ${step.state}`}>
                  {step.state === 'done' ? '✓' : i + 1}
                </div>
                <div className="line" />
                <div>
                  <div className="step-title">{step.title}</div>
                  <div className="step-sub">{step.sub}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {parsed?.visible_injuries?.length > 0 && (
          <div className="card">
            <div className="card-title-row">
              <span className="card-title">Diagnosis details</span>
            </div>
            <div className="label" style={{ marginTop: 0 }}>
              Visible injuries
            </div>
            <div className="injury-tags">
              {parsed.visible_injuries.map((inj, i) => (
                <span className="injury-tag" key={i}>
                  {inj}
                </span>
              ))}
            </div>
            {parsed.confidence != null && (
              <div className="card-meta" style={{ marginTop: '0.65rem' }}>
                Confidence: {(Number(parsed.confidence) * 100).toFixed(0)}%
              </div>
            )}
          </div>
        )}

        {results.length > 0 && (
          <div className="stack" style={{ gap: '0.75rem' }}>
            <div
              className="card-title"
              style={{ paddingLeft: '0.25rem', marginTop: '0.25rem' }}
            >
              Calls placed
            </div>
            {results.map((r) => (
              <ResultCard key={r.call_id || Math.random()} result={r} />
            ))}
          </div>
        )}

        <div className="row" style={{ gap: '0.5rem', marginTop: '0.25rem' }}>
          <button
            className="btn btn-primary btn-block"
            onClick={() => navigate('/session')}
          >
            🐾 New rescue
          </button>
          <button className="btn btn-ghost" onClick={() => navigate('/')}>
            Home
          </button>
        </div>
      </main>

      <BottomNav />
    </div>
  );
}
