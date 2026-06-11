#!/usr/bin/env python3
"""Store Fluent RSS feeds and user-machine STT settings."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fluent_paths import ensure_backups_dir, force_utf8_io  # noqa: E402
from fluent_storage import load_documents, save_documents, storage_files_for_backup  # noqa: E402
from rss_settings import load_stt_settings, save_stt_settings, stt_settings_path  # noqa: E402

force_utf8_io()


def _valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80] or "feed"


def _normalize_feeds(raw_feeds: list[dict]) -> list[dict]:
    if not isinstance(raw_feeds, list):
        raise ValueError("'feeds' must be a list")

    feeds: list[dict] = []
    for index, feed in enumerate(raw_feeds, start=1):
        if not isinstance(feed, dict):
            raise ValueError(f"feed #{index} must be an object")
        url = str(feed.get("url", "")).strip()
        if not _valid_url(url):
            raise ValueError(f"feed #{index} has an invalid http(s) URL")
        content_type = str(feed.get("content_type", "mixed")).strip().lower()
        if content_type not in ("audio", "video", "mixed"):
            raise ValueError("content_type must be audio, video, or mixed")
        label = str(feed.get("label", "")).strip()
        feeds.append({
            "id": str(feed.get("id") or _slug(label or url)),
            "url": url,
            "label": label,
            "content_type": content_type,
        })
    return feeds


def _normalize_transcription(raw: dict | None) -> dict:
    if raw is None:
        return load_stt_settings()
    if not isinstance(raw, dict):
        raise ValueError("'transcription' must be an object")

    enabled = bool(raw.get("enabled", False))
    provider = str(raw.get("provider", "whisper.cpp" if enabled else "none")).strip()
    if enabled and provider != "whisper.cpp":
        raise ValueError("only whisper.cpp transcription is currently supported")

    result = {
        "enabled": enabled,
        "provider": provider,
        "binary": str(raw.get("binary", "")).strip(),
        "model": str(raw.get("model", "")).strip(),
        "language": str(raw.get("language", "auto")).strip() or "auto",
        "ffmpeg": str(raw.get("ffmpeg", "ffmpeg")).strip() or "ffmpeg",
    }
    if enabled and (not result["binary"] or not result["model"]):
        raise ValueError("enabled whisper.cpp transcription requires binary and model")
    return result


def _backup(tag: str) -> None:
    backup_dir = ensure_backups_dir() / tag
    backup_dir.mkdir(parents=True, exist_ok=True)
    for path in storage_files_for_backup():
        shutil.copy2(path, backup_dir / path.name)


def load_payload() -> dict:
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON input: {exc}") from exc


def current_config() -> dict:
    docs, missing, backend = load_documents()
    if missing:
        raise FileNotFoundError(", ".join(missing))
    profile = docs.get("learner_profile", {})
    prefs = profile.get("preferences", {})
    rss = prefs.get("rss", {"feeds": []})
    return {
        "backend": backend,
        "rss": {
            "feeds": rss.get("feeds", []),
            "updated_at": rss.get("updated_at"),
        },
        "transcription": load_stt_settings(),
        "transcription_path": str(stt_settings_path()),
    }


def save_config(payload: dict) -> dict:
    docs, missing, backend = load_documents()
    if missing:
        raise FileNotFoundError(", ".join(missing))

    feeds = _normalize_feeds(payload.get("feeds", []))
    transcription = _normalize_transcription(payload.get("transcription"))
    rss_config = {
        "feeds": feeds,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }

    profile = docs.setdefault("learner_profile", {})
    profile.setdefault("preferences", {})["rss"] = rss_config
    _backup(f"pre-rss-setup-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    saved_backend = save_documents(docs)
    stt_path = save_stt_settings(transcription)
    return {
        "backend": saved_backend or backend,
        "rss": rss_config,
        "transcription": transcription,
        "transcription_path": str(stt_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show", action="store_true", help="print current RSS preferences")
    args = parser.parse_args()

    try:
        result = current_config() if args.show else save_config(load_payload())
    except Exception as exc:  # noqa: BLE001 - CLI should report concise user-facing errors.
        print(f"[Fluent RSS] Error: {exc}", file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
