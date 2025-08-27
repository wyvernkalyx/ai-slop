"""
Fixed Flask app with proper async handling - non-blocking pipeline execution
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime
import threading
import time
import os

app = Flask(__name__)
CORS(app)

# Global storage for job status
job_status = {}
job_threads = {}

def run_pipeline_background(job_id, script_data, post_data, output_dir):
    """Run pipeline in background thread"""
    try:
        job_status[job_id] = {
            'status': 'running',
            'started': datetime.now().isoformat(),
            'message': 'Pipeline is processing your video...'
        }
        
        # Save the script first (IMPORTANT: this must happen before pipeline runs)
        script_path = output_dir / f"script_{post_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(script_path, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)
            
        # Save Reddit post
        post_path = output_dir / f"reddit_post_{post_data['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json" 
        with open(post_path, 'w', encoding='utf-8') as f:
            json.dump(post_data, f, indent=2, ensure_ascii=False)
        
        # Run pipeline
        cmd = [sys.executable, 'src/pipeline.py', '--job-id', job_id]
        
        print(f"[BACKGROUND] Starting pipeline: {job_id}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=900  # 15 minutes max
        )
        
        if result.returncode == 0:
            # Find output files
            video_files = list(output_dir.glob('video_*.mp4'))
            audio_files = list(output_dir.glob('audio_*.wav'))
            thumbnail_files = list(output_dir.glob('thumbnail_*.jpg'))
            
            # Calculate actual duration from audio
            duration_minutes = 0
            if audio_files:
                try:
                    audio_path = audio_files[0]
                    # Get duration using ffprobe
                    probe = subprocess.run(
                        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                         '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    duration_seconds = float(probe.stdout.strip())
                    duration_minutes = duration_seconds / 60
                except:
                    duration_minutes = 0
            
            job_status[job_id] = {
                'status': 'completed',
                'completed': datetime.now().isoformat(),
                'video_file': str(video_files[0]) if video_files else None,
                'audio_file': str(audio_files[0]) if audio_files else None,
                'thumbnail_file': str(thumbnail_files[0]) if thumbnail_files else None,
                'duration_minutes': round(duration_minutes, 1),
                'output_dir': str(output_dir),
                'message': f'Video completed! Duration: {duration_minutes:.1f} minutes'
            }
            print(f"[BACKGROUND] Completed: {job_id}")
        else:
            job_status[job_id] = {
                'status': 'failed',
                'completed': datetime.now().isoformat(),
                'error': result.stderr[-1000:] if result.stderr else 'Unknown error',
                'message': 'Pipeline failed - check logs'
            }
            print(f"[BACKGROUND] Failed: {job_id}")
            
    except subprocess.TimeoutExpired:
        job_status[job_id] = {
            'status': 'timeout',
            'completed': datetime.now().isoformat(),
            'error': 'Processing took too long',
            'message': 'Pipeline timed out after 15 minutes'
        }
    except Exception as e:
        job_status[job_id] = {
            'status': 'error',
            'completed': datetime.now().isoformat(),
            'error': str(e),
            'message': f'Error: {str(e)}'
        }

@app.route('/process', methods=['POST'])
def process_script():
    """Process script asynchronously"""
    data = request.json
    script = data['script']
    post = data['post']
    
    # Create job ID and output directory
    job_id = f"manual_{post['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = Path('data/out') / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Start background thread
    thread = threading.Thread(
        target=run_pipeline_background,
        args=(job_id, script, post, output_dir)
    )
    thread.daemon = True
    thread.start()
    job_threads[job_id] = thread
    
    # Return immediately
    return jsonify({
        'success': True,
        'job_id': job_id,
        'message': 'Processing started! Check status for updates.',
        'status_url': f'/status/{job_id}'
    })

@app.route('/status/<job_id>')
def check_status(job_id):
    """Check job status"""
    if job_id not in job_status:
        # Check if thread is still alive
        if job_id in job_threads and job_threads[job_id].is_alive():
            return jsonify({
                'status': 'running',
                'message': 'Pipeline is still processing...'
            })
        return jsonify({
            'status': 'not_found',
            'error': 'Job not found'
        }), 404
    
    return jsonify(job_status[job_id])

@app.route('/download/<path:filepath>')
def download_file(filepath):
    """Download generated files"""
    file_path = Path(filepath)
    if file_path.exists() and file_path.is_file():
        return send_file(str(file_path), as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/preview/<path:filepath>')
def preview_file(filepath):
    """Stream video/audio file for preview"""
    file_path = Path(filepath)
    if file_path.exists() and file_path.is_file():
        mimetype = 'video/mp4' if file_path.suffix == '.mp4' else 'audio/wav'
        return send_file(str(file_path), mimetype=mimetype)
    return jsonify({'error': 'File not found'}), 404

@app.route('/reddit/fetch', methods=['POST'])
def fetch_reddit_post():
    """Fetch a Reddit post"""
    import praw
    import random
    
    # Initialize Reddit client
    reddit = praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        user_agent=os.getenv('REDDIT_USER_AGENT', 'AI-Slop/1.0')
    )
    
    # Fetch from popular subreddits
    subreddits = ['AskReddit', 'todayilearned', 'explainlikeimfive', 'Showerthoughts']
    subreddit = reddit.subreddit(random.choice(subreddits))
    
    posts = []
    for post in subreddit.hot(limit=25):
        if not post.stickied and post.score > 100:
            posts.append({
                'id': post.id,
                'title': post.title,
                'content': post.selftext[:500] if post.selftext else '',
                'subreddit': post.subreddit.display_name,
                'author': str(post.author) if post.author else 'deleted',
                'score': post.score,
                'url': f"https://reddit.com{post.permalink}"
            })
    
    if posts:
        selected = random.choice(posts)
        return jsonify(selected)
    
    return jsonify({'error': 'No posts found'}), 404

@app.route('/')
def index():
    """Serve the UI"""
    # Try to serve the dark UI first
    ui_path = Path('ui_dark.html')
    if ui_path.exists():
        return ui_path.read_text(encoding='utf-8')
    
    # Fallback to async UI
    ui_path = Path('ui_async.html')
    if ui_path.exists():
        return ui_path.read_text(encoding='utf-8')
    
    return """
    <html>
    <head><title>AI-Slop Pipeline</title></head>
    <body>
        <h1>AI-Slop Pipeline</h1>
        <p>UI file not found. Please ensure ui_dark.html or ui_async.html exists.</p>
        <p>API Endpoints:</p>
        <ul>
            <li>POST /process - Start processing</li>
            <li>GET /status/{job_id} - Check status</li>
            <li>POST /reddit/fetch - Fetch Reddit post</li>
            <li>GET /download/{filepath} - Download file</li>
        </ul>
    </body>
    </html>
    """

if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv('config/.env')
    
    print("=" * 60)
    print("AI-Slop Async Pipeline Server")
    print("=" * 60)
    print("Visit: http://localhost:5001")
    print("Processing runs in background - no timeouts!")
    print("=" * 60)
    
    app.run(debug=False, port=5001, threaded=True)