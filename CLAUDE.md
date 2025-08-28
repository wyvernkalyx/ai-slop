# CLAUDE.md - AI-Slop Development Log

**Last Updated:** August 28, 2025  
**Status:** FULLY OPERATIONAL  
**Current Version:** v1.2.7  
**Decision:** Pipeline fully functional with Google TTS alternative

## Current State Summary

The AI-Slop YouTube automation pipeline is fully functional with all major components working. Google Text-to-Speech has been added as a free alternative to ElevenLabs, and custom ElevenLabs voice selection has been debugged.

### What's Working ✅
- Reddit post fetching and classification
- Manual script generation UI with LLM prompt generation
- **Google TTS**: Free text-to-speech with multiple accents (US, UK, Australian, Canadian, Indian)
- ElevenLabs TTS with 7 preset voices (documentary, news, storytelling, tutorial, mystery, energetic, calm)
- **TTS Provider Selection**: Choose between Google (free) and ElevenLabs (premium)
- Stock video downloading from Pexels/Pixabay
- Flask web UI with async processing
- Pipeline orchestration framework
- **Video Assembly**: Produces full-duration videos (2-3 minutes) with proper audio
- **Video Preview**: HTML5 player in UI for reviewing before upload
- **YouTube Upload**: Full OAuth2 integration with progress tracking
- **JSON Error Handling**: Automatic repair of malformed JSON from LLMs
- **Version Display**: Shows v1.2.7 in UI top-right corner

### Recent Fixes & Features (August 27-28, 2025) ✅
- **Google TTS Integration**: Added free alternative to ElevenLabs with multiple accents
- **TTS Provider Selector**: UI dropdown to choose between Google and ElevenLabs
- **Fixed Custom Voice**: Custom ElevenLabs voice names now properly passed to backend
- **Fixed Video Duration**: Removed conflicting `-shortest` flag in ffmpeg that caused 5-second videos
- **Improved Video Looping**: Better handling of video loops to match audio duration
- **Added Video Player**: Integrated HTML5 video preview with streaming endpoint
- **YouTube Auth**: Fixed credentials path detection (supports both client_secrets.json and youtube_credentials.json)
- **Progress Tracking**: Added real-time YouTube upload progress with SSE (Server-Sent Events)
- **JSON Fixer**: Created JSONFixer utility to handle malformed JSON from various LLMs (ChatGPT, Gemini, Claude)
- **Cache Prevention**: Added no-cache headers to prevent browser caching issues

### Known Issues 🔴
- None currently - all major features working

### Not Implemented Yet ❌
- Scheduling system (manual upload only)
- Automated script generation (using manual JSON input with LLM prompts)

---

## Original Purpose

**Purpose:** This file defines how the LLM (Claude/GPT) should generate scripts, shot lists, and metadata for a fully automated, faceless YouTube channel. It enforces deterministic, monetization‑safe, policy‑aware outputs with strict JSON contracts that the pipeline can consume.

---

## 🔒 System / Developer Prompt (drop into your app)

**Role:** You are a YouTube script and metadata generator for a faceless channel. Your outputs are machine‑consumed and must strictly follow the JSON schemas below. Do not include commentary outside JSON. Keep language clear, concise, and engaging for general audiences. Target 8–12 minute videos (≈1,200–1,800 words at 150–180 wpm) unless `target_minutes` says otherwise.

**Content policy & monetization:** Avoid medical, legal, finance advice claims; avoid graphic, shocking, harassing, hateful, sexually explicit, or unsafe content. Keep PG‑13. If the source is contentious, produce a neutral, factual summary. Do not include copyrighted lyrics or long quotes. Prefer transformation and original narration.

**Readability & retention:** Hook in the first 2–3 sentences. Use short paragraphs and active voice. Use list or chapter structure with mini‑cliffhangers. Insert occasional rhetorical questions. End with a clean CTA.

**Stock/B‑roll awareness:** Suggest visual prompts that are easy to match with royalty‑free stock (e.g., “city skyline timelapse,” “close‑up typing hands,” “satellite earth”). Avoid brand logos and celebrity likenesses.

**Tone presets by topic:**

* `ai_news`: crisp, current, lightly analytical, neutral.
* `listicle`: energetic, curiosity‑driven, punchy.
* `explainer`: patient teacher, plain language.

Return **only** the JSON object required by the requested `output_format`.

---

## 🔧 Inputs (from the pipeline)

