from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, Select, Static

from i18n import t
from models import DeviceState
from widgets.device_card import DeviceCard


class DeviceSidebar(Static):
    class ConnectRequested(Message):
        def __init__(self, port: Optional[str]) -> None:
            self.port = port
            super().__init__()

    class RefreshRequested(Message):
        pass

    devices: reactive[Dict[str, DeviceState]] = reactive({}, recompose=True)
    selected_port: reactive[Optional[str]] = reactive(None, recompose=True)
    port_options: reactive[Sequence[Tuple[str, str]]] = reactive((), recompose=False)

    def compose(self) -> ComposeResult:
        with Vertical(id="sidebar-controls"):
            yield Select(
                list(self.port_options),
                id="port-select",
                prompt=t("devices.select_prompt"),
            )
            with Horizontal(id="sidebar-buttons"):
                yield Button(t("devices.connect"), id="btn-connect", variant="success")
                yield Button(t("devices.refresh"), id="btn-refresh")

            with VerticalScroll(id="device-stack"):
                if not self.devices:
                    yield Label(
                        f"[dim]{t('devices.hint_no_device')}[/dim]",
                        id="no-device-hint",
                    )
                else:
                    for port, state in self.devices.items():
                        card = DeviceCard(port, state)
                        if port == self.selected_port:
                            card.add_class("selected")
                        yield card

    def watch_port_options(self, options: Sequence[Tuple[str, str]]) -> None:
        try:
            select = self.query_one("#port-select", Select)
            select.set_options(list(options))
        except Exception:
            pass

    @on(Button.Pressed, "#btn-connect")
    def _on_connect(self, event: Button.Pressed) -> None:
        event.stop()
        select = self.query_one("#port-select", Select)
        port = None if select.value == Select.BLANK else str(select.value)
        self.post_message(self.ConnectRequested(port))

    @on(Button.Pressed, "#btn-refresh")
    def _on_refresh(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.RefreshRequested())
