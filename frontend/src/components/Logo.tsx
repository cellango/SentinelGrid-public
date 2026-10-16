export function Logo({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Outer shield — faceted, modern */}
      <path
        d="M16 1.5L3 7.5V15C3 22.732 8.82 29.034 16 30.5C23.18 29.034 29 22.732 29 15V7.5L16 1.5Z"
        fill="url(#sg-shield-fill)"
      />
      <path
        d="M16 1.5L3 7.5V15C3 22.732 8.82 29.034 16 30.5C23.18 29.034 29 22.732 29 15V7.5L16 1.5Z"
        stroke="url(#sg-shield-stroke)"
        strokeWidth="0.75"
        strokeLinejoin="round"
      />

      {/* Inner facet line — gives the shield a folded/dimensional feel */}
      <path
        d="M16 3.5L5.5 8.5V15C5.5 21.5 10.2 26.8 16 28.2C21.8 26.8 26.5 21.5 26.5 15V8.5L16 3.5Z"
        stroke="url(#sg-inner-stroke)"
        strokeWidth="0.5"
        strokeLinejoin="round"
        opacity="0.35"
      />

      {/* Stylised S path — formed by two curved segments implying data flow */}
      <path
        d="M19.5 9.5C19.5 9.5 20.5 9.5 20.5 11C20.5 12.5 18.5 13 16 13C13.5 13 11.5 13.5 11.5 15.5C11.5 17.5 13.5 18 16 18C18.5 18 20.5 18.5 20.5 20.5C20.5 22 19.5 22.5 19.5 22.5"
        stroke="url(#sg-s-gradient)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12.5 9.5C12.5 9.5 11.5 9.5 11.5 11C11.5 12.5 13.5 13 16 13"
        stroke="url(#sg-s-gradient)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.5"
      />
      <path
        d="M16 18C18.5 18 20.5 18.5 20.5 20.5"
        stroke="url(#sg-s-gradient)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.5"
      />

      {/* Three sentinel nodes — at S endpoints and center */}
      <circle cx="12" cy="9.5" r="1.5" fill="#22d3ee" />
      <circle cx="16" cy="15.5" r="1.5" fill="#06b6d4" />
      <circle cx="20" cy="22.5" r="1.5" fill="#22d3ee" />

      {/* Subtle glow ring around center node */}
      <circle cx="16" cy="15.5" r="3" stroke="#22d3ee" strokeWidth="0.5" opacity="0.25" />

      <defs>
        <linearGradient id="sg-shield-fill" x1="3" y1="1.5" x2="29" y2="30.5" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0e2a3a" />
          <stop offset="100%" stopColor="#0a1628" />
        </linearGradient>
        <linearGradient id="sg-shield-stroke" x1="3" y1="1.5" x2="29" y2="30.5" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.6" />
          <stop offset="50%" stopColor="#06b6d4" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#22d3ee" stopOpacity="0.6" />
        </linearGradient>
        <linearGradient id="sg-inner-stroke" x1="5.5" y1="3.5" x2="26.5" y2="28.2" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
        <linearGradient id="sg-s-gradient" x1="11.5" y1="9.5" x2="20.5" y2="22.5" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#67e8f9" />
          <stop offset="50%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#67e8f9" />
        </linearGradient>
      </defs>
    </svg>
  );
}
