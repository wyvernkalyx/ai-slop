"""
Enhanced Flask app with voice selection, subreddit options, and YouTube upload control
"""

from flask import Flask, request, jsonify, send_file, Response
import json
import os
import sys
import praw
import random
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.modules.tts_real import ElevenLabsTTS
from src.modules.tts_google import GoogleTTS
from src.modules.assemble_enhanced import EnhancedVideoAssembler
from src.modules.thumbnail_enhanced import EnhancedThumbnailGenerator
from src.modules.upload_youtube import YouTubeUploader
from src.modules.media_picker import MediaPicker
from src.utils.config import get_config
from src.utils.json_fixer import JSONFixer

app = Flask(__name__)

# Load environment variables
load_dotenv('config/.env')
config = get_config()

# Global cache for posts
cached_posts = {}  # Keyed by subreddit
cache_timestamps = {}

# Available voice presets
VOICE_PRESETS = {
    'documentary': {'name': 'Documentary (Daniel)', 'voice': 'daniel', 'description': 'Authoritative and informative'},
    'news': {'name': 'News (Rachel)', 'voice': 'rachel', 'description': 'Clear and professional'},
    'storytelling': {'name': 'Storytelling (Charlie)', 'voice': 'charlie', 'description': 'Engaging and expressive'},
    'tutorial': {'name': 'Tutorial (Jessica)', 'voice': 'jessica', 'description': 'Friendly and clear'},
    'mystery': {'name': 'Mystery (Clyde)', 'voice': 'clyde', 'description': 'Dramatic and suspenseful'},
    'energetic': {'name': 'Energetic (Sarah)', 'voice': 'sarah', 'description': 'Upbeat and enthusiastic'},
    'calm': {'name': 'Calm (George)', 'voice': 'george', 'description': 'Soothing and measured'}
}

# Popular subreddits for content
SUBREDDITS = {
    'all': ['todayilearned', 'explainlikeimfive', 'science', 'technology', 'worldnews', 'interestingasfuck'],
    'todayilearned': ['todayilearned'],
    'explainlikeimfive': ['explainlikeimfive'],
    'science': ['science'],
    'technology': ['technology'],
    'worldnews': ['worldnews'],
    'interestingasfuck': ['interestingasfuck'],
    'askreddit': ['AskReddit'],
    'showerthoughts': ['Showerthoughts'],
    'lifeprotips': ['LifeProTips'],
    'dataisbeautiful': ['dataisbeautiful']
}

def get_reddit_posts(subreddit_key='all'):
    """Fetch Reddit posts from selected subreddit(s)"""
    global cached_posts, cache_timestamps
    
    # Check cache (5 minute expiry)
    if subreddit_key in cached_posts and subreddit_key in cache_timestamps:
        if (datetime.now() - cache_timestamps[subreddit_key]).seconds < 300:
            print(f"Using cached Reddit posts for {subreddit_key}")
            return cached_posts[subreddit_key]
    
    try:
        # Initialize Reddit
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'AI-Slop/1.0')
        )
        
        posts = []
        subreddits = SUBREDDITS.get(subreddit_key, SUBREDDITS['all'])
        
        for sub_name in subreddits:
            try:
                print(f"Fetching from r/{sub_name}...")
                subreddit = reddit.subreddit(sub_name)
                
                # Get hot posts
                for post in subreddit.hot(limit=5):
                    if len(post.title) > 20 and not post.over_18:  # Filter NSFW
                        posts.append({
                            'id': post.id,
                            'title': post.title,
                            'selftext': post.selftext[:500] if post.selftext else f"Link post from r/{sub_name}",
                            'url': post.url,
                            'subreddit': post.subreddit.display_name,
                            'author': str(post.author) if post.author else 'deleted',
                            'score': post.score,
                            'num_comments': post.num_comments,
                            'created_utc': post.created_utc
                        })
            except Exception as e:
                print(f"Error fetching from r/{sub_name}: {e}")
                continue
        
        if posts:
            # Update cache
            cached_posts[subreddit_key] = posts
            cache_timestamps[subreddit_key] = datetime.now()
            print(f"Cached {len(posts)} posts from Reddit")
        
        return posts
        
    except Exception as e:
        print(f"Reddit API error: {e}")
        return []

