function Svg({ size = 20, children, strokeWidth = 1.9 }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {children}
    </svg>
  );
}

/** Microphone with slash — user mic muted during voice session */
export function MicMutedIcon({ size = 22, strokeWidth: sw = 2 }) {
  return (
    <Svg size={size} strokeWidth={sw}>
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" x2="12" y1="19" y2="23" />
      <line x1="8" x2="16" y1="23" y2="23" />
      <line x1="2" x2="22" y1="22" y2="2" />
    </Svg>
  );
}

export function MenuIcon({ size = 22, strokeWidth: sw = 2 }) {
  return (
    <Svg size={size} strokeWidth={sw}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </Svg>
  );
}

export function BellIcon({ size = 22, strokeWidth = 2 }) {
  return (
    <Svg size={size} strokeWidth={strokeWidth}>
      <path d="M12 21a2 2 0 0 0 2-2H10a2 2 0 0 0 2 2Z" />
      <path d="M6 8a6 6 0 1 1 12 0c0 4.5 1.7 6 3 7H3c1.3-1 3-2.5 3-7" />
      <path d="M10 8V6a2 2 0 1 1 4 0v2" />
    </Svg>
  );
}

/** Decorative “community + rescue” motif for teal CTA bar */
export function PeopleHeartIcon({ size = 26, strokeWidth: sw = 1.85 }) {
  return (
    <Svg size={size} strokeWidth={sw}>
      <circle cx="8.5" cy="8.5" r="2.4" />
      <path d="M4 20v-2a4 4 0 0 1 8 0v2" />
      <circle cx="17.5" cy="8.5" r="2.4" />
      <path d="M13 20v-2a4 4 0 0 1 8 0v2" />
      <path d="m12 12.8 1-.8 4.2 6.8H6.8Z" strokeLinejoin="round" />
    </Svg>
  );
}

export function HomeIcon({ size = 20 }) {
  return (
    <Svg size={size}>
      <path d="M3 10.5 12 3l9 7.5" />
      <path d="M5 9.5V20h14V9.5" />
      <path d="M10 20v-5h4v5" />
    </Svg>
  );
}

export function MapPinIcon({ size = 20 }) {
  return (
    <Svg size={size}>
      <path d="M12 22s7-6.4 7-12a7 7 0 1 0-14 0c0 5.6 7 12 7 12Z" />
      <circle cx="12" cy="10" r="2.6" />
    </Svg>
  );
}

export function HeartIcon({ size = 20 }) {
  return (
    <Svg size={size}>
      <path d="M20.4 5.6a5 5 0 0 0-7 0L12 7l-1.4-1.4a5 5 0 0 0-7 7L12 21l8.4-8.4a5 5 0 0 0 0-7Z" />
    </Svg>
  );
}

export function UserIcon({ size = 20 }) {
  return (
    <Svg size={size}>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M4.5 20c.8-3.4 3.7-5.4 7.5-5.4s6.7 2 7.5 5.4" />
    </Svg>
  );
}

export function PhoneIcon({ size = 20 }) {
  return (
    <Svg size={size}>
      <path d="M7.3 2.8c.5-.5 1.4-.5 1.9 0l2.2 2.2c.5.5.5 1.3 0 1.8L9.9 8.3c-.4.4-.5 1.1-.2 1.7a15.4 15.4 0 0 0 4.4 4.4c.6.3 1.3.2 1.7-.2l1.5-1.5c.5-.5 1.3-.5 1.8 0l2.2 2.2c.5.5.5 1.4 0 1.9l-1.2 1.2a3.5 3.5 0 0 1-3.3.9C10.8 17.7 6.3 13.2 5.1 7a3.5 3.5 0 0 1 .9-3.3Z" />
    </Svg>
  );
}

export function BrainIcon({ size = 20 }) {
  return (
    <Svg size={size}>
      <path d="M9.4 3.2a2.9 2.9 0 0 0-4.9 2.1v.9a2.7 2.7 0 0 0-1 4.8 3 3 0 0 0 2 5.3h3.2" />
      <path d="M14.6 3.2a2.9 2.9 0 0 1 4.9 2.1v.9a2.7 2.7 0 0 1 1 4.8 3 3 0 0 1-2 5.3h-3.2" />
      <path d="M9.2 6.3a2.6 2.6 0 0 1 2.8 2.6V21" />
      <path d="M14.8 6.3A2.6 2.6 0 0 0 12 8.9" />
      <path d="M6.5 10.8h2.7" />
      <path d="M14.8 10.8h2.7" />
      <path d="M6.9 15h2.2" />
      <path d="M14.9 15h2.2" />
    </Svg>
  );
}

export function CameraPhoneIcon({ size = 20 }) {
  return (
    <Svg size={size}>
      <rect x="7" y="2.5" width="10" height="19" rx="2.2" />
      <path d="M9.3 8h5.4l.8 1.4v3.4H8.5V9.4L9.3 8Z" />
      <circle cx="12" cy="10.8" r="1.4" />
      <path d="M10.4 18h3.2" />
    </Svg>
  );
}

export function RescueIcon({ size = 20 }) {
  return (
    <Svg size={size}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7.5v9M7.5 12h9" />
    </Svg>
  );
}

export function PawIcon({ size = 20 }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
    >
      <ellipse cx="12" cy="16.2" rx="4.6" ry="3.8" />
      <ellipse cx="5.6" cy="11" rx="1.9" ry="2.4" />
      <ellipse cx="18.4" cy="11" rx="1.9" ry="2.4" />
      <ellipse cx="9" cy="6.2" rx="1.7" ry="2.2" />
      <ellipse cx="15" cy="6.2" rx="1.7" ry="2.2" />
    </svg>
  );
}

export function ClinicIcon({ size = 20 }) {
  return (
    <Svg size={size}>
      <rect x="4" y="4.5" width="16" height="15.5" rx="2" />
      <path d="M12 8v7M8.5 11.5h7" />
      <path d="M9 20v-3h6v3" />
    </Svg>
  );
}
