---
name: fluent-rss
description: Run real-life RSS media study sessions from learner-configured audio or video feeds. Triggered when the learner types /fluent-rss or /fluent-rss setup. Use setup mode to store RSS feed URLs and optional whisper.cpp transcription settings; use study mode to preview feed items, let the learner choose one item, create or load subtitles/transcripts for audio or video, ask one comprehension/listening question at a time, and persist results at session end.
allowed-tools: Read, Write, Bash, AskUserQuestion
disable-model-invocation: true
---

# RSS Media Study

## Overview

Use real RSS audio or video content as lesson material. The learner stores one or more RSS feeds, the agent previews recent media items, the learner chooses what to study, and the session turns authentic material into listening, reading, vocabulary, and summary practice.

This skill has two modes:

- `/fluent-rss setup` - one-time or occasional setup for feed URLs and transcription preferences.
- `/fluent-rss` - study from the configured feeds.

## Setup Mode

### 1. Load learner state

```bash
python3 scripts/read-db.py
```

If required learner stores are missing, stop and route to `/fluent-setup`.

### 2. Collect RSS settings

Ask one setup question at a time. Required:

1. RSS feed URL(s).
2. Feed label, if the feed title is not enough.
3. Expected media type: `audio`, `video`, or `mixed`.

Optional transcription settings:

1. Whether to create subtitles/transcripts for media.
2. Provider. Currently store `whisper.cpp` when the learner says they want whisper.cpp.
3. Path to the whisper.cpp binary, usually `whisper-cli` or `main`.
4. Path to the whisper.cpp model, for example a `ggml-*.bin` file.
5. Language code or `auto`. Prefer the learner's target language when known.
6. `ffmpeg` path, if media must be converted before transcription.

Do not guess local paths. If the learner is unsure, store the feed first and leave transcription disabled or incomplete.

### 3. Save RSS preferences and STT settings

Call the setup helper from the repo root:

```bash
python3 scripts/rss-setup.py <<'EOF'
{
  "feeds": [
    {
      "url": "https://example.com/feed.xml",
      "label": "Example podcast",
      "content_type": "audio"
    }
  ],
  "transcription": {
    "enabled": true,
    "provider": "whisper.cpp",
    "binary": "whisper-cli",
    "model": "/path/to/ggml-model.bin",
    "language": "auto",
    "ffmpeg": "ffmpeg"
  }
}
EOF
```

The helper stores feed URLs in `learner-profile.preferences.rss` through the storage adapter and keeps SQL/JSON mirrors consistent. It stores machine-local transcription settings in `<data_dir>/rss-stt-settings.json`, not in SQL, because binary/model paths are user-machine configuration.

### 4. Verify preview access

```bash
python3 scripts/rss-preview.py --limit 5 --json
```

If the feed cannot be fetched, show the error and ask for a corrected feed URL. Do not start a study session until at least one media item is visible.

## Study Mode

### 1. Load context

```bash
python3 scripts/read-db.py
```

Need:

- `learner-profile.learner.target_language`
- `learner-profile.learner.current_level`
- `learner-profile.preferences.rss.feeds`
- `<data_dir>/rss-stt-settings.json` for whisper.cpp transcription settings, when needed
- due reviews and weak patterns, if present

If no RSS feeds are configured, ask the learner to run `/fluent-rss setup`.

### 2. Preview available items

Run:

```bash
python3 scripts/rss-preview.py --limit 8 --json
```

Present 3-7 choices. For each item, show:

- title
- feed/source
- media type
- date, if present
- short preview or description

Ask the learner to choose one item by number. Do not choose silently unless there is exactly one usable item and the learner has already said to start.

### 3. Prepare the material

For a selected media item:

1. Identify `media_url`, `media_type`, title, source feed, item link, and summary from the preview output.
2. Create a stable `output_id` from the item id or title.
3. Check for an existing transcript/subtitle path under the RSS transcript directory.
4. For audio, create subtitles before comprehension questions when transcription is configured:

```bash
python3 scripts/rss-transcribe.py --media-url "{media_url}" --output-id "{output_id}" --json
```

5. For video, use available subtitles/transcripts when the feed provides them. If not, ask whether to transcribe the audio track with the configured provider.
6. If transcription is unavailable or fails, fall back to the RSS title, summary, and learner-provided notes/transcript. Make the limitation explicit and keep the exercise closer to reading/media-preview comprehension.

Do not reveal the full transcript before the first listening or watching task. Use transcript excerpts only after the learner has attempted gist/detail questions.

### 4. Run the lesson

Use a short sequence, one prompt at a time:

1. Prediction: ask what the learner expects from the title and preview.
2. Gist: ask for the main idea after listening/watching or reading the preview.
3. Detail: ask one fact from the subtitle/transcript.
4. Vocabulary in context: ask about one useful word or phrase.
5. Transcript reconstruction: provide a short gap-fill from the subtitle text.
6. Output: ask for a short summary or opinion in the target language.

Adapt by CEFR:

- A1-A2: short excerpts, multiple choice, true/false, one-sentence answers.
- B1: short open answers, simple summaries, useful chunks from the transcript.
- B2+: inference, stance, register, paraphrase, and discussion.

Use the `fluent-feedback-formatter` pattern after every learner answer. Track comprehension, vocabulary, grammar, and listening errors for the session-end payload.

### 5. Optional vocabulary save

After the comprehension questions, offer 2-5 useful words or phrases from the transcript/summary:

```markdown
Save these for future review?
1. {word/phrase} - {native-language meaning}
2. {word/phrase} - {native-language meaning}

Type the numbers to save, or "skip".
```

Only add selected items to `new_vocabulary[]`.

### 6. Session end

Save a result file:

```text
results/fluent-rss-session-{NNN}.md
```

Include:

- source feed and item title
- item link and media type
- transcript/subtitle path if created
- prompts, learner answers, feedback, scores
- vocabulary selected for review
- error pattern summary and next focus

Avoid copying a full copyrighted transcript into the result file. Store the local transcript path and the excerpts actually used for questions.

Call `fluent-db-updater` once:

- `command_used: "/fluent-rss"`
- `skills_practiced: ["listening", "reading", "vocabulary"]` for audio/video transcript sessions
- include `speaking` or `writing` only if the learner produced extended output
- `skill_scores.listening` for gist/detail/transcript-reconstruction items
- `skill_scores.reading` for preview/transcript reading items
- `skill_scores.vocabulary` for vocabulary-in-context items
- `errors[]` for missed comprehension, vocabulary, or target-language production patterns
- `new_vocabulary[]` for learner-approved words
- `topics_covered[]` including `rss_media`, source/topic, and media type
- `session_notes` with source title and transcript path

## Critical Rules

- Trigger only on explicit `/fluent-rss` or `/fluent-rss setup`.
- Ask one question at a time and wait for the learner's answer.
- Always let the learner choose the item from the RSS preview.
- Do not reveal the full transcript before initial gist/detail attempts.
- Do not transcribe large or paid/private media without learner confirmation.
- Keep RSS feed URLs in `learner-profile.preferences.rss`.
- Keep whisper.cpp/STT binary and model paths in `<data_dir>/rss-stt-settings.json`; do not store machine-local executable paths in SQL.
- Use helper scripts for setup, preview, and transcription; use `update-db.py` only once at session end.
