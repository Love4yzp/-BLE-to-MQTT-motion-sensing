from __future__ import annotations

import functools
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List

import yaml
from rich.markup import escape as rich_escape
from serial.tools import list_ports
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, Grid, VerticalScroll
from textual.validation import Regex, Function
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
    Label,
)

from serial_client import SerialClient


@dataclass
class Preset:
    name: str
    threshold: int
    tail_window: int
    tx_power: int
    label: str = ""
    description: str = ""
    scenario: str = ""
    battery: str = ""


@dataclass
class DeviceState:
    port: str
    connected: bool = False
    mac: str = "-"
    name: str = "-"
    threshold: Optional[int] = None
    tail_window: Optional[int] = None
    tx_power: Optional[int] = None


PRESET_META = {
    "standard": {
        "label": "标准模式",
        "desc": "平衡响应与续航",
        "scenario": "通用场景",
        "battery": "~6个月",
    },
    "high": {
        "label": "高灵敏模式",
        "desc": "极速响应",
        "scenario": "快速互动",
        "battery": "~3个月",
    },
    "low": {
        "label": "低功耗模式",
        "desc": "延长续航",
        "scenario": "展示陈列",
        "battery": "~12个月",
    },
}

EXPLANATIONS = {
    "threshold": "运动阈值 — 越小越灵敏，误触发风险增加；越大越迟钝，可能漏检",
    "tail": "尾随窗口 — 广播结束后等待时间，越长越耗电但能合并连续动作",
    "tx": "发射功率 — 越高覆盖越远但略耗电",
}


class PresetCard(Static):
    def __init__(self, preset: Preset, apply_callback):
        super().__init__()
        self.preset = preset
        self.apply_callback = apply_callback

    def compose(self) -> ComposeResult:
        with Vertical(classes="preset-card-inner"):
            yield Label(
                f"[bold]{self.preset.label or self.preset.name}[/bold]",
                classes="preset-title",
            )
            if self.preset.description:
                yield Label(
                    f"[dim]{self.preset.description}[/dim]", classes="preset-desc"
                )

            with Grid(classes="preset-stats"):
                yield Label(f"阈值: 0x{self.preset.threshold:02X}")
                yield Label(f"窗口: {self.preset.tail_window}ms")
                yield Label(f"功率: {self.preset.tx_power}dBm")
                if self.preset.battery:
                    yield Label(f"续航: {self.preset.battery}")
                if self.preset.scenario:
                    yield Label(f"场景: {self.preset.scenario}")

            with Horizontal(classes="preset-actions"):
                yield Button(
                    "应用到选中",
                    id=f"apply-sel-{self.preset.name}",
                    variant="primary",
                    classes="preset-btn",
                )
                yield Button(
                    "应用到所有",
                    id=f"apply-all-{self.preset.name}",
                    variant="warning",
                    classes="preset-btn",
                )

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if "apply-sel" in event.button.id:
            self.apply_callback(self.preset, target="selected")
        elif "apply-all" in event.button.id:
            self.apply_callback(self.preset, target="all")


class DeviceCard(Static):
    def __init__(self, port: str, state: DeviceState, on_select, on_disconnect):
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", port)
        super().__init__(id=f"device-{safe_id}")
        self.port = port
        self.state = state
        self._on_select = on_select
        self._on_disconnect = on_disconnect

    def compose(self) -> ComposeResult:
        with Horizontal(classes="card-header"):
            status = "[green]●[/green]" if self.state.connected else "[red]●[/red]"
            yield Label(f"{status}  {rich_escape(self.port)}", classes="card-port")
            safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", self.port)
            yield Button(
                "断开",
                id=f"dc-{safe_id}",
                variant="error",
                classes="disconnect-btn",
            )
        with Horizontal(classes="card-info"):
            yield Label(f"MAC: {self.state.mac}  |  名称: {self.state.name}")

    def on_click(self, event) -> None:
        self._on_select(self.port)

    @on(Button.Pressed)
    def on_disconnect_btn(self, event: Button.Pressed) -> None:
        event.stop()
        self._on_disconnect(self.port)


