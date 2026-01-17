# Viktualierum (Dry Storage) Monitoring System Proposal

This document outlines a complete setup for monitoring multiple items in a dry storage room (viktualierum) with sensors and a central broadcasting unit. It covers hardware configuration, software architecture, and a step-by-step migration plan from the current solution.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Hardware Setup](#hardware-setup)
3. [Software Architecture](#software-architecture)
4. [Migration Plan](#migration-plan)
5. [Example Configuration](#example-configuration)
6. [Maintenance and Operations](#maintenance-and-operations)

---

## System Overview

### What We're Building

A centralized monitoring system for a dry storage room with:

- **Multiple storage locations** (shelves, bins, containers) each with sensors
- **Central Raspberry Pi hub** that collects data from all sensors
- **Server** that stores readings, manages alerts, and broadcasts status
- **Web dashboard** showing real-time status of all monitored items

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VIKTUALIERUM (DRY STORAGE)                        │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Shelf 1    │  │   Shelf 2    │  │   Shelf 3    │  │   Shelf 4    │    │
│  │              │  │              │  │              │  │              │    │
│  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │  │ ┌──────────┐ │    │
│  │ │Load Cell │ │  │ │Load Cell │ │  │ │Load Cell │ │  │ │Reed Sw.  │ │    │
│  │ │(HX711)   │ │  │ │(HX711)   │ │  │ │(HX711)   │ │  │ │(GPIO)    │ │    │
│  │ │Rice 5kg  │ │  │ │Flour 2kg │ │  │ │Sugar 3kg │ │  │ │Door      │ │    │
│  │ └────┬─────┘ │  │ └────┬─────┘ │  │ └────┬─────┘ │  │ └────┬─────┘ │    │
│  └──────┼───────┘  └──────┼───────┘  └──────┼───────┘  └──────┼───────┘    │
│         │                 │                 │                 │            │
│         └────────────┬────┴────────────┬────┴────────────┬────┘            │
│                      │                 │                 │                 │
│                      ▼                 ▼                 ▼                 │
│              ┌───────────────────────────────────────────────┐             │
│              │          RASPBERRY PI (CENTRAL HUB)           │             │
│              │                                               │             │
│              │  GPIO Pins ◄── Load cells (HX711 amplifiers)  │             │
│              │  GPIO Pins ◄── Reed switches / presence       │             │
│              │                                               │             │
│              │  ┌─────────────────────────────────────────┐  │             │
│              │  │     Device Service (smart_inventory)    │  │             │
│              │  │  - Polls all sensors @ 200ms            │  │             │
│              │  │  - Debounces/filters readings           │  │             │
│              │  │  - Queues locally (offline tolerance)   │  │             │
│              │  │  - Batches uploads every 15s            │  │             │
│              │  └─────────────────────────────────────────┘  │             │
│              │                      │                        │             │
│              └──────────────────────┼────────────────────────┘             │
│                                     │                                      │
└─────────────────────────────────────┼──────────────────────────────────────┘
                                      │ HTTPS/TLS
                                      ▼
                    ┌─────────────────────────────────────┐
                    │         SERVER (FastAPI + SQLite)   │
                    │                                     │
                    │  - Receives batched readings        │
                    │  - Stores in SQLite database        │
                    │  - Evaluates thresholds             │
                    │  - Creates/resolves alerts          │
                    │  - Broadcasts SSE events            │
                    │  - REST API for UI                  │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         WEB UI (React)              │
                    │                                     │
                    │  - Dashboard with all items         │
                    │  - Status indicators (ok/low/out)   │
                    │  - Alerts panel                     │
                    │  - History graphs                   │
                    │  - Device health monitoring         │
                    └─────────────────────────────────────┘
```

---

## Hardware Setup

### Components List

#### Central Unit (Raspberry Pi Hub)

| Component | Quantity | Purpose | Approximate Cost |
|-----------|----------|---------|------------------|
| Raspberry Pi 4 Model B (2GB+) | 1 | Central processing hub | €45-60 |
| MicroSD Card (32GB+) | 1 | OS and local queue storage | €10 |
| Power Supply (USB-C 5V/3A) | 1 | Power the Pi | €10 |
| Case with cooling | 1 | Protection and thermal management | €10-15 |
| Ethernet cable or WiFi | 1 | Network connectivity | €5 |

#### Per-Monitored Item (Weight-Based)

| Component | Quantity | Purpose | Approximate Cost |
|-----------|----------|---------|------------------|
| HX711 Load Cell Amplifier | 1 per sensor | Analog-to-digital conversion | €3-5 |
| Load Cell (1kg/5kg/10kg) | 1 per sensor | Weight measurement | €5-15 |
| Mounting platform | 1 per sensor | Stable sensor placement | €5-10 |
| Wiring (4-wire cable) | As needed | Connect sensors to Pi | €1/meter |

#### Per-Monitored Item (Presence-Based)

| Component | Quantity | Purpose | Approximate Cost |
|-----------|----------|---------|------------------|
| Reed switch + magnet | 1 per sensor | Door/lid detection | €2-3 |
| Pull-up resistor (10kΩ) | 1 per sensor | Signal conditioning | €0.10 |
| Wiring (2-wire cable) | As needed | Connect to GPIO | €0.50/meter |

#### Optional Additions

| Component | Purpose |
|-----------|---------|
| I2C GPIO Expander (MCP23017) | Expand beyond 26 GPIO pins (16 extra per chip) |
| ADC Module (ADS1115) | For analog sensors like temperature/humidity |
| Temperature/Humidity (DHT22) | Environmental monitoring |
| UPS Battery backup | Survive power outages |

### Wiring Diagram

```
RASPBERRY PI GPIO HEADER
═══════════════════════════════════════════════════════════════════

3.3V (Pin 1)  ─────────────┐
                           │
GND  (Pin 6)  ──────────┐  │
                        │  │
                        │  │
   ┌────────────────────┴──┴────────────────────────────────────┐
   │                                                            │
   │  LOAD CELL 1 (Rice Container)                              │
   │  ┌─────────────┐                                           │
   │  │   HX711     │                                           │
   │  │             │◄── VCC (3.3V)                             │
   │  │             │◄── GND                                    │
   │  │   DOUT  ────┼──► GPIO 5  (Pin 29)                       │
   │  │   SCK   ────┼──► GPIO 6  (Pin 31)                       │
   │  └─────────────┘                                           │
   │        ▲                                                   │
   │        │ (4-wire)                                          │
   │   ┌────┴────┐                                              │
   │   │Load Cell│ (under rice container)                       │
   │   └─────────┘                                              │
   │                                                            │
   │  LOAD CELL 2 (Flour Container)                             │
   │  ┌─────────────┐                                           │
   │  │   HX711     │◄── VCC, GND (shared rail)                 │
   │  │   DOUT  ────┼──► GPIO 13 (Pin 33)                       │
   │  │   SCK   ────┼──► GPIO 19 (Pin 35)                       │
   │  └─────────────┘                                           │
   │                                                            │
   │  LOAD CELL 3 (Sugar Container)                             │
   │  ┌─────────────┐                                           │
   │  │   HX711     │◄── VCC, GND (shared rail)                 │
   │  │   DOUT  ────┼──► GPIO 26 (Pin 37)                       │
   │  │   SCK   ────┼──► GPIO 21 (Pin 40)                       │
   │  └─────────────┘                                           │
   │                                                            │
   │  REED SWITCH (Door Sensor)                                 │
   │                                                            │
   │   3.3V ──────┬─────────┐                                   │
   │              │         │                                   │
   │           [10kΩ]       │                                   │
   │              │         │                                   │
   │   GPIO 17 ───┴─────[REED SW]───── GND                      │
   │   (Pin 11)            (closes when door shut)              │
   │                                                            │
   └────────────────────────────────────────────────────────────┘
```

### Physical Installation Tips

1. **Load Cell Placement**
   - Mount load cells on a stable, level surface
   - Use a small platform (acrylic/wood) to distribute weight evenly
   - Ensure the container sits centered on the load cell
   - Protect wiring from moisture and physical damage

2. **Wiring Best Practices**
   - Use twisted pair or shielded cable for HX711 connections (reduces noise)
   - Keep wire runs under 3 meters if possible
   - Label all cables at both ends
   - Use a terminal block near the Pi for easier maintenance

3. **Environmental Considerations**
   - Keep the Pi in a ventilated enclosure
   - Avoid direct sunlight on sensors
   - For humid storage areas, consider conformal coating on electronics

---

## Software Architecture

### Current System Capabilities

The existing codebase already supports everything needed for a multi-sensor viktualierum setup:

| Feature | Status | Location |
|---------|--------|----------|
| Multiple sensor support | ✅ Implemented | `device/smart_inventory/sensors/` |
| HX711 load cells | ✅ Implemented | `sensors/hx711.py` |
| Digital GPIO (reed switches) | ✅ Implemented | `sensors/digital_gpio.py` |
| Debouncing and filtering | ✅ Implemented | `processing.py` |
| Offline queue with retry | ✅ Implemented | `queue.py` |
| Batched uploads | ✅ Implemented | `transport.py` |
| Server with SQLite | ✅ Implemented | `server/app/` |
| Multi-item dashboard | ✅ Implemented | `ui/src/` |
| Alerts with thresholds | ✅ Implemented | Server + UI |
| Real-time updates (SSE) | ✅ Implemented | Server + UI |
| Device authentication | ✅ Implemented | Bearer tokens |

### Data Flow

```
1. SENSOR READING
   ├── HX711 reads weight → raw ADC value
   ├── Normalize: (raw - tare_offset) / scale_factor → grams
   └── Pass to processor

2. PROCESSING (per sensor)
   ├── Debounce rapid fluctuations
   ├── Apply median filter (analog)
   ├── Evaluate thresholds: ok | low | out
   └── Generate reading if state changed (or always, configurable)

3. LOCAL QUEUE
   ├── SQLite database on Pi
   ├── Survives network outages
   └── FIFO with configurable retention

4. BATCH UPLOAD (every 15s or N readings)
   ├── HTTPS POST to server
   ├── Exponential backoff on failure
   └── Server acknowledges → purge from queue

5. SERVER PROCESSING
   ├── Store readings in database
   ├── Update sensor/item state
   ├── Create/resolve alerts
   └── Broadcast SSE events

6. UI UPDATE
   ├── Receives SSE event
   ├── Refreshes affected item
   └── Updates dashboard in real-time
```

### Sensor Configuration Schema

Each sensor in the config file supports:

```json
{
  "id": "unique-sensor-id",
  "type": "hx711 | digital_gpio | file_sensor",
  
  // HX711-specific
  "gpio_dout": 5,
  "gpio_sck": 6,
  "scale_factor": 2280.0,
  "tare_offset": 8388607,
  
  // Digital GPIO-specific
  "gpio_pin": 17,
  "active_high": true,
  "pull": "up",
  
  // Common
  "thresholds": {
    "low": 500,    // grams - warn when below
    "ok": 1000     // grams - ok when above
  },
  "state_map": {
    "on": "ok",
    "off": "out"
  },
  "debounce_ms": 200,
  "report_on_change_only": true
}
```

### Item-to-Sensor Mapping

Items are created via the API and linked to sensors:

```bash
# Create an item linked to a sensor
curl -X POST http://server:8000/api/v1/items \
  -H "Authorization: Bearer $UI_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rice (Basmati)",
    "sensor_id": "loadcell-rice",
    "thresholds": {"low": 500, "ok": 1000},
    "unit": "g"
  }'
```

---

## Migration Plan

### Phase 1: Preparation (Day 1)

**Goal:** Gather components and set up development environment

- [ ] **1.1** Order all hardware components
  - Raspberry Pi 4 + accessories
  - HX711 modules (one per weight sensor)
  - Load cells (sized for your containers)
  - Reed switches for doors/lids
  - Wiring, connectors, mounting hardware

- [ ] **1.2** Clone and test the software locally
  ```bash
  git clone <repository>
  cd workspace
  
  # Test device service with file sensors
  cp device/config.example.json /tmp/config.json
  # Edit to use file_sensor for testing
  echo "500" > /tmp/sensor_value.txt
  python -m smart_inventory.main --config /tmp/config.json
  ```

- [ ] **1.3** Run the server locally
  ```bash
  cd server
  python -m venv .venv
  . .venv/bin/activate
  pip install -r requirements.txt
  INVENTORY_ALLOW_UNAUTH=true uvicorn app.main:app --port 8000
  ```

- [ ] **1.4** Test the UI
  ```bash
  cd ui
  npm install
  npm run dev
  ```

### Phase 2: Raspberry Pi Setup (Day 2)

**Goal:** Configure the central hub

- [ ] **2.1** Install Raspberry Pi OS (Lite recommended)
  ```bash
  # On your computer, use Raspberry Pi Imager
  # Select: Raspberry Pi OS Lite (64-bit)
  # Configure: hostname, SSH, WiFi/Ethernet
  ```

- [ ] **2.2** Initial Pi configuration
  ```bash
  ssh pi@viktualierum-pi.local
  
  sudo apt update && sudo apt upgrade -y
  sudo apt install -y python3-pip python3-venv git
  
  # Enable interfaces
  sudo raspi-config
  # → Interface Options → Enable: SPI, I2C
  ```

- [ ] **2.3** Install GPIO libraries
  ```bash
  sudo apt install -y python3-rpi.gpio python3-spidev
  pip3 install RPi.GPIO gpiozero hx711
  ```

- [ ] **2.4** Deploy device service
  ```bash
  # Copy device code to Pi
  scp -r device/ pi@viktualierum-pi.local:~/smart-inventory/
  
  # On Pi
  cd ~/smart-inventory
  python3 -m venv .venv
  . .venv/bin/activate
  pip install requests
  ```

### Phase 3: Single Sensor Test (Day 2-3)

**Goal:** Verify one complete sensor-to-dashboard flow

- [ ] **3.1** Wire one load cell
  - Connect HX711 to GPIO 5 (DOUT) and GPIO 6 (SCK)
  - Connect load cell to HX711
  - Power from 3.3V and GND

- [ ] **3.2** Calibrate the sensor
  ```python
  # calibrate.py - run on Pi
  import RPi.GPIO as GPIO
  from hx711 import HX711
  
  GPIO.setmode(GPIO.BCM)
  hx = HX711(dout_pin=5, pd_sck_pin=6)
  hx.reset()
  
  # Get tare offset (empty)
  input("Remove all weight, press Enter...")
  tare = hx.get_raw_data_mean(readings=50)
  print(f"Tare offset: {tare}")
  
  # Get scale factor
  input("Place known weight (e.g., 1000g), press Enter...")
  with_weight = hx.get_raw_data_mean(readings=50)
  known_grams = 1000
  scale = (with_weight - tare) / known_grams
  print(f"Scale factor: {scale}")
  ```

- [ ] **3.3** Create device config
  ```json
  {
    "device": {
      "id": "viktualierum-pi-01",
      "location": "Viktualierum",
      "firmware": "0.1.0"
    },
    "network": {
      "base_url": "http://192.168.1.100:8000",
      "api_token": "your-device-token"
    },
    "storage": {
      "queue_db_path": "/var/lib/smart-inventory/queue.db"
    },
    "runtime": {
      "poll_interval_ms": 500,
      "report_on_change_only": true
    },
    "sensors": [
      {
        "id": "loadcell-rice",
        "type": "hx711",
        "gpio_dout": 5,
        "gpio_sck": 6,
        "scale_factor": 2280.0,
        "tare_offset": 8388607,
        "thresholds": {"low": 500, "ok": 1000},
        "debounce_ms": 1000
      }
    ]
  }
  ```

- [ ] **3.4** Test end-to-end
  ```bash
  # On Pi
  python -m smart_inventory.main --config /path/to/config.json
  
  # On server machine
  INVENTORY_DEVICE_TOKENS=your-device-token uvicorn app.main:app --port 8000
  
  # Create item in UI or via API
  curl -X POST http://localhost:8000/api/v1/items \
    -H "Content-Type: application/json" \
    -d '{"name": "Rice", "sensor_id": "loadcell-rice", "unit": "g"}'
  ```

### Phase 4: Multi-Sensor Deployment (Day 3-4)

**Goal:** Add remaining sensors

- [ ] **4.1** Wire additional load cells
  - Use different GPIO pairs for each HX711
  - Suggested pin pairs: (5,6), (13,19), (26,21), (12,16)

- [ ] **4.2** Calibrate each sensor
  - Run calibration script for each
  - Record tare_offset and scale_factor

- [ ] **4.3** Add reed switches for doors
  - Wire to available GPIO pins with pull-up resistors
  - Configure as `digital_gpio` sensors

- [ ] **4.4** Update config with all sensors
  ```json
  {
    "sensors": [
      {
        "id": "loadcell-rice",
        "type": "hx711",
        "gpio_dout": 5, "gpio_sck": 6,
        "scale_factor": 2280.0, "tare_offset": 8388607,
        "thresholds": {"low": 500, "ok": 1000}
      },
      {
        "id": "loadcell-flour",
        "type": "hx711",
        "gpio_dout": 13, "gpio_sck": 19,
        "scale_factor": 2150.0, "tare_offset": 8400000,
        "thresholds": {"low": 300, "ok": 800}
      },
      {
        "id": "loadcell-sugar",
        "type": "hx711",
        "gpio_dout": 26, "gpio_sck": 21,
        "scale_factor": 2200.0, "tare_offset": 8350000,
        "thresholds": {"low": 250, "ok": 500}
      },
      {
        "id": "door-main",
        "type": "digital_gpio",
        "gpio_pin": 17,
        "active_high": false,
        "pull": "up",
        "state_map": {"on": "ok", "off": "out"},
        "debounce_ms": 100
      }
    ]
  }
  ```

- [ ] **4.5** Create items for each sensor
  ```bash
  for item in "Rice:loadcell-rice" "Flour:loadcell-flour" "Sugar:loadcell-sugar"; do
    name="${item%%:*}"
    sensor="${item##*:}"
    curl -X POST http://server:8000/api/v1/items \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"name\": \"$name\", \"sensor_id\": \"$sensor\", \"unit\": \"g\"}"
  done
  ```

### Phase 5: Production Hardening (Day 5)

**Goal:** Make the system reliable and secure

- [ ] **5.1** Set up systemd service
  ```bash
  sudo cp device/systemd/smart-inventory-device.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable smart-inventory-device
  sudo systemctl start smart-inventory-device
  ```

- [ ] **5.2** Configure server security
  ```bash
  # Generate tokens
  DEVICE_TOKEN=$(openssl rand -hex 32)
  UI_TOKEN=$(openssl rand -hex 32)
  
  # Set environment variables
  export INVENTORY_DEVICE_TOKENS=$DEVICE_TOKEN
  export INVENTORY_UI_TOKEN=$UI_TOKEN
  export INVENTORY_ALLOW_UNAUTH=false
  ```

- [ ] **5.3** Set up TLS (optional but recommended)
  - Use a reverse proxy (nginx/caddy) with Let's Encrypt
  - Or self-signed certs for LAN-only setup

- [ ] **5.4** Configure automatic startup
  ```bash
  # Server as systemd service
  sudo tee /etc/systemd/system/smart-inventory-server.service << EOF
  [Unit]
  Description=Smart Inventory Server
  After=network.target
  
  [Service]
  Type=simple
  User=www-data
  WorkingDirectory=/opt/smart-inventory/server
  Environment="INVENTORY_DB_PATH=/var/lib/smart-inventory/inventory.db"
  Environment="INVENTORY_DEVICE_TOKENS=your-token"
  ExecStart=/opt/smart-inventory/server/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
  Restart=always
  
  [Install]
  WantedBy=multi-user.target
  EOF
  ```

- [ ] **5.5** Set up monitoring
  - Add health check endpoint monitoring
  - Configure log rotation
  - Set up backup for SQLite databases

### Phase 6: Testing and Tuning (Day 6-7)

**Goal:** Validate system behavior

- [ ] **6.1** Test offline resilience
  - Disconnect Pi from network
  - Add/remove items from containers
  - Reconnect and verify queued readings upload

- [ ] **6.2** Tune thresholds
  - Monitor for false alerts
  - Adjust low/ok thresholds per item based on typical consumption

- [ ] **6.3** Test alert workflow
  - Deplete an item below threshold
  - Verify alert appears in UI
  - Acknowledge alert
  - Refill item, verify alert resolves

- [ ] **6.4** Stress test
  - Simulate rapid weight changes
  - Verify debouncing works correctly
  - Check server handles multiple simultaneous updates

---

## Example Configuration

### Complete Device Config (`/etc/smart-inventory/config.json`)

```json
{
  "device": {
    "id": "viktualierum-pi-01",
    "location": "Viktualierum (Ground Floor)",
    "firmware": "1.0.0"
  },
  "network": {
    "base_url": "https://inventory.home.local",
    "api_token": "env:DEVICE_TOKEN",
    "ca_cert_path": "/etc/ssl/certs/home-ca.pem",
    "batch_size": 25,
    "flush_interval_seconds": 15,
    "retry_max_seconds": 300
  },
  "storage": {
    "queue_db_path": "/var/lib/smart-inventory/queue.db",
    "max_queue_rows": 10000,
    "max_queue_age_seconds": 604800
  },
  "runtime": {
    "poll_interval_ms": 500,
    "report_on_change_only": true,
    "state_source": "server"
  },
  "sensors": [
    {
      "id": "loadcell-rice-basmati",
      "type": "hx711",
      "gpio_dout": 5,
      "gpio_sck": 6,
      "scale_factor": 2280.0,
      "tare_offset": 8388607,
      "thresholds": {"low": 500, "ok": 1500},
      "debounce_ms": 2000,
      "report_on_change_only": true
    },
    {
      "id": "loadcell-flour-wheat",
      "type": "hx711",
      "gpio_dout": 13,
      "gpio_sck": 19,
      "scale_factor": 2150.0,
      "tare_offset": 8400000,
      "thresholds": {"low": 300, "ok": 1000},
      "debounce_ms": 2000
    },
    {
      "id": "loadcell-sugar",
      "type": "hx711",
      "gpio_dout": 26,
      "gpio_sck": 21,
      "scale_factor": 2200.0,
      "tare_offset": 8350000,
      "thresholds": {"low": 250, "ok": 750},
      "debounce_ms": 2000
    },
    {
      "id": "loadcell-pasta",
      "type": "hx711",
      "gpio_dout": 12,
      "gpio_sck": 16,
      "scale_factor": 2100.0,
      "tare_offset": 8300000,
      "thresholds": {"low": 200, "ok": 500},
      "debounce_ms": 2000
    },
    {
      "id": "loadcell-coffee",
      "type": "hx711",
      "gpio_dout": 20,
      "gpio_sck": 24,
      "scale_factor": 2250.0,
      "tare_offset": 8380000,
      "thresholds": {"low": 100, "ok": 300},
      "debounce_ms": 2000
    },
    {
      "id": "door-viktualierum",
      "type": "digital_gpio",
      "gpio_pin": 17,
      "active_high": false,
      "pull": "up",
      "state_map": {"on": "ok", "off": "out"},
      "debounce_ms": 500
    }
  ]
}
```

### Server Environment (`.env`)

```bash
INVENTORY_DB_PATH=/var/lib/smart-inventory/inventory.db
INVENTORY_DEVICE_TOKENS=a1b2c3d4e5f6...
INVENTORY_UI_TOKEN=x9y8z7w6...
INVENTORY_ALLOW_UNAUTH=false
INVENTORY_CORS_ORIGINS=https://dashboard.home.local
INVENTORY_EVENT_RETENTION_SECONDS=604800
INVENTORY_EVENT_MAX_ROWS=10000
INVENTORY_HISTORY_LIMIT=5000
```

### UI Environment (`.env`)

```bash
VITE_API_BASE_URL=https://inventory.home.local
VITE_UI_TOKEN=x9y8z7w6...
VITE_POLL_INTERVAL_MS=15000
```

---

## Maintenance and Operations

### Daily Operations

The system is designed to be hands-off. Check the dashboard periodically for:
- Low stock alerts
- Device connectivity (last seen timestamp)
- Any unacknowledged alerts

### Periodic Maintenance

**Weekly:**
- Review alert history for patterns
- Check disk space on Pi and server

**Monthly:**
- Verify load cell calibration (place known weight)
- Check for software updates
- Review logs for errors

**Quarterly:**
- Backup SQLite databases
- Clean sensors and wiring connections
- Test offline/recovery behavior

### Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Sensor shows 0 or erratic values | Loose wiring | Check HX711 connections |
| No data in dashboard | Network issue | Check Pi connectivity, view queue |
| False low alerts | Threshold too high | Adjust threshold via API |
| Dashboard not updating | SSE disconnected | Check CORS, refresh page |
| Pi not responding | SD card failure | Replace card, restore config |

### Useful Commands

```bash
# Check device service status
sudo systemctl status smart-inventory-device
sudo journalctl -u smart-inventory-device -f

# View queued readings on Pi
sqlite3 /var/lib/smart-inventory/queue.db "SELECT COUNT(*) FROM readings;"

# Manual sensor test
python3 -c "
from hx711 import HX711
hx = HX711(5, 6)
print(hx.get_data_mean(readings=10))
"

# Server health check
curl http://server:8000/api/v1/health

# List all items with status
curl -H "Authorization: Bearer $TOKEN" http://server:8000/api/v1/items | jq '.items[] | {name, status, last_value}'
```

---

## Cost Estimate

For a typical viktualierum with 5 weight sensors and 1 door sensor:

| Category | Items | Cost (EUR) |
|----------|-------|------------|
| Central Unit | Pi 4, SD, PSU, case | ~€75-90 |
| Weight Sensors (×5) | HX711 + load cells | ~€40-75 |
| Door Sensor (×1) | Reed switch + resistor | ~€3 |
| Wiring & Mounting | Cables, terminals, platforms | ~€20-30 |
| **Total** | | **~€140-200** |

---

## Next Steps

1. Review this proposal and adjust the sensor list to match your storage needs
2. Order components
3. Follow the migration plan step by step
4. Iterate on thresholds based on actual usage patterns

The existing codebase is fully capable of supporting this setup. No code changes are required - only configuration and hardware assembly.
