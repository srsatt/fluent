#!/usr/bin/env python3
"""
Export or push Fluent spaced-repetition items to Anki.

Default mode is a TSV export that works without Anki add-ons. The optional push
mode uses AnkiConnect on http://127.0.0.1:8765.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fluent_paths import data_dir, force_utf8_io  # noqa: E402

force_utf8_io()

DEFAULT_TYPES = ("vocabulary", "grammar_rule", "error_pattern")
DEFAULT_DECK = "Fluent"
DEFAULT_MODEL = "Fluent Basic"
DEFAULT_ENDPOINT = "http://127.0.0.1:8765"


def load_items(source_dir: Path, include_types: set[str], limit: int | None) -> list[dict]:
    sr_path = source_dir / "spaced-repetition.json"
    if not sr_path.exists():
        raise SystemExit(f"Missing spaced-repetition store: {sr_path}")
    with open(sr_path, "r", encoding="utf-8") as f:
        sr = json.load(f)

    rows = []
    for item_id, item in sr.get("items", {}).items():
        item_type = item.get("type", "")
        if item_type not in include_types:
            continue
        rows.append({
            "id": item_id,
            "type": item_type,
            "front": item.get("content", ""),
            "back": item.get("answer", ""),
            "context": item.get("category", ""),
            "difficulty": item.get("difficulty", ""),
            "priority": item.get("priority", "medium"),
            "due_date": item.get("due_date", ""),
            "mastery_level": item.get("mastery_level", 0),
        })

    rows.sort(key=lambda r: (r["due_date"], r["priority"], r["id"]))
    return rows[:limit] if limit else rows


def tags_for(row: dict, base_tag: str) -> str:
    tags = [base_tag, f"fluent_type::{row['type']}"]
    if row.get("difficulty"):
        tags.append(f"cefr::{row['difficulty']}")
    if row.get("priority"):
        tags.append(f"priority::{row['priority']}")
    return " ".join(tags)


def export_tsv(rows: list[dict], output: Path, deck: str, base_tag: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8", newline="") as f:
        f.write("#separator:tab\n")
        f.write("#html:true\n")
        f.write("#columns:Front\tBack\tContext\tFluentId\tTags\n")
        f.write(f"#deck:{deck}\n")
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for row in rows:
            writer.writerow([
                row["front"],
                row["back"],
                row["context"],
                row["id"],
                tags_for(row, base_tag),
            ])
    print(f"[Fluent] Exported {len(rows)} Anki rows to {output}")


def anki_request(endpoint: str, action: str, params: dict | None = None):
    payload = json.dumps({"action": action, "version": 6, "params": params or {}}).encode("utf-8")
    req = Request(endpoint, data=payload, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as response:
        result = json.loads(response.read().decode("utf-8"))
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result.get("result")


def ensure_deck(endpoint: str, deck: str) -> None:
    decks = anki_request(endpoint, "deckNames")
    if deck not in decks:
        anki_request(endpoint, "createDeck", {"deck": deck})


def ensure_model(endpoint: str, model: str) -> None:
    models = anki_request(endpoint, "modelNames")
    if model in models:
        return
    anki_request(endpoint, "createModel", {
        "modelName": model,
        "inOrderFields": ["Front", "Back", "Context", "FluentId"],
        "css": ".card { font-family: system-ui, sans-serif; font-size: 22px; text-align: left; }",
        "cardTemplates": [{
            "Name": "Card 1",
            "Front": "{{Front}}<br><br><small>{{Context}}</small>",
            "Back": "{{FrontSide}}<hr id=answer>{{Back}}<br><br><small>{{FluentId}}</small>",
        }],
    })


def find_existing_note(endpoint: str, deck: str, fluent_id: str):
    query = f'deck:"{deck}" FluentId:{fluent_id}'
    notes = anki_request(endpoint, "findNotes", {"query": query})
    return notes[0] if notes else None


def push_rows(rows: list[dict], endpoint: str, deck: str, model: str, base_tag: str, dry_run: bool) -> None:
    if dry_run:
        print(json.dumps({"would_push": len(rows), "deck": deck, "model": model}, indent=2))
        return

    try:
        anki_request(endpoint, "version")
    except URLError as e:
        raise SystemExit(f"Cannot reach AnkiConnect at {endpoint}: {e}") from e

    ensure_deck(endpoint, deck)
    ensure_model(endpoint, model)

    added = 0
    updated = 0
    for row in rows:
        fields = {
            "Front": row["front"],
            "Back": row["back"],
            "Context": row["context"],
            "FluentId": row["id"],
        }
        note_id = find_existing_note(endpoint, deck, row["id"])
        if note_id:
            anki_request(endpoint, "updateNoteFields", {"note": {"id": note_id, "fields": fields}})
            anki_request(endpoint, "addTags", {"notes": [note_id], "tags": tags_for(row, base_tag)})
            updated += 1
        else:
            anki_request(endpoint, "addNote", {
                "note": {
                    "deckName": deck,
                    "modelName": model,
                    "fields": fields,
                    "tags": tags_for(row, base_tag).split(),
                    "options": {"allowDuplicate": False, "duplicateScope": "deck"},
                }
            })
            added += 1

    print(f"[Fluent] Anki push complete: {added} added, {updated} updated")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Check AnkiConnect availability")
    status.add_argument("--endpoint", default=DEFAULT_ENDPOINT)

    for name in ("export-tsv", "push"):
        p = sub.add_parser(name)
        p.add_argument("--data-dir", type=Path, default=None)
        p.add_argument("--include-types", default=",".join(DEFAULT_TYPES))
        p.add_argument("--limit", type=int, default=None)
        p.add_argument("--deck", default=DEFAULT_DECK)
        p.add_argument("--tag", default="fluent")
        if name == "export-tsv":
            p.add_argument("--output", type=Path, required=True)
        else:
            p.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
            p.add_argument("--model", default=DEFAULT_MODEL)
            p.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.command == "status":
        try:
            version = anki_request(args.endpoint, "version")
        except URLError as e:
            raise SystemExit(f"Cannot reach AnkiConnect at {args.endpoint}: {e}") from e
        print(f"[Fluent] AnkiConnect available, version {version}")
        return 0

    source = args.data_dir.resolve() if args.data_dir else data_dir()
    include_types = {t.strip() for t in args.include_types.split(",") if t.strip()}
    rows = load_items(source, include_types, args.limit)

    if args.command == "export-tsv":
        export_tsv(rows, args.output.resolve(), args.deck, args.tag)
    elif args.command == "push":
        push_rows(rows, args.endpoint, args.deck, args.model, args.tag, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