class SensorConfigApp(App):
    CSS = """
    Screen {
        background: $surface;
    }

    TabbedContent {
        height: 1fr;
    }

    #device-stack {
        height: 1fr;
        padding: 1;
    }

    DeviceCard {
        height: auto;
        padding: 1;
        margin: 0 0 1 0;
        background: $surface-lighten-1;
        border: tall $primary;
    }

    DeviceCard.selected {
        border: tall $accent;
        background: $surface-lighten-2;
    }

    .card-header {
        height: auto;
        align: left middle;
    }

    .card-port {
        width: 1fr;
    }

    .card-info {
        height: auto;
        margin-left: 2;
        color: $text-muted;
    }

    .disconnect-btn {
        margin-left: 1;
    }

    #preset-container {
        layout: grid;
        grid-size: 3;
        grid-gutter: 1;
        padding: 1;
    }

    PresetCard {
        height: auto;
        background: $surface-lighten-1;
        border: tall $primary;
        padding: 1;
    }
    
    PresetCard:hover {
        border: tall $accent;
    }

    .preset-title {
        text-align: center;
        width: 100%;
        padding-bottom: 1;
    }

    .preset-desc {
        text-align: center;
        width: 100%;
        padding-bottom: 1;
    }

    .preset-stats {
        grid-size: 2;
        grid-gutter: 1;
        margin-bottom: 1;
    }

    .preset-actions {
        align: center middle;
        height: auto;
        margin-top: 1;
    }

    .preset-btn {
        margin: 0 1;
    }

    .config-section {
        padding: 1 2;
    }

    .field-label {
        margin-top: 1;
        color: $text-muted;
    }

    .field-explanation {
        margin-bottom: 1;
        color: $text-muted;
        text-style: italic;
    }

    Input {
        margin-bottom: 0;
    }

    RichLog {
        background: $surface;
        color: $text;
        border: solid $accent;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $primary-darken-2;
        color: $text-muted;
        padding-left: 1;
    }
    
    .button-row {
        height: auto;
        margin: 1 0;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    
    Select {
        width: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出"),
        Binding("r", "refresh_ports", "刷新端口"),
        Binding("1", "show_tab('tab-devices')", "设备"),
        Binding("2", "show_tab('tab-presets')", "预设"),
        Binding("3", "show_tab('tab-config')", "高级配置"),
        Binding("4", "show_tab('tab-log')", "日志"),
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
            with TabPane("设备 (Devices)", id="tab-devices"):
                with Horizontal(classes="button-row"):
                    yield Select([], id="port-select", prompt="选择串口...")
                    yield Button("连接", id="btn-connect", variant="success")
                    yield Button("刷新端口", id="btn-refresh")
                with VerticalScroll(id="device-stack"):
                    yield Label(
                        "[dim]请选择端口并连接设备[/dim]",
                        id="no-device-hint",
                    )

            with TabPane("预设 (Presets)", id="tab-presets"):
                with VerticalScroll(id="preset-container"):
                    pass

            with TabPane("高级配置 (Advanced)", id="tab-config"):
                with VerticalScroll(classes="config-section"):
                    yield Label("当前选中设备: -", id="config-target-label")

                    yield Label("运动阈值 (Threshold 0x02-0x3F)", classes="field-label")
                    yield Input(
                        placeholder="0x0A",
                        id="input-threshold",
                        validators=[
                            Regex(r"^0x[0-9A-Fa-f]{2}$", "Must be hex 0x02-0x3F")
                        ],
                    )
                    yield Label(EXPLANATIONS["threshold"], classes="field-explanation")

                    yield Label(
                        "尾随窗口 (Tail Window 1000-10000ms)", classes="field-label"
                    )
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
                    yield Label(EXPLANATIONS["tail"], classes="field-explanation")

                    yield Label(
                        "发射功率 (TX Power -40 to 4 dBm)", classes="field-label"
                    )
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
                    yield Label(EXPLANATIONS["tx"], classes="field-explanation")

                    with Horizontal(classes="button-row"):
                        yield Button(
                            "应用配置", id="btn-apply-config", variant="primary"
                        )
                        yield Button(
                            "保存到闪存", id="btn-save-flash", variant="warning"
                        )
                        yield Button("恢复默认", id="btn-defaults")
                        yield Button("重启设备", id="btn-reboot", variant="error")

            with TabPane("日志 (Log)", id="tab-log"):
                yield RichLog(id="log", wrap=True, highlight=False, markup=True)

        yield Label("Ready", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.load_presets()
        self.refresh_port_select()

    def load_presets(self) -> None:
        presets: Dict[str, Preset] = {}
        if self.preset_dir.exists():
            for path in sorted(self.preset_dir.glob("*.yaml")):
                try:
                    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                    name = data.get("name") or path.stem

                    meta = PRESET_META.get(name, {})

                    presets[name] = Preset(
                        name=name,
                        threshold=self._parse_threshold_value(
                            data.get("threshold_hex")
                        ),
                        tail_window=int(data.get("tail_window_ms", 3000)),
                        tx_power=int(data.get("tx_power_dbm", 4)),
                        label=meta.get("label", name),
                        description=meta.get("desc", ""),
                        scenario=meta.get("scenario", ""),
                        battery=meta.get("battery", ""),
                    )
                except Exception as e:
                    self.notify(
                        f"Error loading preset {path.name}: {e}", severity="error"
                    )

        self.presets = presets
        container = self.query_one("#preset-container")
        container.remove_children()
        for preset in presets.values():
            container.mount(PresetCard(preset, self.apply_preset))

    def rebuild_device_stack(self) -> None:
        """Rebuild the device card stack from current connected devices."""
        stack = self.query_one("#device-stack", VerticalScroll)
        stack.remove_children()

        if not self.clients:
            stack.mount(
                Label(
                    "[dim]未连接任何设备。请选择端口并连接。[/dim]",
                    id="no-device-hint",
                )
            )
            return

        for port in self.clients:
            state = self.device_states.get(port, DeviceState(port=port))
            card = DeviceCard(port, state, self.select_device, self.disconnect_device)
            stack.mount(card)
            if port == self.selected_port:
                card.add_class("selected")

    def select_device(self, port: str) -> None:
        """Select a device as the target for config/preset operations."""
        self.selected_port = port
        self.query_one("#config-target-label", Label).update(
            f"当前选中设备: {rich_escape(port)}"
        )
        self.rebuild_device_stack()
        if port in self.clients:
            self.send_command(port, "AT+INFO")

    def refresh_available_ports(self) -> None:
        """Check for disappeared ports, disconnect stale clients, update UI."""
        ports = list_ports.comports()
        current = {p.device for p in ports}
        for port in list(self.clients.keys()):
            if port not in current:
                self.disconnect_device(port)
        self.query_one("#status-bar", Label).update(
            f"检测到 {len(ports)} 个端口，已连接: {len(self.clients)}"
        )
        self.rebuild_device_stack()

    def refresh_port_select(self) -> None:
        """填充串口下拉列表，过滤掉已连接的端口。"""
        ports = list_ports.comports()
        select = self.query_one("#port-select", Select)
        options = [
            (f"{p.device} - {p.description}", p.device)
            for p in ports
            if p.device not in self.clients
        ]
        select.set_options(options)
        self.query_one("#status-bar", Label).update(
            f"检测到 {len(ports)} 个端口，已连接: {len(self.clients)}"
        )

    @on(Button.Pressed, "#btn-connect")
    def on_btn_connect(self) -> None:
        select = self.query_one("#port-select", Select)
        if select.value == Select.BLANK:
            self.notify("请先选择一个串口", severity="warning")
            return
        port = str(select.value)
        if port in self.clients:
            self.notify("该端口已连接", severity="warning")
            return
        self.run_worker(lambda p=port: self.connect_device(p), thread=True)

    def connect_device(self, port: str) -> None:
        if port in self.clients and self.clients[port].is_connected():
            return

        self.device_states.setdefault(port, DeviceState(port=port))

        client = SerialClient(
            port=port, on_line=functools.partial(self.on_serial_line, port)
        )
        try:
            client.connect()
            self.clients[port] = client
            self.device_states[port].connected = True
            self.log_message(port, f"[green]Connected to {rich_escape(port)}[/green]")
            self.notify(f"Connected to {rich_escape(port)}")

            if self.selected_port is None:
                self.selected_port = port
                self.call_from_thread(
                    self.query_one("#config-target-label", Label).update,
                    f"当前选中设备: {rich_escape(port)}",
                )

            self.send_command(port, "AT+INFO")

            if not self.has_switched_to_presets:
                self.call_from_thread(
                    setattr,
                    self.query_one(TabbedContent),
                    "active",
                    "tab-presets",
                )
                self.has_switched_to_presets = True

            self.call_from_thread(self.rebuild_device_stack)
            self.call_from_thread(self.refresh_port_select)
        except Exception as e:
            self.log_message(port, f"[red]Connection failed: {e}[/red]")
            self.notify(f"Failed to connect {rich_escape(port)}: {e}", severity="error")

    def disconnect_device(self, port: str) -> None:
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
            if self.selected_port:
                self.query_one("#config-target-label", Label).update(
                    f"当前选中设备: {rich_escape(self.selected_port)}"
                )
            else:
                self.query_one("#config-target-label", Label).update("当前选中设备: -")

        self.log_message(port, "[yellow]Disconnected[/yellow]")
        self.rebuild_device_stack()
        self.refresh_port_select()

    def send_command(self, port: str, command: str) -> None:
        if port in self.clients:
            self.log_message(port, f"[blue]>> {command}[/blue]")
            try:
                self.clients[port].send_command(command)
            except Exception as e:
                self.log_message(port, f"[red]Command error: {e}[/red]")

    def on_serial_line(self, port: str, line: str) -> None:
        self.call_from_thread(self.handle_serial_line, port, line)

    def handle_serial_line(self, port: str, line: str) -> None:
        self.log_message(port, line)

        state = self.device_states.get(port)
        if not state:
            return

        mac_match = re.search(r"\bMAC:\s*(.+)$", line)
        if mac_match:
            state.mac = mac_match.group(1).strip()
            self.rebuild_device_stack()

        name_match = re.search(r"\bName:\s*(.+)$", line)
        if name_match:
            state.name = name_match.group(1).strip()
            self.rebuild_device_stack()

        threshold_match = re.search(r"THRESHOLD=0x([0-9A-Fa-f]{2})", line)
        if threshold_match:
            state.threshold = int(threshold_match.group(1), 16)
            if self.selected_port == port:
                self.query_one(
                    "#input-threshold", Input
                ).value = f"0x{state.threshold:02X}"

        tail_match = re.search(r"TAILWINDOW=([0-9]+)", line)
        if tail_match:
            state.tail_window = int(tail_match.group(1))
            if self.selected_port == port:
                self.query_one("#input-tail", Input).value = str(state.tail_window)

        tx_match = re.search(r"TXPOWER=([-0-9]+)", line)
        if tx_match:
            state.tx_power = int(tx_match.group(1))
            if self.selected_port == port:
                self.query_one("#input-tx", Input).value = str(state.tx_power)

    def log_message(self, port: str, message: str) -> None:
        log = self.query_one("#log", RichLog)
        log.write(f"[{rich_escape(port)}] {message}")

    def apply_preset(self, preset: Preset, target: str) -> None:
        targets = []
        if target == "all":
            targets = list(self.clients.keys())
        elif target == "selected":
            if self.selected_port and self.selected_port in self.clients:
                targets = [self.selected_port]
            else:
                self.notify("No connected device selected", severity="warning")
                return

        if not targets:
            self.notify("No devices to apply preset to", severity="warning")
            return

        self.notify(f"Applying preset {preset.name} to {len(targets)} devices...")

        commands = [
            f"AT+THRESHOLD={preset.threshold:02X}",
            f"AT+TAILWINDOW={preset.tail_window}",
            f"AT+TXPOWER={preset.tx_power}",
            "AT+INFO",
        ]

        for port in targets:
            self.run_worker(self.send_commands_worker(port, commands), thread=True)

    def send_commands_worker(self, port: str, commands: List[str]) -> None:
        for cmd in commands:
            self.send_command(port, cmd)
            time.sleep(0.1)

    def action_show_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_refresh_ports(self) -> None:
        self.refresh_available_ports()
        self.notify("Ports refreshed")

    @on(Button.Pressed, "#btn-refresh")
    def on_btn_refresh(self) -> None:
        self.refresh_port_select()
        self.refresh_available_ports()

    @on(Button.Pressed, "#btn-apply-config")
    def on_btn_apply_config(self) -> None:
        if not self.selected_port or self.selected_port not in self.clients:
            self.notify("No connected device selected", severity="error")
            return

        try:
            t_val = self.query_one("#input-threshold", Input).value
            threshold = self._parse_threshold_value(t_val)

            tail = int(self.query_one("#input-tail", Input).value)
            tx = int(self.query_one("#input-tx", Input).value)

            commands = [
                f"AT+THRESHOLD={threshold:02X}",
                f"AT+TAILWINDOW={tail}",
                f"AT+TXPOWER={tx}",
                "AT+INFO",
            ]
            self.run_worker(
                self.send_commands_worker(self.selected_port, commands), thread=True
            )
            self.notify("Config applied")
        except Exception as e:
            self.notify(f"Invalid values: {e}", severity="error")

    @on(Button.Pressed, "#btn-save-flash")
    def on_btn_save_flash(self) -> None:
        if self.selected_port and self.selected_port in self.clients:
            self.send_command(self.selected_port, "AT+SAVE")
            self.notify("Saved to flash")

    @on(Button.Pressed, "#btn-defaults")
    def on_btn_defaults(self) -> None:
        if self.selected_port and self.selected_port in self.clients:
            self.send_command(self.selected_port, "AT+DEFAULT")
            self.notify("Restored defaults")

    @on(Button.Pressed, "#btn-reboot")
    def on_btn_reboot(self) -> None:
        if self.selected_port and self.selected_port in self.clients:
            self.send_command(self.selected_port, "AT+REBOOT")
            self.notify("Rebooting...")

    def _parse_threshold_value(self, raw: object) -> int:
        if raw is None:
            return 0x0A
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str):
            text = raw.strip().lower()
            if text.startswith("0x"):
                return int(text, 16)
            if re.fullmatch(r"[0-9a-f]+", text):
                return int(text, 16)
            try:
                return int(text)
            except ValueError:
                pass
        return 0x0A


if __name__ == "__main__":
    SensorConfigApp().run()
