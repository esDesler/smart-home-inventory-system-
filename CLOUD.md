# Testing guide

## Device service
- Run unit tests:
  - `python3 -m unittest discover -s device/tests`
- Run the device service locally (requires config file):
  - `cp /workspace/device/config.example.json /tmp/smart-inventory-config.json`
  - `python -m smart_inventory.main --config /tmp/smart-inventory-config.json`

## Server service
- Run the API server (requires virtualenv + deps):
  - `python -m venv .venv`
  - `. .venv/bin/activate`
  - `pip install -r server/requirements.txt`
  - `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Manual checks
- Device ingestion: `POST /api/v1/readings/batch`
- UI list: `GET /api/v1/items`
- UI events: `GET /api/v1/stream`
