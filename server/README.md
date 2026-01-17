# Smart Inventory Server

FastAPI server that stores device readings, exposes REST APIs, and streams
real-time updates via SSE. Runs on a single machine (LAN-first) with SQLite.

## Setup

1) Create a virtual environment and install dependencies:

   - `python -m venv .venv`
   - `. .venv/bin/activate`
   - `pip install -r requirements.txt`

2) Configure environment variables:

   - `INVENTORY_DB_PATH=./data/inventory.db`
   - `INVENTORY_DEVICE_TOKENS=dev-token-1,dev-token-2`
   - `INVENTORY_UI_TOKEN=ui-token-1`
   - `INVENTORY_ALLOW_UNAUTH=false`
   - `INVENTORY_CORS_ORIGINS=http://localhost:5173`
   - `INVENTORY_EVENT_RETENTION_SECONDS=604800`
   - `INVENTORY_EVENT_MAX_ROWS=10000`
   - `INVENTORY_EVENT_REPLAY_LIMIT=500`

3) Run the server:

   - `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## API notes

- Device ingestion: `POST /api/v1/readings/batch`
- UI list: `GET /api/v1/items`
- UI events: `GET /api/v1/stream` (SSE, supports `Last-Event-ID`)
  - For browser EventSource, send `?token=...` if UI auth is enabled.

## Example device request

```
curl -X POST http://localhost:8000/api/v1/readings/batch \
  -H "Authorization: Bearer dev-token-1" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "pi-kitchen-01",
    "firmware": "0.1.0",
    "sent_at": "2026-01-16T20:00:00Z",
    "readings": [
      {
        "seq_id": 100,
        "sensor_id": "loadcell-01",
        "ts": "2026-01-16T19:59:58Z",
        "raw_value": 8423912,
        "normalized_value": 180,
        "state": "low"
      }
    ]
  }'
```

## Security

- Use TLS in front of the server (reverse proxy or direct uvicorn TLS).
- Set `INVENTORY_DEVICE_TOKENS` and `INVENTORY_UI_TOKEN`.
- Keep `INVENTORY_ALLOW_UNAUTH=false` for production.
