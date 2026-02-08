from pathlib import Path
from typing import Any

import yaml

_strings: dict[str, Any] = {}
_locale: str = "zh"
_locale_dir = Path(__file__).resolve().parent / "locales"


def set_locale(locale: str) -> None:
    global _strings, _locale
    _locale = locale
    path = _locale_dir / f"{locale}.yaml"
    _strings = yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def get_locale() -> str:
    return _locale


def t(key: str, **kwargs: Any) -> str:
    parts = key.split(".")
    val: Any = _strings
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part, None)
        else:
            return key
    if val is None:
        return key
    if isinstance(val, str) and kwargs:
        return val.format(**kwargs)
    return str(val) if val is not None else key


set_locale("zh")
