# AI-Slop 🎬

An automated YouTube video generation pipeline that creates faceless videos from trending Reddit content using AI. Now with **FREE Google Text-to-Speech** support!

## 🚀 Features

- **Reddit Content Ingestion**: Automatically fetches trending posts from Reddit
- **AI Script Generation**: Converts Reddit posts into engaging video scripts with LLM prompts
- **Dual TTS Support**: 
  - **Google TTS (FREE)**: Multiple accents (US, UK, Australian, Canadian, Indian)
  - **ElevenLabs (Premium)**: 7 voice presets + custom voice support
- **Stock Footage**: Downloads relevant B-roll from Pexels/Pixabay
- **Video Assembly**: Smart video looping with intro/outro support
- **YouTube Upload**: Full OAuth2 integration with real-time progress tracking
- **Thumbnail Generation**: Auto-generates eye-catching thumbnails
- **Web Interface**: Modern UI with video preview player
- **JSON Error Recovery**: Automatically fixes malformed JSON from LLMs

## 📋 Prerequisites

- Python 3.8+
- FFmpeg installed and in PATH
- API Keys for:
  - Reddit API (for fetching posts)
  - Pexels/Pixabay (for stock footage)
  - YouTube OAuth2 credentials (for upload)
  - ElevenLabs (optional, for premium TTS)
  - OpenAI/Claude/Gemini (optional, for script generation)

## 🔧 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-slop.git
cd ai-slop
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp config/.env.template config/.env
# Edit config/.env with your API keys
```

## 🎯 Quick Start

### Enhanced Web Interface (Recommended)
```bash
# Windows
restart_enhanced.bat
# or
python app_enhanced.py
```
Then open http://localhost:5000 in your browser.

### Features in Web UI:
1. **Fetch Reddit Post**: Get trending content from various subreddits
2. **Generate Script**: Copy the LLM prompt and generate script with ChatGPT/Claude
3. **Select TTS Provider**: Choose between FREE Google TTS or premium ElevenLabs
4. **Process & Generate**: Create full video with one click
5. **Preview Video**: Watch before uploading
6. **Upload to YouTube**: One-click upload with progress tracking

### First-Time YouTube Setup
```bash
python setup_youtube.py
```
Follow the OAuth2 flow to authorize YouTube access.

## 📁 Project Structure

```
AI-Slop/
├── app_enhanced.py             # Main web application
├── ui_enhanced.html            # Enhanced web interface
├── src/
│   ├── modules/
│   │   ├── ingest_reddit.py    # Reddit content fetching
│   │   ├── tts_google.py       # Google TTS (FREE)
│   │   ├── tts_real.py         # ElevenLabs TTS
│   │   ├── media_picker.py     # Stock footage selection
│   │   ├── assemble_enhanced.py # Smart video assembly
│   │   ├── thumbnail_enhanced.py # Thumbnail generation
│   │   └── upload_youtube.py   # YouTube upload with progress
│   └── utils/
│       ├── config.py           # Configuration management
│       └── json_fixer.py       # LLM JSON repair utility
├── data/
│   └── out/                   # Generated videos
├── config/
│   ├── config.yaml            # Main configuration
│   └── client_secrets.json    # YouTube OAuth credentials
├── CLAUDE.md                  # Development documentation
└── restart_enhanced.bat       # Quick restart script
```

## 🔑 Configuration

### Environment Variables
Create a `.env` file in the root directory:

```env
# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=AI-Slop/1.0

# Stock Media
PEXELS_API_KEY=your_pexels_key
PIXABAY_API_KEY=your_pixabay_key  # Optional

# ElevenLabs TTS (Optional - for premium voices)
ELEVENLABS_API_KEY=your_elevenlabs_key

# LLM APIs (Optional - for automated script generation)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key
```

### YouTube OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable YouTube Data API v3
4. Create OAuth 2.0 credentials (Desktop application)
5. Download credentials as `config/client_secrets.json`

## 🎥 Output

Videos are saved to `data/out/production_*/` with:
- Full-length video (MP4)
- Audio narration (MP3/WAV)
- Stock footage clips
- Thumbnail image
- Metadata JSON files

## 🐛 Troubleshooting

### Common Issues

1. **"Failed to copy to clipboard"**: Browser security warning - text still copies successfully
2. **No audio in video**: Ensure FFmpeg is properly installed
3. **Google TTS not working**: Install dependencies: `pip install gtts pyttsx3`
4. **Custom voice not working**: Make sure to enter the exact ElevenLabs voice name
5. **YouTube upload fails**: Re-run `python setup_youtube.py` to refresh OAuth token

### Requirements

- FFmpeg must be installed: `ffmpeg -version`
- Python 3.8+: `python --version`
- Sufficient API credits for TTS and stock media

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🚨 Disclaimer

This tool is for educational purposes. Ensure you comply with:
- YouTube's Terms of Service
- Copyright laws regarding content usage
- API usage terms for all integrated services
- Reddit's content policy

## 🙏 Acknowledgments

- Reddit PRAW for Reddit API access
- ElevenLabs for TTS
- Pexels/Pixabay for stock footage
- FFmpeg for video processing

## 📊 Status

**Current Version**: v1.2.7 (Fully Operational)

### Recent Updates (August 28, 2025)
- ✅ **Google TTS Integration**: FREE text-to-speech alternative
- ✅ **Fixed Custom Voice**: ElevenLabs custom voices working
- ✅ **Fixed Video Duration**: Proper full-length videos
- ✅ **YouTube Upload**: Real-time progress tracking
- ✅ **JSON Error Recovery**: Auto-fixes LLM output
- ✅ **Video Preview**: In-browser video player
- ✅ **Enhanced UI**: Modern, responsive interface

## 🎙️ Voice Options

### Google TTS (FREE)
- Documentary (UK English)
- News (US English)
- Storytelling (Australian)
- Tutorial (US English)
- Mystery (UK English, Slow)
- Energetic (US English)
- Calm (Canadian, Slow)

### ElevenLabs (Premium)
- Documentary (Adam)
- News (Rachel)
- Storytelling (Josh)
- Tutorial (Domi)
- Mystery (Arnold)
- Energetic (Bella)
- Calm (Antoni)
- Custom Voice Support

## 💡 Future Enhancements

- [ ] Automated scheduling
- [ ] Multi-language support
- [ ] Analytics dashboard
- [ ] Batch processing
- [ ] A/B thumbnail testing

---

**Note**: This project uses real API services that may incur costs. Monitor your usage carefully.