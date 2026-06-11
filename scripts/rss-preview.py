#!/usr/bin/env python3
"""Preview media items from Fluent RSS study feeds."""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fluent_paths import force_utf8_io  # noqa: E402
from fluent_storage import load_documents  # noqa: E402

force_utf8_io()

MEDIA_EXTENSIONS = {
    ".mp3": "audio",
    ".m4a": "audio",
    ".aac": "audio",
    ".ogg": "audio",
    ".wav": "audio",
    ".flac": "audio",
    ".mp4": "video",
    ".m4v": "video",
    ".mov": "video",
    ".webm": "video",
}


def _tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1].lower()


def _first_text(element: ET.Element, names: tuple[str, ...]) -> str:
    wanted = set(names)
    for child in element.iter():
        if child is element:
            continue
        if _tag_name(child) in wanted and child.text:
            return child.text.strip()
    return ""


def _strip_html(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _infer_media_type(url: str, content_type: str = "") -> str:
    content_type = content_type.lower()
    if content_type.startswith("audio/"):
        return "audio"
    if content_type.startswith("video/"):
        return "video"
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    return MEDIA_EXTENSIONS.get(suffix, "")


def _media_candidates(item: ET.Element, base_url: str) -> list[dict]:
    candidates: list[dict] = []
    for child in item.iter():
        name = _tag_name(child)
        attrs = {k.rsplit("}", 1)[-1].lower(): v for k, v in child.attrib.items()}
        url = ""
        content_type = ""
        if name == "enclosure":
            url = attrs.get("url", "")
            content_type = attrs.get("type", "")
        elif name in ("content", "group") and ("url" in attrs or "type" in attrs):
            url = attrs.get("url", "")
            content_type = attrs.get("type", "")
        elif name == "link" and attrs.get("rel") == "enclosure":
            url = attrs.get("href", "")
            content_type = attrs.get("type", "")

        if not url:
            continue
        media_type = _infer_media_type(url, content_type)
        if not media_type:
            continue
        candidates.append({
            "url": urljoin(base_url, url),
            "content_type": content_type,
            "media_type": media_type,
            "length": attrs.get("length", ""),
        })
    return candidates


def _entries(root: ET.Element) -> list[ET.Element]:
    root_name = _tag_name(root)
    if root_name == "rss":
        channel = next((child for child in root if _tag_name(child) == "channel"), root)
        return [child for child in channel if _tag_name(child) == "item"]
    if root_name == "feed":
        return [child for child in root if _tag_name(child) == "entry"]
    return [child for child in root.iter() if _tag_name(child) in ("item", "entry")]


def _feed_title(root: ET.Element) -> str:
    root_name = _tag_name(root)
    if root_name == "rss":
        channel = next((child for child in root if _tag_name(child) == "channel"), root)
        return _first_text(channel, ("title",))
    return _first_text(root, ("title",))


def parse_feed(xml_bytes: bytes, source_url: str, configured_type: str = "mixed") -> dict:
    root = ET.fromstring(xml_bytes)
    feed_title = _feed_title(root)
    items: list[dict] = []
    for item in _entries(root):
        media = _media_candidates(item, source_url)
        if configured_type in ("audio", "video"):
            media = [candidate for candidate in media if candidate["media_type"] == configured_type]
        if not media:
            continue

        title = _first_text(item, ("title",)) or "Untitled"
        link = _first_text(item, ("link",))
        if not link:
            for child in item:
                if _tag_name(child) == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        summary = _first_text(item, ("description", "summary", "subtitle", "content"))
        published = _first_text(item, ("pubdate", "published", "updated"))
        guid = _first_text(item, ("guid", "id")) or media[0]["url"] or title
        items.append({
            "id": re.sub(r"[^a-zA-Z0-9_.-]+", "-", guid).strip("-")[:120] or "rss-item",
            "feed_title": feed_title,
            "source_url": source_url,
            "title": title,
            "link": urljoin(source_url, link) if link else "",
            "published": published,
            "summary": _strip_html(summary)[:500],
            "media_url": media[0]["url"],
            "media_type": media[0]["media_type"],
            "media_content_type": media[0]["content_type"],
            "media_length": media[0]["length"],
        })
    return {"title": feed_title, "source_url": source_url, "items": items}


def fetch_url(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "FluentRSS/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - user-provided feed URL.
        return response.read()


def configured_feeds() -> list[dict]:
    docs, missing, _backend = load_documents()
    if missing:
        raise FileNotFoundError(", ".join(missing))
    profile = docs.get("learner_profile", {})
    rss = profile.get("preferences", {}).get("rss", {})
    return rss.get("feeds", [])


def collect_previews(args: argparse.Namespace) -> dict:
    feed_specs: list[dict] = []
    for url in args.url:
        feed_specs.append({"url": url, "label": "", "content_type": "mixed"})
    for file_path in args.file:
        path = Path(file_path).resolve()
        feed_specs.append({"file": str(path), "url": path.as_uri(), "label": path.name, "content_type": "mixed"})
    if not feed_specs:
        feed_specs = configured_feeds()
    if not feed_specs:
        raise ValueError("no RSS feeds configured; run /fluent-rss setup first")

    feeds = []
    all_items = []
    for feed in feed_specs:
        source_url = feed["url"]
        content_type = feed.get("content_type", "mixed")
        xml_bytes = Path(feed["file"]).read_bytes() if feed.get("file") else fetch_url(source_url, args.timeout)
        parsed = parse_feed(xml_bytes, source_url, content_type)
        if feed.get("label"):
            parsed["label"] = feed["label"]
        parsed["items"] = parsed["items"][:args.limit]
        feeds.append(parsed)
        all_items.extend(parsed["items"])

    def sort_key(item: dict) -> str:
        published = item.get("published", "")
        try:
            return datetime.fromisoformat(published.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return published

    all_items.sort(key=sort_key, reverse=True)
    return {"feeds": feeds, "items": all_items[:args.limit]}


def print_text(result: dict) -> None:
    for index, item in enumerate(result["items"], start=1):
        date = f" ({item['published']})" if item.get("published") else ""
        print(f"{index}. [{item['media_type']}] {item['title']}{date}")
        print(f"   Feed: {item.get('feed_title') or item.get('source_url')}")
        if item.get("summary"):
            print(f"   Preview: {item['summary'][:220]}")
        print(f"   Media: {item['media_url']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", default=[], help="RSS/Atom feed URL; repeatable")
    parser.add_argument("--file", action="append", default=[], help="local RSS/Atom XML file; repeatable")
    parser.add_argument("--limit", type=int, default=8, help="maximum items to return")
    parser.add_argument("--timeout", type=int, default=20, help="network timeout in seconds")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args()

    try:
        result = collect_previews(args)
    except Exception as exc:  # noqa: BLE001 - CLI should report concise user-facing errors.
        print(f"[Fluent RSS] Error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
