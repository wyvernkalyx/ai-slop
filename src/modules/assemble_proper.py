"""Proper video assembly using actual video clips with ffmpeg"""

import subprocess
import json
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
from datetime import datetime

from ..utils.config import get_config
from ..utils.logger import get_logger


class ProperVideoAssembler:
    """Assemble videos using actual video clips, not static images"""
    
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
        """Assemble video using actual video clips."""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        post_id = script.get('post_id', 'unknown') if script else 'unknown'
        title = script.get('title', '') if script else ''
        output_filename = f"video_{post_id}_{timestamp}.mp4"
        output_path = output_dir / output_filename
        
        if self.dry_run:
            output_path.touch()
            return output_path, {"duration_seconds": 5.0, "method": "mock"}
            
        try:
            # Get all video clips
            clips = sorted(clips_dir.glob('*.mp4'))
            if not clips:
                self.logger.error("No video clips found!")
                raise Exception("No video clips in clips directory")
            
            self.logger.info(f"Found {len(clips)} video clips")
            
            # Get audio duration
            audio_duration = self._get_duration(audio_path)
            self.logger.info(f"Audio duration: {audio_duration:.1f}s")
            
            # Method 1: Concatenate clips then add audio (faster, better quality)
            concat_video = output_dir / 'concat_temp.mp4'
            
            # Create concat file list
            concat_list = output_dir / 'concat_list.txt'
            with open(concat_list, 'w') as f:
                # Calculate how many times to loop clips
                clip_duration = 5.0  # Each clip is ~5 seconds
                total_clip_duration = len(clips) * clip_duration
                loops_needed = int(audio_duration / total_clip_duration) + 1
                
                self.logger.info(f"Looping {len(clips)} clips {loops_needed} times for {audio_duration}s audio")
                
                for _ in range(loops_needed):
                    for clip in clips:
                        # Use forward slashes and absolute path for ffmpeg
                        clip_path = str(clip.absolute()).replace('\\', '/')
                        f.write(f"file '{clip_path}'\n")
            
            # Step 1: Concatenate all clips
            self.logger.info("Concatenating video clips...")
            concat_cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_list),
                '-c', 'copy',  # Copy without re-encoding (fast!)
                '-t', str(audio_duration),  # Trim to audio length
                str(concat_video),
                '-y'
            ]
            
            result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                self.logger.error(f"Concat failed: {result.stderr[-500:]}")
                
                # Try alternative method: direct input of files
                self.logger.info("Trying alternative concatenation method...")
                
                # Build input args for each clip
                input_args = []
                for clip in clips[:20]:  # Limit to 20 clips to avoid command line length issues
                    input_args.extend(['-i', str(clip)])
                
                # Create filter complex for concatenation
                filter_str = ''.join([f'[{i}:v][{i}:a]' for i in range(len(clips[:20]))])
                filter_str += f'concat=n={len(clips[:20])}:v=1:a=1[outv][outa]'
                
                alt_concat_cmd = [
                    'ffmpeg'
                ] + input_args + [
                    '-filter_complex', filter_str,
                    '-map', '[outv]',
                    '-map', '[outa]',
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-crf', '28',
                    '-c:a', 'aac',
                    '-t', str(audio_duration),
                    str(concat_video),
                    '-y'
                ]
                
                result = subprocess.run(alt_concat_cmd, capture_output=True, text=True, timeout=180)
                if result.returncode != 0:
                    raise Exception(f"Both concat methods failed: {result.stderr[-200:]}")
            
            # Step 2: Add audio to concatenated video
            self.logger.info("Adding audio track...")
            
            # Add title overlay if we have a title
            if title:
                # Create title with proper escaping and wrapping
                title_safe = title.replace("'", "\\'").replace('"', '\\"')
                # Wrap long titles
                if len(title_safe) > 50:
                    words = title_safe.split()
                    lines = []
                    current_line = []
                    current_length = 0
                    
                    for word in words:
                        if current_length + len(word) + 1 <= 50:
                            current_line.append(word)
                            current_length += len(word) + 1
                        else:
                            if current_line:
                                lines.append(' '.join(current_line))
                            current_line = [word]
                            current_length = len(word)
                    
                    if current_line:
                        lines.append(' '.join(current_line))
                    
                    title_safe = '\\n'.join(lines[:3])  # Max 3 lines
                
                final_cmd = [
                    'ffmpeg',
                    '-i', str(concat_video),
                    '-i', str(audio_path),
                    '-filter_complex', 
                    f"[0:v]drawtext=text='{title_safe}':fontfile=C\\\\:/Windows/Fonts/arial.ttf:fontsize=36:fontcolor=white:bordercolor=black:borderw=2:x=(w-text_w)/2:y=50:enable='between(t,0,5)'[v]",
                    '-map', '[v]',
                    '-map', '1:a',
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-c:a', 'copy',  # Copy audio without re-encoding
                    '-t', str(audio_duration),  # Use full audio duration
                    '-movflags', '+faststart',
                    str(output_path),
                    '-y'
                ]
            else:
                # No title overlay
                final_cmd = [
                    'ffmpeg',
                    '-i', str(concat_video),
                    '-i', str(audio_path),
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-c:a', 'copy',  # Copy audio without re-encoding
                    '-t', str(audio_duration),  # Use full audio duration
                    '-movflags', '+faststart',
                    str(output_path),
                    '-y'
                ]
            
            result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=180)
            
            if result.returncode != 0:
                self.logger.error(f"Final assembly failed: {result.stderr[-500:]}")
                # Try without title overlay
                if title:
                    self.logger.info("Retrying without title overlay...")
                    simple_cmd = [
                        'ffmpeg',
                        '-i', str(concat_video),
                        '-i', str(audio_path),
                        '-c:v', 'copy',  # Just copy video
                        '-c:a', 'copy',  # Copy audio
                        '-t', str(audio_duration),  # Full duration
                        '-movflags', '+faststart',
                        str(output_path),
                        '-y'
                    ]
                    result = subprocess.run(simple_cmd, capture_output=True, text=True, timeout=120)
                    
                if result.returncode != 0:
                    raise Exception("Failed to add audio")
            
            # Clean up temp files
            concat_video.unlink(missing_ok=True)
            concat_list.unlink(missing_ok=True)
            
            # Verify output
            if output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                self.logger.info(f"Video created: {output_path} ({file_size_mb:.1f} MB)")
                
                # Get final video properties
                final_duration = self._get_duration(output_path)
                
                metadata = {
                    "video_file": output_path.name,
                    "duration_seconds": final_duration,
                    "duration_minutes": final_duration / 60,
                    "file_size_mb": file_size_mb,
                    "num_clips": len(clips),
                    "method": "proper_concatenation",
                    "has_video_content": True
                }
                
                return output_path, metadata
            else:
                raise Exception("Output file not created")
                
        except subprocess.TimeoutExpired:
            self.logger.error("Video assembly timed out")
            output_path.touch()
            return output_path, {"error": "timeout"}
            
        except Exception as e:
            self.logger.error(f"Assembly failed: {e}")
            output_path.touch()
            return output_path, {"error": str(e)}
    
    def _get_duration(self, media_path: Path) -> float:
        """Get duration of audio/video file"""
        try:
            probe_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(media_path)
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
            return float(result.stdout.strip() or '0')
        except:
            return 0.0