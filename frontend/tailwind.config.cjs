/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      /* ── Typography ────────────────────────────────────────────── */
      fontFamily: {
        display: ['var(--font-display)', 'DM Sans', 'system-ui', 'sans-serif'],
        sans: ['var(--font-sans)', 'IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'Menlo', 'monospace'],
      },
      /* Modular type scale (1.200 minor third) */
      fontSize: {
        'xs':   ['0.694rem', { lineHeight: '1.1rem',  letterSpacing: '0.02em' }],  // 11.1px
        'sm':   ['0.833rem', { lineHeight: '1.25rem', letterSpacing: '0.01em' }],  // 13.3px
        'base': ['1rem',     { lineHeight: '1.5rem',  letterSpacing: '0' }],       // 16px
        'lg':   ['1.2rem',   { lineHeight: '1.75rem', letterSpacing: '-0.01em' }], // 19.2px
        'xl':   ['1.44rem',  { lineHeight: '2rem',    letterSpacing: '-0.015em' }],// 23px
        '2xl':  ['1.728rem', { lineHeight: '2.25rem', letterSpacing: '-0.02em' }], // 27.6px
        '3xl':  ['2.074rem', { lineHeight: '2.5rem',  letterSpacing: '-0.025em' }],// 33.2px
        '4xl':  ['2.488rem', { lineHeight: '2.75rem', letterSpacing: '-0.03em' }], // 39.8px
        '5xl':  ['2.986rem', { lineHeight: '1.1',     letterSpacing: '-0.035em' }],// 47.8px
        '6xl':  ['3.583rem', { lineHeight: '1.1',     letterSpacing: '-0.04em' }], // 57.3px
      },

      /* ── OKLCH Color System (Impeccable CSS) ──────────────────── */
      /* Tinted neutrals — no pure black or gray */
      colors: {
        bg:           'oklch(0.13 0.015 250)',        // Deep navy, not pure black
        'bg-alt':     'oklch(0.18 0.02 250)',         // Elevated surface
        surface:      'oklch(0.13 0.015 250)',
        border:       'oklch(0.28 0.015 250)',
        primary:      'oklch(0.82 0.15 192)',         // Cyan — high chroma
        'primary-soft':  'oklch(0.82 0.15 192 / 0.15)',
        'primary-ghost': 'oklch(0.82 0.15 192 / 0.05)',
        secondary:    'oklch(0.65 0.25 310)',         // Purple — high chroma
        'text-main':  'oklch(0.9 0.01 250)',          // Off-white, tinted
        'text-muted': 'oklch(0.68 0.02 250)',         // Muted, tinted
        // Surface tokens
        'surface-card':        'oklch(0.18 0.02 250 / 0.9)',
        'surface-card-border': 'oklch(0.18 0.02 250 / 0.95)',
        'surface-hover':       'oklch(0.18 0.02 250 / 0.5)',
        'surface-input':       'oklch(0.18 0.02 250 / 0.6)',
        'surface-overlay':       'oklch(0.13 0.015 250 / 0.5)',
        'surface-overlay-strong': 'oklch(0.13 0.015 250 / 0.85)',
        // Border tokens
        'border-faint':  'oklch(1 0 0 / 0.06)',
        'border-muted':  'oklch(0.68 0.02 250 / 0.4)',
        'border-strong': 'oklch(0.68 0.02 250 / 0.5)',
        'border-grid':   'oklch(0.68 0.02 250 / 0.1)',
        // Semantic status tokens
        'success-soft':       'oklch(0.65 0.2 145 / 0.15)',
        'success-soft-hover': 'oklch(0.65 0.2 145 / 0.25)',
      },
      borderRadius: {
        lg: '18px',
        md: '12px',
        sm: '999px',
      },
    },
  },
  plugins: [],
};
