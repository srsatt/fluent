"""
Personalization helpers for learner-profile facts.

Facts are stored inside learner_profile so the existing SQL/JSON document
boundary remains the source of truth. MCP tools and session updates should use
these helpers instead of editing the structure ad hoc.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

FACT_CATEGORIES = {
    "interest",
    "hobby",
    "lifestyle",
    "goal_context",
    "conversation_preference",
    "preferred_context",
    "avoid_topic",
    "constraint",
    "background",
    "other",
}

PROFILE_BUCKETS = {
    "interest": "interests",
    "hobby": "hobbies",
    "lifestyle": "lifestyle",
    "goal_context": "goals_context",
    "conversation_preference": "conversation_preferences",
    "preferred_context": "preferred_contexts",
    "avoid_topic": "avoid_topics",
    "constraint": "constraints",
    "background": "background",
    "other": "other",
}

DEFAULT_PROFILE = {
    "interests": [],
    "hobbies": [],
    "lifestyle": [],
    "preferred_contexts": [],
    "conversation_preferences": [],
    "avoid_topics": [],
    "goals_context": [],
    "constraints": [],
    "background": [],
    "other": [],
}


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def ensure_personalization(profile: dict[str, Any]) -> dict[str, Any]:
    personalization = profile.setdefault("personalization", {})
    personalization.setdefault("facts", [])
    existing_profile = personalization.setdefault("profile", {})
    for key, value in DEFAULT_PROFILE.items():
        existing_profile.setdefault(key, list(value))
    personalization.setdefault("last_internalized_at", None)
    return personalization


def _slug(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
    return slug[:40] or "fact"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).casefold()


def _bounded_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 0.8
    return round(max(0.0, min(1.0, parsed)), 2)


def _category(value: Any) -> str:
    if not isinstance(value, str):
        return "other"
    category = value.strip().lower().replace("-", "_").replace(" ", "_")
    return category if category in FACT_CATEGORIES else "other"


def _next_fact_id(facts: list[dict[str, Any]], text: str, created_at: str) -> str:
    base = f"profile_fact_{created_at.replace('-', '')}_{_slug(text)}"
    existing = {fact.get("id") for fact in facts}
    if base not in existing:
        return base
    counter = 2
    while f"{base}_{counter}" in existing:
        counter += 1
    return f"{base}_{counter}"


def add_profile_fact(
    profile: dict[str, Any],
    fact: dict[str, Any],
    *,
    default_source: str = "manual",
    created_at: str | None = None,
) -> dict[str, Any]:
    text = str(fact.get("text") or fact.get("fact") or "").strip()
    if not text:
        raise ValueError("profile fact text is required")

    created_date = created_at or str(fact.get("created_at") or today())
    personalization = ensure_personalization(profile)
    facts = personalization["facts"]
    normalized = _normalize_text(text)

    for existing in facts:
        if _normalize_text(str(existing.get("text", ""))) == normalized and existing.get("status", "active") == "active":
            existing["last_seen"] = created_date
            existing["confidence"] = max(
                _bounded_confidence(existing.get("confidence", 0.8)),
                _bounded_confidence(fact.get("confidence", existing.get("confidence", 0.8))),
            )
            if fact.get("source"):
                existing["source"] = fact["source"]
            return existing

    stored = {
        "id": str(fact.get("id") or _next_fact_id(facts, text, created_date)),
        "text": text,
        "category": _category(fact.get("category")),
        "confidence": _bounded_confidence(fact.get("confidence", 0.8)),
        "source": str(fact.get("source") or default_source),
        "created_at": created_date,
        "last_seen": created_date,
        "status": str(fact.get("status") or "active"),
        "sensitivity": str(fact.get("sensitivity") or "normal"),
    }
    if fact.get("evidence"):
        stored["evidence"] = str(fact["evidence"])
    facts.append(stored)
    return stored


def active_facts(profile: dict[str, Any], fact_ids: list[str] | None = None) -> list[dict[str, Any]]:
    personalization = ensure_personalization(profile)
    requested = set(fact_ids or [])
    facts = [
        fact for fact in personalization["facts"]
        if fact.get("status", "active") == "active" and (not requested or fact.get("id") in requested)
    ]
    return sorted(
        facts,
        key=lambda fact: (
            PROFILE_BUCKETS.get(fact.get("category", "other"), "other"),
            -_bounded_confidence(fact.get("confidence", 0.8)),
            fact.get("text", ""),
        ),
    )


def build_profile_from_facts(facts: list[dict[str, Any]]) -> dict[str, list[str]]:
    summary = {key: list(value) for key, value in DEFAULT_PROFILE.items()}
    seen: dict[str, set[str]] = {key: set() for key in summary}
    for fact in facts:
        bucket = PROFILE_BUCKETS.get(fact.get("category", "other"), "other")
        text = str(fact.get("text", "")).strip()
        normalized = _normalize_text(text)
        if not text or normalized in seen[bucket]:
            continue
        summary[bucket].append(text)
        seen[bucket].add(normalized)
    return summary


def internalize_profile(
    profile: dict[str, Any],
    *,
    synthesized_profile: dict[str, Any] | None = None,
    fact_ids: list[str] | None = None,
    internalized_at: str | None = None,
) -> dict[str, Any]:
    personalization = ensure_personalization(profile)
    if synthesized_profile is None:
        new_profile = build_profile_from_facts(active_facts(profile, fact_ids))
    else:
        new_profile = {key: list(value) for key, value in DEFAULT_PROFILE.items()}
        for key, value in synthesized_profile.items():
            if key in new_profile and isinstance(value, list):
                new_profile[key] = [str(item).strip() for item in value if str(item).strip()]
    personalization["profile"] = new_profile
    personalization["last_internalized_at"] = internalized_at or now_iso()
    return personalization
