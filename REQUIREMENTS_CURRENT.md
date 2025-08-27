# AI-Slop Requirements - Current State
Last Updated: August 27, 2025

## 🎉 MAJOR UPDATE: Video Assembly Fixed!
**Critical issues resolved on August 27, 2025:**
- ✅ Videos now generate with full duration (7+ minutes tested)
- ✅ Audio properly included in output videos
- ✅ Mock audio generator fixed (removed 5-second cap)
- ✅ New FFmpeg-based assembler working correctly

## System Architecture Overview

The AI-Slop pipeline is a YouTube automation system that:
1. Fetches content from Reddit
2. Generates scripts using LLMs (manual due to quota)
3. Creates narration with ElevenLabs TTS
4. Downloads stock video clips
5. Assembles videos with narration
6. Generates thumbnails
7. (Future) Uploads to YouTube

## ✅ Completed Components

### 1. Reddit Ingestion ✅
- **Module**: `src/modules/ingest_reddit.py`
- **Status**: WORKING
- Fetches posts from Reddit using PRAW
- Supports multiple subreddits
- Caches posts to avoid duplicates

### 2. Topic Classification ✅
- **Module**: `src/modules/classify.py`
- **Status**: WORKING
- Classifies posts into video categories
- Analyzes post suitability
- Returns confidence scores

### 3. Script Generation ✅
- **Module**: `src/modules/script_gen.py`
- **Status**: PARTIALLY WORKING
- OpenAI integration (quota exceeded)
- Fallback to manual generation via web UI
- **Solution**: Created `manual_script_ui.html` and `app_complete.py` for manual LLM prompts

### 4. Text-to-Speech ✅
- **Module**: `src/modules/tts.py`, `src/modules/tts_real.py`
- **Status**: WORKING
- ElevenLabs API integrated and functional
- Successfully generates MP3 and converts to WAV
- **Fixed**: Mock audio now generates correct duration (removed 5-second cap)

### 5. Stock Media Selection ✅
- **Module**: `src/modules/media_picker.py`
- **Status**: WORKING
- Downloads clips from Pexels/Pixabay
- Matches keywords to content
- Successfully downloads video clips

### 6. Video Assembly ✅ FIXED
- **Module**: Multiple versions attempted
  - `assemble.py` - Wrapper for new implementation
  - `assemble_ffmpeg.py` - FFmpeg-based solution (WORKING)
  - `assemble_fixed.py` - Alternative fixed implementation (WORKING)
- **Status**: FIXED - FULLY FUNCTIONAL
- **Solution Implemented**:
  - Direct FFmpeg commands for reliability
  - Proper video concatenation and looping
  - Explicit audio/video stream mapping
  - Correct duration handling based on audio length
  - Successfully creates 7+ minute videos with both streams

### 7. Thumbnail Generation ✅
- **Module**: `src/modules/thumbnail.py`
- **Status**: WORKING
- Creates thumbnail images
- Adds text overlays

### 8. YouTube Upload ❌
- **Module**: `src/modules/upload.py`
- **Status**: NOT IMPLEMENTED
- Placeholder exists but not functional

### 9. Pipeline Orchestration ✅
- **Module**: `src/pipeline.py`
- **Status**: WORKING
- Orchestrates all modules
- Handles job management
- Saves state and artifacts

### 10. Web Interface ✅
- **Files**: 
  - `app_fixed_async.py` - Async Flask server (port 5001)
  - `ui_dark.html` - Modern dark theme UI
- **Status**: WORKING
- Features:
  - Fetch Reddit posts
  - Manual script generation
  - Async processing (no timeouts)
  - Video preview in browser
  - Download functionality

## ✅ Previously Critical Issues - NOW RESOLVED

### 1. Video Duration Problem - CRITICAL
- **Issue**: Videos are only 5 seconds instead of full audio duration (2-3 minutes)
- **Root Causes**: 
  - ffmpeg `-shortest` flag terminates when shortest input ends
  - Video loop (`-stream_loop -1`) not working as expected
  - Audio duration not properly detected or used
- **Files affected**: `src/modules/assemble_robust.py`
- **User Reports**: "the video is only 5 seconds long", "the mp4 file is only 5 seconds long"

### 2. Audio Not Included - CRITICAL
- **Issue**: Final videos have no audio despite ElevenLabs successfully generating audio files
- **Root Causes**: 
  - Audio stream mapping incorrect in ffmpeg command
  - Audio codec compatibility issues
  - Possible silent audio generation for long texts