```json
{
  "topic_id": "ai_news | listicle | explainer",
  "target_minutes": 10,
  "source": {
    "title": "string",
    "selftext": "string",
    "url": "https://...",
    "subreddit": "string",
    "captured_at": "YYYY-MM-DD",
    "safe_summary": "(optional) sanitized summary if provided by app"
  },
  "brand": {
    "channel_name": "string",
    "style_notes": "(optional) brief house style",
    "banned_terms": ["list", "of", "terms"],
    "voice_name": "Rachel"
  },
  "output_format": "script.v1 | metadata.v1 | shotlist.v1 | all.v1"
}
```

---

## 📤 Outputs (JSON contracts)

### 1) `script.v1`

```json
{
  "version": "script.v1",
  "title": "Concise working title (<= 100 chars)",
  "hook": "2–3 sentence cold open that creates curiosity",
  "narration": {
    "intro": "~120–180 words",
    "chapters": [
      {"id": 1, "heading": "#10 — ...", "body": "120–180 words"},
      {"id": 2, "heading": "#9 — ...",  "body": "120–180 words"}
    ],
    "outro": "~80–120 words with CTA"
  },
  "broll_keywords": ["stockable visual prompts, 1–3 words each"],
  "disclaimers": ["any disclaimers needed"],
  "policy_checklist": {
    "copyright_risk": false,
    "medical_or_financial_claims": false,
    "nsfw": false,
    "shocking_or_graphic": false
  }
}
```

### 2) `metadata.v1`

```json
{
  "version": "metadata.v1",
  "youtube": {
    "title": "55–65 char CTR-optimized",
    "description": "2 short paragraphs + timestamps, include Source URL",
    "tags": ["broad", "niche", "long-tail"],
    "categoryId": 27,
    "language": "en",
    "made_for_kids": false
  },
  "thumbnail_text": "3–5 BIG words, no punctuation",
  "slug": "kebab-case-for-filenames"
}
```

### 3) `shotlist.v1`

```json
{
  "version": "shotlist.v1",
  "fps": 30,
  "music_mood": "calm | upbeat | cinematic",
  "beats": [
    {
      "t_start": 0.0,
      "t_end": 6.5,
      "narration_ref": "intro",
      "visual_prompt": "city skyline timelapse",
      "avoid": ["logos", "recognizable faces"],
      "transition": "hard-cut"
    }
  ]
}
```

### 4) `all.v1`

Return an object with keys `script`, `metadata`, and `shotlist`, each adhering to the schemas above.

---

## 🧱 Template Hints per Topic

**ai\_news**

* Hook: “Here’s what actually changed today and why it matters.”
* Chapters: company/tech → implications → risks/limitations → what to watch next.
* B‑roll: newsroom, code, datacenters, analysts, charts (generic).

**listicle**

* Hook: “#3 surprised us” style. Descend #10→#1 with mini‑cliffhangers.
* B‑roll: neutral visuals aligned to each item concept; avoid brands.

**explainer**

* Hook: simple metaphor + promise.
* Chapters: definition → how it works → example → misconception → takeaway.

---

## ✅ Style Rules

* Reading rate: 150–180 wpm.
* Sentences ≤ 20 words on average.
* Avoid passive voice where possible.
* No jargon unless explained.
* Keep facts neutral and sourced (mention “source in description”).

---

## 🚫 Guardrails & Fallbacks

* If input is unsafe or off‑limits, output a safe, evergreen variant of the topic (same format) and set a `disclaimers` note explaining the substitution.
* If not enough source detail, widen with general background but stay truthful and generic.

---

## 🧪 Example (truncated)

**Input** → `{ "topic_id": "listicle", "target_minutes": 10, "source": { "title": "Scientists spot a massive solar flare", "selftext": "", "url": "https://reddit.com/...", "subreddit": "r/popular" }, "output_format": "metadata.v1" }`

**Output** (`metadata.v1`)

```json
{
  "version": "metadata.v1",
  "youtube": {
    "title": "Top 10 Solar Phenomena That Bend Nature",
    "description": "Today we’re counting down the ten wildest solar phenomena...\n\nSource: https://reddit.com/...\n\n00:00 Intro\n00:35 Coronal Mass Ejections\n...",
    "tags": ["space", "sun", "science", "astronomy", "solar flare", "coronal mass ejection"],
    "categoryId": 27,
    "language": "en",
    "made_for_kids": false
  },
  "thumbnail_text": "SUN’S WILDEST TRICKS",
  "slug": "top-10-solar-phenomena"
}
```

---

## 🔁 Determinism Settings (recommended)

* Temperature 0.3, Top‑p 0.9, max tokens sized for target minutes.
* Enforce JSON with a parser/repair step; reject on schema mismatch and re‑ask with: “Return **only** valid JSON per schema X. No commentary.”

