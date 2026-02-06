# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SeeedUA Smart Retail — an IoT system that detects when products are picked up from shelves using BLE motion sensors and triggers video playback on screens via MQTT. Three components:

1. **nRF52840 Sensor Firmware** (`XIAO_nRF52840_LowPowerMotionDetect/`) — Arduino C++, runs on Seeed XIAO nRF52840 Sense with LSM6DS3 IMU. Sleeps at <5µA, wakes on motion, broadcasts BTHome v2 BLE packets, returns to sleep.
2. **ESP32 Gateway Firmware** (`XIAO_ESP32_Series_BluetoothProxy/`) — Arduino C++, runs on XIAO ESP32-C3/S3/C6/C5. Scans BLE, converts BTHome broadcasts to JSON, publishes over MQTT.
3. **FastAPI Backend** (`backend/`) — Python. Manages product-to-video mappings, consumes MQTT sensor events, deduplicates, publishes screen playback commands. Serves admin web UI.

## Build & Development

### Arduino Firmware (both projects)

Developed in Arduino IDE. No Makefile or PlatformIO — open the `.ino` file directly.

**nRF52840 Sensor:**
- Board package: Seeed nRF52 Boards (Adafruit BSP)
- Library: Seeed Arduino LSM6DS3
- Board selection: Seeed XIAO nRF52840 Sense
- FQBN: `Seeeduino:nrf52:xiaonRF52840Sense`
- CLI compile: `arduino-cli compile --fqbn Seeeduino:nrf52:xiaonRF52840Sense XIAO_nRF52840_LowPowerMotionDetect/`
- Serial monitor: 115200 baud
- USB mode AT commands for runtime config: `AT+HELP`, `AT+INFO`, `AT+THRESHOLD=0x0A`, `AT+TAILWINDOW=3000`, `AT+TXPOWER=4`, `AT+SAVE`, `AT+REBOOT`

**ESP32 Gateway:**
- Board package: Espressif ESP32 Arduino
- Libraries: WiFiManager, PubSubClient, ArduinoJson, NimBLE
- Partition scheme: Minimal SPIFFS
- Supports C3/S3/C6/C5 variants (pin mappings auto-detected via board defines)

### Python Backend

```bash
cd backend
pip install -r requirements.txt
python main.py                    # http://localhost:8080
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Configuration via environment variables or `.env` file (see `config.py` — Pydantic BaseSettings).

## Architecture — Data Flow

```
nRF52840 Sensor (BLE broadcast, BTHome UUID 0xFCD2)
    → ESP32 Gateway (BLE scan → MQTT publish to bthome/{mac}/state)
    → MQTT Broker (Mosquitto)
    → FastAPI Backend (dedup 2s window → lookup product_map.csv → publish screen/{id}/play)
    → Display Player (plays video)
```

## Key Technical Details

### nRF52840 Sensor

- **Power modes**: Auto-detects USB vs battery via VBUS voltage. USB mode enables serial CLI + diagnostic output. Battery mode is production (deep sleep → wake → broadcast → sleep).
- **Motion detection**: LSM6DS3 wake-up interrupt on INT1 (GPIO P0.11). Threshold configurable 0x02-0x3F (value × 31.25mg). No activity state machine — uses wake-up pulse only.
- **Broadcast cycle**: Wake → 300ms fast BLE advertising (20ms interval) → 3s tail window (listens for more motion) → sleep.
- **Sensitivity presets** in `config.h`: 0=custom, 1=high, 2=standard (default), 3=low. Affects threshold, tail window, TX power.
- **Flash storage**: Runtime config persisted to last 4KB page of nRF52840 flash (custom implementation, not NVMC library).
- **LED pins**: GPIO12 (blue), GPIO13 (green). Green flash = motion detected, blue flash = entering sleep.

### ESP32 Gateway

- **WiFiManager portal**: Creates `SeeedUA-Gateway` AP if unconfigured. Config stored in EEPROM.
- **MQTT topics published**: `bthome/{mac}/state` (sensor data), `gateway/{id}/info` (self-registration).
- **MQTT topics subscribed**: `gateway/{id}/cmd` (identify command triggers LED blink).
- **Device filtering**: Only processes BLE devices with name prefix `SeeedUA-`.

### FastAPI Backend

- **Product mapping**: `data/product_map.csv` — MAC address (lowercase, no colons) → SKU → product name → video file → screen ID.
- **Gateway registry**: `data/gateways.json` — auto-updated when gateways report info.
- **Deduplication**: Same MAC within `dedup_window` (default 2s) is ignored.
- **Sensor timeout**: Background thread checks every 1s. If no motion for `sensor_timeout` (default 5s), emits "put_down" event.
- **Event log**: In-memory ring buffer, last 100 events.
- **i18n**: Chinese (zh) and English (en), translation files in `backend/locales/`.
- **Threading**: Daemon threads for MQTT client loop and timeout checker, initialized in FastAPI lifespan context manager.

## MQTT Topic Reference

| Topic | Direction | Payload |
|-------|-----------|---------|
| `bthome/{mac}/state` | Gateway → Backend | `{"motion": bool, "rssi": int, "gateway_id": str}` |
| `screen/{id}/play` | Backend → Player | `{"video": str, "sku": str, "name": str}` |
| `gateway/{id}/info` | Gateway → Backend | `{"gateway_id", "mac", "ip", "board"}` |
| `gateway/{id}/cmd` | Backend → Gateway | `{"action": "identify"}` |

## Conventions

- MAC addresses are normalized to lowercase hex without colons (e.g., `f7dac49b63d1`).
- Commit messages follow conventional commits: `fix(sensor):`, `feat(gateway):`, `docs:`, `debug(sensor):`.
- The nRF52840 firmware uses a modular multi-file architecture: thin `.ino` entry point → `app.h/cpp` orchestrator → module files (`ble_adv`, `imu`, `power`, `flash_store`, `cli_at`, `telemetry`, etc.). Note: `ble_adv.h` (not `ble.h`) to avoid name collision with Nordic SDK's `ble.h`.
- Both firmware projects use `config.h` for deployment-specific settings (credentials, sensitivity presets).
