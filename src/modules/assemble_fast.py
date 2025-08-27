"""Fast video assembly module - optimized for speed"""

import json
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from ..utils.config import get_config
from ..utils.logger import get_logger


class FastVideoAssembler:
    """Optimized video assembly for faster processing"""
    
    def __init__(self, dry_run: bool = False):
        """Initialize video assembler with fast settings."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.dry_run = dry_run
        
        # Use lower resolution for faster processing
        self.width = 1280  # 720p instead of 1080p
        self.height = 720
        self.fps = 24  # Lower FPS
        self.codec = 'libx264'
        self.preset = 'ultrafast'  # Fastest encoding preset
        self.bitrate = '2M'  # Lower bitrate
        self.fade_duration = 0  # No fades for speed
        
    def assemble_video(self,
                      audio_path: Path,
                      clips_dir: Path, 
                      output_dir: Path,
                      script: Optional[Dict[str, Any]] = None,
                      thumbnail_path: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
        """Fast video assembly using optimized settings."""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        post_id = script.get('post_id', 'unknown') if script else 'unknown'
        output_filename = f"video_{post_id}_{timestamp}.mp4"
        output_path = output_dir / output_filename
        
        if self.dry_run:
            output_path.touch()
            return output_path, {"duration_seconds": 5.0}
            
        try:
            from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, ColorClip
            
            # Load audio
            self.logger.info("Loading audio...")
            audio = AudioFileClip(str(audio_path))
            audio_duration = audio.duration
            
            # Get video clips (limit to 5 for speed)
            clip_files = sorted(clips_dir.glob('*.mp4'))[:5]
            
            if not clip_files:
                # Create simple black video
                self.logger.info("Creating black video...")
                video = ColorClip(size=(self.width, self.height), 
                                color=(0,0,0), 
                                duration=audio_duration)
            else:
                # Load clips with minimal processing
                clips = []
                target_duration = audio_duration / len(clip_files)
                
                for i, clip_file in enumerate(clip_files):
                    try:
                        self.logger.info(f"Processing clip {i+1}/{len(clip_files)}...")
                        clip = VideoFileClip(str(clip_file))
                        
                        # Simple resize without fancy interpolation
                        clip = clip.resize(newsize=(self.width, self.height))
                        
                        # Set duration without complex looping
                        if clip.duration > target_duration:
                            clip = clip.subclip(0, target_duration)
                        else:
                            clip = clip.set_duration(target_duration)
                        
                        clips.append(clip)
                        
                    except Exception as e:
                        self.logger.warning(f"Skipping clip {clip_file}: {e}")
                
                if clips:
                    self.logger.info("Concatenating clips...")
                    video = concatenate_videoclips(clips, method="compose")
                else:
                    video = ColorClip(size=(self.width, self.height), 
                                    color=(0,0,0), 
                                    duration=audio_duration)
            
            # Add audio
            self.logger.info("Adding audio track...")
            video = video.set_audio(audio)
            
            # Match duration
            if video.duration != audio_duration:
                video = video.set_duration(audio_duration)
            
            # Write with fast settings
            self.logger.info(f"Encoding video with ultrafast preset...")
            video.write_videofile(
                str(output_path),
                fps=self.fps,
                codec=self.codec,
                preset=self.preset,
                bitrate=self.bitrate,
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger=None,  # Disable verbose logging
                threads=4  # Use multiple threads
            )
            
            # Clean up
            video.close()
            audio.close()
            
            self.logger.info(f"Video assembled: {output_path}")
            
            # Create metadata
            metadata = {
                "video_file": output_path.name,
                "duration_seconds": audio_duration,
                "resolution": f"{self.width}x{self.height}",
                "fps": self.fps,
                "preset": self.preset
            }
            
            return output_path, metadata
            
        except Exception as e:
            self.logger.error(f"Fast assembly failed: {e}")
            # Create placeholder
            output_path.touch()
            return output_path, {"error": str(e)}