"""数据模型与 AT 协议解析器。

包含 Preset、DeviceState 数据类，以及串口 AT 响应行的解析逻辑。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Preset:
    """传感器预设配置。"""

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
    """单个已连接设备的运行状态。"""

    port: str
    connected: bool = False
    mac: str = "-"
    name: str = "-"
    threshold: Optional[int] = None
    tail_window: Optional[int] = None
    tx_power: Optional[int] = None


@dataclass
class ATUpdate:
    """从单行 AT 响应中解析出的字段更新。

    仅被成功匹配的字段会被设置（非 None）。
    """

    mac: Optional[str] = None
    name: Optional[str] = None
    threshold: Optional[int] = None
    tail_window: Optional[int] = None
    tx_power: Optional[int] = None


# 预编译正则表达式，避免每次解析时重复编译
_RE_MAC = re.compile(r"\bMAC:\s*(.+)$")
_RE_NAME = re.compile(r"\bName:\s*(.+)$")
_RE_THRESHOLD = re.compile(r"THRESHOLD=0x([0-9A-Fa-f]{2})")
_RE_TAILWINDOW = re.compile(r"TAILWINDOW=([0-9]+)")
_RE_TXPOWER = re.compile(r"TXPOWER=([-0-9]+)")


def parse_at_line(line: str) -> ATUpdate:
    """解析一行 AT 响应，提取设备信息字段。

    每行最多匹配一个字段。返回 ATUpdate，其中仅匹配到的字段非 None。
    """
    update = ATUpdate()

    m = _RE_MAC.search(line)
    if m:
        update.mac = m.group(1).strip()
        return update

    m = _RE_NAME.search(line)
    if m:
        update.name = m.group(1).strip()
        return update

    m = _RE_THRESHOLD.search(line)
    if m:
        update.threshold = int(m.group(1), 16)
        return update

    m = _RE_TAILWINDOW.search(line)
    if m:
        update.tail_window = int(m.group(1))
        return update

    m = _RE_TXPOWER.search(line)
    if m:
        update.tx_power = int(m.group(1))
        return update

    return update


def apply_at_update(state: DeviceState, update: ATUpdate) -> bool:
    """将 ATUpdate 中非 None 的字段应用到 DeviceState。

    返回 True 表示状态有变更。
    """
    changed = False
    if update.mac is not None and state.mac != update.mac:
        state.mac = update.mac
        changed = True
    if update.name is not None and state.name != update.name:
        state.name = update.name
        changed = True
    if update.threshold is not None and state.threshold != update.threshold:
        state.threshold = update.threshold
        changed = True
    if update.tail_window is not None and state.tail_window != update.tail_window:
        state.tail_window = update.tail_window
        changed = True
    if update.tx_power is not None and state.tx_power != update.tx_power:
        state.tx_power = update.tx_power
        changed = True
    return changed


def parse_threshold_value(raw: object) -> int:
    """解析灵敏度阈值，支持多种输入格式。

    支持: None -> 0x0A, int -> 原值, "0x0A" -> 10, "0a" -> 10, "10" -> 16(hex),
    无法解析时返回默认值 0x0A。
    """
    if raw is None:
        return 0x0A
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        text = raw.strip().lower()
        if text.startswith("0x"):
            try:
                return int(text, 16)
            except ValueError:
                return 0x0A
        if re.fullmatch(r"[0-9a-f]+", text):
            return int(text, 16)
        try:
            return int(text)
        except ValueError:
            pass
    return 0x0A
