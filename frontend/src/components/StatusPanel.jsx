const SEVERITY_LABEL = {
  CRITICAL: 'Critical',
  MODERATE: 'Moderate',
  MILD: 'Mild',
  UNKNOWN: 'Observing',
};

export default function StatusPanel({ observation, frameCount, cameraOpen }) {
  const parsed = observation?.parsed;
  const severity = (observation?.severity || 'UNKNOWN').toUpperCase();
  const sevClass = severity.toLowerCase();

  const animal = parsed?.animal || (cameraOpen ? 'Looking…' : 'Camera is off');
  const injuries = parsed?.visible_injuries || [];
  const guidance = parsed?.guidance;
  const changes = parsed?.changes_since_last;

  return (
    <section className="card status-card" aria-live="polite">
      <div className="header-row">
        <span className="card-title">PawGuard sees</span>
        <span className={`severity-pill ${sevClass}`}>
          <span className="dot" /> {SEVERITY_LABEL[severity] || severity}
        </span>
      </div>

      <div className="animal">{animal}</div>

      {!parsed && cameraOpen && (
        <div className="placeholder-text" style={{ marginTop: '0.4rem' }}>
          Point your phone at the animal and hold steady. Analysis will appear
          here in a moment.
        </div>
      )}

      {!parsed && !cameraOpen && (
        <div className="placeholder-text" style={{ marginTop: '0.4rem' }}>
          Turn the camera back on to resume live triage.
        </div>
      )}

      {injuries.length > 0 && (
        <>
          <div className="label">Visible injuries</div>
          <div className="injury-tags">
            {injuries.map((inj, i) => (
              <span className="injury-tag" key={i}>
                {inj}
              </span>
            ))}
          </div>
        </>
      )}

      {changes && changes.trim() && (
        <>
          <div className="label">Since last frame</div>
          <div className="muted-line">{changes}</div>
        </>
      )}

      {guidance && <div className="guidance-box">{guidance}</div>}

      <div className="card-meta" style={{ marginTop: '0.6rem' }}>
        {frameCount} frame{frameCount === 1 ? '' : 's'} analyzed
      </div>
    </section>
  );
}
