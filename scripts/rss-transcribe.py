#!/usr/bin/env python3
"""Download media and create subtitles with configured whisper.cpp."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fluent_paths import data_dir, ensure_data_dir, force_utf8_io  # noqa: E402
from fluent_storage import load_documents  # noqa: E402

force_utf8_io()


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "rss-media"


def _config() -> dict:
    docs, missing, _backend = load_documents()
    if missing:
        return {}
    profile = docs.get("learner_profile", {})
    return profile.get("preferences", {}).get("rss", {}).get("transcription", {})


def _download(url: str, target_dir: Path, output_id: str) -> Path:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix or ".media"
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    target = target_dir / f"{_slug(output_id)}-{digest}{suffix}"
    if target.exists():
        return target

    request = urllib.request.Request(url, headers={"User-Agent": "FluentRSS/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 - learner-configured media URL.
        target.write_bytes(response.read())
    return target


def _convert_if_needed(input_path: Path, ffmpeg: str, output_dir: Path) -> Path:
    if input_path.suffix.lower() == ".wav":
        return input_path
    if ffmpeg == "":
        return input_path
    ffmpeg_bin = ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return input_path
    target = output_dir / f"{input_path.stem}.wav"
    if target.exists():
        return target
    subprocess.run(
        [ffmpeg_bin, "-y", "-i", str(input_path), "-ar", "16000", "-ac", "1", str(target)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return target


def _build_command(args: argparse.Namespace, audio_path: Path, output_base: Path) -> list[str]:
    config = _config()
    binary = args.binary or config.get("binary", "")
    model = args.model or config.get("model", "")
    language = args.language or config.get("language", "auto")
    if not binary:
        raise ValueError("missing whisper.cpp binary; run /fluent-rss setup or pass --binary")
    if not model:
        raise ValueError("missing whisper.cpp model; run /fluent-rss setup or pass --model")

    command = [
        binary,
        "-m", model,
        "-f", str(audio_path),
        "-osrt",
        "-otxt",
        "-of", str(output_base),
    ]
    if language and language != "auto":
        command.extend(["-l", language])
    return command


def transcribe(args: argparse.Namespace) -> dict:
    config = _config()
    media_dir = ensure_data_dir() / "rss-media"
    transcript_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else data_dir() / "rss-transcripts"
    media_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)

    source = args.media_url or args.input
    if not source:
        raise ValueError("pass --media-url or --input")

    output_id = args.output_id or Path(urlparse(source).path).stem or "rss-media"
    if re.match(r"^https?://", source):
        media_path = _download(source, media_dir, output_id)
    else:
        media_path = Path(source).expanduser().resolve()
        if not media_path.exists():
            raise FileNotFoundError(media_path)

    ffmpeg = args.ffmpeg if args.ffmpeg is not None else config.get("ffmpeg", "ffmpeg")
    audio_path = _convert_if_needed(media_path, ffmpeg, media_dir)
    output_base = transcript_dir / _slug(output_id)
    command = _build_command(args, audio_path, output_base)

    result = {
        "media_path": str(media_path),
        "audio_path": str(audio_path),
        "output_base": str(output_base),
        "srt_path": str(output_base.with_suffix(".srt")),
        "txt_path": str(output_base.with_suffix(".txt")),
        "command": command,
    }
    if args.dry_run:
        return result

    proc = subprocess.run(command, capture_output=True, text=True)
    result["returncode"] = proc.returncode
    result["stdout"] = proc.stdout[-4000:]
    result["stderr"] = proc.stderr[-4000:]
    if proc.returncode != 0:
        raise RuntimeError(f"whisper.cpp failed with exit code {proc.returncode}: {proc.stderr[-1000:]}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media-url", help="media URL from RSS item")
    parser.add_argument("--input", help="local media/audio path or URL")
    parser.add_argument("--output-id", help="stable transcript id")
    parser.add_argument("--output-dir", help="transcript output directory")
    parser.add_argument("--binary", help="whisper.cpp binary path")
    parser.add_argument("--model", help="whisper.cpp model path")
    parser.add_argument("--language", help="target language code, or auto")
    parser.add_argument("--ffmpeg", help="ffmpeg path; pass an empty value to skip conversion")
    parser.add_argument("--dry-run", action="store_true", help="print planned command without running")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args()

    try:
        result = transcribe(args)
    except Exception as exc:  # noqa: BLE001 - CLI should report concise user-facing errors.
        print(f"[Fluent RSS] Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print(f"SRT: {result['srt_path']}")
        print(f"TXT: {result['txt_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