---

## 📏 Length Targets

* 8–12 minutes default (`target_minutes` controls chapter count/length).
* Intro \~100–150 words; each chapter \~120–180 words; outro \~80–120 words.

---

# REQUIREMENTS.md

## 1. Overview

Implement a headless pipeline that ingests trending Reddit content, classifies it into a channel topic, generates narration/script + shotlist + metadata, synthesizes voiceover, assembles a stock‑footage video with captions, auto‑generates a thumbnail, and uploads to YouTube on a schedule—**without human intervention** after initial configuration.

## 2. Goals & Non‑Goals

**Goals**

* Fully automated daily/hourly publishing with zero manual steps.
* Monetization‑safe (policy‑aware) narration and visuals.
* Deterministic, recoverable pipeline with audit logs.

**Non‑Goals**

* No scraping copyrighted assets or displaying Reddit users’ media.
* No live commentary; all faceless narration.

## 3. Scope

**In**: Reddit ingest, topic routing, LLM templating, TTS, stock media selection, rendering, thumbnailing, YouTube upload, scheduling, logging, metrics, deduplication.
**Out**: Custom music composition, face animation, manual video editing.

## 4. Architecture

* **Orchestrator** (`pipeline.py`) runs one job per cycle.
* **Modules**: `ingest_reddit` → `classify` → `script_gen`(LLM+templates) → `tts` → `media_picker` → `assemble` → `thumbnail` → `upload_youtube` → `metrics`.
* **Data**: JSON artifacts persisted under `data/out/` per job (script, metadata, shotlist, logs).
* **Config**: `config.yaml` + `.env` + topic templates.

## 5. Functional Requirements (FR)

* **FR1 – Reddit Ingest**: Fetch top SFW post from r/popular with title; configurable filters (score ≥ X, exclude subreddits list).
* **FR2 – Dedup**: Maintain a hash (e.g., post permalink) to skip already‑processed items for N days.
* **FR3 – Classification**: Rule‑based keyword match to `topic_id`; fallback random/weighted selection; override via allowlist.
* **FR4 – Script Generation**: Use Jinja2 templates + optional LLM polish; produce `script.v1` JSON with chapters sized to `target_minutes`.
* **FR5 – Policy Check**: Compute `policy_checklist` and fail safe if any flag is true (skip or substitute safe topic variant).
* **FR6 – TTS**: Convert narration to MP3/WAV using ElevenLabs (or Azure/Play.ht); return duration; handle rate limits and retries (exponential backoff up to 3 attempts).
* **FR7 – Media Selection**: Extract keywords; fetch Pexels/Pixabay stock clips; prefer 720p or 1080p MP4; min 3s, max 7s per clip; number of clips = `clips_per_minute * target_minutes`.
* **FR8 – Assembly**: Concatenate clips to match audio duration, add fades (0.2s), set final duration = min(video, audio). Render H.264 MP4, 1080p, 30fps, 10–14 Mbps.
* **FR9 – Captions (optional)**: Generate SRT from narration timestamps (basic sentence splitting) and mux as soft subs.
* **FR10 – Thumbnail**: Auto‑generate 1280×720 JPG with 3–5 word text block, high contrast. Support either a solid background or blurred frame still.
* **FR11 – Metadata**: Generate `metadata.v1` (title 55–65 chars, SEO description with timestamps, 10–20 tags, categoryId 27, not made for kids).
* **FR12 – Upload**: Use YouTube Data API v3; resumable upload; set title/description/tags/category/visibility; set custom thumbnail.
* **FR13 – Scheduling**: Immediate or CRON‑like scheduling (Windows Task Scheduler/Cron); configuration `upload.schedule`.
* **FR14 – Logging**: Structured logs (JSON) with correlation id per job; store under `data/logs/`.
* **FR15 – Metrics**: Emit basic metrics (jobs\_started/succeeded/failed, durations, external API counts) to a CSV or SQLite file.
* **FR16 – Alerts**: On fatal failure, optionally send email/webhook with last 100 log lines.

## 6. Non‑Functional Requirements (NFR)

* **NFR1 – Reliability**: Job success rate ≥ 95% excluding external API outages; idempotent retries.
* **NFR2 – Cost**: Average per‑video variable cost ≤ \$0.50–\$1.50 (stock + TTS). Use free stock quotas first.
* **NFR3 – Performance**: End‑to‑end render ≤ 10 minutes on a typical desktop for a 10‑min video.
* **NFR4 – Maintainability**: Modular Python code; config‑driven behavior; templates in `/templates`.
* **NFR5 – Security**: Secrets via `.env` and OS keychain if available; never log secrets.
* **NFR6 – Compliance**: Respect stock licenses; keep attributions where required (in description if needed). Avoid trademark/logos in visuals.

