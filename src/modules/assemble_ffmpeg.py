"""FFmpeg-based video assembly module that properly handles audio and duration."""

import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import tempfile

from ..utils.config import get_config
from ..utils.logger import get_logger


class FFmpegVideoAssembler:
    """Assembles videos using direct ffmpeg commands for reliability."""
    
    def __init__(self, dry_run: bool = False):
        """Initialize FFmpeg video assembler.
        
        Args:
            dry_run: If True, create mock video file
        """
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.dry_run = dry_run
        
        # Load video configuration
        self.video_config = self.config.get_video_config()
        self.fps = self.video_config.get('fps', 30)
        self.resolution = self.video_config.get('resolution', '1920x1080')
        self.bitrate = self.video_config.get('bitrate', '12M')
        self.codec = self.video_config.get('codec', 'libx264')
        self.fade_duration = self.video_config.get('fade_duration', 0.2)
        
        # Parse resolution
        self.width, self.height = map(int, self.resolution.split('x'))
        
        # Check ffmpeg availability
        self.ffmpeg_available = self._check_ffmpeg()
        
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available."""
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("ffmpeg not found in PATH")
            return False
    
    def assemble(self,
                 audio_file: Path,
                 clips: List[Path],
                 thumbnail_file: Optional[Path] = None,
                 script: Optional[Dict[str, Any]] = None,
                 output_dir: Optional[Path] = None,
                 include_intro: bool = True,
                 include_outro: bool = True) -> Path:
        """Main assembly method matching expected interface.
        
        Args:
            audio_file: Path to audio file
            clips: List of video clip paths
            thumbnail_file: Optional thumbnail path
            script: Optional script metadata
            output_dir: Output directory
            include_intro: Whether to include intro video
            include_outro: Whether to include outro video
            
        Returns:
            Path to output video
        """
        if output_dir is None:
            output_dir = Path('data/out')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"video_{timestamp}.mp4"
        
        # Get audio duration
        audio_duration = self._get_audio_duration(audio_file)
        if audio_duration <= 0:
            self.logger.error(f"Invalid audio duration: {audio_duration}")
            raise ValueError(f"Invalid audio duration: {audio_duration}")
            
        self.logger.info(f"Audio duration: {audio_duration:.1f} seconds")
        
        if self.dry_run or not self.ffmpeg_available:
            # Create mock video
            output_file.touch()
            self._save_metadata({
                'video_file': str(output_file),
                'duration_seconds': audio_duration,
                'duration_minutes': audio_duration / 60,
                'dry_run': True
            }, output_dir)
            return output_file
        
        # Assemble with ffmpeg
        success = self._assemble_with_ffmpeg(
            audio_file, clips, output_file, audio_duration, thumbnail_file, include_intro, include_outro
        )
        
        if not success:
            raise RuntimeError("Video assembly failed")
            
        # Save metadata
        self._save_metadata({
            'video_file': str(output_file),
            'duration_seconds': audio_duration,
            'duration_minutes': audio_duration / 60,
            'resolution': self.resolution,
            'fps': self.fps,
            'num_clips': len(clips),
            'has_audio': True,
            'generated_at': datetime.now().isoformat()
        }, output_dir)
        
        return output_file
    
    def _get_audio_duration(self, audio_file: Path) -> float:
        """Get duration of audio file using ffprobe.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Duration in seconds
        """
        if not audio_file.exists():
            self.logger.error(f"Audio file not found: {audio_file}")
            return 0
            
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(audio_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            return duration
        except (subprocess.CalledProcessError, ValueError) as e:
            self.logger.error(f"Failed to get audio duration: {e}")
            # Try to read from metadata file
            metadata_file = audio_file.with_suffix('.json')
            if metadata_file.exists():
                with open(metadata_file) as f:
                    data = json.load(f)
                    return data.get('duration_seconds', 180)
            return 180  # Default 3 minutes
    
    def _assemble_with_ffmpeg(self,
                             audio_file: Path,
                             clips: List[Path],
                             output_file: Path,
                             audio_duration: float,
                             thumbnail_file: Optional[Path] = None,
                             include_intro: bool = True,
                             include_outro: bool = True) -> bool:
        """Assemble video using ffmpeg directly.
        
        Args:
            audio_file: Path to audio file
            clips: List of video clip paths
            output_file: Output video path
            audio_duration: Target duration in seconds
            thumbnail_file: Optional thumbnail for intro
            
        Returns:
            True if successful
        """
        try:
            # Filter out non-existent clips
            valid_clips = [c for c in clips if c.exists()]
            
            if not valid_clips:
                self.logger.warning("No valid video clips found, creating black video")
                return self._create_black_video_with_audio(
                    audio_file, output_file, audio_duration
                )
            
            # Create temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Step 1: Check for intro and outro videos
                intro_file = None
                outro_file = None
                
                if include_intro:
                    intro_path = Path("assets/videos/intro.mp4")
                    if intro_path.exists():
                        intro_file = intro_path
                        self.logger.info(f"Using intro video: {intro_file}")
                    else:
                        self.logger.warning("Intro video not found at assets/videos/intro.mp4")
                
                if include_outro:
                    outro_path = Path("assets/videos/outro.mp4")
                    if outro_path.exists():
                        outro_file = outro_path
                        self.logger.info(f"Using outro video: {outro_file}")
                    else:
                        self.logger.warning("Outro video not found at assets/videos/outro.mp4")
                
                # Step 2: Concatenate all clips (with intro and outro if available)
                concat_file = temp_path / "concatenated.mp4"
                if not self._concatenate_clips(valid_clips, concat_file, intro_file, outro_file):
                    return False
                
                # Step 3: Loop concatenated video to match audio duration
                looped_file = temp_path / "looped.mp4"
                if not self._loop_video_to_duration(concat_file, looped_file, audio_duration):
                    return False
                
                # Step 4: Combine video with audio
                if not self._combine_video_audio(looped_file, audio_file, output_file, audio_duration):
                    return False
                
            # Verify output
            if output_file.exists() and output_file.stat().st_size > 1000:
                self.logger.info(f"Video assembled successfully: {output_file}")
                self._verify_output(output_file)
                return True
            else:
                self.logger.error("Output file is missing or too small")
                return False
                
        except Exception as e:
            self.logger.error(f"FFmpeg assembly failed: {e}")
            return False
    
    def _create_intro_from_thumbnail(self, thumbnail_file: Path, output_file: Path) -> bool:
        """Create a 3-second intro video from thumbnail.
        
        Args:
            thumbnail_file: Path to thumbnail image
            output_file: Output video path
            
        Returns:
            True if successful
        """
        try:
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-framerate', str(self.fps),
                '-i', str(thumbnail_file),
                '-c:v', self.codec,
                '-t', '3',
                '-pix_fmt', 'yuv420p',
                '-vf', f'scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2',
                str(output_file)
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to create intro: {e}")
            return False
    
    def _concatenate_clips(self, clips: List[Path], output_file: Path, 
                          intro_file: Optional[Path] = None, outro_file: Optional[Path] = None) -> bool:
        """Concatenate video clips using ffmpeg concat demuxer.
        
        Args:
            clips: List of video clips to concatenate
            output_file: Output file path
            intro_file: Optional intro video to prepend
            outro_file: Optional outro video to append
            
        Returns:
            True if successful
        """
        try:
            # Create concat list file
            list_file = output_file.parent / "concat_list.txt"
            with open(list_file, 'w') as f:
                # Add intro if available
                if intro_file and intro_file.exists():
                    f.write(f"file '{intro_file.absolute()}'\n")
                # Add all clips
                for clip in clips:
                    f.write(f"file '{clip.absolute()}'\n")
                # Add outro if available
                if outro_file and outro_file.exists():
                    f.write(f"file '{outro_file.absolute()}'\n")
            
            # Concatenate with re-encoding for consistency
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(list_file),
                '-c:v', self.codec,
                '-preset', 'fast',
                '-crf', '23',
                '-vf', f'scale={self.width}:{self.height}:force_original_aspect_ratio=decrease,pad={self.width}:{self.height}:(ow-iw)/2:(oh-ih)/2,setsar=1',
                '-r', str(self.fps),
                '-pix_fmt', 'yuv420p',
                '-an',  # No audio in concatenated clips
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            list_file.unlink()  # Clean up
            
            if result.returncode != 0:
                self.logger.error(f"Concatenation failed: {result.stderr}")
                return False
                
            return output_file.exists()
            
        except Exception as e:
            self.logger.error(f"Failed to concatenate clips: {e}")
            return False
    
    def _loop_video_to_duration(self, input_file: Path, output_file: Path, duration: float) -> bool:
        """Loop video to match target duration.
        
        Args:
            input_file: Input video file
            output_file: Output video file
            duration: Target duration in seconds
            
        Returns:
            True if successful
        """
        try:
            # Get input video duration
            probe_cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(input_file)
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            input_duration = float(result.stdout.strip())
            
            self.logger.info(f"Input video duration: {input_duration}s, target: {duration}s")
            
            if input_duration >= duration:
                # Just trim if longer than needed
                self.logger.info(f"Trimming video from {input_duration}s to {duration}s")
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(input_file),
                    '-t', str(duration),
                    '-c', 'copy',
                    str(output_file)
                ]
            else:
                # Loop video to extend duration
                loops_needed = int(duration / input_duration) + 2  # Add extra loop for safety
                self.logger.info(f"Looping video {loops_needed} times to reach {duration}s")
                
                # Use filter_complex for more reliable looping
                cmd = [
                    'ffmpeg', '-y',
                    '-stream_loop', str(loops_needed),
                    '-i', str(input_file),
                    '-t', str(duration),
                    '-c:v', self.codec,  # Re-encode for reliability
                    '-preset', 'fast',
                    '-crf', '23',
                    '-r', str(self.fps),
                    '-pix_fmt', 'yuv420p',
                    '-an',  # No audio in looped video
                    str(output_file)
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Loop command failed: {result.stderr[:500]}")
                return False
                
            # Verify the output duration
            if output_file.exists():
                verify_cmd = [
                    'ffprobe', '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(output_file)
                ]
                verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
                if verify_result.returncode == 0:
                    actual_duration = float(verify_result.stdout.strip())
                    self.logger.info(f"Looped video duration: {actual_duration}s")
                    
            return output_file.exists()
            
        except (subprocess.CalledProcessError, ValueError) as e:
            self.logger.error(f"Failed to loop video: {e}")
            return False
    
    def _combine_video_audio(self, video_file: Path, audio_file: Path, output_file: Path, duration: float) -> bool:
        """Combine video and audio streams.
        
        Args:
            video_file: Video file path
            audio_file: Audio file path  
            output_file: Output file path
            duration: Target duration
            
        Returns:
            True if successful
        """
        try:
            # First approach: Use the audio duration as the master duration
            # This ensures the full audio plays even if video needs to loop
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_file),
                '-i', str(audio_file),
                '-map', '0:v:0',  # Use first video stream from first input
                '-map', '1:a:0',  # Use first audio stream from second input
                '-c:v', 'copy',  # Copy video stream
                '-c:a', 'aac',  # Encode audio as AAC
                '-b:a', '192k',  # Audio bitrate
                '-ar', '44100',  # Audio sample rate
                '-ac', '2',  # Stereo audio
                '-t', str(duration),  # Set duration to audio duration
                '-movflags', '+faststart',  # Optimize for streaming
                str(output_file)
            ]
            
            self.logger.info(f"Combining video and audio with duration: {duration}s")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.warning(f"First attempt failed: {result.stderr[:200]}")
                
                # Second approach: Re-encode video if copy fails
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(video_file),
                    '-i', str(audio_file),
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-c:v', self.codec,  # Re-encode video
                    '-preset', 'fast',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-ar', '44100',
                    '-ac', '2',
                    '-t', str(duration),
                    '-movflags', '+faststart',
                    str(output_file)
                ]
                
                self.logger.info("Retrying with video re-encoding...")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Failed to combine video and audio: {e}")
            return False
    
    def _create_black_video_with_audio(self, audio_file: Path, output_file: Path, duration: float) -> bool:
        """Create a black video with audio as fallback.
        
        Args:
            audio_file: Audio file path
            output_file: Output file path
            duration: Video duration
            
        Returns:
            True if successful
        """
        try:
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi',
                '-i', f'color=c=black:s={self.width}x{self.height}:r={self.fps}:d={duration}',
                '-i', str(audio_file),
                '-map', '0:v',
                '-map', '1:a',
                '-c:v', self.codec,
                '-preset', 'fast',
                '-crf', '23',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                '-movflags', '+faststart',
                str(output_file)
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to create black video: {e}")
            return False
    
    def _verify_output(self, output_file: Path):
        """Verify the output video has both audio and video streams.
        
        Args:
            output_file: Path to output video
        """
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_streams',
                '-of', 'json',
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            has_video = any(s['codec_type'] == 'video' for s in data['streams'])
            has_audio = any(s['codec_type'] == 'audio' for s in data['streams'])
            
            if has_audio:
                audio_stream = next(s for s in data['streams'] if s['codec_type'] == 'audio')
                self.logger.info(f"Audio stream found: {audio_stream.get('codec_name')} @ {audio_stream.get('bit_rate', 'unknown')} bps")
                
            if has_video:
                video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
                duration = float(video_stream.get('duration', 0))
                self.logger.info(f"Video stream found: {video_stream.get('codec_name')} @ {duration:.1f}s")
            
            if not has_audio:
                self.logger.warning("WARNING: Output video has NO AUDIO!")
            if not has_video:
                self.logger.warning("WARNING: Output video has NO VIDEO!")
                
        except Exception as e:
            self.logger.warning(f"Could not verify output: {e}")
    
    def _save_metadata(self, metadata: Dict[str, Any], output_dir: Path):
        """Save assembly metadata.
        
        Args:
            metadata: Metadata dictionary
            output_dir: Output directory
        """
        metadata_file = output_dir / f"assembly_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        self.logger.info(f"Metadata saved to {metadata_file}")


# Compatibility wrapper for existing code
class VideoAssembler(FFmpegVideoAssembler):
    """Compatibility wrapper for existing VideoAssembler interface."""
    
    def assemble_video(self,
                      audio_path: Path,
                      clips_dir: Path, 
                      output_dir: Path,
                      script: Optional[Dict[str, Any]] = None,
                      thumbnail_path: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
        """Legacy interface for video assembly.
        
        Args:
            audio_path: Path to audio file
            clips_dir: Directory containing clips
            output_dir: Output directory
            script: Optional script metadata
            thumbnail_path: Optional thumbnail
            
        Returns:
            Tuple of (video_path, metadata)
        """
        # Get list of clips from directory
        clips = sorted(clips_dir.glob('*.mp4'))
        
        # Call new interface
        video_path = self.assemble(
            audio_file=audio_path,
            clips=clips,
            thumbnail_file=thumbnail_path,
            script=script,
            output_dir=output_dir
        )
        
        # Create legacy metadata format
        metadata = {
            'video_file': str(video_path.name),
            'duration_seconds': self._get_audio_duration(audio_path),
            'duration_minutes': self._get_audio_duration(audio_path) / 60,
            'resolution': self.resolution,
            'fps': self.fps,
            'generated_at': datetime.now().isoformat()
        }
        
        return video_path, metadata