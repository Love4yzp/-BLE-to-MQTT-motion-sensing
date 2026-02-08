# Sensor Config TUI

Terminal UI client for configuring nRF52840 sensors over AT commands.

Features:
- Config panel for THRESHOLD / TAILWINDOW / TXPOWER
- Live serial monitor for motion/status logs
- Preset save/load and batch apply

## Requirements

- Python 3.10+
- Serial driver for the board

## Install

Using uv (recommended):

```bash
cd app/tools/sensor-config
uv sync
uv run python app.py
```

Using pip:

```bash
cd app/tools/sensor-config
python -m venv .venv
source .venv/bin/activate
pip install "pyserial>=3.5" "pyyaml>=6.0" "textual>=0.74.0"
python app.py
```

## Usage

1. Connect the sensor via USB.
2. Select the serial port and press Connect.
3. Click Read Info to sync the current config.
4. Adjust values and press Apply, then Save if you want persistence.

## Presets

Preset files live in `presets/`:

```yaml
name: standard
threshold_hex: 0x0A
tail_window_ms: 3000
tx_power_dbm: 4
```

You can add your own preset files and they will appear in the UI.
