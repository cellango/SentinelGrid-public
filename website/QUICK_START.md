# SentinelGrid Website - Quick Start

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


## 🚀 Getting Started

### 1. Install Dependencies

```bash
cd website
npm install
```

### 2. Run Development Server

```bash
npm run dev
```

The website will be available at [http://localhost:3000](http://localhost:3000)

### 3. Build for Production

```bash
npm run build
npm start
```

## 📁 Project Structure

```
website/
├── app/
│   ├── page.tsx          # Homepage
│   ├── signup/
│   │   └── page.tsx      # Sign-up & onboarding flow
│   ├── demo/
│   │   └── page.tsx      # Demo booking page
│   ├── layout.tsx        # Root layout
│   └── globals.css       # Global styles
├── components/
│   ├── Header.tsx        # Navigation header
│   ├── Footer.tsx        # Footer
│   ├── Logo.tsx           # SVG logo component
│   ├── RotatingStatements.tsx  # Rotating hero statements
│   ├── TrustBar.tsx      # Quick trust signals
│   ├── HowItWorks.tsx    # 4-step process
│   ├── SecurityInABox.tsx # Feature highlights
│   ├── Pricing.tsx       # Pricing tiers
│   └── TrustSection.tsx  # Detailed trust info
└── package.json
```

## 🎨 Design System

- **Theme**: Dark cybersecurity theme (slate-950 background)
- **Accent Color**: Cyan-400/500 for CTAs and highlights
- **Typography**: System fonts with clear hierarchy
- **Logo**: Shield with grid pattern (SVG)

## ✨ Key Features

### Homepage
- Hero section with rotating statements
- Trust bar with quick security signals
- "How it Works" 4-step process
- "Security in a Box" feature highlights
- Pricing tiers (Micro/Startup/Scaleup)
- Trust & Security section

### Sign-up Flow
1. **Account** - Email, name, company, password
2. **Environment** - Company size, environment, IdP choice
3. **Identity** - Connect IdP or use SentinelGrid Identity
4. **Cloud** - Connect cloud accounts

### Trust Messaging
- Data isolation and encryption
- Least-privilege access
- AI without data farming
- Transparent and auditable
- Operational security features

## 🔧 Customization

### Update Rotating Statements

Edit `components/RotatingStatements.tsx`:

```typescript
const STATEMENTS = [
  "Your custom statement 1",
  "Your custom statement 2",
  // ...
];
```

### Update Pricing

Edit `components/Pricing.tsx` to modify pricing tiers and features.

### Update Logo

Edit `components/Logo.tsx` to customize the SVG logo.

## 📝 Notes

- All components are responsive (mobile-first)
- Uses Tailwind CSS for styling
- Next.js 14 with App Router
- TypeScript for type safety

## 🐛 Troubleshooting

### Port Already in Use

If port 3000 is busy, use:

```bash
npm run dev -- -p 3001
```

### Build Errors

Clear Next.js cache:

```bash
rm -rf .next
npm run build
```

