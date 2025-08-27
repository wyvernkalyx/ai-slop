#!/usr/bin/env python3
"""Main orchestrator pipeline for YouTube video generation."""

import sys
import json
import time
import argparse
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.modules.ingest_reddit import RedditIngestor
from src.modules.classify import TopicClassifier
from src.modules.script_gen import ScriptGenerator
from src.modules.tts import TextToSpeech
from src.modules.media_picker import MediaPicker
from src.modules.thumbnail import ThumbnailGenerator
from src.modules.assemble import VideoAssembler
from src.utils.config import get_config
from src.utils.logger import get_logger, log_job_start, log_job_end, log_error
from src.utils.dedup import DeduplicationManager


class Pipeline:
    """Main orchestrator for the video generation pipeline."""
    
    def __init__(self, dry_run: bool = False, job_id: Optional[str] = None):
        """Initialize pipeline.
        
        Args:
            dry_run: If True, use test data and mock services
            job_id: Unique job identifier
        """
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.dry_run = dry_run
        self.job_id = job_id or str(uuid.uuid4())[:8]
        
        # Initialize output directory
        self.output_dir = Path(self.config.get_paths()['output_dir']) / self.job_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize modules
        self.reddit_ingestor = RedditIngestor(dry_run=dry_run)
        self.classifier = TopicClassifier()
        self.script_generator = ScriptGenerator(dry_run=dry_run)
        self.tts = TextToSpeech(dry_run=dry_run)
        self.media_picker = MediaPicker(dry_run=dry_run)
        self.thumbnail_generator = ThumbnailGenerator()
        
        # Use robust video assembler that always works
        try:
            from src.modules.assemble_robust import RobustVideoAssembler
            self.video_assembler = RobustVideoAssembler(dry_run=dry_run)
            self.logger.info("Using RobustVideoAssembler (simple and reliable)")
        except ImportError:
            try:
                from src.modules.assemble_proper import ProperVideoAssembler
                self.video_assembler = ProperVideoAssembler(dry_run=dry_run)
                self.logger.info("Using ProperVideoAssembler (real video clips)")
            except ImportError:
                from src.modules.assemble_simple import SimpleVideoAssembler
                self.video_assembler = SimpleVideoAssembler(dry_run=dry_run)
                self.logger.info("Using SimpleVideoAssembler (static image + audio)")
        
        # Pipeline state
        self.state = {
            'job_id': self.job_id,
            'started_at': None,
            'completed_at': None,
            'status': 'pending',
            'current_step': None,
            'artifacts': {},
            'errors': []
        }
        
    def run(self) -> Dict[str, Any]:
        """Run the complete pipeline.
        
        Returns:
            Pipeline execution results
        """
        start_time = time.time()
        self.state['started_at'] = datetime.now().isoformat()
        
        log_job_start(self.job_id, {'dry_run': self.dry_run})
        self.logger.info(f"Starting pipeline job {self.job_id}")
        
        try:
            # Step 1: Ingest Reddit content
            self._run_step('reddit_ingest', self._step_reddit_ingest)
            
            # Step 2: Classify topic
            self._run_step('classification', self._step_classify)
            
            # Step 3: Generate script
            self._run_step('script_generation', self._step_generate_script)
            
            # Step 4: Generate audio
            self._run_step('tts', self._step_generate_audio)
            
            # Step 5: Select media
            self._run_step('media_selection', self._step_select_media)
            
            # Step 6: Generate thumbnail
            self._run_step('thumbnail_generation', self._step_generate_thumbnail)
            
            # Step 7: Assemble video
            self._run_step('video_assembly', self._step_assemble_video)
            
            # Step 8: Upload to YouTube (placeholder for now)
            if not self.dry_run and self.config.is_feature_enabled('upload'):
                self._run_step('youtube_upload', self._step_upload_youtube)
            
            # Mark as successful
            self.state['status'] = 'completed'
            self.logger.info(f"Pipeline completed successfully: {self.job_id}")
            
        except Exception as e:
            self.state['status'] = 'failed'
            self.state['errors'].append(str(e))
            log_error(f"Pipeline failed: {self.job_id}", e)
            self.logger.error(f"Pipeline failed: {e}")
            traceback.print_exc()
            
        finally:
            # Calculate duration
            duration = time.time() - start_time
            self.state['completed_at'] = datetime.now().isoformat()
            self.state['duration_seconds'] = duration
            
            # Save state
            self._save_state()
            
            # Log completion
            log_job_end(self.job_id, self.state['status'], duration, 
                       {'artifacts': len(self.state['artifacts'])})
            
        return self.state
        
    def _run_step(self, step_name: str, step_function):
        """Run a pipeline step with error handling.
        
        Args:
            step_name: Name of the step
            step_function: Function to execute
        """
        self.state['current_step'] = step_name
        self.logger.info(f"Running step: {step_name}")
        
        try:
            result = step_function()
            self.state['artifacts'][step_name] = result
            self.logger.info(f"Step completed: {step_name}")
        except Exception as e:
            self.logger.error(f"Step failed: {step_name} - {e}")
            raise
            
    def _step_reddit_ingest(self) -> Dict[str, Any]:
        """Step 1: Ingest Reddit content."""
        # Fetch trending posts
        posts = self.reddit_ingestor.fetch_trending_posts(limit=20)
        
        if not posts:
            raise ValueError("No suitable Reddit posts found")
            
        # Try multiple posts if needed
        for i, post in enumerate(posts):
            # Check if post has sufficient content
            if len(post.get('selftext', '')) > 100 or (post.get('title', '') and len(post.get('title', '')) > 30):
                # Save post data
                post_file = self.reddit_ingestor.save_post(post, self.output_dir)
                
                return {
                    'post': post,
                    'post_file': str(post_file),
                    'num_candidates': len(posts),
                    'selected_index': i
                }
        
        # If no suitable post found, use the best scored one
        best_post = self.reddit_ingestor.get_best_post(posts)
        
        if not best_post:
            raise ValueError("Could not select a suitable post")
            
        # Save post data
        post_file = self.reddit_ingestor.save_post(best_post, self.output_dir)
        
        return {
            'post': best_post,
            'post_file': str(post_file),
            'num_candidates': len(posts)
        }
        
    def _step_classify(self) -> Dict[str, Any]:
        """Step 2: Classify the post topic."""
        post = self.state['artifacts']['reddit_ingest']['post']
        
        # Classify topic
        topic_id, confidence, metadata = self.classifier.classify(post)
        
        # Get topic configuration
        topic_config = self.classifier.get_topic_config(topic_id)
        
        # Check suitability
        suitability = self.classifier.analyze_post_suitability(post)
        
        if not suitability['is_suitable']:
            self.logger.warning(f"Post has suitability issues: {suitability['issues']}")
            # Continue anyway for testing
            
        return {
            'topic_id': topic_id,
            'confidence': confidence,
            'topic_config': topic_config,
            'suitability': suitability,
            'metadata': metadata
        }
        
    def _step_generate_script(self) -> Dict[str, Any]:
        """Step 3: Generate video script."""
        post = self.state['artifacts']['reddit_ingest']['post']
        topic_config = self.state['artifacts']['classification']['topic_config']
        
        # Check if a script already exists in the output directory
        existing_scripts = list(self.output_dir.glob('script_*.json'))
        if existing_scripts:
            # Use the existing script provided by the user
            script_file = existing_scripts[0]
            self.logger.info(f"Using existing script: {script_file}")
            with open(script_file, 'r', encoding='utf-8') as f:
                script = json.load(f)
        else:
            # Generate script if none exists
            self.logger.info("No existing script found, generating new one")
            target_minutes = self.config.get('video.target_minutes', 10)
            script = self.script_generator.generate_script(post, topic_config, target_minutes)
            
            # Save script
            script_file = self.script_generator.save_script(script, self.output_dir)
        
        # Calculate duration
        duration = self.script_generator.calculate_duration(script)
        
        return {
            'script': script,
            'script_file': str(script_file),
            'estimated_duration_minutes': duration
        }
        
    def _step_generate_audio(self) -> Dict[str, Any]:
        """Step 4: Generate audio from script."""
        script = self.state['artifacts']['script_generation']['script']
        
        # Estimate cost
        narration_text = self.tts._extract_narration(script)
        cost_estimate = self.tts.estimate_cost(narration_text)
        
        # Generate audio
        audio_path, duration = self.tts.generate_audio(script, self.output_dir)
        
        return {
            'audio_file': str(audio_path),
            'duration_seconds': duration,
            'duration_minutes': duration / 60,
            'cost_estimate': cost_estimate
        }
        
    def _step_select_media(self) -> Dict[str, Any]:
        """Step 5: Select stock media clips."""
        script = self.state['artifacts']['script_generation']['script']
        duration_minutes = self.state['artifacts']['tts']['duration_minutes']
        
        # Select media clips
        clips = self.media_picker.select_media(script, duration_minutes, self.output_dir)
        
        return {
            'num_clips': len(clips),
            'total_clips_duration': sum(c.get('duration', 0) for c in clips),
            'clips': clips[:10]  # Save first 10 for reference
        }
        
    def _step_assemble_video(self) -> Dict[str, Any]:
        """Step 6: Assemble video from components."""
        # Get paths from previous steps
        audio_path = Path(self.state['artifacts']['tts']['audio_file'])
        clips_dir = self.output_dir / 'clips'
        thumbnail_path = Path(self.state['artifacts']['thumbnail_generation']['thumbnail_file'])
        script = self.state['artifacts']['script_generation']['script']
        
        # Assemble video
        video_path, metadata = self.video_assembler.assemble_video(
            audio_path=audio_path,
            clips_dir=clips_dir,
            output_dir=self.output_dir,
            script=script,
            thumbnail_path=thumbnail_path
        )
        
        return {
            'video_file': str(video_path),
            'duration_seconds': metadata.get('duration_seconds', 0),
            'duration_minutes': metadata.get('duration_minutes', metadata.get('duration_seconds', 0) / 60),
            'resolution': metadata.get('resolution', '1280x720'),
            'fps': metadata.get('fps', 25),
            'file_size_mb': metadata.get('file_size_mb', 0)
        }
        
    def _step_generate_thumbnail(self) -> Dict[str, Any]:
        """Step 7: Generate video thumbnail."""
        script = self.state['artifacts']['script_generation']['script']
        metadata_info = self.state['artifacts'].get('metadata', {})
        
        # Generate thumbnail
        thumbnail_path = self.thumbnail_generator.generate_thumbnail(
            script, metadata_info, self.output_dir
        )
        
        return {
            'thumbnail_file': str(thumbnail_path),
            'dimensions': f'{self.thumbnail_generator.width}x{self.thumbnail_generator.height}'
        }
        
    def _step_upload_youtube(self) -> Dict[str, Any]:
        """Step 8: Upload to YouTube."""
        # Placeholder - would use YouTube upload module
        self.logger.info("YouTube upload step (placeholder)")
        
        return {
            'video_id': 'placeholder_id',
            'upload_status': 'skipped',
            'privacy': 'unlisted'
        }
        
    def _save_state(self):
        """Save pipeline state to file."""
        state_file = self.output_dir / 'pipeline_state.json'
        with open(state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
            
        self.logger.info(f"Pipeline state saved to {state_file}")


def main():
    """Main entry point for the pipeline."""
    parser = argparse.ArgumentParser(description='YouTube video generation pipeline')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run with test data and mock services')
    parser.add_argument('--job-id', type=str, help='Unique job identifier')
    parser.add_argument('--config', type=str, help='Path to config file')
    args = parser.parse_args()
    
    # Validate configuration
    config = get_config()
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please run 'python validate_config.py' to check your setup")
        sys.exit(1)
        
    # Create and run pipeline
    print(f"\n{'='*60}")
    print(f"YouTube Video Generation Pipeline")
    print(f"{'='*60}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
    print(f"Job ID: {args.job_id or 'auto-generated'}")
    print(f"{'='*60}\n")
    
    pipeline = Pipeline(dry_run=args.dry_run, job_id=args.job_id)
    
    try:
        result = pipeline.run()
        
        print(f"\n{'='*60}")
        print(f"Pipeline Result: {result['status'].upper()}")
        print(f"{'='*60}")
        print(f"Job ID: {result['job_id']}")
        print(f"Duration: {result.get('duration_seconds', 0):.1f} seconds")
        print(f"Output: {pipeline.output_dir}")
        
        if result['status'] == 'completed':
            print(f"\nArtifacts generated:")
            for step, artifact in result['artifacts'].items():
                print(f"  • {step}")
                
        else:
            print(f"\nErrors:")
            for error in result.get('errors', []):
                print(f"  • {error}")
                
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nPipeline failed with error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()