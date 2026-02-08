from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import SensorConfigApp
from i18n import get_locale, set_locale
from models import DeviceState, parse_at_line, apply_at_update, parse_threshold_value
from serial_client import SerialClient
from widgets import DeviceCard, PresetCard


@pytest.mark.asyncio
async def test_app_launches_and_has_tabs(mock_serial_ports):
    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        tabs = app.query("TabPane")
        tab_ids = {tab.id for tab in tabs}
        assert "tab-devices" in tab_ids
        assert "tab-presets" in tab_ids
        assert "tab-config" in tab_ids
        assert "tab-log" in tab_ids


@pytest.mark.asyncio
async def test_port_select_populated(mock_serial_ports):
    from textual.widgets import Select

    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        select = app.query_one("#port-select", Select)
        assert select is not None
        option_values = [val for _label, val in select._options]
        assert "/dev/cu.fake1" in option_values
        assert "/dev/cu.fake2" in option_values
        assert "/dev/cu.fake3" in option_values


@pytest.mark.asyncio
async def test_preset_cards_rendered(mock_serial_ports):
    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        cards = list(app.query(PresetCard))
        assert len(cards) == 3

        preset_names = {c.preset.name for c in cards}
        assert "standard" in preset_names
        assert "high" in preset_names
        assert "low" in preset_names


@pytest.mark.asyncio
async def test_config_inputs_exist(mock_serial_ports):
    from textual.widgets import Input

    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        threshold_input = app.query_one("#input-threshold", Input)
        tail_input = app.query_one("#input-tail", Input)
        tx_input = app.query_one("#input-tx", Input)

        assert threshold_input is not None
        assert tail_input is not None
        assert tx_input is not None


@pytest.mark.asyncio
async def test_config_buttons_exist(mock_serial_ports):
    from textual.widgets import Button

    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        apply_btn = app.query_one("#btn-apply-config", Button)
        save_btn = app.query_one("#btn-save-flash", Button)
        defaults_btn = app.query_one("#btn-defaults", Button)
        reboot_btn = app.query_one("#btn-reboot", Button)

        assert apply_btn is not None
        assert save_btn is not None
        assert defaults_btn is not None
        assert reboot_btn is not None


@pytest.mark.asyncio
async def test_status_bar_shows_port_count(mock_serial_ports):
    from textual.widgets import Label

    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        status = app.query_one("#status-bar", Label)
        rendered = str(status.render())
        assert "3" in rendered


@pytest.mark.asyncio
async def test_no_device_hint_visible(mock_serial_ports):
    from textual.widgets import Label

    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        hint = app.query_one("#no-device-hint", Label)
        assert hint is not None


@pytest.mark.asyncio
async def test_log_widget_exists(mock_serial_ports):
    from textual.widgets import RichLog

    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        log = app.query_one("#log", RichLog)
        assert log is not None


@pytest.mark.asyncio
async def test_language_switch(mock_serial_ports):
    set_locale("zh")
    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        initial = get_locale()

        await pilot.press("l")
        await pilot.pause()
        switched = get_locale()
        assert switched != initial

        await pilot.press("l")
        await pilot.pause()
        assert get_locale() == initial

        await pilot.press("l")
        await pilot.pause()
        assert get_locale() == "en"

        await pilot.press("l")
        await pilot.pause()
        assert get_locale() == "zh"


@pytest.mark.asyncio
async def test_connect_without_selection_warns(mock_serial_ports):
    from textual.widgets import Select

    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        select = app.query_one("#port-select", Select)
        select.value = Select.BLANK

        await pilot.click("#btn-connect")
        await pilot.pause()


@pytest.mark.asyncio
async def test_keyboard_tab_switching(mock_serial_ports):
    from textual.widgets import TabbedContent

    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        tc = app.query_one(TabbedContent)

        await pilot.press("2")
        await pilot.pause()
        assert tc.active == "tab-presets"

        await pilot.press("3")
        await pilot.pause()
        assert tc.active == "tab-config"

        await pilot.press("4")
        await pilot.pause()
        assert tc.active == "tab-log"

        await pilot.press("1")
        await pilot.pause()
        assert tc.active == "tab-devices"


@pytest.mark.asyncio
async def test_preset_card_has_threshold_values(mock_serial_ports):
    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        cards = list(app.query(PresetCard))
        standard = [c for c in cards if c.preset.name == "standard"][0]
        assert standard.preset.threshold > 0
        assert standard.preset.tail_window >= 1000
        assert -40 <= standard.preset.tx_power <= 4


@pytest.mark.asyncio
async def test_language_switch_with_device_connected(mock_serial_ports):
    set_locale("zh")
    app = SensorConfigApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        mock_client = MagicMock(spec=SerialClient)
        mock_client.is_connected.return_value = True
        app.clients["/dev/cu.fake1"] = mock_client
        app.device_states["/dev/cu.fake1"] = DeviceState(
            port="/dev/cu.fake1", connected=True, mac="AABBCCDDEEFF"
        )
        app.selected_port = "/dev/cu.fake1"
        app._push_device_panel_state()
        await pilot.pause()

        cards = list(app.query(DeviceCard))
        assert len(cards) == 1

        await pilot.press("l")
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()
        await pilot.press("l")
        await pilot.pause()

        cards_after = list(app.query(DeviceCard))
        assert len(cards_after) >= 1


@pytest.mark.asyncio
async def test_parse_threshold():
    assert parse_threshold_value("0x0A") == 10
    assert parse_threshold_value("0x3F") == 63
    assert parse_threshold_value("0a") == 10
    assert parse_threshold_value(None) == 10
    assert parse_threshold_value(15) == 15
    assert parse_threshold_value("invalid") == 10


@pytest.mark.asyncio
async def test_parse_at_line_mac():
    update = parse_at_line("  MAC: AABBCCDDEEFF")
    assert update.mac == "AABBCCDDEEFF"
    assert update.name is None


@pytest.mark.asyncio
async def test_parse_at_line_threshold():
    update = parse_at_line("THRESHOLD=0x0A")
    assert update.threshold == 0x0A


@pytest.mark.asyncio
async def test_apply_at_update():
    state = DeviceState(port="/dev/test")
    from models import ATUpdate

    update = ATUpdate(mac="ABCDEF123456", threshold=5)
    changed = apply_at_update(state, update)
    assert changed is True
    assert state.mac == "ABCDEF123456"
    assert state.threshold == 5

    changed2 = apply_at_update(state, ATUpdate())
    assert changed2 is False
