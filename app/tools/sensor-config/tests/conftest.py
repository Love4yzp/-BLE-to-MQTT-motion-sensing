"""Shared fixtures for sensor-config TUI tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure app module is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakePortInfo:
    """Fake serial port info for testing without real hardware."""

    def __init__(self, device: str, description: str = "Fake Device"):
        self.device = device
        self.description = description


@pytest.fixture
def mock_serial_ports():
    """Mock serial.tools.list_ports.comports to return fake ports."""
    fake_ports = [
        FakePortInfo("/dev/cu.fake1", "Seeed XIAO nRF52840 #1"),
        FakePortInfo("/dev/cu.fake2", "Seeed XIAO nRF52840 #2"),
        FakePortInfo("/dev/cu.fake3", "USB Serial Device"),
    ]
    with patch("serial.tools.list_ports.comports", return_value=fake_ports):
        yield fake_ports
