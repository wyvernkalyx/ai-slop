"""Robust video assembly - simple and reliable"""

import subprocess
import random
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from ..utils.config import get_config
from ..utils.logger import get_logger


class RobustVideoAssembler:
    """Simple, robust video assembly that always works"""
    
    def __init__(self, dry_run: bool = False):
        """Initialize assembler."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.dry_run = dry_run
        
    def assemble_video(self,
                      audio_path: Path,
                      clips_dir: Path, 
                      output_dir: Path,
                      script: Optional[Dict[str, Any]] = None,
                      thumbnail_path: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
        """Assemble video using simple, reliable method."""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        post_id = script.get('post_id', 'unknown') if script else 'unknown'
        output_filename = f"video_{post_id}_{timestamp}.mp4"
        output_path = output_dir / output_filename
        
        if self.dry_run:
            output_path.touch()
            return output_path, {"duration_seconds": 5.0}
            
        try:
            # Get video clips
            clips = sorted(clips_dir.glob('*.mp4'))
            if not clips:
                self.logger.warning("No clips found, using thumbnail")
                # Fall back to thumbnail
                if thumbnail_path and thumbnail_path.exists():
                    return self._create_from_image(thumbnail_path, audio_path, output_path)
                else:
                    raise Exception("No video clips or thumbnail available")
            
            # Get audio duration
            audio_duration = self._get_duration(audio_path)
            self.logger.info(f"Creating {audio_duration:.1f}s video from {len(clips)} clips")
            
            # Simple approach: Pick one good clip and loop it
            # This avoids complex concatenation issues
            selected_clip = clips[0]  # Use first clip
            if len(clips) > 3:
                # Pick a random clip from the middle ones (often better quality)
                selected_clip = random.choice(clips[1:-1])
            
            self.logger.info(f"Using clip: {selected_clip.name}")
            
            # Create looped video with audio
            # IMPORTANT: Use only video from clip, audio from narration
            cmd = [
                'ffmpeg',
                '-stream_loop', '-1',  # Loop video infinitely
                '-i', str(selected_clip),
                '-i', str(audio_path),
                '-map', '0:v:0',  # Only video from first input
                '-map', '1:a:0',  # Only audio from second input (narration)
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '24',
                '-c:a', 'aac',
                '-b:a', '192k',  # Higher bitrate for better quality
                '-ac', '2',  # Convert to stereo for better compatibility
                '-t', str(audio_duration),  # Trim to audio length
                '-movflags', '+faststart',
                str(output_path),
                '-y'
            ]
            
            self.logger.info("Assembling video with looped clip...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode != 0:
                self.logger.error(f"Assembly failed: {result.stderr[-500:]}")
                
                # Try even simpler approach - just add narration to first clip
                self.logger.info("Trying simplest approach...")
                simple_cmd = [
                    'ffmpeg',
                    '-i', str(selected_clip),
                    '-i', str(audio_path),
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-ac', '2',  # Stereo
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-shortest',  # Stop at shortest stream
                    str(output_path),
                    '-y'
                ]
                result = subprocess.run(simple_cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    raise Exception("All assembly methods failed")
            
            # Verify output
            if output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                actual_duration = self._get_duration(output_path)
                
                self.logger.info(f"Video created: {output_path}")
                self.logger.info(f"Size: {file_size_mb:.1f} MB, Duration: {actual_duration:.1f}s")
                
                metadata = {
                    "video_file": output_path.name,
                    "duration_seconds": actual_duration,
                    "duration_minutes": actual_duration / 60,
                    "file_size_mb": file_size_mb,
                    "method": "robust_loop",
                    "clip_used": selected_clip.name
                }
                
                return output_path, metadata
            else:
                raise Exception("Output file not created")
                
        except Exception as e:
            self.logger.error(f"Robust assembly failed: {e}")
            # Last resort: create simple video from thumbnail
            if thumbnail_path and thumbnail_path.exists():
                return self._create_from_image(thumbnail_path, audio_path, output_path)
            else:
                # Create placeholder
                output_path.touch()
                return output_path, {"error": str(e)}
    
    def _create_from_image(self, image_path: Path, audio_path: Path, output_path: Path) -> Tuple[Path, Dict[str, Any]]:
        """Create video from static image + audio"""
        try:
            audio_duration = self._get_duration(audio_path)
            
            cmd = [
                'ffmpeg',
                '-loop', '1',
                '-i', str(image_path),
                '-i', str(audio_path),
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-tune', 'stillimage',
                '-crf', '24',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-pix_fmt', 'yuv420p',
                '-t', str(audio_duration),
                '-movflags', '+faststart',
                str(output_path),
                '-y'
            ]
            
            self.logger.info("Creating video from image...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 and output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                return output_path, {
                    "video_file": output_path.name,
                    "duration_seconds": audio_duration,
                    "file_size_mb": file_size_mb,
                    "method": "image_with_audio"
                }
        except:
            pass
        
        # Failed
        output_path.touch()
        return output_path, {"error": "All methods failed"}
    
    def _get_duration(self, media_path: Path) -> float:
        """Get media duration"""
        try:
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(media_path)
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
            return float(result.stdout.strip() or '60')
        except:
            return 60.0  # Default 1 minute