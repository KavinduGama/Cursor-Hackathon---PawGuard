/**
 * Decorative pets + foliage for landing hero — approximates hi-fi mockup without raster art.
 */
export default function HeroIllustration({ className = '' }) {
  return (
    <svg
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 200 160"
      fill="none"
      aria-hidden
    >
      <ellipse cx="100" cy="148" rx="72" ry="10" fill="rgba(0,128,128,0.06)" />
      <path
        d="M154 52c16-22 42-34 42-34s-28 22-42 54c6-42 34-104 53-146"
        stroke="#3d9f9a"
        strokeWidth="3.8"
        strokeLinecap="round"
        opacity="0.62"
      />
      <path
        d="M44 62C28 40 2 28 2 28s26 26 41 61c6-62-10-154 55-246"
        stroke="#149191"
        strokeWidth="3.5"
        strokeLinecap="round"
        opacity="0.42"
      />
      <ellipse cx="88" cy="98" rx="38" ry="28" fill="#eab308" opacity="0.94" />
      <ellipse cx="88" cy="112" rx="22" ry="14" fill="#ca8a04" opacity="0.33" />
      <ellipse cx="64" cy="88" rx="14" ry="13" fill="#fcd34d" />
      <circle cx="73" cy="88" r="2.4" fill="#1f2937" />
      <circle cx="82" cy="87" r="2.4" fill="#1f2937" />
      <ellipse cx="52" cy="104" rx="10" ry="9" fill="#eab308" />
      <ellipse cx="130" cy="102" rx="26" ry="22" fill="#fcd34d" stroke="#d97706" strokeWidth="1.1" opacity="0.96" />
      <ellipse cx="130" cy="118" rx="14" ry="10" fill="#eab308" opacity="0.35" />
      <path d="M112 74l12-10 12 14-24-4Z" fill="#fcd34d" stroke="#d97706" strokeWidth="1.1" />
      <circle cx="120" cy="98" r="2" fill="#1f2937" />
      <circle cx="128" cy="97" r="2" fill="#1f2937" />
      <path
        stroke="#92400e"
        strokeWidth="1.8"
        strokeLinecap="round"
        opacity="0.42"
        d="M134 117c-3 10-17 17-38 17"
      />
      <ellipse cx="130" cy="108" rx="3" ry="2.5" fill="#d97706" opacity="0.45" />
    </svg>
  );
}
