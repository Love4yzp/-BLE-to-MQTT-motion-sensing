from __future__ import annotations

from rich.markup import escape as rich_escape
from textual import on
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Button, Label, Static

from i18n import t
from models import DeviceState


class DeviceCard(Static):
    class Selected(Message):
        def __init__(self, port: str) -> None:
            self.port = port
            super().__init__()

    class DisconnectRequested(Message):
        def __init__(self, port: str) -> None:
            self.port = port
            super().__init__()

    def __init__(self, port: str, state: DeviceState) -> None:
        super().__init__()
        self.port = port
        self.state = state

    def compose(self) -> ComposeResult:
        status = "[green]●[/green]" if self.state.connected else "[red]●[/red]"
        # 窄边栏布局：垂直堆叠，避免水平截断
        yield Label(f"{status} {rich_escape(self.port)}", classes="card-port")
        yield Label(f"  MAC: {self.state.mac}", classes="card-info-line")
        yield Label(
            f"  {t('devices.name_label')}: {self.state.name}",
            classes="card-info-line",
        )
        yield Button(
            t("devices.disconnect"),
            variant="error",
            classes="disconnect-btn",
        )

    def on_click(self, event) -> None:
        self.post_message(self.Selected(self.port))

    @on(Button.Pressed)
    def _on_disconnect_btn(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.DisconnectRequested(self.port))
