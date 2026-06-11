---
name: fluent-vocab
description: Run an interactive vocabulary drill session with flashcard-style prompts, contextual production, spaced repetition, and per-answer feedback. Triggered only when the learner types /fluent-vocab. Reads learner stores to pick words, presents one word at a time, scores each answer, and persists one session payload at the end.
allowed-tools: Read, Write, Bash
disable-model-invocation: true
---

# Vocabulary Drill Session

## Overview

Flashcard-style vocabulary practice using spaced repetition. One word at a time, immediate feedback, DB update at the end. Interleaves three modes (recognition, production, cloze) to force active recall rather than passive re-reading.

## When to Use

Trigger this skill only when the learner types `/fluent-vocab`. The skill is gated with `disable-model-invocation: true` — a false-positive auto-trigger would launch a 15-min interactive session and mutate learner state.

Skip this skill if no vocabulary items are due and no new words are queued — offer `/fluent-review` or `/fluent-learn` instead.

## Instructions

### 1. Load vocabulary data

```bash
python3 scripts/read-db.py
```

Prefer MCP tool `fluent_read_state`; use the command above only as fallback.

If the helper is unavailable, resolve `<data_dir>` via `fluent_paths.data_dir()` then read:

- `<data_dir>/spaced-repetition.json`
- `<data_dir>/mistakes-db.json`
- `<data_dir>/mastery-db.json`
- `<data_dir>/learner-profile.json` (for target_language, name, level)

If any are missing, direct the learner to `/fluent-setup` and stop.

### 2. Select words

Priority order:

1. Items in `spaced-repetition.review_queue.today` with `item_type == "vocabulary"`.
2. Words from `mistakes-db.json` where `category == "vocabulary"` and `mastery_level <= 2`.
3. New high-frequency or goal-relevant words matching `learner-profile.focus_areas`.

Limit: `spaced-repetition.daily_limits.review_items_per_day` (default 20).

### 3. Present one word at a time

Rotate the modes so the session builds both recognition and usable production.

**Recognition** (target_language → native):

```markdown
## Word {N}/{total}

**{target_language}:** {word}

**Context:** {example_sentence}

**What does it mean in {native_language}?**

**Type your answer:**
```

**Production** (native → target_language):

```markdown
## Word {N}/{total}

**{native_language}:** {word}

**Use it in a sentence (optional).**

**How do you say this in {target_language}?**

**Type your answer:**
```

**Cloze** (fill in the blank):

```markdown
## Word {N}/{total}

**Complete the sentence:**

{target_language sentence with _____ where the word goes}

**Type the missing word:**
```

**Personalized use** (adult task):

```markdown
## Word {N}/{total}

Use **{word}** in a sentence about {learner_goal_or_interest}.

**Type your sentence:**
```

### 4. Feedback after each answer

Use the `fluent-feedback-formatter` skill's template. Score out of 10, tag severity.

Track the answer for the end-of-session DB update:

- Add to `review_results[]` with quality from MCP tool `fluent_score_to_quality`.
- If the learner met a new word, stage it for `new_vocabulary[]`.
- If the learner made an error, stage it for `errors[]`.

Do **not** call `fluent_update_session` or `update-db.py` after every word — batch at session end.

### 5. Session summary

```markdown
## 📚 Vocabulary Session Complete!

**Words Reviewed:** {N}
**Accuracy:** {X}%
**New Words Learned:** {Y}
**Words Mastered (→ level 5):** {Z}

**Strong:** {list words with mastery 4-5}
**Need more practice:** {list words with mastery 0-2}

**Next review:**
- Tomorrow: {count} words
- This week: {count} words

**Anki:** Type `/fluent-anki-sync` if you want these cards exported.

{target-language "well done"}! 🌟
```

### 6. Update all databases

Call MCP tool `fluent_update_session` once with:

- `session_id`, `date`, `duration_minutes`
- `command_used: "/fluent-vocab"`
- `skills_practiced: ["vocabulary"]`
- `skill_scores.vocabulary`: `{exercises, correct, time_minutes}`
- `errors[]`, `new_vocabulary[]`, `review_results[]` collected during the session
- `exercises[]` with prompts, learner answers, correct answers, feedback, and scores worth keeping
- `focus_next_session[]` — top 2-3 weak words

Fallback: call `python3 scripts/update-db.py` once with the same payload.

## Examples

### Example 1 — recognition drill

> ## Word 1/15
>
> **Target language:** de keuken
>
> **Context:** "De keuken is klein maar mooi."
>
> **What does it mean in English?**
>
> Type your answer:

Learner: "the kitchen"

> ✅ Exactly.
>
> **Answer:** the kitchen
> **Meaning:** A room used for cooking and food preparation.
> **Example:** "De keuken is klein maar mooi." (The kitchen is small but pretty.)
>
> **Score: 10/10** 🎯
>
> ---

### Example 2 — production with error

> ## Word 7/15
>
> **Native language:** to write
>
> **How do you say this in the target language?**

Learner: "schrijven"

> ✅ Correct — infinitive form.
>
> Now: can you also give the first-person present? (I write → …)

### Example 3 — session end summary

> ## 📚 Vocabulary Session Complete!
>
> **Words Reviewed:** 15
> **Accuracy:** 80% (12/15)
> **New Words Learned:** 3
> **Words Mastered:** 1
>
> **Need more practice:** de sleutel, het raam, gisteren
>
> **Next review:** Tomorrow 4 words, this week 8 words.
>
> Goed gedaan! 🌟

## Critical Rules

- **One word at a time.** Wait for the learner's answer before showing the next.
- **Immediate feedback** after each — use `fluent-feedback-formatter`.
- **Mix modes.** Don't drill 20 recognition prompts in a row — interleave for discrimination.
- **Use target language** for greetings + transitions when the learner is B1+; for A1-A2 mix target + native.
- **Never** update the DBs mid-session — batch at end.
- **Never auto-invoke.** This skill is gated; must fire only on explicit `/fluent-vocab`.
- **Prefer usable vocabulary.** Adult learners need words they can deploy in their real contexts, not only isolated translations.

## Tips for the Learner (append if they seem tired or unsure)

- Review daily for best retention — spaced repetition depends on it.
- Focus time on weak words (mastery 0-2), not already-strong ones.
- Use words in sentences to build contextual memory.
- Say words out loud even though you're typing.
