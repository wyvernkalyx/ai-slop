"""
Enhanced video assembler that preserves intro/outro audio
"""

import subprocess
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

class EnhancedVideoAssembler:
    """Assembles videos with proper audio handling for intro/outro"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Configure logging to show more detail
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
        
        self.fps = 30
        self.width = 1920
        self.height = 1080
        self.codec = 'libx264'
        self.preset = 'medium'
        self.crf = 23
        
    def assemble_with_bookends(self,
                               audio_file: Path,
                               clips: List[Path],
                               output_dir: Path,
                               include_intro: bool = True,
                               include_outro: bool = True) -> Path:
        """
        Assemble video with intro/outro that keep their original audio,
        and narration that plays only during stock footage.
        
        Args:
            audio_file: Path to narration audio
            clips: List of stock video clips
            output_dir: Output directory
            include_intro: Whether to include intro
            include_outro: Whether to include outro
            
        Returns:
            Path to assembled video
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = Path(audio_file).stem
        output_file = output_dir / f"video_enhanced_{timestamp}.mp4"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Get intro and outro files
            intro_file = Path("assets/videos/intro.mp4") if include_intro else None
            outro_file = Path("assets/videos/outro.mp4") if include_outro else None
            
            # Step 1: Get durations
            intro_duration = self._get_duration(intro_file) if intro_file and intro_file.exists() else 0
            outro_duration = self._get_duration(outro_file) if outro_file and outro_file.exists() else 0
            narration_duration = self._get_duration(audio_file)
            
            self.logger.info(f"Durations - Intro: {intro_duration}s, Narration: {narration_duration}s, Outro: {outro_duration}s")
            
            # Step 2: Create main content video with narration
            main_video = temp_path / "main_content.mp4"
            self.logger.info(f"Creating main content with {len(clips)} clips, duration: {narration_duration}s")
            
            if not clips:
                self.logger.error("No clips provided for assembly!")
                return None
            
            if not self._create_main_content(clips, audio_file, main_video, narration_duration):
                self.logger.error("Failed to create main content")
                return None
            
            # Step 3: Concatenate with intro and outro (preserving their audio)
            parts = []
            
            if intro_file and intro_file.exists():
                parts.append(intro_file)
                self.logger.info(f"Including intro: {intro_file}")
            
            parts.append(main_video)
            
            if outro_file and outro_file.exists():
                parts.append(outro_file)
                self.logger.info(f"Including outro: {outro_file}")
            
            # Step 4: Final concatenation
            if len(parts) > 1:
                if not self._concatenate_with_audio(parts, output_file):
                    self.logger.error("Failed to concatenate final video")
                    return None
            else:
                # Just copy the main video if no bookends
                import shutil
                shutil.copy2(main_video, output_file)
            
            # Verify output
            if output_file.exists() and output_file.stat().st_size > 1000:
                total_duration = self._get_duration(output_file)
                self.logger.info(f"Video assembled successfully: {output_file}")
                self.logger.info(f"Total duration: {total_duration:.1f}s")
                return output_file
            else:
                self.logger.error("Output file is missing or too small")
                return None
    
    def _get_duration(self, file_path: Path) -> float:
        """Get duration of media file in seconds"""
        if not file_path or not file_path.exists():
            return 0
            
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(file_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except:
            return 0
    
    def _create_main_content(self, clips: List[Path], audio_file: Path, output_file: Path, duration: float) -> bool:
        """Create the main content video with narration"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # First, concatenate all stock clips
                concat_file = temp_path / "concatenated.mp4"
                if not self._concatenate_clips(clips, concat_file):
                    return False
                
                # Loop video to match narration duration
                looped_file = temp_path / "looped.mp4"
                if not self._loop_video_to_duration(concat_file, looped_file, duration):
                    return False
                
                # Combine with narration audio
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(looped_file),
                    '-i', str(audio_file),
                    '-map', '0:v:0',  # Video from first input
                    '-map', '1:a:0',  # Audio from second input
                    '-c:v', self.codec,
                    '-preset', self.preset,
                    '-crf', str(self.crf),
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-ar', '44100',
                    '-ac', '2',
                    '-t', str(duration),
                    '-shortest',
                    str(output_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"Failed to create main content: {result.stderr}")
                    return False
                    
                return True
                
        except Exception as e:
            self.logger.error(f"Error creating main content: {e}")
            return False
    
    def _concatenate_clips(self, clips: List[Path], output_file: Path) -> bool:
        """Concatenate video clips without audio"""
        try:
            self.logger.info(f"Concatenating {len(clips)} clips")
            
            # Verify clips exist
            valid_clips = [clip for clip in clips if clip.exists()]
            if not valid_clips:
                self.logger.error("No valid clips found for concatenation!")
                return False
            
            self.logger.info(f"Found {len(valid_clips)} valid clips")
            
            # Create list file
            list_file = output_file.parent / "concat_list.txt"
            with open(list_file, 'w') as f:
                for clip in valid_clips:
                    f.write(f"file '{clip.absolute()}'\n")
            
            # Concatenate
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(list_file),
                '-c:v', self.codec,
                '-preset', self.preset,
                '-crf', str(self.crf),
                '-an',  # No audio for stock footage concatenation
                '-vf', f'scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2',
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Concatenation failed: {e}")
            return False
    
    def _loop_video_to_duration(self, input_file: Path, output_file: Path, duration: float) -> bool:
        """Loop video to match target duration"""
        try:
            input_duration = self._get_duration(input_file)
            if input_duration <= 0:
                return False
            
            loops = int(duration / input_duration) + 1
            
            cmd = [
                'ffmpeg', '-y',
                '-stream_loop', str(loops),
                '-i', str(input_file),
                '-t', str(duration),
                '-c:v', self.codec,
                '-preset', self.preset,
                '-crf', str(self.crf),
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Looping failed: {e}")
            return False
    
    def _concatenate_with_audio(self, parts: List[Path], output_file: Path) -> bool:
        """Concatenate video parts with fade transitions"""
        try:
            # If we have multiple parts, add transitions
            if len(parts) > 1:
                # Add fade transition between intro and main content
                transition_duration = 0.5  # Half second fade
                
                # Build complex filter for transitions
                filter_parts = []
                
                # Process each video with fade effects
                temp_parts = []
                for i, part in enumerate(parts):
                    temp_file = output_file.parent / f"part_{i}_fade.mp4"
                    
                    if i == 0:  # Intro - add fade out at the end
                        cmd = [
                            'ffmpeg', '-y',
                            '-i', str(part),
                            '-vf', f'fade=t=out:st={self._get_duration(part)-transition_duration}:d={transition_duration}',
                            '-c:a', 'copy',
                            str(temp_file)
                        ]
                    elif i == len(parts) - 1:  # Outro - add fade in at the beginning
                        cmd = [
                            'ffmpeg', '-y',
                            '-i', str(part),
                            '-vf', f'fade=t=in:st=0:d={transition_duration}',
                            '-c:a', 'copy',
                            str(temp_file)
                        ]
                    else:  # Main content - add both fade in and out
                        cmd = [
                            'ffmpeg', '-y',
                            '-i', str(part),
                            '-vf', f'fade=t=in:st=0:d={transition_duration},fade=t=out:st={self._get_duration(part)-transition_duration}:d={transition_duration}',
                            '-c:a', 'copy',
                            str(temp_file)
                        ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        self.logger.error(f"Failed to add fade to part {i}: {result.stderr}")
                        # Use original file if fade fails
                        temp_parts.append(part)
                    else:
                        temp_parts.append(temp_file)
                
                # Now concatenate the parts with transitions
                list_file = output_file.parent / "final_concat_list.txt"
                with open(list_file, 'w') as f:
                    for part in temp_parts:
                        if part.exists():
                            f.write(f"file '{part.absolute()}'\n")
                
                # Final concatenation
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(list_file),
                    '-c:v', self.codec,
                    '-preset', self.preset,
                    '-crf', str(self.crf),
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-ar', '44100',
                    '-ac', '2',
                    '-movflags', '+faststart',
                    str(output_file)
                ]
                
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"Final concatenation failed: {result.stderr}")
                    return False
                
                # Clean up temp files after successful concatenation
                for temp_file in temp_parts:
                    if temp_file.exists():
                        temp_file.unlink()
                
                return True
            
            else:
                # Single part - just copy
                import shutil
                shutil.copy2(parts[0], output_file)
                return True
            
        except Exception as e:
            self.logger.error(f"Final concatenation error: {e}")
            return False