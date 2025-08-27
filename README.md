# AI-Slop 🎬

An automated YouTube video generation pipeline that creates faceless videos from trending Reddit content using AI.

## 🚀 Features

- **Reddit Content Ingestion**: Automatically fetches trending posts from Reddit
- **AI Script Generation**: Converts Reddit posts into engaging video scripts
- **Text-to-Speech**: Generates natural narration using ElevenLabs API
- **Stock Footage**: Downloads relevant B-roll from Pexels/Pixabay
- **Video Assembly**: Combines audio and video into complete YouTube videos
- **Thumbnail Generation**: Auto-generates video thumbnails
- **Web Interface**: User-friendly UI for manual control and monitoring

## 📋 Prerequisites

- Python 3.8+
- FFmpeg installed and in PATH
- API Keys for:
  - Reddit API
  - ElevenLabs (for TTS)
  - Pexels/Pixabay (for stock footage)
  - OpenAI (optional, for script generation)

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

### Production Pipeline (Real APIs)
```bash
python production_simple.py
```

This will:
1. Load a script (or generate one if OpenAI is configured)
2. Generate narration with ElevenLabs
3. Download stock footage from Pexels
4. Assemble everything into a complete video

### Web Interface
```bash
python app_fixed_async.py
```
Then open http://localhost:5001 in your browser.

## 📁 Project Structure

```
AI-Slop/
├── src/
│   ├── modules/
│   │   ├── ingest_reddit.py    # Reddit content fetching
│   │   ├── classify.py         # Content classification
│   │   ├── script_gen.py       # Script generation
│   │   ├── tts.py             # Text-to-speech
│   │   ├── media_picker.py     # Stock footage selection
│   │   ├── assemble_ffmpeg.py  # Video assembly
│   │   └── thumbnail.py        # Thumbnail generation
│   └── utils/
│       ├── config.py           # Configuration management
│       └── logger.py           # Logging utilities
├── data/
│   └── out/                   # Generated videos
├── config/
│   └── .env                   # API keys (not in repo)
├── production_simple.py        # Production pipeline script
└── app_fixed_async.py         # Web interface
```

## 🔑 Configuration

Create a `config/.env` file with your API keys:

```env
# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=AI-Slop/1.0

# ElevenLabs TTS
ELEVENLABS_API_KEY=your_elevenlabs_key

# Stock Media
PEXELS_API_KEY=your_pexels_key
PIXABAY_API_KEY=your_pixabay_key

# OpenAI (optional)
OPENAI_API_KEY=your_openai_key
```

## 🎥 Output

Videos are saved to `data/out/production_*/` with:
- Full-length video (MP4)
- Audio narration (MP3/WAV)
- Stock footage clips
- Thumbnail image
- Metadata JSON files

## 🐛 Troubleshooting

### Common Issues

1. **No audio in video**: Ensure FFmpeg is properly installed
2. **API quota errors**: Check your API credits/limits
3. **Video duration issues**: Fixed in latest version (v1.1)

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

**Current Version**: 1.1.0 (Production Ready)

### Recent Updates (Aug 27, 2025)
- ✅ Fixed video assembly duration issues
- ✅ Fixed audio integration problems  
- ✅ Production pipeline fully operational
- ✅ Successfully generates 7+ minute videos with narration

## 💡 Future Enhancements

- [ ] YouTube upload automation
- [ ] Multi-language support
- [ ] Advanced voice cloning
- [ ] Automated scheduling
- [ ] Analytics dashboard

---

**Note**: This project uses real API services that may incur costs. Monitor your usage carefully.