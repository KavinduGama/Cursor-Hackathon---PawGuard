import { useLocation, useNavigate } from 'react-router-dom';

const ITEMS = [
  { to: '/', label: 'Home', icon: '🏠' },
  { to: '/map', label: 'Map', icon: '📍', disabled: true },
  { to: '/session', label: '', icon: '＋', fab: true },
  { to: '/results', label: 'Rescues', icon: '🐾' },
  { to: '/profile', label: 'Profile', icon: '👤', disabled: true },
];

export default function BottomNav() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <nav className="bottom-nav" aria-label="Primary">
      {ITEMS.map((item) => {
        const active = pathname === item.to;
        if (item.fab) {
          return (
            <button
              key="fab"
              type="button"
              className="nav-fab"
              onClick={() => navigate(item.to)}
              aria-label="Start rescue"
            >
              {item.icon}
            </button>
          );
        }
        return (
          <button
            key={item.to}
            type="button"
            className={`nav-item ${active ? 'active' : ''}`}
            onClick={() => !item.disabled && navigate(item.to)}
            disabled={item.disabled}
            style={item.disabled ? { opacity: 0.45 } : undefined}
          >
            <span className="icon">{item.icon}</span>
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
