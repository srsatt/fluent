# Practice Analysis Guide

**Purpose:** Explain how to turn Fluent session records into the next lesson plan. This file is language-agnostic and applies to any skill, not only exam writing.

## Inputs

Use these sources in order:

1. `read-db.py` output for current counts, mastery, due reviews, and recent sessions.
2. The latest 3-5 `/results/fluent-{skill}-session-{NNN}.md` files for rich examples.
3. The learner profile for goals, level, interests, and constraints.

Do not scan the entire history unless the learner explicitly asks for a long-term audit.

## What to Extract

From result files, extract:

- recurring error patterns
- severity labels
- examples of the learner's actual wording
- corrected target forms
- scores and accuracy trend
- strengths worth reinforcing
- tasks that were too easy or too hard
- learner confidence or frustration signals

Use database aggregates for counts; use markdown files for context.

## Error Pattern Categories

Use these default categories, adding language-specific subcategories when useful:

| Category | Examples |
|----------|----------|
| grammar | word order, tense, agreement, conjugation, case |
| vocabulary | wrong word, collocation, false friend, English/native-language mixing |
| register | formal/informal, politeness, genre conventions |
| pronunciation_proxy | sound-spelling issue represented in typed practice |
| articles_determiners | articles, classifiers, gender, definiteness |
| prepositions_particles | prepositions, particles, postpositions |
| spelling_script | spelling, accents, script, punctuation |
| comprehension | main idea, detail, inference, vocabulary in context |
| task_completion | missing required element, off-topic answer, wrong format |

Severity:

- `critical`: blocks communication or undermines the learner's stated goal.
- `moderate`: understandable but salient or recurring.
- `minor`: low-impact form issue.

## Pattern Priority

Rank practice targets by:

1. due review status
2. critical severity
3. frequency across recent sessions
4. low mastery level
5. relevance to the learner's goal
6. readiness: the learner has enough foundation to benefit

Avoid over-prioritizing rare minor errors. Adults need visible progress on meaningful tasks.

## Next-Session Plan

Use this structure:

```markdown
## Session Plan ({minutes} min)

**Primary task:** {real-world task}
**Patterns to target:** {2-3 patterns}
**Review first:** {due items or "none"}

1. Warm-up ({x} min) - one easy retrieval task.
2. Review ({x} min) - due items, highest priority first.
3. Focus drill ({x} min) - pattern #1 in context.
4. Contrast drill ({x} min) - pattern #2 or common confusion.
5. Integration ({x} min) - realistic task requiring both patterns.
6. Reflection ({x} min) - one self-correction or confidence rating.
```

## Adaptive Decisions

Use the last 5-10 answers or latest comparable session:

- **<50% accuracy:** add scaffolds, reduce length, isolate one variable.
- **50-75% accuracy:** keep difficulty, interleave patterns.
- **>80% accuracy:** increase realism, reduce hints, add time pressure only if relevant.

For speaking-style practice, use communicative clarity as the main score. For exam writing, include task completion and register.

## Feedback Mining Rules

When parsing session files:

- `❌` marks errors.
- `✅` marks strengths.
- `**Score:** X/10` marks per-answer score.
- `**Accuracy:** N%` marks session accuracy.
- `**Focus Areas:**` marks next-session planning cues.

Normalize equivalent pattern names. For example, `formal_informal`, `register_formality`, and `u_vs_je` should not become three separate targets.

## Result File Requirements

Every new result file should include:

- prompt
- learner answer
- corrected answer
- feedback
- score
- error pattern summary
- strengths
- focus areas for next time

The file is a narrative learning record. The databases hold the aggregate state.
