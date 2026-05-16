import { useNavigate } from 'react-router-dom';
import {
  BrainIcon,
  CameraPhoneIcon,
  PawIcon,
  PhoneIcon,
  RescueIcon,
} from '../components/AppIcons.jsx';
import BottomNav from '../components/BottomNav.jsx';
import MicIcon from '../components/MicIcon.jsx';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="app-shell">
      <main className="page">
        <header className="brand-header" aria-label="PawGuard">
          <span className="brand-logo" aria-hidden>
            <PawIcon size={25} />
          </span>
          <div className="brand-copy">
            <div className="brand-name">PawGuard</div>
            <p className="brand-tagline">Animal rescue assistant</p>
          </div>
        </header>

        <section className="card hero-card-launch">
          <div className="hero-card-body">
            <h2>Help an animal in need</h2>
            <p className="sub">
              Talk to PawGuard and we&apos;ll route a vet or shelter to you.
            </p>
          </div>
          <div className="hero-card-art" aria-hidden>
            🐶🐱
          </div>
        </section>

        <button
          type="button"
          className="card voice-teaser-card"
          aria-label="Start a rescue session to talk to PawGuard"
          onClick={() => navigate('/session', { state: { autoStart: true } })}
        >
          <span className="voice-teaser-btn" aria-hidden>
            <MicIcon size={40} />
          </span>
          <p className="voice-teaser-title">
            Tap to talk to <span className="accent-name">PawGuard</span>
          </p>
          <p className="voice-teaser-hint">
            Voice starts live during a rescue — begin a session to connect.
          </p>
        </button>

        <section className="card how-section stack">
          <span className="how-label-pill">How it works</span>
          <h3>Help in 3 simple steps</h3>
          <div className="how-steps">
            <div className="how-step">
              <span className="how-step-icon" aria-hidden>
                <CameraPhoneIcon size={24} />
              </span>
              <span className="how-step-num">1</span>
              <h4>Show the animal</h4>
              <p>Use your camera to show the animal in need.</p>
            </div>
            <span className="how-dash" aria-hidden>
              ─
            </span>
            <div className="how-step">
              <span className="how-step-icon" aria-hidden>
                <BrainIcon size={24} />
              </span>
              <span className="how-step-num">2</span>
              <h4>AI analyzes instantly</h4>
              <p>Our AI checks the condition and tells you what&apos;s happening.</p>
            </div>
            <span className="how-dash" aria-hidden>
              ─
            </span>
            <div className="how-step">
              <span className="how-step-icon" aria-hidden>
                <PhoneIcon size={24} />
              </span>
              <span className="how-step-num">3</span>
              <h4>Help is contacted</h4>
              <p>If it&apos;s serious, we call the nearest vet and keep you updated.</p>
            </div>
          </div>
        </section>

        <button
          type="button"
          className="cta-card"
          onClick={() => navigate('/session', { state: { autoStart: true } })}
        >
          <span className="cta-card-icon-circle" aria-hidden>
            <RescueIcon size={24} />
          </span>
          <span className="cta-card-body">
            <span className="title">Ready to save a life?</span>
            <span className="cta-subtitle">
              Every second matters. Let&apos;s make a difference together.
            </span>
          </span>
          <span className="arrow" aria-hidden>
            →
          </span>
        </button>
      </main>

      <BottomNav />
    </div>
  );
}
