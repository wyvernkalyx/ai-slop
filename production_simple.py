#!/usr/bin/env python3
"""
SIMPLIFIED PRODUCTION PIPELINE
Uses manual script but REAL APIs for everything else
NO MOCKS - Production only
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# Real API modules only
from src.modules.tts_real import ElevenLabsTTS
from src.modules.assemble_ffmpeg import FFmpegVideoAssembler
from src.utils.config import get_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def download_stock_videos(keywords, output_dir, count=20):
    """Download real stock videos from Pexels"""
    import requests
    
    config = get_config()
    pexels_key = config.get_env('PEXELS_API_KEY')
    
    if not pexels_key:
        logger.error("PEXELS_API_KEY not set!")
        return []
    
    clips = []
    output_dir.mkdir(exist_ok=True)
    
    for keyword in keywords:
        if len(clips) >= count:
            break
            
        logger.info(f"Searching Pexels for: {keyword}")
        
        headers = {'Authorization': pexels_key}
        url = 'https://api.pexels.com/videos/search'
        params = {
            'query': keyword,
            'per_page': 5,
            'size': 'medium',
            'orientation': 'landscape'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                
                for video in data.get('videos', [])[:3]:
                    if len(clips) >= count:
                        break
                    
                    # Find best quality file
                    video_files = video.get('video_files', [])
                    hd_files = [f for f in video_files if f.get('quality') == 'hd']
                    
                    if hd_files:
                        file_url = hd_files[0]['link']
                        file_name = f"clip_{len(clips):03d}_{keyword.replace(' ', '_')}.mp4"
                        file_path = output_dir / file_name
                        
                        # Download
                        logger.info(f"  Downloading: {file_name}")
                        video_response = requests.get(file_url, stream=True)
                        
                        with open(file_path, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        clips.append(file_path)
            else:
                logger.warning(f"Pexels API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to download from Pexels: {e}")
    
    return clips

def run_production():
    """Run production pipeline with manual script"""
    
    config = get_config()
    
    # Check API keys
    if not config.get_env('ELEVENLABS_API_KEY'):
        logger.error("ELEVENLABS_API_KEY not set in .env!")
        return False
    
    if not config.get_env('PEXELS_API_KEY'):
        logger.error("PEXELS_API_KEY not set in .env!")
        return False
    
    # Load manual script
    script_file = Path("data/out/manual_20250826_160443/script_error_fallback_20250826_160443.json")
    
    if not script_file.exists():
        logger.error(f"Script file not found: {script_file}")
        logger.error("Please run the manual script generator first")
        return False
    
    with open(script_file) as f:
        script = json.load(f)
    
    logger.info("="*60)
    logger.info("PRODUCTION VIDEO GENERATION")
    logger.info("="*60)
    logger.info(f"Script: {script['title']}")
    logger.info(f"Chapters: {len(script['narration']['chapters'])}")
    
    # Create output directory
    job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path('data/out') / f'production_{job_id}'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Generate REAL audio with ElevenLabs
    logger.info("\n[1/3] Generating Audio with ElevenLabs...")
    
    # Build full narration
    narration = script['narration']['intro']
    for chapter in script['narration']['chapters']:
        narration += f" {chapter['heading']}. {chapter['body']}"
    narration += f" {script['narration']['outro']}"
    
    word_count = len(narration.split())
    logger.info(f"Text length: {len(narration)} chars, {word_count} words")
    logger.info(f"Estimated duration: {word_count/150:.1f} minutes")
    
    # Check if we have enough credits
    char_count = len(narration)
    logger.info(f"ElevenLabs credits needed: {char_count}")
    
    # Generate audio
    tts = ElevenLabsTTS(api_key=config.get_env('ELEVENLABS_API_KEY'))
    try:
        audio_path, duration = tts.generate_audio(
            text=narration,
            output_path=output_dir / "narration",
            voice="rachel",
            model="eleven_monolingual_v1"
        )
        logger.info(f"✅ Audio generated: {audio_path}")
        logger.info(f"Duration: {duration:.1f} seconds")
    except Exception as e:
        logger.error(f"Audio generation failed: {e}")
        logger.error("Check your ElevenLabs credits")
        return False
    
    # Step 2: Download REAL stock footage
    logger.info("\n[2/3] Downloading Stock Footage...")
    
    clips_dir = output_dir / "clips"
    clips = download_stock_videos(
        keywords=script['broll_keywords'],
        output_dir=clips_dir,
        count=20
    )
    
    if not clips:
        logger.error("No stock footage downloaded!")
        return False
    
    logger.info(f"✅ Downloaded {len(clips)} video clips")
    
    # Step 3: Assemble video with FFmpeg
    logger.info("\n[3/3] Assembling Final Video...")
    
    assembler = FFmpegVideoAssembler()
    output_video = output_dir / f"video_{job_id}.mp4"
    
    try:
        final_video = assembler.assemble(
            audio_file=audio_path,
            clips=clips,
            output_dir=output_dir
        )
        
        logger.info("\n" + "="*60)
        logger.info("✅ PRODUCTION VIDEO COMPLETE!")
        logger.info("="*60)
        logger.info(f"Video: {final_video}")
        logger.info(f"Duration: {duration/60:.1f} minutes")
        logger.info(f"Title: {script['title']}")
        
        # Verify with ffprobe
        import subprocess
        probe_cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams', str(final_video)
        ]
        
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            has_audio = any(s['codec_type'] == 'audio' for s in data['streams'])
            has_video = any(s['codec_type'] == 'video' for s in data['streams'])
            
            logger.info(f"\nVerification:")
            logger.info(f"  Has video: {'✅' if has_video else '❌'}")
            logger.info(f"  Has audio: {'✅' if has_audio else '❌'}")
        
        return True
        
    except Exception as e:
        logger.error(f"Video assembly failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nAI-SLOP PRODUCTION - REAL APIs ONLY")
    print("This will use your ElevenLabs and Pexels credits")
    print("-"*40)
    
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled")
        sys.exit(0)
    
    success = run_production()
    sys.exit(0 if success else 1)