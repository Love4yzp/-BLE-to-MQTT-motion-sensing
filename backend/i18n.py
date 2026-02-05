"""
简单的 JSON 文件 i18n 国际化模块
支持中英文切换
"""

import json
from pathlib import Path
from typing import Any

# 支持的语言
SUPPORTED_LANGUAGES = ["zh", "en"]
DEFAULT_LANGUAGE = "zh"

# 翻译缓存
_translations: dict[str, dict] = {}

# locales 目录
LOCALES_DIR = Path(__file__).parent / "locales"


def load_translations() -> None:
    """加载所有翻译文件到内存"""
    global _translations
    _translations = {}

    for lang in SUPPORTED_LANGUAGES:
        file_path = LOCALES_DIR / f"{lang}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                _translations[lang] = json.load(f)
            print(f"[i18n] 已加载 {lang}.json")
        else:
            print(f"[i18n] 警告: {lang}.json 不存在")
            _translations[lang] = {}


def get_translations(lang: str) -> dict:
    """获取指定语言的完整翻译字典"""
    if not _translations:
        load_translations()

    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    return _translations.get(lang, {})


def t(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """
    获取翻译文本
    key 格式: "section.subsection.key", 如 "product.title"
    """
    if not _translations:
        load_translations()

    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    translations = _translations.get(lang, {})

    # 按点分割 key 并逐层获取
    keys = key.split(".")
    value: Any = translations
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return key  # 未找到，返回 key 本身

    return value if isinstance(value, str) else key


def get_language_list() -> list[dict]:
    """获取支持的语言列表"""
    return [
        {"code": "zh", "name": "中文"},
        {"code": "en", "name": "English"},
    ]
