# RoadLink

> **You're never alone on the road.**

RoadLink is a real-time roadside safety and traveller-support platform. It helps people share their location, discover nearby travellers, send SOS alerts, coordinate assistance, and communicate securely during an incident.

## Features

- User registration, login, token refresh, and profile management
- Live map with GPS-based location sharing
- Manual location entry when GPS is unavailable
- Nearby traveller discovery using distance-based search
- SOS creation, dispatch, acceptance, resolution, and cancellation
- Real-time SOS notifications and status updates over WebSockets
- Participant-only SOS chat
- Persistent notification replay after reconnects
- Emergency call shortcut for `112`
- SQLite by default, with optional PostgreSQL support
- Automatic API documentation through FastAPI and OpenAPI

## Tech Stack

### Frontend

- React 19
- TypeScript
- Vite
- Leaflet and React Leaflet
- Zustand
- Axios

### Backend

- Python
- FastAPI
- SQLAlchemy 2 with async support
- Alembic migrations
- SQLite by default, PostgreSQL-compatible configuration
- JWT authentication
- WebSockets

## Project Structure

```text
roadlink/
├── backend/
│   ├── app/
│   │   ├── models/       # Database models
│   │   ├── routers/      # API and WebSocket routes
│   │   ├── schemas/      # Request and response schemas
│   │   ├── services/     # Application services
│   │   └── workers/      # Background work
│   ├── alembic/          # Database migrations
│   └── tests/             # Backend test suite
├── frontend/
│   ├── src/
│   │   ├── components/   # User interface components
│   │   ├── api/          # API client
│   │   └── store/        # Client state stores
│   └── package.json
└── PROGRESS.md
```

## Requirements

- Python 3.11 or newer
- Node.js 18 or newer
- npm

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/aman-dev23/road-link.git
cd road-link/roadlink
```

### 2. Configure and run the backend

From the `roadlink` directory:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Install dependencies and configure the environment:

```bash
python -m pip install -r requirements.txt
copy .env.example .env
```

On macOS/Linux, use `cp .env.example .env` instead of `copy`.

Run database migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The backend will be available at:

- API: <http://127.0.0.1:8000>
- Swagger UI: <http://127.0.0.1:8000/api/docs>
- ReDoc: <http://127.0.0.1:8000/api/redoc>

### 3. Run the frontend

Open another terminal and run:

```bash
cd road-link/roadlink/frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, usually <http://localhost:5173>.

The frontend is configured to use the local backend. If the API runs on another address, configure the Vite API proxy through the frontend environment settings.

## Testing and Builds

### Backend

```bash
cd roadlink/backend
python -m pytest tests
```

### Frontend

```bash
cd roadlink/frontend
npm run lint
npm run build
```

## Environment Configuration

The backend uses SQLite by default, so no separate database service is required for local development. Copy `backend/.env.example` to `backend/.env` and update values as needed.

Important settings include:

- `DATABASE_URL` for the database connection
- `JWT_SECRET` for token signing
- `CORS_ORIGINS` for allowed frontend origins
- `AI_PROVIDER` and `OLLAMA_*` for optional local AI features
- `VAPID_*` for optional web push notifications

Never commit `.env` files, JWT secrets, private keys, or production credentials.

## API Overview

The API is grouped into the following areas:

- `/api/auth` — registration, login, and token management
- `/api/me` — authenticated profile and settings
- `/api/locations` — location updates and nearby travellers
- `/api/sos` — SOS lifecycle, feed, responders, and chat
- `/api/ws` — WebSocket connection and live event delivery
- `/api/health` — service health checks

For the complete request and response schemas, use the interactive documentation at `/api/docs`.

## Current Deployment Note

Persisted notification replay works across reconnects and backend workers. Active WebSocket connections are currently process-local, so a shared broker should be added before deploying multiple backend workers.

Map tiles use external OpenStreetMap services and require network access.

## Contributing

1. Create a feature branch.
2. Make focused changes with tests where appropriate.
3. Run the backend tests and frontend lint/build checks.
4. Open a pull request describing the change.

## License

This project does not currently declare a license. Add a license before distributing or reusing the code outside the project.
