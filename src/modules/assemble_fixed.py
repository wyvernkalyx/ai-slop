#!/usr/bin/env python3
"""
Fixed Video Assembly Module for AI-Slop Pipeline
Addresses critical issues: 5-second videos and missing audio
"""

import os
import subprocess
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class VideoAssembler:
    def __init__(self):
        self.temp_dir = Path("temp_assembly")
        self.temp_dir.mkdir(exist_ok=True)
    
    def get_audio_duration(self, audio_path):
        """Get audio duration using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 
                'format=duration', '-of', 'csv=p=0', str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0
    
    def get_video_duration(self, video_path):
        """Get video duration using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 
                'format=duration', '-of', 'csv=p=0', str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            logger.error(f"Failed to get video duration: {e}")
            return 0.0
    
    def create_concatenated_video(self, video_clips, target_duration):
        """Create a single video file that loops to match target duration"""
        if not video_clips:
            raise ValueError("No video clips provided")
        
        concat_file = self.temp_dir / "concat_list.txt"
        total_clips_duration = 0
        
        # Calculate total duration of all clips
        for clip in video_clips:
            total_clips_duration += self.get_video_duration(clip)
        
        if total_clips_duration == 0:
            raise ValueError("All video clips have zero duration")
        
        # Calculate how many times we need to repeat the sequence
        repeat_count = max(1, int(target_duration / total_clips_duration) + 1)
        
        # Create concatenation file
        with open(concat_file, 'w') as f:
            for _ in range(repeat_count):
                for clip in video_clips:
                    f.write(f"file '{os.path.abspath(clip)}'\n")
        
        # Create concatenated video
        concat_output = self.temp_dir / "concatenated.mp4"
        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(concat_file),
            '-c', 'copy',
            str(concat_output)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return concat_output
        except subprocess.CalledProcessError as e:
            logger.error(f"Concatenation failed: {e.stderr.decode()}")
            raise
    
    def assemble_video(self, video_clips, audio_path, output_path):
        """
        Main assembly function - combines video clips with audio
        
        Args:
            video_clips: List of paths to video clip files
            audio_path: Path to audio file
            output_path: Path for final output video
        """
        logger.info(f"Starting video assembly with {len(video_clips)} clips and audio {audio_path}")
        
        # Step 1: Get audio duration (this determines final video length)
        audio_duration = self.get_audio_duration(audio_path)
        if audio_duration <= 0:
            raise ValueError(f"Audio file has invalid duration: {audio_duration}")
        
        logger.info(f"Target duration from audio: {audio_duration:.2f} seconds")
        
        # Step 2: Create concatenated/looped video to match audio duration
        concat_video = self.create_concatenated_video(video_clips, audio_duration)
        
        # Step 3: Combine video and audio with precise duration control
        cmd = [
            'ffmpeg', '-y',
            '-i', str(concat_video),  # Video input
            '-i', str(audio_path),    # Audio input
            '-t', str(audio_duration),  # Set exact duration to match audio
            '-c:v', 'libx264',        # Video codec
            '-c:a', 'aac',            # Audio codec
            '-b:a', '128k',           # Audio bitrate
            '-map', '0:v:0',          # Map first video stream
            '-map', '1:a:0',          # Map first audio stream
            '-shortest',              # Stop when shortest stream ends (should be audio)
            '-avoid_negative_ts', 'make_zero',
            str(output_path)
        ]
        
        logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info("Video assembly completed successfully")
            
            # Verify output
            if not os.path.exists(output_path):
                raise RuntimeError("Output file was not created")
            
            final_duration = self.get_video_duration(output_path)
            logger.info(f"Final video duration: {final_duration:.2f} seconds")
            
            if abs(final_duration - audio_duration) > 1.0:  # Allow 1 second tolerance
                logger.warning(f"Duration mismatch: expected {audio_duration:.2f}s, got {final_duration:.2f}s")
            
            return {
                'success': True,
                'output_path': output_path,
                'duration': final_duration,
                'audio_duration': audio_duration
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            logger.error(f"FFmpeg failed: {error_msg}")
            raise RuntimeError(f"Video assembly failed: {error_msg}")
        
        finally:
            # Cleanup temporary files
            self.cleanup()
    
    def cleanup(self):
        """Remove temporary files"""
        try:
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(exist_ok=True)  # Recreate empty dir
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
    
    def test_with_simple_case(self):
        """Test function for debugging"""
        # This can be used to test with minimal inputs
        logger.info("Running simple test case")
        
        # Create a simple test video (3 seconds, solid color)
        test_video = self.temp_dir / "test.mp4"
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', 
            '-i', 'color=blue:size=1280x720:duration=3',
            '-c:v', 'libx264', str(test_video)
        ]
        subprocess.run(cmd, check=True)
        
        return test_video


def main():
    """Test function"""
    logging.basicConfig(level=logging.INFO)
    
    assembler = VideoAssembler()
    
    # Test case - you'll need to provide actual file paths
    # video_clips = ['path/to/clip1.mp4', 'path/to/clip2.mp4']
    # audio_path = 'path/to/audio.wav'
    # output_path = 'output_test.mp4'
    
    # assembler.assemble_video(video_clips, audio_path, output_path)


if __name__ == "__main__":
    main()