@app.route('/')
def index():
    """Serve the enhanced HTML UI with no-cache headers"""
    with open('ui_enhanced.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    response = Response(html_content)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/fetch-reddit', methods=['POST'])
def fetch_reddit():
    """Fetch a random Reddit post from selected subreddit"""
    try:
        data = request.json
        subreddit = data.get('subreddit', 'all')
        
        posts = get_reddit_posts(subreddit)
        
        if not posts:
            return jsonify({
                'title': 'Amazing Discovery: Scientists Find New Species',
                'selftext': 'Researchers have discovered a new species of deep-sea fish that glows in the dark. This remarkable creature was found at depths of over 3000 meters in the Pacific Ocean.',
                'url': 'https://reddit.com/fallback',
                'subreddit': 'science'
            })
        
        # Return a random post
        post = random.choice(posts)
        return jsonify(post)
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-script', methods=['POST'])
def generate_script():
    """Generate script from Reddit post (saves it for video generation)"""
    try:
        data = request.json
        reddit_title = data.get('title', '')
        reddit_text = data.get('selftext', '')
        reddit_url = data.get('url', '')
        subreddit = data.get('subreddit', 'unknown')
        custom_script = data.get('customScript', '')
        voice_preset = data.get('voicePreset', 'documentary')
        tts_provider = data.get('ttsProvider', 'elevenlabs')
        
        # Validate voice preset
        if voice_preset == 'custom':
            # Check if a custom voice name was provided
            custom_voice_name = data.get('customVoiceName', '')
            if not custom_voice_name:
                return jsonify({
                    'error': 'Custom voice selected but no voice name provided. Please either select a preset voice or enter a custom voice name.'
                }), 400
            # Use the custom voice name instead of 'custom'
            voice_preset = custom_voice_name
            print(f"Using custom voice for script: {voice_preset}")
        
        # Prepare script content
        if custom_script:
            # Try to parse as JSON using the JSON fixer
            print(f"Attempting to parse script (length: {len(custom_script)} chars)")
            
            # Use JSONFixer to handle common LLM JSON errors
            parsed_json = JSONFixer.parse_with_fixes(custom_script)
            
            if parsed_json and 'narration' in parsed_json:
                # Successfully parsed as JSON
                script = parsed_json
                
                # Ensure required fields exist
                if 'version' not in script:
                    script['version'] = 'script.v1'
                if 'title' not in script:
                    script['title'] = reddit_title[:100]
                if 'source_url' not in script:
                    script['source_url'] = reddit_url
                    
                # Validate the script structure
                if not JSONFixer.validate_script(script):
                    print("Warning: Script validation failed, using fallback structure")
                    # Create a basic structure from what we have
                    script = {
                        "version": "script.v1",
                        "title": parsed_json.get('title', reddit_title[:100]),
                        "hook": parsed_json.get('hook', ''),
                        "narration": {
                            "intro": parsed_json.get('narration', {}).get('intro', ''),
                            "chapters": parsed_json.get('narration', {}).get('chapters', []),
                            "outro": parsed_json.get('narration', {}).get('outro', 'Thanks for watching!')
                        },
                        "broll_keywords": parsed_json.get('broll_keywords', extract_keywords(str(parsed_json))),
                        "source_url": reddit_url
                    }
                
                print(f"Using JSON script format with {len(script.get('broll_keywords', []))} keywords")
                print(f"Script has {len(script.get('narration', {}).get('chapters', []))} chapters")
                
            else:
                # Failed to parse as JSON or no narration field - treat as plain text
                print("Could not parse as JSON, treating as plain text script")
                script = {
                    "version": "script.v1",
                    "title": reddit_title[:100],
                    "hook": custom_script[:150],
                    "narration": {
                        "intro": custom_script[:200] if len(custom_script) > 200 else custom_script,
                        "chapters": [],
                        "outro": "Thanks for watching! Don't forget to subscribe for more content."
                    },
                    "broll_keywords": extract_keywords(custom_script),
                    "source_url": reddit_url
                }
        else:
            # Basic template - NOT using LLM, just a simple template
            print("WARNING: No custom script provided, using basic template")
            script = {
                "version": "script.v1",
                "title": reddit_title[:100],
                "hook": f"Today we're exploring an interesting post from r/{subreddit}.",
                "narration": {
                    "intro": f"Today we're exploring an interesting post from r/{subreddit}. {reddit_title}",
                    "chapters": [],
                    "outro": "Thanks for watching! Don't forget to subscribe for more content."
                },
                "broll_keywords": ["reddit", "social media", "technology", "internet", "community"],
                "source_url": reddit_url
            }
        
        # Create job directory with shorter ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Extract a shorter ID from the URL or use custom
        if reddit_url:
            # Try to extract the Reddit post ID (usually 6-7 characters)
            url_parts = reddit_url.split('/')
            reddit_id = None
            for part in url_parts:
                # Reddit IDs are typically 5-10 alphanumeric characters
                if part and len(part) <= 10 and part.replace('_', '').isalnum():
                    reddit_id = part[:10]  # Limit to 10 chars
                    break
            if not reddit_id:
                # Fallback: use first 8 chars of title
                reddit_id = ''.join(c for c in reddit_title[:8] if c.isalnum())
        else:
            reddit_id = 'custom'
        
        # Ensure job_id isn't too long
        job_id = f"web_{reddit_id}_{timestamp}"
        output_dir = Path('data/out') / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Add metadata to script
        script['id'] = job_id
        script['voice_preset'] = voice_preset
        script['tts_provider'] = tts_provider
        script['post_id'] = reddit_id
        script['source_url'] = reddit_url
        script['timestamp'] = timestamp
        
        # Save script
        script_path = output_dir / f'script_{job_id}.json'
        with open(script_path, 'w') as f:
            json.dump(script, f, indent=2)
        
        # Save Reddit post data
        reddit_data = {
            'title': reddit_title,
            'selftext': reddit_text,
            'url': reddit_url,
            'subreddit': subreddit,
            'fetched_at': datetime.now().isoformat()
        }
        
        reddit_path = output_dir / f'reddit_post_{job_id}.json'
        with open(reddit_path, 'w') as f:
            json.dump(reddit_data, f, indent=2)
        
        # Create display text for UI
        display_text = f"Title: {script.get('title', 'Untitled')}\n\n"
        if script.get('hook'):
            display_text += f"Hook: {script['hook']}\n\n"
        display_text += f"Intro: {script['narration'].get('intro', '')}\n\n"
        for chapter in script['narration'].get('chapters', []):
            display_text += f"Chapter {chapter.get('id', '')}: {chapter.get('heading', '')}\n{chapter.get('body', '')}\n\n"
        display_text += f"Outro: {script['narration'].get('outro', '')}\n\n"
        display_text += f"Keywords: {', '.join(script.get('broll_keywords', []))}"
        
        # Count actual narration words
        word_count = len(script['narration'].get('intro', '').split())
        for chapter in script['narration'].get('chapters', []):
            word_count += len(chapter.get('body', '').split())
        word_count += len(script['narration'].get('outro', '').split())
        
        print(f"Word count breakdown:")
        print(f"  Intro: {len(script['narration'].get('intro', '').split())} words")
        print(f"  Chapters: {len(script['narration'].get('chapters', []))} chapters")
        for i, chapter in enumerate(script['narration'].get('chapters', [])):
            print(f"    Chapter {i+1}: {len(chapter.get('body', '').split())} words")
        print(f"  Outro: {len(script['narration'].get('outro', '').split())} words")
        print(f"  Total: {word_count} words")
        
        return jsonify({
            'success': True,
            'script': display_text,
            'job_id': job_id,
            'voice_preset': VOICE_PRESETS.get(voice_preset, {'name': f'Custom: {voice_preset}'})['name'],
            'word_count': word_count,
            'has_chapters': len(script['narration'].get('chapters', [])) > 0
        })
        
    except Exception as e:
        print(f"Error generating script: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    """Generate full video with voice options"""
    try:
        data = request.json
        print(f"[DEBUG] Received request data: {data}")
        
        job_id = data.get('job_id')
        voice_preset = data.get('voicePreset', 'documentary')
        tts_provider = data.get('ttsProvider', 'elevenlabs')
        include_intro = data.get('includeIntro', True)
        include_outro = data.get('includeOutro', True)
        
        print(f"[DEBUG] TTS Provider: '{tts_provider}'")
        print(f"[DEBUG] Voice preset received: '{voice_preset}'")
        print(f"[DEBUG] Voice preset type: {type(voice_preset)}")
        print(f"[DEBUG] Voice preset length: {len(str(voice_preset))}")
        
        if not job_id:
            return jsonify({'error': 'No job ID provided'}), 400
        
        output_dir = Path('data/out') / job_id
        script_path = output_dir / f'script_{job_id}.json'
        
        if not script_path.exists():
            return jsonify({'error': 'Script not found'}), 404
        
        # Load script
        with open(script_path) as f:
            script = json.load(f)
        
        # Step 1: Generate Audio with selected voice and provider
        print(f"Generating audio with '{voice_preset}' voice using {tts_provider}...")
        
        # Initialize TTS based on provider
        if tts_provider == 'google':
            print("Using Google TTS (free)")
            tts = GoogleTTS()
        else:
            # Default to ElevenLabs
            api_key = os.getenv('ELEVENLABS_API_KEY')
            if not api_key:
                print("Warning: No ElevenLabs API key, falling back to Google TTS")
                tts = GoogleTTS()
                tts_provider = 'google'
            else:
                tts = ElevenLabsTTS(api_key)
        
        # Combine all text
        full_text = script['narration']['intro']
        for chapter in script['narration'].get('chapters', []):
            full_text += f" {chapter.get('body', '')}"
        full_text += f" {script['narration']['outro']}"
        
        # Enhanced voice validation and debugging
        print(f"[VOICE DEBUG] Raw voice_preset value: '{voice_preset}'")
        print(f"[VOICE DEBUG] Voice preset repr: {repr(voice_preset)}")
        print(f"[VOICE DEBUG] Is 'custom' string: {voice_preset == 'custom'}")
        print(f"[VOICE DEBUG] Full request data keys: {list(data.keys())}")
        
        # Handle custom voice selection
        if voice_preset == 'custom':
            # Get the custom voice name from the dedicated field
            custom_voice_name = data.get('customVoiceName', '')
            print(f"[VOICE DEBUG] Custom voice name received: '{custom_voice_name}'")
            
            if custom_voice_name:
                voice_preset = custom_voice_name
                print(f"[SUCCESS] Using custom voice: {voice_preset}")
            else:
                # Fallback: try other possible field names
                possible_fields = ['custom_voice', 'voiceName', 'voice']
                for field in possible_fields:
                    if field in data and data[field]:
                        print(f"[RECOVERY] Found voice in field '{field}': {data[field]}")
                        voice_preset = data[field]
                        break
                else:
                    return jsonify({'error': 'Custom voice name not received. Please ensure you entered a voice name (e.g., Gregg) in the custom voice field.'}), 400
        
        if voice_preset == '' or voice_preset is None:
            print(f"ERROR: Empty voice value received")
            print(f"[DEBUG] Full request: {json.dumps(data, indent=2)}")
            return jsonify({'error': 'Please select a voice preset or enter a custom voice name'}), 400
        
        print(f"[DEBUG] Processing with voice/preset: '{voice_preset}'")
        
        # Generate audio with selected preset
        try:
            if tts_provider == 'google':
                # Google TTS uses different method name
                audio_path, duration = tts.generate_speech(
                    text=full_text,
                    voice=voice_preset,
                    output_path=str(output_dir / f"audio_{job_id}")
                )
                # Convert string path to Path object
                audio_path = Path(audio_path)
            else:
                # ElevenLabs TTS
                audio_path, duration = tts.generate_audio_with_preset(
                    text=full_text,
                    output_path=output_dir / f"audio_{job_id}",
                    preset=voice_preset
                )
                # Ensure it's a Path object
                if not isinstance(audio_path, Path):
                    audio_path = Path(audio_path)
        except Exception as e:
            print(f"Audio generation error: {e}")
            return jsonify({'error': f'Audio generation failed: {str(e)}'}), 500
        
        # Step 2: Download Stock Videos
        print(f"Downloading stock footage for {duration:.1f} seconds of content...")
        keywords = script.get('broll_keywords', ['technology', 'science', 'innovation', 'future', 'discovery'])
        
        # For 6-7 minute videos, we need more clips
        clip_count = max(25, int(duration / 15))  # Roughly one new clip every 15 seconds
        
        clips = download_stock_videos(
            keywords=keywords,
            output_dir=output_dir / 'clips',
            count=clip_count
        )
        
        print(f"Downloaded {len(clips)} clips for {duration:.1f}s video")
        
        if not clips:
            print("ERROR: No stock videos downloaded!")
            return jsonify({
                'success': False,
                'error': 'Failed to download stock videos. Check Pexels API key.'
            }), 500
        
        # Step 3: Generate Thumbnail
        print("Generating enhanced thumbnail...")
        thumbnail_gen = EnhancedThumbnailGenerator()
        thumbnail_path = thumbnail_gen.generate(
            text=script.get('title', 'Amazing Video'),
            output_dir=output_dir,
            job_id=job_id,
            use_stock_bg=True  # Use stock image background
        )
        
        # Step 4: Assemble Video with intro/outro
        print(f"Assembling video (intro: {include_intro}, outro: {include_outro})...")
        assembler = EnhancedVideoAssembler()
        video_path = assembler.assemble_with_bookends(
            audio_file=audio_path,
            clips=clips,
            output_dir=output_dir,
            include_intro=include_intro,
            include_outro=include_outro
        )
        
        if not video_path:
            print("ERROR: Video assembly failed - assembler returned None")
            return jsonify({
                'success': False,
                'error': 'Video assembly failed. Check logs for details.'
            }), 500
        
        # Save video metadata
        video_metadata = {
            'video_file': str(video_path),
            'duration': duration,
            'voice_preset': voice_preset,
            'intro_included': include_intro,
            'outro_included': include_outro,
            'generated_at': datetime.now().isoformat()
        }
        
        metadata_path = output_dir / 'video_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(video_metadata, f, indent=2)
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'video_path': str(video_path),
            'thumbnail_path': str(thumbnail_path),
            'duration': duration,
            'voice_used': VOICE_PRESETS.get(voice_preset, {'name': f'Custom: {voice_preset}'})['name']
        })
        
    except Exception as e:
        print(f"Error generating video: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview-video/<job_id>')
def preview_video(job_id):
    """Get video preview information"""
    try:
        output_dir = Path('data/out') / job_id
        video_files = list(output_dir.glob('video_*.mp4'))
        
        if not video_files:
            return jsonify({'error': 'Video not found'}), 404
        
        video_path = video_files[0]
        thumbnail_files = list(output_dir.glob('thumbnail_*.jpg'))
        
        # Get video info
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size',
             '-of', 'json', str(video_path)],
            capture_output=True, text=True
        )
        
        video_info = {}
        if result.returncode == 0:
            info = json.loads(result.stdout)
            video_info = {
                'duration': float(info['format']['duration']),
                'size_mb': float(info['format']['size']) / (1024 * 1024)
            }
        
        return jsonify({
            'success': True,
            'video_path': str(video_path),
            'thumbnail_path': str(thumbnail_files[0]) if thumbnail_files else None,
            'video_info': video_info
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview-video/<job_id>/stream')
def stream_video(job_id):
    """Stream video file for preview"""
    try:
        output_dir = Path('data/out') / job_id
        video_files = list(output_dir.glob('video_*.mp4'))
        
        if not video_files:
            return jsonify({'error': 'Video not found'}), 404
        
        video_path = video_files[0]
        
        # Use Flask's send_file for streaming
        from flask import send_file
        return send_file(
            str(video_path),
            mimetype='video/mp4',
            as_attachment=False,
            download_name=f'preview_{job_id}.mp4'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Store upload progress for each job
upload_progress = {}

@app.route('/api/upload-youtube', methods=['POST'])
def upload_to_youtube():
    """Upload video to YouTube with approval"""
    try:
        print(f"YouTube upload requested for job: {request.json}")
        data = request.json
        job_id = data.get('job_id')
        privacy_status = data.get('privacy', 'private')
        print(f"Upload requested - Job ID: {job_id}, Privacy: {privacy_status}")
        
        # Initialize progress tracking
        upload_progress[job_id] = {'progress': 0, 'status': 'starting'}
        
        output_dir = Path('data/out') / job_id
        video_files = list(output_dir.glob('video_*.mp4'))
        
        if not video_files:
            return jsonify({'error': 'Video not found'}), 404
        
        video_path = video_files[0]
        thumbnail_files = list(output_dir.glob('thumbnail_*.jpg'))
        
        # Load script for metadata
        script_files = list(output_dir.glob('script_*.json'))
        if script_files:
            with open(script_files[0]) as f:
                script = json.load(f)
        else:
            return jsonify({'error': 'Script not found'}), 404
        
        # Initialize uploader with correct credentials file
        # Try multiple possible credential file locations
        credentials_files = [
            'config/client_secrets.json',
            'config/youtube_credentials.json'
        ]
        
        uploader = None
        for cred_file in credentials_files:
            if Path(cred_file).exists():
                print(f"Using credentials file: {cred_file}")
                uploader = YouTubeUploader(cred_file)
                break
        
        if not uploader:
            return jsonify({'error': 'YouTube credentials not found'}), 404
        
        if not uploader.authenticate():
            return jsonify({'error': 'YouTube authentication failed'}), 401
        
        # Prepare metadata
        title = script['title'][:100]
        description = f"{script['title']}\n\n"
        description += script['narration']['intro'] + "\n\n"
        description += f"Created with AI-Slop on {datetime.now().strftime('%Y-%m-%d')}\n\n"
        description += f"Source: {script.get('source_url', 'Reddit')}\n\n"
        description += "#AI #Automated #YouTube"
        
        tags = script.get('broll_keywords', [])[:10] + ['AI', 'automated', 'reddit']
        
        # Progress callback function
        def update_progress(progress):
            upload_progress[job_id] = {'progress': progress, 'status': 'uploading'}
            print(f"Upload progress for {job_id}: {progress}%")
        
        # Upload with progress tracking
        upload_progress[job_id] = {'progress': 0, 'status': 'uploading'}
        video_id = uploader.upload_video(
            video_file=video_path,
            title=title,
            description=description,
            tags=tags,
            category_id="27",  # Education
            privacy_status=privacy_status,
            thumbnail_file=thumbnail_files[0] if thumbnail_files else None,
            progress_callback=update_progress
        )
        
        if video_id:
            # Mark upload as complete
            upload_progress[job_id] = {'progress': 100, 'status': 'complete', 'video_id': video_id}
            
            # Try to get channel URL
            channel_url = None
            try:
                channel_info = uploader.get_channel_info()
                if channel_info and 'id' in channel_info:
                    channel_url = f"https://www.youtube.com/channel/{channel_info['id']}"
            except:
                pass
            
            return jsonify({
                'success': True,
                'video_id': video_id,
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'channel_url': channel_url,
                'privacy': privacy_status
            })
        else:
            upload_progress[job_id] = {'progress': 0, 'status': 'failed'}
            return jsonify({'error': 'Upload failed'}), 500
            
    except Exception as e:
        print(f"Error uploading to YouTube: {e}")
        if job_id in upload_progress:
            upload_progress[job_id] = {'progress': 0, 'status': 'error', 'error': str(e)}
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-progress/<job_id>')
def get_upload_progress(job_id):
    """Get upload progress for a specific job"""
    progress = upload_progress.get(job_id, {'progress': 0, 'status': 'unknown'})
    return jsonify(progress)

@app.route('/api/get-options')
def get_options():
    """Get available voice and subreddit options"""
    return jsonify({
        'voices': VOICE_PRESETS,
        'subreddits': list(SUBREDDITS.keys())
    })

def extract_keywords(text):
    """Extract keywords from text for stock video search"""
    # Simple keyword extraction
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
    words = text.lower().split()
    keywords = []
    
    for word in words:
        word = word.strip('.,!?";:')
        if len(word) > 4 and word not in stop_words and word not in keywords:
            keywords.append(word)
    
    # Add some generic keywords
    keywords.extend(['technology', 'science', 'discovery'])
    
    return keywords[:10]

def download_stock_videos(keywords, output_dir, count=15):
    """Download stock VIDEOS (with motion) from Pexels"""
    import requests
    
    clips = []
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    pexels_key = os.getenv('PEXELS_API_KEY')
    if not pexels_key:
        print("Warning: No Pexels API key - cannot download stock videos")
        return []
    
    headers = {'Authorization': pexels_key}
    
    # Add motion-focused keywords
    motion_keywords = []
    for kw in keywords[:5]:
        motion_keywords.append(kw)
        # Add motion variants
        if 'animation' not in kw.lower():
            motion_keywords.append(f"{kw} motion")
    
    print(f"Searching for stock videos with keywords: {motion_keywords[:8]}")
    
    for keyword in motion_keywords[:8]:  # Try more keywords
        if len(clips) >= count:
            break
            
        try:
            url = 'https://api.pexels.com/videos/search'
            params = {
                'query': keyword,
                'per_page': 5,  # Get more options
                'size': 'medium',
                'orientation': 'landscape'
            }
            
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                
                videos = data.get('videos', [])
                print(f"  Found {len(videos)} videos for '{keyword}'")
                
                for video in videos[:3]:  # Try more videos per keyword
                    if len(clips) >= count:
                        break
                    
                    # Get video info
                    duration = video.get('duration', 0)
                    video_files = video.get('video_files', [])
                    
                    # Prefer HD videos with reasonable duration (5-30 seconds)
                    hd_files = [f for f in video_files if f.get('quality') == 'hd']
                    if not hd_files:
                        hd_files = [f for f in video_files if f.get('quality') == 'sd']
                    
                    if hd_files and duration >= 5:
                        # Sort by width (resolution) to get best quality
                        hd_files.sort(key=lambda x: x.get('width', 0), reverse=True)
                        file_info = hd_files[0]
                        file_url = file_info['link']
                        
                        file_name = f"clip_{len(clips):03d}_{keyword.replace(' ', '_')[:20]}.mp4"
                        file_path = output_dir / file_name
                        
                        print(f"  Downloading: {file_name} ({duration}s, {file_info.get('width')}x{file_info.get('height')})")
                        
                        try:
                            video_response = requests.get(file_url, stream=True, timeout=30)
                            with open(file_path, 'wb') as f:
                                for chunk in video_response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            
                            clips.append(file_path)
                        except Exception as download_error:
                            print(f"  Failed to download: {download_error}")
                            continue
        except Exception as e:
            print(f"Error downloading {keyword}: {e}")
            continue
    
    print(f"\nDownloaded {len(clips)} video clips total")
    if clips:
        total_size = sum(clip.stat().st_size for clip in clips) / (1024 * 1024)
        print(f"Total size: {total_size:.1f} MB")
    
    return clips

if __name__ == '__main__':
    print("=" * 60)
    print("AI-Slop Enhanced Web Interface")
    print("=" * 60)
    print("Starting server at: http://localhost:5000")
    print("\nFeatures:")
    print("- Voice selection (7 presets)")
    print("- Subreddit selector")
    print("- Intro/Outro control")
    print("- YouTube upload with approval")
    print("-" * 60)
    
    app.run(debug=True, port=5000)