# App Layer

This folder contains user-facing applications and tooling for the system.

## Contents

- `app/backend/` — FastAPI backend service (MQTT ingestion, product mapping, playback triggers)
- `app/tools/sensor-config/` — USB AT command TUI for configuring nRF52840 sensors

## Quick Start

### Backend

```bash
cd app/backend
uv sync
cp .env.example .env
uv run python main.py
```

### Sensor Config TUI

```bash
cd app/tools/sensor-config
uv sync
uv run python app.py
```

## Notes

- The firmware projects live at the repo root:
  - `XIAO_nRF52840_LowPowerMotionDetect/`
  - `XIAO_ESP32_Series_BluetoothProxy/`
