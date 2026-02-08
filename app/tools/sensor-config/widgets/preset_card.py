from __future__ import annotations

from typing import Literal

from textual import on
from textual.app import ComposeResult
from textual.containers import Grid, Horizontal, Vertical
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
        with Vertical(classes="preset-card-inner"):
            yield Label(
                f"[bold]{self.preset.label or self.preset.name}[/bold]",
                classes="preset-title",
            )
            if self.preset.description:
                yield Label(
                    f"[dim]{self.preset.description}[/dim]",
                    classes="preset-desc",
                )

            with Grid(classes="preset-stats"):
                yield Label(
                    f"{t('preset_card.threshold')}: 0x{self.preset.threshold:02X}"
                )
                yield Label(
                    f"{t('preset_card.tail_window')}: {self.preset.tail_window}ms"
                )
                yield Label(f"{t('preset_card.tx_power')}: {self.preset.tx_power}dBm")
                if self.preset.battery:
                    yield Label(f"{t('preset_card.battery')}: {self.preset.battery}")
                if self.preset.scenario:
                    yield Label(f"{t('preset_card.scenario')}: {self.preset.scenario}")

            with Horizontal(classes="preset-actions"):
                yield Button(
                    t("preset_card.apply_selected"),
                    variant="primary",
                    classes="preset-btn apply-selected",
                )
                yield Button(
                    t("preset_card.apply_all"),
                    variant="warning",
                    classes="preset-btn apply-all",
                )

    @on(Button.Pressed)
    def _on_button_pressed(self, event: Button.Pressed) -> None:
        if "apply-selected" in event.button.classes:
            self.post_message(self.Applied(self.preset, "selected"))
        elif "apply-all" in event.button.classes:
            self.post_message(self.Applied(self.preset, "all"))
