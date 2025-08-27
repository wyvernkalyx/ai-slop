"""Text-to-Speech module for converting scripts to audio."""

import json
import time
import wave
import struct
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

from ..utils.config import get_config
from ..utils.logger import get_logger


class TextToSpeech:
    """Converts text scripts to speech audio."""
    
    def __init__(self, dry_run: bool = False):
        """Initialize TTS module.
        
        Args:
            dry_run: If True, generate mock audio files
        """
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.dry_run = dry_run
        
        # Load TTS configuration
        self.tts_config = self.config.get_tts_config()
        self.provider = self.tts_config.get('provider', 'elevenlabs')
        self.voice_id = self.tts_config.get('voice_id', 'rachel')
        self.output_format = self.tts_config.get('output_format', 'mp3')
        
        self.client = None
        if not dry_run and self.config.is_feature_enabled('tts'):
            self._init_tts_client()
            
    def _init_tts_client(self):
        """Initialize TTS API client."""
        try:
            if self.provider == 'elevenlabs':
                # Import the real ElevenLabs implementation
                from .tts_real import ElevenLabsTTS
                api_key = self.tts_config.get('api_key')
                if api_key:
                    self.client = ElevenLabsTTS(api_key)
                    if self.client.test_connection():
                        self.logger.info("ElevenLabs TTS initialized successfully")
                    else:
                        self.logger.warning("ElevenLabs API key invalid or connection failed")
                        self.client = None
                else:
                    self.logger.warning("No ElevenLabs API key found in configuration")
                    self.client = None
            else:
                self.logger.warning(f"TTS provider {self.provider} not implemented")
                self.client = None
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS client: {e}")
            self.client = None
            
    def generate_audio(self, 
                      script: Dict[str, Any], 
                      output_dir: Path,
                      voice_settings: Optional[Dict[str, Any]] = None) -> Tuple[Path, float]:
        """Generate audio from script.
        
        Args:
            script: Script dictionary in script.v1 format
            output_dir: Output directory for audio file
            voice_settings: Optional voice customization settings
            
        Returns:
            Tuple of (audio_file_path, duration_seconds)
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract narration text
        narration_text = self._extract_narration(script)
        
        if self.dry_run or not self.client:
            # Generate mock audio
            audio_path, duration = self._generate_mock_audio(narration_text, output_dir, script.get('post_id', 'unknown'))
        else:
            # Generate real audio via API
            audio_path, duration = self._generate_real_audio(narration_text, output_dir, script.get('post_id', 'unknown'), voice_settings)
            
        self.logger.info(f"Generated audio: {audio_path} (duration: {duration:.1f}s)")
        
        # Save audio metadata
        self._save_audio_metadata(audio_path, script, duration)
        
        return audio_path, duration
        
    def _extract_narration(self, script: Dict[str, Any]) -> str:
        """Extract full narration text from script.
        
        Args:
            script: Script dictionary
            
        Returns:
            Complete narration text
        """
        parts = []
        
        # Add hook
        if 'hook' in script:
            parts.append(script['hook'])
            parts.append("")  # Pause
            
        narration = script.get('narration', {})
        
        # Add intro
        if 'intro' in narration:
            parts.append(narration['intro'])
            parts.append("")  # Pause
            
        # Add chapters
        for chapter in narration.get('chapters', []):
            if 'heading' in chapter:
                parts.append(f"{chapter['heading']}.")
            if 'body' in chapter:
                parts.append(chapter['body'])
            parts.append("")  # Pause between chapters
            
        # Add outro
        if 'outro' in narration:
            parts.append(narration['outro'])
            
        return "\n\n".join(parts)
        
    def _generate_mock_audio(self, text: str, output_dir: Path, post_id: str) -> Tuple[Path, float]:
        """Generate mock audio file for testing.
        
        Args:
            text: Text to convert
            output_dir: Output directory
            post_id: Post identifier
            
        Returns:
            Tuple of (audio_path, duration)
        """
        # Calculate duration (165 words per minute)
        word_count = len(text.split())
        duration = (word_count / 165) * 60  # seconds
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"audio_{post_id}_{timestamp}.wav"
        audio_path = output_dir / filename
        
        # Create a WAV file with generated tones to simulate speech
        sample_rate = 44100
        num_samples = int(sample_rate * duration)  # Full duration, no cap
        
        # Generate a simple tone (440 Hz = A4 note) with variations
        import math
        samples = []
        base_frequency = 440  # A4 note
        
        for i in range(num_samples):
            # Create a varying tone to simulate speech rhythm
            # Change frequency every 0.5 seconds
            segment = int(i / (sample_rate * 0.5))
            
            # Vary frequency between 200-600 Hz to simulate speech
            frequency = base_frequency + (segment % 10) * 40 - 200
            
            # Generate sine wave with varying amplitude
            amplitude = 16000 * (0.5 + 0.5 * math.sin(i / sample_rate * 2))  # Volume modulation
            t = i / sample_rate
            
            # Mix two frequencies for more natural sound
            sample = int(amplitude * (
                0.7 * math.sin(2 * math.pi * frequency * t) +
                0.3 * math.sin(2 * math.pi * frequency * 1.5 * t)
            ))
            
            # Clamp to 16-bit range
            sample = max(-32767, min(32767, sample))
            samples.append(struct.pack('<h', sample))
            
        # Write WAV file
        with wave.open(str(audio_path), 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b''.join(samples))
            
        self.logger.info(f"Generated mock audio: {word_count} words, {duration:.1f}s")
        
        return audio_path, duration
        
    def _generate_real_audio(self, 
                           text: str, 
                           output_dir: Path, 
                           post_id: str,
                           voice_settings: Optional[Dict[str, Any]] = None) -> Tuple[Path, float]:
        """Generate real audio via TTS API.
        
        Args:
            text: Text to convert
            output_dir: Output directory
            post_id: Post identifier
            voice_settings: Voice customization settings
            
        Returns:
            Tuple of (audio_path, duration)
        """
        if self.client and hasattr(self.client, 'generate_audio'):
            try:
                # Generate timestamp for unique filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = output_dir / f"audio_{post_id}_{timestamp}"
                
                # Use the real ElevenLabs client
                audio_path, duration = self.client.generate_audio(
                    text=text,
                    output_path=output_path,
                    voice=self.voice_id,
                    model="eleven_monolingual_v1"
                )
                
                self.logger.info(f"Generated REAL audio via ElevenLabs: {audio_path}")
                return audio_path, duration
                
            except Exception as e:
                self.logger.error(f"ElevenLabs generation failed: {e}")
                self.logger.warning("Falling back to mock audio")
                return self._generate_mock_audio(text, output_dir, post_id)
        else:
            # No client available, use mock
            self.logger.warning("No TTS client available, using mock audio")
            return self._generate_mock_audio(text, output_dir, post_id)
        
    def _save_audio_metadata(self, audio_path: Path, script: Dict[str, Any], duration: float):
        """Save audio metadata to JSON file.
        
        Args:
            audio_path: Path to audio file
            script: Original script
            duration: Audio duration in seconds
        """
        metadata = {
            'audio_file': str(audio_path.name),
            'duration_seconds': duration,
            'duration_minutes': duration / 60,
            'script_title': script.get('title', ''),
            'post_id': script.get('post_id', ''),
            'generated_at': datetime.now().isoformat(),
            'voice_id': self.voice_id,
            'provider': self.provider
        }
        
        metadata_path = audio_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
    def estimate_cost(self, text: str) -> Dict[str, Any]:
        """Estimate TTS generation cost.
        
        Args:
            text: Text to convert
            
        Returns:
            Cost estimation dictionary
        """
        character_count = len(text)
        word_count = len(text.split())
        
        # Cost estimates (example rates)
        costs = {
            'elevenlabs': character_count * 0.00003,  # $0.30 per 10k chars
            'azure': character_count * 0.00001,  # $0.10 per 10k chars
            'playht': character_count * 0.00002,  # $0.20 per 10k chars
        }
        
        return {
            'character_count': character_count,
            'word_count': word_count,
            'estimated_duration_minutes': word_count / 165,
            'provider': self.provider,
            'estimated_cost': costs.get(self.provider, 0),
            'cost_breakdown': costs
        }
        
    def split_text_for_api(self, text: str, max_chars: int = 5000) -> List[str]:
        """Split text into chunks for API limits.
        
        Args:
            text: Text to split
            max_chars: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        # Split by sentences to avoid cutting mid-sentence
        sentences = text.replace('\n', ' ').split('. ')
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 2 <= max_chars:
                if current_chunk:
                    current_chunk += ". " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk + ".")
                current_chunk = sentence
                
        if current_chunk:
            chunks.append(current_chunk + "." if not current_chunk.endswith('.') else current_chunk)
            
        return chunks
        
    def combine_audio_files(self, audio_paths: List[Path], output_path: Path) -> Path:
        """Combine multiple audio files into one.
        
        Args:
            audio_paths: List of audio file paths
            output_path: Output file path
            
        Returns:
            Combined audio file path
        """
        # This would use pydub or similar to combine audio files
        # For now, just return the first file
        if audio_paths:
            return audio_paths[0]
        return output_path


