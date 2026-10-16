# SentinelGrid Posture Agent - Frontend

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../RELEASE_SCOPE.md) first.


AI-powered chat interface and dashboard for Cloud Security Posture Management.

## Overview

Next.js 14 application providing:
- **AI Chat Interface**: Natural language security posture queries
- **Posture Dashboard**: Score visualization and key metrics
- **Findings Browser**: Searchable security findings
- **Asset Inventory**: Discovered cloud resources

## Quick Start

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Open browser
open http://localhost:3000
```

## Features

### AI Chat Interface (`/chat`)

Ask questions in natural language:
- "What's my security posture score?"
- "Show me critical findings"
- "List all S3 buckets with public access"
- "Analyze my AWS account"

**Powered by MCP Protocol** - Connects to Posture MCP Server

### Posture Dashboard (`/posture`)

- **Score Card**: Security posture score (0-100) with grade (A-F)
- **Statistics**: Findings by severity (critical/high/medium/low)
- **Priority Findings**: Top security issues
- **Quick Links**: Access to detailed views

### Findings Page (`/posture/findings`)

- Filterable table by severity and status
- Real-time updates
- Detailed finding information
- OWASP/CWE mappings

### Assets Page (`/posture/assets`)

- Grouped by asset type
- Risk scores per asset
- Metadata display
- Cloud resource inventory

## Technology Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Radix UI primitives
- **Icons**: Lucide React
- **Charts**: Recharts (for future dashboards)

## Configuration

### Environment Variables

```bash
# Public (accessible in browser)
NEXT_PUBLIC_API_URL=http://localhost:8100
NEXT_PUBLIC_MCP_URL=http://localhost:8102

# Server-side only
POSTURE_SERVICE_URL=http://posture-service:8000
MCP_URL=http://posture-mcp-server:8000
```

### API Integration

**Posture Service** (Port 8100):
- `/api/v1/posture/summary/{tenant_id}`
- `/api/v1/findings/`
- `/api/v1/assets/`

**MCP Server** (Port 8102):
- Tool calls via MCP protocol
- Proxied through Next.js API routes

## Development

```bash
# Install dependencies
npm install

# Run dev server (with hot reload)
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run linter
npm run lint
```

## Docker

```bash
# Build image
docker build -t posture-frontend .

# Run container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8100 \
  posture-frontend
```

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js app router
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Home page
│   │   ├── chat/              # AI chat interface
│   │   ├── posture/           # Posture dashboard
│   │   └── api/               # API routes (proxy)
│   ├── components/
│   │   ├── chat/              # Chat UI components
│   │   └── posture/           # Dashboard components
│   └── lib/
│       ├── api-client.ts      # Posture Service client
│       └── mcp-client.ts      # MCP protocol client
├── package.json
├── next.config.mjs
├── tailwind.config.ts
└── tsconfig.json
```

## Components

### Chat Components

- `ChatInterface.tsx` - Main chat UI with message history
- `MessageBubble.tsx` - Individual message display
- `ThinkingIndicator.tsx` - Loading state while AI processes
- `QuickActions.tsx` - Preset prompt buttons

### Posture Components

- `ScoreCard.tsx` - Posture score visualization
- `FindingsTable.tsx` - Filterable findings table
- `AssetInventory.tsx` - Asset grouping and display

## MCP Integration

The frontend connects to the Posture MCP Server via Next.js API routes:

```typescript
// Client-side
import { mcpClient } from '@/lib/mcp-client';

const response = await mcpClient.getPostureSummary('tenant-id');

// → Calls Next.js API route
// → API route proxies to MCP Server
// → MCP Server calls Posture Service
// → Results returned to frontend
```

## Styling

**Tailwind CSS** with custom theme:
- CSS variables for theming
- Dark mode support
- Responsive breakpoints
- Custom color palette

## Future Enhancements

- [ ] Real-time WebSocket updates for scans
- [ ] Advanced filtering and search
- [ ] Data visualization (charts, graphs)
- [ ] Export functionality (CSV, PDF)
- [ ] Notification system
- [ ] User preferences
- [ ] Mobile app

## Deployment

Included in main docker-compose.yml:

```bash
# From SentinelGridPostureAgent root
docker-compose up -d posture-frontend

# Access at
http://localhost:3001
```

## Support

For issues or questions:
- See main [README](../README.md)
- Check [MCP_INTEGRATION_GUIDE](../docs/MCP_INTEGRATION_GUIDE.md)
- Review [ARCHITECTURE](../docs/architecture.md)

---

**SentinelGrid Posture Agent Frontend** - AI-Powered Security Posture UI

