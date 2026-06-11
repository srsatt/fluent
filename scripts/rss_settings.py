"""User-machine settings for Fluent RSS media helpers."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fluent_paths import data_dir, ensure_data_dir

DEFAULT_STT_SETTINGS = {
    "enabled": False,
    "provider": "none",
}


def stt_settings_path() -> Path:
    return data_dir() / "rss-stt-settings.json"


def load_stt_settings() -> dict:
    path = stt_settings_path()
    if not path.exists():
        return dict(DEFAULT_STT_SETTINGS)
    with open(path, "r", encoding="utf-8") as f:
        settings = json.load(f)
    return settings if isinstance(settings, dict) else dict(DEFAULT_STT_SETTINGS)


def save_stt_settings(settings: dict) -> Path:
    target = ensure_data_dir() / "rss-stt-settings.json"
    tmp_path = target.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(tmp_path), str(target))
    return target
