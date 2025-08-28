# AI-Slop Quick Setup Guide

## 🚀 5-Minute Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg
- **Windows**: Download from https://ffmpeg.org/download.html and add to PATH
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg`

### 3. Get API Keys

#### Required (Minimum to Start)
1. **Reddit API** (Free)
   - Go to https://www.reddit.com/prefs/apps
   - Click "Create App" → Script
   - Note your Client ID and Secret

2. **Pexels API** (Free)
   - Sign up at https://www.pexels.com/api/
   - Get your API key

#### Optional (For Full Features)
- **ElevenLabs**: For premium voices (https://elevenlabs.io)
- **YouTube OAuth**: For upload feature (see YouTube Setup below)

### 4. Configure Environment
Create `.env` file in root directory:
```env
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=AI-Slop/1.0
PEXELS_API_KEY=your_pexels_key

# Optional
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### 5. Start the Application
```bash
# Windows
restart_enhanced.bat

# Or directly
python app_enhanced.py
```

Open http://localhost:5000 in your browser

## 📺 YouTube Upload Setup (Optional)

### 1. Enable YouTube API
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Enable "YouTube Data API v3"

### 2. Create OAuth Credentials
1. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
2. Choose "Desktop app"
3. Download JSON file
4. Save as `config/client_secrets.json`

### 3. Authorize
```bash
python setup_youtube.py
```
Follow the browser prompts to authorize

## 🎬 Creating Your First Video

1. **Open Web UI**: http://localhost:5000
2. **Fetch Reddit Post**: Click "Fetch Post" to get content
3. **Generate Script**: 
   - Click "Copy Prompt for LLM"
   - Paste into ChatGPT/Claude
   - Copy the JSON response back
4. **Select Voice**: 
   - Choose "Google TTS (Free)" to start
   - Or use ElevenLabs if you have credits
5. **Process Script**: Click to prepare the script
6. **Generate Video**: Click to create the full video
7. **Preview**: Watch your video in the browser
8. **Upload**: Click "Upload to YouTube" when ready

## 🆘 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| No audio in video | Check FFmpeg installation: `ffmpeg -version` |
| Google TTS not working | Run: `pip install gtts pyttsx3` |
| Can't fetch Reddit posts | Check Reddit API credentials in `.env` |
| No stock videos | Verify Pexels API key |
| Upload fails | Re-run `python setup_youtube.py` |

## 📝 Tips for Best Results

1. **Script Generation**: Use Claude or GPT-4 for best scripts
2. **Voice Selection**: 
   - Start with Google TTS (free)
   - Documentary voice works well for most content
3. **Video Length**: Aim for 8-10 minute scripts (1200-1500 words)
4. **Keywords**: Include diverse keywords for varied stock footage

## 🎯 Next Steps

- Read [CLAUDE.md](CLAUDE.md) for advanced configuration
- Check [README.md](README.md) for full feature list
- Join discussions in GitHub Issues

---

**Need Help?** Create an issue at https://github.com/wyvernkalyx/ai-slop/issues