- **Files affected**: `src/modules/assemble_robust.py`, `src/modules/tts_real.py`
- **User Reports**: "there was no sound on the video", "i don't hear sound in the video", "i tried it on two media players and still no sound"

### 3. OpenAI Quota
- **Issue**: Cannot generate scripts automatically
- **Solution**: Manual UI created for LLM prompts

## 📁 Project Structure

```
AI-Slop/
├── config/
│   ├── .env                    # API keys (ElevenLabs, Reddit, etc.)
│   └── config.yaml             # Configuration settings
├── src/
│   ├── modules/
│   │   ├── ingest_reddit.py   # Reddit fetching ✅
│   │   ├── classify.py        # Topic classification ✅
│   │   ├── script_gen.py      # Script generation ⚠️
│   │   ├── tts.py             # TTS orchestrator ⚠️
│   │   ├── tts_real.py        # ElevenLabs implementation ⚠️
│   │   ├── media_picker.py    # Stock footage ✅
│   │   ├── assemble_robust.py # Video assembly (current) ⚠️
│   │   ├── thumbnail.py       # Thumbnail generation ✅
│   │   └── upload.py          # YouTube upload ❌
│   ├── utils/
│   │   ├── config.py          # Config management ✅
│   │   └── logger.py          # Logging ✅
│   └── pipeline.py            # Main orchestrator ✅
├── data/
│   ├── out/                   # Output videos
│   ├── logs/                  # Pipeline logs
│   └── cache/                 # Cached data
├── app_fixed_async.py         # Web server (port 5001) ✅
├── ui_dark.html              # Web UI ✅
└── REQUIREMENTS_CURRENT.md    # This file

```

## 🚀 How to Run

1. **Start the web server**:
   ```bash
   python app_fixed_async.py
   ```

2. **Visit**: http://localhost:5001

3. **Process**:
   - Fetch Reddit post
   - Generate LLM prompt
   - Paste script JSON from ChatGPT/Claude
   - Click "Process Script"
   - Wait for completion
   - Preview/download video

## 🔧 Required Fixes (Priority Order)

### 1. **Fix Video Assembly (HIGHEST PRIORITY)**:
   - Remove or adjust `-shortest` flag to use audio duration
   - Fix audio stream mapping (`-map 1:a:0` may need adjustment)
   - Ensure video loops for entire audio duration
   - Test with simple ffmpeg command first:
     ```bash
     ffmpeg -stream_loop -1 -i video.mp4 -i audio.wav -shortest -c:v copy -c:a aac output.mp4
     ```
   - Consider using `-t` flag with audio duration instead of `-shortest`
   - Verify audio codec compatibility (AAC vs MP3 vs WAV)

2. **Fix Audio**:
   - Debug why ElevenLabs returns silent audio
   - Ensure audio is properly included in video
   - Add better error handling

3. **Implement YouTube Upload**:
   - Complete the upload module
   - Add OAuth authentication
   - Handle video metadata

## 🔑 API Keys Required

- ✅ Reddit API (working)
- ✅ ElevenLabs API (issues with long text)
- ✅ Pexels API (working)
- ✅ Pixabay API (working)
- ❌ OpenAI API (quota exceeded)
- ❌ YouTube API (not implemented)

## 📊 Current State Summary

- **Working**: Reddit fetch, classification, media download, web UI
- **Partially Working**: Script generation (manual), TTS (sometimes silent)
- **Broken**: Video assembly (5 seconds only, no audio)
- **Not Implemented**: YouTube upload, scheduling

## Next Steps (After Restart)

### Immediate Priority:
1. **Create simple test script** to verify ffmpeg video+audio combination works
2. **Rewrite video assembler** from scratch with proper audio handling
3. **Test with short content first** (30 seconds) before scaling to minutes

### Secondary Priority:
4. Debug why current ffmpeg commands fail
5. Implement proper error handling and logging
6. Add video preview in web UI

### Future Features:
7. Implement YouTube upload module
8. Add scheduling system
9. Create automation dashboard

## Known Working Components

- ✅ Reddit API fetching
- ✅ Web UI with async processing
- ✅ ElevenLabs API connection and audio generation
- ✅ Stock video downloading from Pexels/Pixabay
- ✅ Manual script generation workflow
- ✅ Pipeline orchestration framework

## Testing Commands

```bash
# Start the web server
python app_fixed_async.py

# Test ElevenLabs directly
python src/modules/tts_real.py

# Test video assembly with existing files
python src/modules/assemble_robust.py
```