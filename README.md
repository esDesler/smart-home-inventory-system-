# smart-home-inventory-system-

## UI tests (Playwright)

### Setup
- `npm install`
- `npx playwright install`

### Run
- `npm run test:ui`

### Configuration
- `BASE_URL` (optional): URL of the running app under test.
- `PLAYWRIGHT_MCP_WS_ENDPOINT` (optional): WebSocket endpoint for a Playwright MCP server.

If `BASE_URL` is not set, the tests run against a local HTML fixture in `tests/ui/fixtures/`.