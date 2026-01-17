# Smart Inventory Device Service

Lightweight device service for Raspberry Pi class hardware. Reads one or more
GPIO-connected sensors, debounces/calibrates the values, stores readings
locally, and uploads batched updates to the server over HTTPS.

## Quick start (local dev)

1) Copy the example config:

   - `cp /workspace/device/config.example.json /tmp/smart-inventory-config.json`

2) Edit the config for your environment:

   - Set `device.id`
   - Set `network.base_url`
   - Provide `network.api_token` or use `env:DEVICE_TOKEN`
   - Use `file_sensor` to simulate values during development
   - Optional: set `storage.max_queue_rows` / `storage.max_queue_age_seconds` to
     cap offline buffering
   - If the server is the source of truth for thresholds/alerts, set
     `runtime.state_source` to `server` to report every sample

3) Run the service:

   - `python -m smart_inventory.main --config /tmp/smart-inventory-config.json`

## Raspberry Pi setup

- Install GPIO dependencies if you use real sensors:
  - `RPi.GPIO` or `gpiozero` for digital GPIO sensors
  - A compatible `hx711` library for load cells
- Keep the service local-first (LAN), and use TLS with a local CA certificate.

## Systemd

Copy the unit file and adjust paths:

- `/workspace/device/systemd/smart-inventory-device.service`

Ensure the config file and SQLite queue directory are writable by the
`smart-inventory` user.
