import { useLocation, useNavigate } from 'react-router-dom';
import {
  HomeIcon,
  PhoneIcon,
  UserIcon,
} from './AppIcons.jsx';

const ITEMS = [
  { to: '/', label: 'Home', icon: HomeIcon },
  { to: '/session', label: 'Call', icon: PhoneIcon },
  { to: '/profile', label: 'Profile', icon: UserIcon, disabled: true },
];

export default function BottomNav() {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <nav className="bottom-nav" aria-label="Primary">
      {ITEMS.map((item) => {
        const active =
          pathname === item.to ||
          (item.to === '/' ? false : pathname.startsWith(item.to) && item.to !== '/profile');
        const Icon = item.icon;
        return (
          <button
            key={item.to}
            type="button"
            className={`nav-item ${active ? 'active' : ''}`}
            onClick={() => !item.disabled && navigate(item.to)}
            disabled={item.disabled}
            style={item.disabled ? { opacity: 0.45 } : undefined}
          >
            <span className="icon">
              <Icon size={20} />
            </span>
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
