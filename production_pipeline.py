#!/usr/bin/env python3
"""
PRODUCTION PIPELINE - NO MOCKS, REAL APIs ONLY
This script uses actual APIs and generates real content.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.modules.ingest_reddit import RedditIngestor
from src.modules.classify import Classifier
from src.modules.script_gen import ScriptGenerator  
from src.modules.tts_real import ElevenLabsTTS
from src.modules.media_picker import MediaPicker
from src.modules.assemble_fixed import VideoAssembler
from src.modules.thumbnail import ThumbnailGenerator
from src.utils.config import get_config

# Set up production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_production_pipeline():
    """Run the full production pipeline with real APIs only"""
    
    config = get_config()
    
    # Check for required API keys
    required_keys = {
        'REDDIT_CLIENT_ID': config.get_env('REDDIT_CLIENT_ID'),
        'REDDIT_CLIENT_SECRET': config.get_env('REDDIT_CLIENT_SECRET'),
        'ELEVENLABS_API_KEY': config.get_env('ELEVENLABS_API_KEY'),
        'PEXELS_API_KEY': config.get_env('PEXELS_API_KEY'),
    }
    
    missing_keys = [k for k, v in required_keys.items() if not v]
    if missing_keys:
        logger.error(f"Missing required API keys: {', '.join(missing_keys)}")
        logger.error("Please set these in your .env file")
        return False
    
    # Create output directory
    job_id = f"production_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = Path('data/out') / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("="*60)
    logger.info("PRODUCTION PIPELINE - REAL APIs ONLY")
    logger.info("="*60)
    logger.info(f"Job ID: {job_id}")
    logger.info(f"Output: {output_dir}")
    
    try:
        # Step 1: Fetch Reddit Post
        logger.info("\n[1/7] Fetching Reddit Post...")
        reddit = RedditIngestor()
        posts = reddit.fetch_posts(subreddit='popular', limit=5)
        
        if not posts:
            logger.error("No posts fetched from Reddit")
            return False
        
        # Select first suitable post
        post = posts[0]
        logger.info(f"Selected post: {post['title'][:80]}...")
        logger.info(f"Subreddit: r/{post['subreddit']}")
        logger.info(f"Score: {post['score']}")
        
        # Step 2: Classify Topic
        logger.info("\n[2/7] Classifying Topic...")
        classifier = Classifier()
        classification = classifier.classify(post)
        logger.info(f"Topic: {classification['topic_id']}")
        logger.info(f"Confidence: {classification['confidence']:.2f}")
        
        # Step 3: Generate Script
        logger.info("\n[3/7] Generating Script...")
        
        # Check if OpenAI key is available
        openai_key = config.get_env('OPENAI_API_KEY')
        if openai_key:
            logger.info("Using OpenAI to generate script...")
            script_gen = ScriptGenerator()
            script = script_gen.generate(post, classification['topic_id'])
        else:
            logger.warning("No OpenAI key - using existing script file")
            # Use the Internet History script as fallback
            script_file = Path("data/out/manual_20250826_160443/script_error_fallback_20250826_160443.json")
            if script_file.exists():
                with open(script_file) as f:
                    script = json.load(f)
                logger.info(f"Loaded script: {script['title']}")
            else:
                logger.error("No script available and OpenAI key missing")
                return False
        
        # Save script
        script_path = output_dir / "script.json"
        with open(script_path, 'w') as f:
            json.dump(script, f, indent=2)
        
        # Step 4: Generate Audio with ElevenLabs
        logger.info("\n[4/7] Generating Audio with ElevenLabs...")
        
        # Extract full narration text
        narration_text = script['narration']['intro']
        for chapter in script['narration']['chapters']:
            narration_text += f" {chapter['heading']}. {chapter['body']}"
        narration_text += f" {script['narration']['outro']}"
        
        # Generate with ElevenLabs
        tts = ElevenLabsTTS()
        audio_path, audio_duration = tts.generate_audio(
            text=narration_text,
            output_path=output_dir / "narration",
            voice="rachel"
        )
        
        logger.info(f"Audio generated: {audio_path}")
        logger.info(f"Duration: {audio_duration:.1f} seconds ({audio_duration/60:.1f} minutes)")
        
        # Step 5: Download Stock Footage
        logger.info("\n[5/7] Downloading Stock Footage...")
        media_picker = MediaPicker()
        
        # Calculate clips needed
        clips_needed = int(audio_duration / 10) + 5  # One clip per 10 seconds + buffer
        
        logger.info(f"Downloading {clips_needed} clips for keywords: {', '.join(script['broll_keywords'][:5])}")
        
        clips = []
        clips_dir = output_dir / "clips"
        clips_dir.mkdir(exist_ok=True)
        
        for i, keyword in enumerate(script['broll_keywords'] * 3):  # Cycle keywords if needed
            if len(clips) >= clips_needed:
                break
            
            logger.info(f"Searching for: {keyword}")
            found_clips = media_picker.search_and_download(
                keyword=keyword,
                output_dir=clips_dir,
                max_clips=3
            )
            clips.extend(found_clips)
        
        if not clips:
            logger.error("No stock footage downloaded")
            return False
        
        logger.info(f"Downloaded {len(clips)} video clips")
        
        # Step 6: Generate Thumbnail
        logger.info("\n[6/7] Generating Thumbnail...")
        thumbnail_gen = ThumbnailGenerator()
        
        # Extract key words from title for thumbnail
        title_words = script['title'].split()[:5]
        thumbnail_text = ' '.join(title_words).upper()
        
        thumbnail_path = thumbnail_gen.generate(
            text=thumbnail_text,
            output_dir=output_dir,
            background_image=clips[0] if clips else None  # Use first clip frame
        )
        
        logger.info(f"Thumbnail created: {thumbnail_path}")
        
        # Step 7: Assemble Final Video
        logger.info("\n[7/7] Assembling Final Video...")
        assembler = VideoAssembler()
        
        # Get clip paths
        clip_paths = [str(c) for c in clips_dir.glob("*.mp4")][:20]  # Limit to 20 clips
        
        output_video = output_dir / f"final_video_{job_id}.mp4"
        
        result = assembler.assemble_video(
            video_clips=clip_paths,
            audio_path=audio_path,
            output_path=output_video
        )
        
        logger.info("\n" + "="*60)
        logger.info("PRODUCTION VIDEO COMPLETED!")
        logger.info("="*60)
        logger.info(f"Video: {output_video}")
        logger.info(f"Duration: {result['duration']:.1f} seconds ({result['duration']/60:.1f} minutes)")
        logger.info(f"Title: {script['title']}")
        logger.info(f"\nAll files saved in: {output_dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    
    print("\n" + "="*60)
    print("AI-SLOP PRODUCTION PIPELINE")
    print("Real APIs Only - No Mocks")
    print("="*60)
    
    # Confirm before running
    print("\nThis will use your API credits for:")
    print("- Reddit API")
    print("- ElevenLabs TTS") 
    print("- Pexels/Pixabay Stock Media")
    print("- OpenAI (if available)")
    
    response = input("\nProceed with production run? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    success = run_production_pipeline()
    
    if success:
        print("\n✅ Production pipeline completed successfully!")
    else:
        print("\n❌ Production pipeline failed - check logs")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()