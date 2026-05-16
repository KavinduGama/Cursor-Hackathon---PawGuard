import { useNavigate } from 'react-router-dom';
import {
  BellIcon,
  BrainIcon,
  CameraPhoneIcon,
  MenuIcon,
  PawIcon,
  PeopleHeartIcon,
  PhoneIcon,
} from '../components/AppIcons.jsx';
import BottomNav from '../components/BottomNav.jsx';
import HeroIllustration from '../components/HeroIllustration.jsx';

function StepConnector() {
  return (
    <div className="landing-step-connector" aria-hidden>
      <svg width="40" height="12" viewBox="0 0 40 12" fill="none">
        <path
          d="M2 6h34M34 6l-4-4M34 6l-4 4"
          stroke="currentColor"
          strokeWidth="1.65"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray="3 4"
          opacity={0.45}
        />
      </svg>
    </div>
  );
}

export default function Landing() {
  const navigate = useNavigate();
  const goRescue = () => navigate('/session', { state: { autoStart: true } });

  return (
    <div className="app-shell landing-shell">
      <main className="page landing-page">
        <header className="landing-topbar">
          <div className="landing-brand-cluster">
            <span className="landing-logo-chip" aria-hidden>
              <PawIcon size={30} />
            </span>
            <div className="brand-copy">
              <div className="brand-name">PawGuard</div>
              <p className="brand-tagline">Animal rescue assistant</p>
            </div>
          </div>
          <button
            type="button"
            className="landing-menu-btn icon-btn muted"
            aria-label="Menu"
          >
            <MenuIcon size={21} strokeWidth={2} />
          </button>
        </header>

        <section className="landing-hero-mock card-mock-glow">
          <div className="landing-hero-row">
            <div className="landing-hero-copy">
              <h2>Help an animal in need</h2>
              <p className="sub">
                Talk to PawGuard and we&apos;ll route a vet or shelter to you.
              </p>
            </div>
            <div className="landing-hero-art" aria-hidden>
              <HeroIllustration />
            </div>
          </div>
          <button type="button" className="landing-start-btn" onClick={goRescue}>
            <span className="landing-start-icon" aria-hidden>
              <BellIcon size={20} strokeWidth={2} />
            </span>
            Start rescue
          </button>
        </section>

        <section className="landing-how-stack card bordered-how">
          <span className="landing-how-label">HOW IT WORKS</span>
          <h3>Help in 3 Simple Steps</h3>

          <div className="landing-how-flow">
            <article className="landing-step-card">
              <span className="landing-step-disk" aria-hidden>
                <CameraPhoneIcon size={22} strokeWidth={1.85} />
              </span>
              <span className="landing-step-chip">1</span>
              <h4>Show the animal</h4>
              <p>Use your camera to show us the animal in need.</p>
            </article>
            <StepConnector />
            <article className="landing-step-card">
              <span className="landing-step-disk" aria-hidden>
                <BrainIcon size={22} strokeWidth={1.85} />
              </span>
              <span className="landing-step-chip">2</span>
              <h4>AI analyzes instantly</h4>
              <p>Our AI checks the condition and tells you what&apos;s happening.</p>
            </article>
            <StepConnector />
            <article className="landing-step-card">
              <span className="landing-step-disk" aria-hidden>
                <PhoneIcon size={22} strokeWidth={1.85} />
              </span>
              <span className="landing-step-chip">3</span>
              <h4>Help is contacted</h4>
              <p>
                If it&apos;s serious, we call the nearest vet and keep you updated.
              </p>
            </article>
          </div>
        </section>

        <button type="button" className="landing-bottom-cta" onClick={goRescue}>
          <span className="landing-bottom-cta-icon" aria-hidden>
            <PeopleHeartIcon size={26} strokeWidth={1.85} />
          </span>
          <span className="landing-bottom-cta-copy">
            <span className="landing-bottom-cta-title">Ready to save a life?</span>
            <span className="landing-bottom-cta-sub">
              Every second matters. Let&apos;s make a difference together.
            </span>
          </span>
          <span className="landing-bottom-cta-arrow" aria-hidden>
            →
          </span>
        </button>
      </main>

      <BottomNav />
    </div>
  );
}
