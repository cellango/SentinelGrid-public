# SentinelGrid Website - Development Server

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../RELEASE_SCOPE.md) first.


Quick reference for running the redesigned website locally.

## Starting the Development Server

```bash
./start-dev.sh
```

This will:
- Install dependencies if needed
- Start the Next.js development server on port 3000
- Run in the background so you can continue working
- Save the process ID for easy stopping

The website will be available at: **http://localhost:3000**

## Stopping the Development Server

```bash
./stop-dev.sh
```

This will gracefully stop the development server.

## Viewing Logs

To view real-time logs while the server is running:

```bash
tail -f .dev-server.log
```

## What's New in the Redesign

✨ **Brand New Components:**
- Modern hexagonal logo with gradient effects
- ICP Section - Three persona cards for target customers
- Three Pillars - Interactive tabbed component with security alarms
- Interactive Pricing Calculator - Team-size slider with real-time pricing
- Comparison Table - Positions SentinelGrid vs alternatives
- Fit Section - Pre-qualifies customers

🎨 **Visual Enhancements:**
- Ultra-modern UI with gradient effects
- Glass morphism design elements
- Smooth animations and transitions
- Enhanced hover effects
- Custom scrollbar styling
- Radial gradient backgrounds

📝 **Content Updates:**
- 17 rotating statements (7 original + 10 new security alarms)
- ICP-focused copy (20-500 person teams)
- No mention of specific open-source tools (Keycloak, Wazuh, etc.)
- Engaging, approachable language
- Transparent pricing messaging

## Alternative: Manual Start

If you prefer to run the server manually:

```bash
npm run dev
```

This will run in the foreground and show live logs.

## Troubleshooting

**Port 3000 already in use?**
```bash
# Find and kill the process using port 3000
lsof -ti:3000 | xargs kill -9
```

**Server won't start?**
```bash
# Clean install dependencies
rm -rf node_modules package-lock.json
npm install
./start-dev.sh
```

**Check if server is running:**
```bash
ps aux | grep "next dev"
```

