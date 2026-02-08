from __future__ import annotations

from typing import Literal

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Label, Static

from i18n import t
from models import Preset


class PresetCard(Static):
    class Applied(Message):
        def __init__(self, preset: Preset, target: Literal["selected", "all"]) -> None:
            self.preset = preset
            self.target = target
            super().__init__()

    def __init__(self, preset: Preset) -> None:
        super().__init__()
        self.preset = preset

    def compose(self) -> ComposeResult:
        with Horizontal(classes="preset-row"):
            yield Label(
                f"[bold]{self.preset.label or self.preset.name}[/bold]",
                classes="preset-label",
            )
            battery = self.preset.battery or "-"
            yield Label(battery, classes="preset-battery")
            yield Button(
                t("preset_card.apply_selected_short"),
                variant="primary",
                classes="preset-btn apply-selected",
            )
            yield Button(
                t("preset_card.apply_all_short"),
                variant="warning",
                classes="preset-btn apply-all",
            )

    @on(Button.Pressed)
    def _on_button_pressed(self, event: Button.Pressed) -> None:
        if "apply-selected" in event.button.classes:
            self.post_message(self.Applied(self.preset, "selected"))
        elif "apply-all" in event.button.classes:
            self.post_message(self.Applied(self.preset, "all"))
