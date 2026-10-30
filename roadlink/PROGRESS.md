# RoadLink Progress

## Audit
- Existing app: FastAPI + async SQLAlchemy, SQLite default/local DB, React 19 + Vite + Leaflet. No standalone original-prompt file was found; audited against the supplied RoadLink specification.
- Implemented: registration/login/refresh, profile/settings/skills, location update and Haversine nearby search, SOS create/feed/accept/resolve/cancel, participant-only REST chat, WebSocket ticketing/live dispatch, and mobile-first map/auth/SOS/profile UI.
- Baseline verified: backend `23 passed`; frontend `npm run build` succeeds.
- Database reality: runtime defaults to SQLite and `roadlink.db`; no PostGIS integration is used. `.env.example` now defaults to SQLite and documents PostgreSQL as optional.
- Resolved migration gap: SQLite Alembic upgrade/downgrade/re-upgrade now works; location/SOS/chat tables are included and `aiosqlite` is declared.
- Other audited gaps: WebSocket events were process-local with no reconnect replay; GPS sync errors were hidden; nearby lookup included stale positions (the latter two are fixed below).

## Completed milestone
- Added the SQLite runtime driver, portable SQLite revisions, a migration for location/SOS/chat tables, and SQLite defaults to `.env.example`.
- Fresh-database migration regression test passes; all backend tests pass, including WebSocket replay regressions, and the frontend production build passes.
- Profile settings now mount only after auth loading, so form fields initialize from the fetched profile.
- Added configurable Vite API proxying and enabled WebSocket upgrades on `/api`, matching the backend route.
- Live startup reports `db: true`; browser registration/profile load and live SOS toast work. A three-user API flow verified location, SOS feed/create, accept, duplicate-accept `409`, private chat, resolution, and database writes.
- Added a 30-minute/50-event per-user reconnect buffer with client-side event-ID deduplication; a browser reconnect replayed an SOS created while disconnected.
- Nearby search now excludes stale positions, and SOS dispatch excludes stale or unavailable responders.
- GPS/backend sync failures are shown, the map no longer labels its fallback center as the user's location, and SOS submission is disabled until a real GPS fix exists (112 remains available).
- Final automated verification: 28 backend tests pass; frontend build passes.
- Fixed the live SOS detail view's Zustand subscription loop. Browser verification completed the UI flow: create SOS, second account accepts, WebSocket status/chat updates arrive, requester replies, and resolves.
- Verified the browser-created SOS is persisted as resolved with its responder and both chat messages in the isolated SQLite database.
- Logout now disconnects the WebSocket; chat history loading avoids state updates after unmount. Final frontend build and lint both pass without warnings.
- WebSocket notifications now persist per user in `notification_events`, and reconnect replay reads the shared database (last 50 events within 30 minutes), so reconnect history survives worker restarts and works across workers. Added Alembic revision `003` and tests proving a separate connection manager can replay stored events.
- Added a manual latitude/longitude flow for GPS-denied or unavailable users. Coordinates are range-validated, are not applied until backend sync succeeds, are clearly identified as manual, and pause GPS tracking until the user explicitly resumes it.
- Verification after these changes: all 28 backend tests pass, frontend production build and lint pass.
- Stopped the test backend and Vite sessions, confirmed their ports are closed, and removed only `%TEMP%\\roadlink_e2e_58948.db`.

## Remaining
- Add a shared live-delivery mechanism (such as a broker) before multi-process deployment; persisted reconnect replay is cross-worker, but active WebSocket connections remain process-local.
- Keep optional services (PostGIS, Ollama, places) out of the MVP until core workflows are reliable.

## Known gaps
- Active WebSocket connections and single-use tickets remain process-local; use a shared broker for live cross-worker delivery.
- Map tiles depend on external OpenStreetMap access.

## Known blockers / next action
- DevRelay community research and registered-event lookup could not run because the account is not connected; `devrelay login` is the documented fallback.
- Next: add broker-backed live delivery before running multiple backend workers.

## Run / verify
- Backend: `cd backend; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Migrations: `cd backend; alembic upgrade head`
- Tests: `cd backend; python -m pytest tests`
- Frontend: `cd frontend; npm run dev` / `npm run build`
