import { useNavigate } from 'react-router-dom';
import BottomNav from '../components/BottomNav.jsx';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="app-shell">
      <main className="page">
        <header className="header-row">
          <div>
            <div className="greeting">Hi there 👋</div>
          </div>
          <div className="header-actions">
            <button
              className="icon-btn"
              aria-label="Notifications"
              onClick={() => {}}
            >
              🔔
            </button>
            <div className="avatar" aria-hidden>
              P
            </div>
          </div>
        </header>

        <section className="hero">
          <h1>
            Let&apos;s make their <span className="accent">tomorrow better</span>
          </h1>
          <p className="sub">
            Found an injured animal? PawGuard sees through your camera, talks
            you through triage, and calls the nearest vet for you.
          </p>
        </section>

        <div className="hero-illustration" aria-hidden>
          🐶🐾🐱
        </div>

        <button
          type="button"
          className="cta-card"
          onClick={() => navigate('/session')}
        >
          <div>
            <span className="label">Start now</span>
            <span className="title">Begin a rescue</span>
          </div>
          <span className="arrow" aria-hidden>
            →
          </span>
        </button>

        <div className="stats-card">
          <div className="stat">
            <span className="num">128</span>
            <span className="lbl">Rescued</span>
          </div>
          <div className="stat">
            <span className="num">56</span>
            <span className="lbl">Volunteers</span>
          </div>
          <div className="stat">
            <span className="num">320</span>
            <span className="lbl">Clinics</span>
          </div>
        </div>

        <div className="card">
          <div className="card-title-row">
            <span className="card-title">How PawGuard helps</span>
          </div>
          <div className="help-grid">
            <button
              className="help-tile"
              type="button"
              onClick={() => navigate('/session')}
            >
              <span className="tile-icon green">👁️</span>
              <span className="tile-title">Live triage</span>
              <span className="tile-sub">Gemini watches your camera</span>
            </button>
            <button className="help-tile" type="button">
              <span className="tile-icon amber">🎙️</span>
              <span className="tile-title">Voice vet</span>
              <span className="tile-sub">ElevenLabs assistant</span>
            </button>
            <button className="help-tile" type="button">
              <span className="tile-icon blue">📞</span>
              <span className="tile-title">Auto-call</span>
              <span className="tile-sub">Reach a clinic for you</span>
            </button>
          </div>
        </div>

        <div className="card card-tinted">
          <div className="row" style={{ gap: '0.75rem' }}>
            <div
              className="tile-icon green"
              style={{ width: 36, height: 36, fontSize: '1.1rem' }}
            >
              💚
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: '0.92rem' }}>
                Every action saves a life
              </div>
              <div className="card-meta" style={{ marginTop: 2 }}>
                Tap “Begin a rescue” to start — your camera does the rest.
              </div>
            </div>
          </div>
        </div>
      </main>

      <BottomNav />
    </div>
  );
}
