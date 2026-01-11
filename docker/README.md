# PasteTrader Docker Configuration

Docker configuration for the PasteTrader application.

## Quick Start

### Development

```bash
# Start all services
cd docker
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Production

```bash
# Build and start with production settings
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| frontend | 3000 | Next.js 15 application |
| backend | 8000 | FastAPI server |
| db | 5432 | PostgreSQL 16 database |
| redis | 6379 | Redis 7 cache |

## Configuration

1. Copy `env.example` to `.env`
2. Update the values as needed
3. Start the services

## Directory Structure

```
docker/
├── docker-compose.yml      # Main compose file
├── docker-compose.prod.yml # Production overrides
├── Dockerfile.frontend     # Frontend multi-stage build
├── Dockerfile.backend      # Backend multi-stage build
├── .dockerignore          # Docker build exclusions
├── env.example            # Environment template
├── init-db/               # Database initialization
│   └── 01-init.sql        # Initial schema setup
└── README.md              # This file
```

## Build Targets

### Frontend (Dockerfile.frontend)
- `development`: Hot reload enabled, volume mounts
- `production`: Optimized standalone build

### Backend (Dockerfile.backend)
- `development`: Hot reload with uvicorn
- `production`: Multi-worker production server

## Health Checks

All services include health checks:
- Frontend: `http://localhost:3000/api/health`
- Backend: `http://localhost:8000/health`
- Database: `pg_isready`
- Redis: `redis-cli ping`

## Volumes

Persistent data is stored in named volumes:
- `pastetrader-postgres-data`: Database files
- `pastetrader-redis-data`: Redis persistence
- `pastetrader-backend-cache`: Python package cache
