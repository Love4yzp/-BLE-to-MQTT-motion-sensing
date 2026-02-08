from __future__ import annotations

from rich.markup import escape as rich_escape
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
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
        with Horizontal(classes="card-header"):
            status = "[green]●[/green]" if self.state.connected else "[red]●[/red]"
            yield Label(f"{status}  {rich_escape(self.port)}", classes="card-port")
            yield Button(
                t("devices.disconnect"),
                variant="error",
                classes="disconnect-btn",
            )
        with Horizontal(classes="card-info"):
            yield Label(
                f"{t('devices.mac_label')}: {self.state.mac}  |  "
                f"{t('devices.name_label')}: {self.state.name}"
            )

    def on_click(self, event) -> None:
        self.post_message(self.Selected(self.port))

    @on(Button.Pressed)
    def _on_disconnect_btn(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.DisconnectRequested(self.port))