def main():
    """Test the TTS module."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Text-to-Speech conversion')
    parser.add_argument('--input', type=str, help='Input script JSON file')
    parser.add_argument('--text', type=str, help='Direct text to convert')
    parser.add_argument('--dry-run', action='store_true', help='Generate mock audio')
    parser.add_argument('--output', type=str, default='data/out', help='Output directory')
    args = parser.parse_args()
    
    tts = TextToSpeech(dry_run=args.dry_run)
    
    if args.input:
        # Load script from file
        with open(args.input, 'r') as f:
            script = json.load(f)
            
        # Estimate cost
        narration_text = tts._extract_narration(script)
        cost_estimate = tts.estimate_cost(narration_text)
        
        print(f"Script: {script.get('title', 'Unknown')}")
        print(f"Words: {cost_estimate['word_count']}")
        print(f"Est. duration: {cost_estimate['estimated_duration_minutes']:.1f} minutes")
        print(f"Est. cost: ${cost_estimate['estimated_cost']:.4f}")
        
        # Generate audio
        print("\nGenerating audio...")
        output_dir = Path(args.output)
        audio_path, duration = tts.generate_audio(script, output_dir)
        print(f"\nGenerated: {audio_path}")
        print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
            
    elif args.text:
        # Convert direct text
        script = {
            'title': 'Direct Text',
            'hook': args.text,
            'narration': {},
            'post_id': 'direct'
        }
        
        output_dir = Path(args.output)
        audio_path, duration = tts.generate_audio(script, output_dir)
        print(f"Generated: {audio_path}")
        print(f"Duration: {duration:.1f} seconds")
        
    else:
        # Test with sample script
        script = {
            'version': 'script.v1',
            'title': 'Test Script',
            'hook': 'This is a test of the text to speech system.',
            'narration': {
                'intro': 'Welcome to our test video. This is the introduction.',
                'chapters': [
                    {'id': 1, 'heading': 'Chapter 1', 'body': 'This is the first chapter content.'},
                    {'id': 2, 'heading': 'Chapter 2', 'body': 'This is the second chapter content.'}
                ],
                'outro': 'Thank you for watching this test. Goodbye!'
            },
            'post_id': 'test123'
        }
        
        output_dir = Path(args.output)
        audio_path, duration = tts.generate_audio(script, output_dir)
        print(f"Generated test audio: {audio_path}")
        print(f"Duration: {duration:.1f} seconds")


if __name__ == '__main__':
    main()