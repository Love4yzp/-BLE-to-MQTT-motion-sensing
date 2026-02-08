from __future__ import annotations

import functools
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from rich.markup import escape as rich_escape
from serial.tools import list_ports
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.validation import Function, Regex
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    TabbedContent,
    TabPane,
)

from i18n import get_locale, set_locale, t
from models import (
    DeviceState,
    Preset,
    apply_at_update,
    parse_at_line,
    parse_threshold_value,
)
from serial_client import SerialClient
from widgets import DeviceCard, DevicePanel, PresetCard


class SensorConfigApp(App):
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh_ports", "Refresh"),
        Binding("1", "show_tab('tab-devices')", "Devices"),
        Binding("2", "show_tab('tab-presets')", "Presets"),
        Binding("3", "show_tab('tab-config')", "Config"),
        Binding("4", "show_tab('tab-log')", "Log"),
        Binding("l", "switch_lang", "Lang"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.clients: Dict[str, SerialClient] = {}
        self.device_states: Dict[str, DeviceState] = {}
        self.presets: Dict[str, Preset] = {}
        self.preset_dir = Path(__file__).resolve().parent / "presets"
        self.has_switched_to_presets = False
        self.selected_port: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent(initial="tab-devices"):
            with TabPane(t("tabs.devices"), id="tab-devices"):
                yield DevicePanel(id="device-panel")

            with TabPane(t("tabs.presets"), id="tab-presets"):
                with VerticalScroll(id="preset-container"):
                    for preset in self.presets.values():
                        yield PresetCard(preset)

            with TabPane(t("tabs.config"), id="tab-config"):
                with VerticalScroll(classes="config-section"):
                    yield Label(t("devices.target_none"), id="config-target-label")

                    yield Label(t("config.threshold_label"), classes="field-label")
                    yield Input(
                        placeholder="0x0A",
                        id="input-threshold",
                        validators=[
                            Regex(r"^0x[0-9A-Fa-f]{2}$", "Must be hex 0x02-0x3F")
                        ],
                    )
                    yield Label(
                        t("config.threshold_explanation"),
                        classes="field-explanation",
                    )

                    yield Label(t("config.tail_label"), classes="field-label")
                    yield Input(
                        placeholder="3000",
                        id="input-tail",
                        validators=[
                            Function(
                                lambda v: v.isdigit() and 1000 <= int(v) <= 10000,
                                "Must be 1000-10000 ms",
                            )
                        ],
                    )
                    yield Label(
                        t("config.tail_explanation"), classes="field-explanation"
                    )

                    yield Label(t("config.tx_label"), classes="field-label")
                    yield Input(
                        placeholder="4",
                        id="input-tx",
                        validators=[
                            Function(
                                lambda v: (v.lstrip("-").isdigit())
                                and -40 <= int(v) <= 4,
                                "Must be -40 to 4 dBm",
                            )
                        ],
                    )
                    yield Label(t("config.tx_explanation"), classes="field-explanation")

                    with Horizontal(classes="button-row"):
                        yield Button(
                            t("config.apply_config"),
                            id="btn-apply-config",
                            variant="primary",
                        )
                        yield Button(
                            t("config.save_flash"),
                            id="btn-save-flash",
                            variant="warning",
                        )
                        yield Button(t("config.restore_defaults"), id="btn-defaults")
                        yield Button(
                            t("config.reboot"), id="btn-reboot", variant="error"
                        )

            with TabPane(t("tabs.log"), id="tab-log"):
                yield RichLog(id="log", wrap=True, highlight=False, markup=True)

        yield Label(t("devices.status_ready"), id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._load_presets()
        self._refresh_ports()

    def _load_presets(self) -> None:
        presets: Dict[str, Preset] = {}
        if self.preset_dir.exists():
            for path in sorted(self.preset_dir.glob("*.yaml")):
                try:
                    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                    name = data.get("name") or path.stem

                    meta_label = t(f"presets.{name}.label")
                    meta_desc = t(f"presets.{name}.desc")
                    meta_scenario = t(f"presets.{name}.scenario")
                    meta_battery = t(f"presets.{name}.battery")

                    presets[name] = Preset(
                        name=name,
                        threshold=parse_threshold_value(data.get("threshold_hex")),
                        tail_window=int(data.get("tail_window_ms", 3000)),
                        tx_power=int(data.get("tx_power_dbm", 4)),
                        label=(
                            meta_label
                            if meta_label != f"presets.{name}.label"
                            else name
                        ),
                        description=(
                            "" if meta_desc == f"presets.{name}.desc" else meta_desc
                        ),
                        scenario=(
                            ""
                            if meta_scenario == f"presets.{name}.scenario"
                            else meta_scenario
                        ),
                        battery=(
                            ""
                            if meta_battery == f"presets.{name}.battery"
                            else meta_battery
                        ),
                    )
                except Exception as e:
                    self.notify(
                        f"Error loading preset {path.name}: {e}", severity="error"
                    )
        self.presets = presets
        self._rebuild_preset_container()

    def _rebuild_preset_container(self) -> None:
        try:
            container = self.query_one("#preset-container")
        except Exception:
            return
        for child in list(container.query(PresetCard)):
            child.remove()
        for preset in self.presets.values():
            container.mount(PresetCard(preset))

    def _refresh_ports(self) -> None:
        ports = list_ports.comports()
        current = {p.device for p in ports}

        for port in list(self.clients.keys()):
            if port not in current:
                self._disconnect_device(port)

        options = [
            (f"{p.device} - {p.description}", p.device)
            for p in ports
            if p.device not in self.clients
        ]
        self._push_device_panel_state(port_options=options)
        self._update_status_bar(total=len(ports))

    def _push_device_panel_state(
        self,
        port_options: Optional[List] = None,
    ) -> None:
        try:
            panel = self.query_one("#device-panel", DevicePanel)
        except Exception:
            return
        panel.devices = dict(self.device_states)
        panel.selected_port = self.selected_port
        if port_options is not None:
            panel.port_options = port_options

    def _update_status_bar(self, total: Optional[int] = None) -> None:
        if total is None:
            total = len(list_ports.comports())
        try:
            self.query_one("#status-bar", Label).update(
                t("devices.status_bar", total=total, connected=len(self.clients))
            )
        except Exception:
            pass

    @on(DevicePanel.ConnectRequested)
    def _on_connect_requested(self, message: DevicePanel.ConnectRequested) -> None:
        if message.port is None:
            self.notify(t("devices_notify.select_port_first"), severity="warning")
            return
        if message.port in self.clients:
            self.notify(t("devices_notify.already_connected"), severity="warning")
            return
        self._connect_device(message.port)

    @work(thread=True, exclusive=True, group="serial-connect")
    def _connect_device(self, port: str) -> None:
        if port in self.clients and self.clients[port].is_connected():
            return

        self.device_states.setdefault(port, DeviceState(port=port))

        client = SerialClient(
            port=port,
            on_line=functools.partial(self._on_serial_line, port),
        )
        try:
            client.connect()
            self.clients[port] = client
            self.device_states[port].connected = True
            self._log_message(
                port,
                f"[green]{t('log.connected', port=rich_escape(port))}[/green]",
            )
            self.call_from_thread(self._after_connect, port)
        except Exception as e:
            self._log_message(port, f"[red]Connection failed: {e}[/red]")
            self.call_from_thread(
                self.notify,
                t(
                    "devices_notify.connect_failed",
                    port=rich_escape(port),
                    error=str(e),
                ),
                severity="error",
            )

    def _after_connect(self, port: str) -> None:
        self.notify(t("devices_notify.connected", port=rich_escape(port)))

        if self.selected_port is None:
            self.selected_port = port
            try:
                self.query_one("#config-target-label", Label).update(
                    t("devices.target_label", port=rich_escape(port))
                )
            except Exception:
                pass

        self._send_command(port, "AT+INFO")

        if not self.has_switched_to_presets:
            try:
                self.query_one(TabbedContent).active = "tab-presets"
            except Exception:
                pass
            self.has_switched_to_presets = True

        self._refresh_ports()
        self._push_device_panel_state()

    @on(DeviceCard.DisconnectRequested)
    def _on_disconnect_requested(self, message: DeviceCard.DisconnectRequested) -> None:
        self._disconnect_device(message.port)

    def _disconnect_device(self, port: str) -> None:
        if port in self.clients:
            try:
                self.clients[port].disconnect()
            except Exception:
                pass
            del self.clients[port]

        if port in self.device_states:
            self.device_states[port].connected = False
            self.device_states[port].mac = "-"
            self.device_states[port].name = "-"

        if self.selected_port == port:
            self.selected_port = next(iter(self.clients), None)
            target_text = (
                t("devices.target_label", port=rich_escape(self.selected_port))
                if self.selected_port
                else t("devices.target_none")
            )
            try:
                self.query_one("#config-target-label", Label).update(target_text)
            except Exception:
                pass

        self._log_message(port, "[yellow]Disconnected[/yellow]")
        self._refresh_ports()
        self._push_device_panel_state()

    @on(DeviceCard.Selected)
    def _on_device_selected(self, message: DeviceCard.Selected) -> None:
        self.selected_port = message.port
        try:
            self.query_one("#config-target-label", Label).update(
                t("devices.target_label", port=rich_escape(message.port))
            )
        except Exception:
            pass
        self._push_device_panel_state()
        if message.port in self.clients:
            self._send_command(message.port, "AT+INFO")

    @on(DevicePanel.RefreshRequested)
    def _on_refresh_requested(self, message: DevicePanel.RefreshRequested) -> None:
        self._refresh_ports()
        self.notify(t("devices_notify.ports_refreshed"))

    def _on_serial_line(self, port: str, line: str) -> None:
        self.call_from_thread(self._handle_serial_line, port, line)

    def _handle_serial_line(self, port: str, line: str) -> None:
        self._log_message(port, line)

        state = self.device_states.get(port)
        if not state:
            return

        update = parse_at_line(line)
        changed = apply_at_update(state, update)

        if changed:
            self._push_device_panel_state()

        if self.selected_port == port:
            if update.threshold is not None:
                try:
                    self.query_one(
                        "#input-threshold", Input
                    ).value = f"0x{state.threshold:02X}"
                except Exception:
                    pass
            if update.tail_window is not None:
                try:
                    self.query_one("#input-tail", Input).value = str(state.tail_window)
                except Exception:
                    pass
            if update.tx_power is not None:
                try:
                    self.query_one("#input-tx", Input).value = str(state.tx_power)
                except Exception:
                    pass

    def _send_command(self, port: str, command: str) -> None:
        if port in self.clients:
            self._log_message(port, f"[blue]>> {command}[/blue]")
            try:
                self.clients[port].send_command(command)
            except Exception as e:
                self._log_message(
                    port,
                    f"[red]{t('log.command_error', error=str(e))}[/red]",
                )

    def _log_message(self, port: str, message: str) -> None:
        try:
            log = self.query_one("#log", RichLog)
            log.write(f"[{rich_escape(port)}] {message}")
        except Exception:
            pass

    @on(PresetCard.Applied)
    def _on_preset_applied(self, message: PresetCard.Applied) -> None:
        targets: List[str] = []
        if message.target == "all":
            targets = list(self.clients.keys())
        elif message.target == "selected":
            if self.selected_port and self.selected_port in self.clients:
                targets = [self.selected_port]
            else:
                self.notify(t("preset_notify.no_device_selected"), severity="warning")
                return

        if not targets:
            self.notify(t("preset_notify.no_devices"), severity="warning")
            return

        preset = message.preset
        self.notify(t("preset_notify.applying", name=preset.name, count=len(targets)))

        commands = [
            f"AT+THRESHOLD={preset.threshold:02X}",
            f"AT+TAILWINDOW={preset.tail_window}",
            f"AT+TXPOWER={preset.tx_power}",
            "AT+INFO",
        ]

        for port in targets:
            self._send_commands_batch(port, commands)

    @work(thread=True)
    def _send_commands_batch(self, port: str, commands: List[str]) -> None:
        for cmd in commands:
            self._send_command(port, cmd)
            time.sleep(0.1)

    @on(Button.Pressed, "#btn-apply-config")
    def _on_apply_config(self) -> None:
        if not self.selected_port or self.selected_port not in self.clients:
            self.notify(t("config_notify.no_device"), severity="error")
            return
        try:
            t_val = self.query_one("#input-threshold", Input).value
            threshold = parse_threshold_value(t_val)
            tail = int(self.query_one("#input-tail", Input).value)
            tx = int(self.query_one("#input-tx", Input).value)

            commands = [
                f"AT+THRESHOLD={threshold:02X}",
                f"AT+TAILWINDOW={tail}",
                f"AT+TXPOWER={tx}",
                "AT+INFO",
            ]
            self._send_commands_batch(self.selected_port, commands)
            self.notify(t("config_notify.applied"))
        except Exception as e:
            self.notify(
                t("config_notify.invalid_values", error=str(e)), severity="error"
            )

    @on(Button.Pressed, "#btn-save-flash")
    def _on_save_flash(self) -> None:
        if self.selected_port and self.selected_port in self.clients:
            self._send_command(self.selected_port, "AT+SAVE")
            self.notify(t("config_notify.saved"))

    @on(Button.Pressed, "#btn-defaults")
    def _on_defaults(self) -> None:
        if self.selected_port and self.selected_port in self.clients:
            self._send_command(self.selected_port, "AT+DEFAULT")
            self.notify(t("config_notify.restored"))

    @on(Button.Pressed, "#btn-reboot")
    def _on_reboot(self) -> None:
        if self.selected_port and self.selected_port in self.clients:
            self._send_command(self.selected_port, "AT+REBOOT")
            self.notify(t("config_notify.rebooting"))

    def action_show_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_refresh_ports(self) -> None:
        self._refresh_ports()
        self.notify(t("devices_notify.ports_refreshed"))

    def action_switch_lang(self) -> None:
        new_lang = "en" if get_locale() == "zh" else "zh"
        set_locale(new_lang)
        self.notify(f"{t('bindings.switch_lang')}: {new_lang}")
        self._load_presets()
        self._refresh_ports()
        self._push_device_panel_state()

    def _parse_threshold_value(self, raw: object) -> int:
        return parse_threshold_value(raw)


if __name__ == "__main__":
    SensorConfigApp().run()