## 7. External Dependencies

* Reddit API (PRAW)
* ElevenLabs (or Azure TTS/Play.ht)
* Pexels/Pixabay Videos API
* YouTube Data API v3 (OAuth Desktop flow)

## 8. Configuration

* `config.yaml` controls topics, target length, media pacing, default tags, visibility, schedule.
* `.env` holds keys: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT`, `PEXELS_API_KEY`, `ELEVENLABS_API_KEY`, `GOOGLE_CLIENT_SECRETS`, `YT_CATEGORY_ID`, `YT_VISIBILITY`.

## 9. Data Model (artifacts)

* `job.json`: { id, started\_at, post\_url, topic\_id, status }
* `script.json`: `script.v1`
* `metadata.json`: `metadata.v1`
* `shotlist.json`: `shotlist.v1`
* `narration.mp3` | `wav`
* `clips/` downloaded assets
* `video.mp4`, `thumb.jpg`, `upload_receipt.json`

## 10. Error Handling & Retries

* Network/API: exponential backoff (1s, 3s, 9s), 3 attempts.
* Schema violations: ask LLM to re‑emit valid JSON; hard‑fail after 2 repairs.
* Missing media: relax keyword search, then fallback to generic B‑roll pack.
* Upload failure: resume chunked upload; if still failing, set status `blocked` and alert.

## 11. Acceptance Criteria

* AC1: One scheduled run produces a compliant 8–12 min video, a thumbnail, and uploads public/unlisted successfully with correct metadata.
* AC2: Dedup prevents re‑processing the same Reddit URL within 7 days.
* AC3: Title length 55–65 chars; thumbnail text ≤ 5 words; no banned terms.
* AC4: Final duration within ±30s of target minutes × 60.
* AC5: Logs show each module start/finish with durations.

## 12. Test Plan (high level)

* Unit: classify rules, schema validation, timestamp maker.
* Integration: fake Reddit input → full pipeline dry run with mocked APIs.
* Live smoke: real APIs in a sandbox playlist/unlisted visibility.
* Regression: golden sample inputs checked into `/tests/data/`.

## 13. Scheduling & Ops

* Windows Task Scheduler XML (hourly). Cron example: `0 * * * * /usr/bin/python /app/src/pipeline.py`.
* Daily budget cap: stop after N jobs or when daily API quota reaches threshold.
* Rotating logs; retain 14 days by default.

## 14. Risks & Mitigations

* Reddit/YouTube API changes → pin SDK versions; feature flags.
* Stock media shortage → maintain a local fallback pack.
* Policy strikes → conservative topic filter, human‑review mode toggle.

## 15. Roadmap (nice‑to‑have)

* Shorts auto‑derivation (30–45s clips with captions).
* Thumbnail A/B (two versions, pick higher CTR historically).
* Multi‑voice narration per chapter.
* Simple on‑screen text captions burned in.

---

## Troubleshooting Guide

### Custom Voice Not Working
**Problem:** Selecting "Custom Voice" and entering a name (e.g., "Gregg") results in error: "Received 'custom' as voice value"

**Debug Steps:**
1. Check version number in UI (should be v1.2.1)
2. Clear browser cache (Ctrl+F5 or use incognito mode)
3. Open browser console (F12) before testing
4. When selecting Custom Voice and generating video, check console for:
   - `=== VOICE SELECTION DEBUG ===`
   - Value being sent in request body
5. Check server console for `[VOICE DEBUG]` messages

**Current Code Status (v1.2.1):**
- `ui_enhanced.html`: Has comprehensive debugging, multiple fallback methods
- `app_enhanced.py`: Has voice validation and recovery attempts
- `src/modules/tts_real.py`: Has custom voice search via ElevenLabs API

**To Restart with Latest Code:**
```bash
# PowerShell
.\restart_enhanced.ps1

# Or CMD
restart_enhanced.bat

# Or manually
taskkill /F /IM python.exe
python app_enhanced.py
```

### Files Modified in Latest Session
- `ui_enhanced.html` - Added debugging, version display, custom voice handling
- `app_enhanced.py` - Added cache headers, enhanced voice debugging
- `src/modules/assemble_ffmpeg.py` - Fixed video duration issue
- `src/modules/upload_youtube.py` - Added progress callbacks
- `src/modules/tts_real.py` - Added custom voice search
- `src/utils/json_fixer.py` - Created JSON repair utility

---

**End of Documents**
