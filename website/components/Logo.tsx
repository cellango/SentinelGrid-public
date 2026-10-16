export function Logo({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Modern hexagonal frame with depth */}
      <path
        d="M20 2L34.6410 10.5V27.5L20 36L5.3590 27.5V10.5L20 2Z"
        fill="url(#bgGradient)"
        stroke="url(#strokeGradient)"
        strokeWidth="1.2"
      />
      
      {/* Inner geometric pattern - concentric hexagons */}
      <path
        d="M20 8L28.6603 13V23L20 28L11.3397 23V13L20 8Z"
        fill="url(#innerGradient)"
        opacity="0.4"
      />
      
      {/* Center pulse ring */}
      <circle 
        cx="20" 
        cy="18" 
        r="5" 
        stroke="url(#pulseGradient)" 
        strokeWidth="1.5"
        fill="none"
        opacity="0.8"
      />
      
      {/* Central sentinel dot with glow */}
      <circle 
        cx="20" 
        cy="18" 
        r="3" 
        fill="url(#centerGradient)"
      />
      
      {/* Modern S letterform integrated */}
      <path
        d="M20 10C23 10 25 11.5 25 13.5C25 15 24 16 22 16.5C24.5 17 26 18.5 26 20.5C26 23 23.5 25 20 25C17 25 15 23.5 15 21.5"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-cyan-300"
        opacity="0.6"
      />
      
      <defs>
        {/* Background gradient */}
        <linearGradient id="bgGradient" x1="5" y1="2" x2="35" y2="36" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#0891b2" />
          <stop offset="50%" stopColor="#0e7490" />
          <stop offset="100%" stopColor="#155e75" />
        </linearGradient>
        
        {/* Stroke gradient */}
        <linearGradient id="strokeGradient" x1="5" y1="2" x2="35" y2="36" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#0891b2" />
        </linearGradient>
        
        {/* Inner shape gradient */}
        <linearGradient id="innerGradient" x1="11" y1="8" x2="29" y2="28" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#67e8f9" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
        
        {/* Pulse ring gradient */}
        <linearGradient id="pulseGradient" x1="15" y1="13" x2="25" y2="23" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#a5f3fc" />
          <stop offset="100%" stopColor="#22d3ee" />
        </linearGradient>
        
        {/* Center dot gradient */}
        <radialGradient id="centerGradient" cx="20" cy="18" r="3" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#ecfeff" />
          <stop offset="50%" stopColor="#67e8f9" />
          <stop offset="100%" stopColor="#22d3ee" />
        </radialGradient>
      </defs>
    </svg>
  );
}

