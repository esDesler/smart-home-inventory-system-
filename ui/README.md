# Smart Inventory UI

React-based web UI for viewing item status, alerts, and device health. It
polls the server for updates and caches the last known data locally.

## Setup

1) Install dependencies:

   - `npm install`

2) Configure environment variables:

   - Copy `.env.example` to `.env`
   - Set `VITE_API_BASE_URL` to your server URL
   - Set `VITE_UI_TOKEN` to match `INVENTORY_UI_TOKEN`

3) Run the UI:

   - `npm run dev`

## Notes

- The dashboard refreshes on a polling interval controlled by
  `VITE_POLL_INTERVAL_MS` (default 15000 ms).
- Use the "Refresh" button to force an immediate sync.
