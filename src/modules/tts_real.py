"""
Real ElevenLabs TTS implementation using REST API
"""

import json
import requests
import struct
import wave
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

class ElevenLabsTTS:
    """ElevenLabs Text-to-Speech implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
        self.headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        # Default voice IDs (Updated with actual ElevenLabs voices)
        self.voices = {
            "rachel": "21m00Tcm4TlvDq8ikWAM",     # Rachel - Female
            "sarah": "EXAVITQu4vr4xnSDxMaL",      # Sarah - Female
            "charlie": "IKne3meq5aSn9XLyUdCD",    # Charlie - Male
            "daniel": "onwK4e9ZLuTAKqWW03F9",     # Daniel - Male
            "george": "JBFqnCBsd6RMkjVDRZzb",     # George - Male
            "jessica": "cgSgspJ2msm6clMCkdW9",    # Jessica - Female
            "matilda": "XrExE9yKIg1WjnnlVkGX",    # Matilda - Female
            "liam": "TX3LPaxmHKxFdv7VOQHJ",       # Liam - Male
            "clyde": "2EiwWnXFnvU5JabPnv8n"       # Clyde - Male
        }
        
        # Voice presets for different content types
        self.voice_presets = {
            "documentary": {
                "voice": "daniel",
                "settings": {"stability": 0.7, "similarity_boost": 0.6, "style": 0.4, "use_speaker_boost": True}
            },
            "news": {
                "voice": "rachel",
                "settings": {"stability": 0.8, "similarity_boost": 0.7, "style": 0.3, "use_speaker_boost": True}
            },
            "storytelling": {
                "voice": "charlie",
                "settings": {"stability": 0.4, "similarity_boost": 0.5, "style": 0.7, "use_speaker_boost": True}
            },
            "tutorial": {
                "voice": "jessica",
                "settings": {"stability": 0.6, "similarity_boost": 0.6, "style": 0.5, "use_speaker_boost": True}
            },
            "mystery": {
                "voice": "clyde",
                "settings": {"stability": 0.5, "similarity_boost": 0.5, "style": 0.8, "use_speaker_boost": True}
            },
            "energetic": {
                "voice": "sarah",
                "settings": {"stability": 0.3, "similarity_boost": 0.5, "style": 0.9, "use_speaker_boost": True}
            },
            "calm": {
                "voice": "george",
                "settings": {"stability": 0.9, "similarity_boost": 0.7, "style": 0.2, "use_speaker_boost": False}
            }
        }
        
    def _find_voice_by_name(self, name: str) -> Optional[str]:
        """
        Find a voice ID by name from the ElevenLabs API
        
        Args:
            name: Voice name to search for (case insensitive)
            
        Returns:
            Voice ID if found, None otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/voices",
                headers={"xi-api-key": self.api_key}
            )
            
            if response.status_code == 200:
                voices = response.json().get('voices', [])
                
                # Search for exact match (case insensitive)
                for voice in voices:
                    if voice.get('name', '').lower() == name.lower():
                        voice_id = voice.get('voice_id')
                        print(f"Found custom voice: {voice.get('name')} (ID: {voice_id})")
                        return voice_id
                
                # Search for partial match if no exact match
                for voice in voices:
                    if name.lower() in voice.get('name', '').lower():
                        voice_id = voice.get('voice_id')
                        print(f"Found custom voice (partial match): {voice.get('name')} (ID: {voice_id})")
                        return voice_id
                        
            return None
        except Exception as e:
            print(f"Error searching for voice: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test if the API key is valid"""
        try:
            # Test with voices endpoint which doesn't require user_read permission
            response = requests.get(
                f"{self.base_url}/voices",
                headers={"xi-api-key": self.api_key}
            )
            if response.status_code == 200:
                voices = response.json().get('voices', [])
                print(f"[+] ElevenLabs connected: {len(voices)} voices available")
                return True
            else:
                print(f"[-] ElevenLabs API error: {response.status_code}")
                return False
        except Exception as e:
            print(f"[-] ElevenLabs connection failed: {e}")
            return False
    
    def generate_audio(self, 
                      text: str, 
                      output_path: Path,
                      voice: str = "rachel",
                      model: str = "eleven_monolingual_v1",
                      voice_settings: Optional[Dict[str, Any]] = None) -> Tuple[Path, float]:
        """
        Generate audio from text using ElevenLabs API
        
        Args:
            text: Text to convert to speech
            output_path: Where to save the audio file
            voice: Voice name or ID
            model: ElevenLabs model to use
            voice_settings: Optional custom voice settings dict with:
                - stability: 0.0-1.0 (consistency vs expression)
                - similarity_boost: 0.0-1.0 (voice similarity)
                - style: 0.0-1.0 (style exaggeration)
                - use_speaker_boost: true/false (voice enhancement)
            
        Returns:
            Tuple of (audio_path, duration_seconds)
        """
        
        # Get voice ID
        # First check if it's a predefined voice
        voice_id = self.voices.get(voice.lower())
        
        # If not found in predefined voices, try to find it in the API
        if not voice_id:
            # Check if it's already a voice ID (20+ chars)
            if len(voice) >= 20:
                voice_id = voice
            else:
                # Try to find custom voice by name
                voice_id = self._find_voice_by_name(voice)
                if not voice_id:
                    print(f"Warning: Voice '{voice}' not found, using default 'Rachel'")
                    voice_id = self.voices.get("rachel")  # Default to Rachel
            
        # API endpoint
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        # Request payload
        if voice_settings is None:
            # Default settings
            voice_settings = {
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0.5,
                "use_speaker_boost": True
            }
        
        data = {
            "text": text,
            "model_id": model,
            "voice_settings": voice_settings
        }
        
        try:
            # Make request
            print(f"[*] Generating audio with ElevenLabs (voice: {voice})...")
            print(f"    Text length: {len(text)} characters")
            
            response = requests.post(
                url,
                json=data,
                headers=self.headers
            )
            
            if response.status_code == 200:
                # Save audio file
                audio_path = output_path.with_suffix('.mp3')
                with open(audio_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"[+] Audio saved to: {audio_path}")
                
                # Convert MP3 to WAV for compatibility
                wav_path = self.convert_to_wav(audio_path, output_path)
                
                # Get duration
                duration = self.get_wav_duration(wav_path)
                
                return wav_path, duration
                
            else:
                error = response.json() if response.headers.get('content-type') == 'application/json' else response.text
                raise Exception(f"API error {response.status_code}: {error}")
                
        except Exception as e:
            print(f"[-] ElevenLabs generation failed: {e}")
            print(f"    Full error: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fall back to creating silent audio
            raise Exception(f"ElevenLabs TTS failed: {e}")
    
    def convert_to_wav(self, mp3_path: Path, output_path: Path) -> Path:
        """Convert MP3 to WAV using ffmpeg or create a placeholder"""
        wav_path = output_path.with_suffix('.wav')
        
        try:
            import subprocess
            # Try to use ffmpeg
            result = subprocess.run(
                ['ffmpeg', '-i', str(mp3_path), '-ar', '44100', '-ac', '1', str(wav_path), '-y'],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"[+] Converted to WAV: {wav_path}")
                mp3_path.unlink()  # Delete MP3
                return wav_path
        except:
            pass
        
        # If ffmpeg fails, try using pydub
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(str(mp3_path))
            audio = audio.set_frame_rate(44100).set_channels(1)
            audio.export(str(wav_path), format="wav")
            print(f"[+] Converted to WAV using pydub: {wav_path}")
            mp3_path.unlink()
            return wav_path
        except:
            pass
        
        # If all else fails, rename MP3 to WAV (not ideal but works for some players)
        print(f"[!] Could not convert MP3, using as-is")
        mp3_path.rename(wav_path)
        return wav_path
    
    def get_wav_duration(self, wav_path: Path) -> float:
        """Get duration of WAV file in seconds"""
        try:
            with wave.open(str(wav_path), 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration = frames / float(rate)
                return duration
        except:
            # Estimate based on file size
            file_size = wav_path.stat().st_size
            # Rough estimate: 44100 Hz, 16-bit, mono = ~88KB per second
            return file_size / 88000
    
    def create_silent_audio(self, output_path: Path, text_length: int) -> Tuple[Path, float]:
        """Create silent audio as fallback"""
        # Estimate duration (150 words per minute, ~5 chars per word)
        words = text_length / 5
        duration = (words / 150) * 60  # seconds
        
        wav_path = output_path.with_suffix('.wav')
        sample_rate = 44100
        num_samples = int(sample_rate * duration)
        
        with wave.open(str(wav_path), 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            # Write silence
            samples = b'\x00\x00' * num_samples
            wav_file.writeframes(samples)
        
        print(f"[!] Created silent audio fallback: {duration:.1f}s")
        return wav_path, duration
    
    def generate_audio_with_preset(self,
                                  text: str,
                                  output_path: Path,
                                  preset: str = "documentary",
                                  model: str = "eleven_monolingual_v1") -> Tuple[Path, float]:
        """
        Generate audio using a content type preset or custom voice
        
        Args:
            text: Text to convert to speech
            output_path: Where to save the audio file
            preset: Content type preset OR custom voice name
            model: ElevenLabs model to use
            
        Returns:
            Tuple of (audio_path, duration_seconds)
        """
        # Check if it's a known preset
        if preset in self.voice_presets:
            preset_config = self.voice_presets[preset]
            print(f"[*] Using preset '{preset}' - Voice: {preset_config['voice']}")
            voice = preset_config['voice']
            settings = preset_config['settings']
        else:
            # Treat as custom voice name
            print(f"[*] Using custom voice: {preset}")
            voice = preset
            settings = {
                "stability": 0.5,
                "similarity_boost": 0.5,
                "style": 0.5,
                "use_speaker_boost": True
            }
        
        return self.generate_audio(
            text=text,
            output_path=output_path,
            voice=voice,
            model=model,
            voice_settings=settings
        )


def test_elevenlabs():
    """Test ElevenLabs integration"""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv('config/.env')
    api_key = os.getenv('ELEVENLABS_API_KEY')
    
    if not api_key:
        print("[-] No ElevenLabs API key found in .env")
        return
    
    # Initialize TTS
    tts = ElevenLabsTTS(api_key)
    
    # Test connection
    if not tts.test_connection():
        return
    
    # Test generation
    test_text = "Hello! This is a test of the ElevenLabs text to speech system. If you can hear this, it means the integration is working correctly."
    
    output_dir = Path('data/out/test_tts')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    
    audio_path, duration = tts.generate_audio(test_text, output_path)
    
    print(f"\n[+] Test complete!")
    print(f"    Audio file: {audio_path}")
    print(f"    Duration: {duration:.1f} seconds")
    print(f"    File size: {audio_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    test_elevenlabs()