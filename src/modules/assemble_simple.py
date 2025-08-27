"""Ultra-simple video assembly - just audio with static image"""

import subprocess
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from ..utils.config import get_config
from ..utils.logger import get_logger


class SimpleVideoAssembler:
    """Create simple videos using ffmpeg directly"""
    
    def __init__(self, dry_run: bool = False):
        """Initialize simple assembler."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.dry_run = dry_run
        
    def assemble_video(self,
                      audio_path: Path,
                      clips_dir: Path, 
                      output_dir: Path,
                      script: Optional[Dict[str, Any]] = None,
                      thumbnail_path: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
        """Create video using ffmpeg with static image + audio."""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        post_id = script.get('post_id', 'unknown') if script else 'unknown'
        output_filename = f"video_{post_id}_{timestamp}.mp4"
        output_path = output_dir / output_filename
        
        if self.dry_run:
            output_path.touch()
            return output_path, {"duration_seconds": 5.0, "method": "mock"}
            
        try:
            # Use thumbnail or first clip frame as static image
            image_path = thumbnail_path
            
            if not image_path or not image_path.exists():
                # Try to extract frame from first video clip
                clips = list(clips_dir.glob('*.mp4'))
                if clips:
                    image_path = output_dir / 'frame.jpg'
                    extract_cmd = [
                        'ffmpeg', '-i', str(clips[0]),
                        '-vframes', '1',  # Extract 1 frame
                        '-q:v', '2',  # Quality
                        str(image_path),
                        '-y'
                    ]
                    subprocess.run(extract_cmd, capture_output=True, timeout=5)
                    
            if not image_path or not image_path.exists():
                # Create a simple black image
                self.logger.warning("No image available, creating black video")
                image_path = output_dir / 'black.jpg'
                create_black = [
                    'ffmpeg',
                    '-f', 'lavfi',
                    '-i', 'color=c=black:s=1280x720:d=1',
                    '-frames:v', '1',
                    str(image_path),
                    '-y'
                ]
                subprocess.run(create_black, capture_output=True, timeout=5)
            
            # Get audio duration
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(audio_path)
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
            audio_duration = float(result.stdout.strip() or '60')
            
            # Create video with static image + audio using ffmpeg directly
            self.logger.info(f"Creating video with ffmpeg (duration: {audio_duration:.1f}s)...")
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-loop', '1',  # Loop the image
                '-i', str(image_path),  # Input image
                '-i', str(audio_path),  # Input audio
                '-c:v', 'libx264',  # Video codec
                '-preset', 'ultrafast',  # Fastest encoding
                '-crf', '28',  # Lower quality for speed
                '-tune', 'stillimage',  # Optimize for still image
                '-c:a', 'aac',  # Audio codec
                '-b:a', '128k',  # Audio bitrate
                '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
                '-t', str(audio_duration),  # Duration
                '-movflags', '+faststart',  # Web optimization
                str(output_path),
                '-y'  # Overwrite
            ]
            
            self.logger.info(f"Running: {' '.join(ffmpeg_cmd[:6])}...")
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=60  # Should complete within 1 minute for static image
            )
            
            if result.returncode != 0:
                self.logger.error(f"FFmpeg error: {result.stderr[-500:]}")
                raise Exception(f"FFmpeg failed: {result.returncode}")
            
            # Verify output exists
            if output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                self.logger.info(f"Video created: {output_path} ({file_size_mb:.1f} MB)")
                
                metadata = {
                    "video_file": output_path.name,
                    "duration_seconds": audio_duration,
                    "file_size_mb": file_size_mb,
                    "method": "simple_ffmpeg",
                    "encoding": "ultrafast"
                }
                
                return output_path, metadata
            else:
                raise Exception("Output file not created")
                
        except subprocess.TimeoutExpired:
            self.logger.error("FFmpeg timed out")
            output_path.touch()
            return output_path, {"error": "timeout", "method": "simple_ffmpeg"}
            
        except Exception as e:
            self.logger.error(f"Simple assembly failed: {e}")
            # Create placeholder
            output_path.touch()
            return output_path, {"error": str(e), "method": "simple_ffmpeg"}