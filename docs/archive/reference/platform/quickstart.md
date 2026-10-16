# SentinelGrid Quick Start Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

SentinelGrid is an AI-driven Security-as-a-Service platform. This guide will help you get the V1 foundation up and running.

## Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

## Project Structure

```
sentinelgrid/
├── backend/
│   ├── services/          # FastAPI microservices
│   │   ├── api_gateway/   # Public REST API
│   │   ├── orchestrator/  # Tenant + SOC orchestration
│   │   ├── model_gateway/ # LLM inference gateway
│   │   ├── siem_agent/    # SIEM integration
│   │   ├── soar_agent/    # SOAR integration
│   │   ├── iam_agent/     # IAM integration
│   │   └── posture_agent/ # CSPM integration
│   ├── libs/              # Shared libraries
│   │   ├── sg_core/       # Core utilities, models, security
│   │   └── sg_events/     # Event bus abstraction
│   ├── migrations/         # Database migrations
│   └── tests/             # Test suite
├── frontend/               # Next.js app (console + marketing)
├── docs/                   # Documentation
└── docker-compose.dev.yml  # Development environment
```

## Getting Started

### 1. Start Development Environment

```bash
# Start all services with Docker Compose
make dev

# Or manually:
docker-compose -f docker-compose.dev.yml up --build
```

This will start:
- Frontend (Next.js) on http://localhost:3000
- API Gateway on http://localhost:8080
- All backend services
- PostgreSQL database
- Keycloak (auth) on http://localhost:8081

### 2. Initialize Database

```bash
# Connect to PostgreSQL container
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg

# Run migration
\i /path/to/backend/migrations/001_initial_schema.sql

# Or from host:
docker-compose -f docker-compose.dev.yml exec postgres psql -U sg -d sg -f /docker-entrypoint-initdb.d/001_initial_schema.sql
```

### 3. Access the Application

- **Marketing Website**: http://localhost:3000
- **Dashboard**: http://localhost:3000/dashboard
- **API Gateway**: http://localhost:8080
- **Keycloak Admin**: http://localhost:8081 (admin/admin)

## Development

### Backend Services

Each service is a FastAPI application. To run individually:

```bash
cd backend/services/api_gateway
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
cd backend
pytest tests/
```

## V1 Status

### ✅ Completed

- Project structure (monorepo)
- Backend services (stubs for all agents)
- Shared libraries (sg_core, sg_events)
- Database schema (PostgreSQL)
- Frontend marketing website (Priority 2)
- Dashboard UI (Priority 1)
- Docker setup
- Basic tests

### 🚧 In Progress / Stubs

- Keycloak integration (structure in place, needs full implementation)
- Model Gateway (stub, needs actual LLM server connection)
- SIEM Agent (stub, needs OpenSearch/Wazuh integration)
- SOAR Agent (stub, needs TheHive integration)
- IAM Agent (stub)
- Posture Agent (stub)

## Next Steps

1. **Connect Real SIEM**: Integrate OpenSearch or Wazuh in `siem_agent`
2. **Connect TheHive**: Integrate TheHive in `soar_agent`
3. **LLM Integration**: Connect local LLM server (SecGPT/Lily-Cybersecurity) in `model_gateway`
4. **Keycloak Setup**: Configure Keycloak realm and complete auth flow
5. **Database Seeding**: Add sample data for testing

## Architecture Notes

- **Multi-tenant**: All data is scoped by `tenant_id`
- **Microservices**: Each agent is a separate service
- **Event-driven**: Uses event bus for inter-service communication (in-memory for V1)
- **Local LLM**: No OpenAI dependency - uses open-source cybersecurity models

## Documentation

See `docs/` folder for detailed architecture and implementation guides:
- `SentinelGridV1Proposal.txt` - V1 scope and design
- `SentinelGridTechStack.txt` - Technology choices
- `SentinelGridImplementation.txt` - Phased implementation plan

## Support

For questions or issues, refer to the documentation in `docs/` or check the code comments.

