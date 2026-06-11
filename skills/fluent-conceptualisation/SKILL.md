---
name: fluent-conceptualisation
description: Run an interactive grammar conceptualisation session where the learner discovers, tests, and names a grammar rule needed for speaking or writing. Triggered only when the learner types /fluent-conceptualisation or /fluent-conceptualization. Selects a high-impact rule from due reviews, weak patterns, and learner goals, teaches through examples before explanation, asks one hypothesis or production task at a time, and persists the discovered rule for spaced review.
allowed-tools: Read, Write, Bash
disable-model-invocation: true
---

# Grammar Conceptualisation Session

## Overview

Help the learner discover one useful grammar rule instead of receiving a lecture. The session answers: "Which grammar rule do I need next to speak or write better?" Pick the rule from evidence, create examples that make the pattern visible, ask the learner to infer it, then test transfer in realistic output.

Typical length: 10-15 minutes. One rule per session.

## When to Use

Trigger this skill only when the learner types `/fluent-conceptualisation` or `/fluent-conceptualization`, or explicitly asks to discover which grammar rule they need next.

Skip this skill when the learner needs pure vocabulary review, reading comprehension, or a full writing task. Route to `/fluent-review`, `/fluent-vocab`, `/fluent-reading`, or `/fluent-writing` instead.

## Instructions

### 1. Load learner context

```bash
python3 scripts/read-db.py
```

Prefer MCP tool `fluent_read_state`; use the command above only as fallback.

Need: learner profile, due reviews, mistakes, mastery, and recent progress. If stores are missing, route to `/fluent-setup` and stop.

### 2. Choose one rule

Select one grammar rule by this priority order:

1. Due `grammar_rule` or high-priority `error_pattern` review items.
2. Recurring grammar errors with severity `critical` or `moderate`.
3. A rule blocking the learner's stated goal, such as speaking about reasons, time, opinions, requests, or citizenship/admin tasks.
4. A missing prerequisite for the next CEFR level.

Prefer rules that unlock real output. Avoid low-impact terminology and rare edge cases.

For early German A2-B1, common high-impact targets include:

- verb-second order in main clauses
- verb-final order after subordinators such as `weil`, `dass`, `wenn`
- modal verbs with infinitive at the end
- perfect tense with `haben` / `sein`
- separable verbs
- cases after frequent prepositions, especially dative after `seit`, `mit`, `bei`, `nach`, `aus`, `von`, `zu`
- adjective endings only after stronger basics are stable

### 3. Open with the purpose

Show a compact plan, not a grammar lecture:

```markdown
Today we will discover one rule that helps with: {real task}.

I chose it because: {due review / weak pattern / goal}.

First, look at examples. Then you will tell me what you notice.
```

### 4. Noticing before explanation

Present 3-5 short examples in the target language. Include a contrast pair when useful. Do not name the rule yet.

```markdown
Look at these sentences:

1. {example}
2. {example}
3. {example}

What changes in the word order/form when {condition}?
```

Ask only one noticing question. Wait for the learner's answer.

### 5. Build the rule with the learner

After the answer:

1. Confirm the useful observation.
2. Correct misconceptions briefly.
3. Ask the learner to state the rule in their own words.

```markdown
Good observation: {what they noticed}.

Small correction: {if needed}.

Now state the rule in one sentence: "When ..., I ..."
```

Wait for the learner's rule before giving the canonical version.

### 6. Give the compact rule

Keep the explanation short and operational:

```markdown
Rule: {one sentence}

Use it when: {communication need}
Watch out: {one common trap}
Russian comparison: {only if useful and not misleading}
```

Do not add a full grammar table unless the learner asks.

### 7. Test transfer

Run 3-5 one-at-a-time tasks:

1. Recognition: choose which sentence follows the rule.
2. Repair: fix one broken sentence.
3. Controlled production: write one sentence using the rule.
4. Realistic output: answer a mini speaking/writing prompt where the rule is useful.

After each answer, use the `fluent-feedback-formatter` shape:

- communicative success
- correction with severity and category `grammar`
- corrected version
- score out of 10

If the learner scores below 6 twice, simplify: return to examples and reduce the task length.

### 8. Ask for metacognition

Near the end, ask one reflection question:

```markdown
When will you use this rule in real life?
```

or:

```markdown
What is the warning sign that tells you this rule is needed?
```

Use the answer to decide whether the rule is conceptualized or only mechanically repeated.

### 9. Session end

Include useful exchange detail in `exercises[]`:

- selected rule and reason for selection
- examples used for noticing
- learner's rule hypothesis
- canonical rule
- transfer tasks and scores
- errors and corrected forms
- next focus

Then call MCP tool `fluent_update_session` with one payload:

- `command_used: "/fluent-conceptualisation"`
- `skills_practiced: ["grammar"]`
- `skill_scores.grammar`
- `errors[]` for distinct mistakes
- `review_results[]` for reviewed existing items
- `new_vocabulary[]` only for new spaced-repetition items supported by the persistence layer; use `item_type: "grammar_rule"` for a newly conceptualized rule, or `item_type: "vocabulary"` for new words
- `exercises[]` with the selected rule, noticing examples, learner hypothesis, transfer tasks, feedback, and scores
- `topics_covered: ["grammar conceptualisation", "{rule_id}"]`
- `breakthroughs[]` when the learner states the rule correctly and transfers it
- `focus_next_session[]` with the next rule or contrast pattern

For a newly discovered rule that should enter spaced repetition, add an `errors[]` item when it came from a mistake, or a `new_vocabulary[]` item with `item_type: "grammar_rule"` when it is a clean new rule. Do not hand-edit the stores.

Fallback: call `python3 scripts/update-db.py` once with the same payload.

## Example

Tutor:

```markdown
Today we will discover one rule that helps you explain reasons in German.

I chose it because your recent practice had trouble with `weil`.

Look at these sentences:

1. Ich komme morgen.
2. Ich komme morgen, weil ich heute arbeiten muss.
3. Ich bin muede, weil ich schlecht geschlafen habe.

What happens to the verb after `weil`?
```

Learner:

```text
The verb goes to the end.
```

Tutor:

```markdown
Yes. Now state the rule in one sentence: "When I use weil, I ..."
```

## Critical Rules

- One rule per session.
- Do not reveal the rule before the noticing task.
- Ask one question at a time and wait.
- Choose rules from learner evidence, not a generic grammar order.
- Prefer useful speech/writing rules over terminology.
- Persist once at the end through `fluent_update_session`.
