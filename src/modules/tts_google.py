"""
Google Text-to-Speech module for AI-Slop
Free alternative to ElevenLabs with no credit requirements
"""

import os
from pathlib import Path
from gtts import gTTS
import pyttsx3
import tempfile
import wave
import subprocess

class GoogleTTS:
    def __init__(self):
        """Initialize Google TTS - no API key required!"""
        self.voices = {
            # gTTS language/accent options that work well for different styles
            "documentary": {"lang": "en", "tld": "co.uk", "slow": False},  # British accent
            "news": {"lang": "en", "tld": "com", "slow": False},  # US accent
            "storytelling": {"lang": "en", "tld": "com.au", "slow": False},  # Australian accent
            "tutorial": {"lang": "en", "tld": "com", "slow": False},  # US accent
            "mystery": {"lang": "en", "tld": "co.uk", "slow": True},  # British, slower
            "energetic": {"lang": "en", "tld": "com", "slow": False},  # US accent
            "calm": {"lang": "en", "tld": "ca", "slow": True},  # Canadian, slower
            # Google TTS specific voices
            "google_us": {"lang": "en", "tld": "com", "slow": False},
            "google_uk": {"lang": "en", "tld": "co.uk", "slow": False},
            "google_au": {"lang": "en", "tld": "com.au", "slow": False},
            "google_in": {"lang": "en", "tld": "co.in", "slow": False},
            "google_ca": {"lang": "en", "tld": "ca", "slow": False}
        }
        
    def generate_speech(self, text, voice="documentary", output_path="output", preset=None):
        """
        Generate speech using Google TTS
        
        Args:
            text: Text to convert to speech
            voice: Voice preset or name
            output_path: Output path (without extension)
            preset: Voice preset (overrides voice parameter)
            
        Returns:
            tuple: (audio_path, duration_seconds)
        """
        try:
            # Use preset if provided, otherwise use voice
            voice_key = preset if preset else voice
            
            # Get voice settings
            if voice_key in self.voices:
                settings = self.voices[voice_key]
            else:
                # Default to US English if voice not found
                print(f"Voice '{voice_key}' not found, using default US English")
                settings = {"lang": "en", "tld": "com", "slow": False}
            
            # Create gTTS object
            print(f"Generating speech with Google TTS (accent: {settings['tld']}, slow: {settings['slow']})")
            tts = gTTS(
                text=text,
                lang=settings["lang"],
                tld=settings["tld"],
                slow=settings["slow"]
            )
            
            # Save to temporary MP3 file first
            temp_mp3 = f"{output_path}_temp.mp3"
            tts.save(temp_mp3)
            print(f"Saved temporary MP3: {temp_mp3}")
            
            # Convert MP3 to WAV using ffmpeg for consistency
            wav_path = f"{output_path}.wav"
            mp3_path = f"{output_path}.mp3"
            
            # Keep the MP3 and also create a WAV
            os.rename(temp_mp3, mp3_path)
            
            # Convert to WAV if ffmpeg is available
            try:
                subprocess.run([
                    'ffmpeg', '-i', mp3_path, '-acodec', 'pcm_s16le',
                    '-ar', '44100', '-ac', '2', wav_path, '-y'
                ], check=True, capture_output=True)
                print(f"Converted to WAV: {wav_path}")
                
                # Get duration from WAV file
                with wave.open(wav_path, 'r') as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    duration = frames / float(rate)
            except (subprocess.CalledProcessError, FileNotFoundError):
                # If ffmpeg not available, just use MP3
                print("FFmpeg not found, using MP3 format only")
                wav_path = mp3_path
                # Estimate duration (rough estimate)
                duration = len(text.split()) / 150.0 * 60.0  # Rough estimate: 150 WPM
            
            print(f"[SUCCESS] Google TTS generated successfully")
            print(f"   Duration: {duration:.1f} seconds")
            print(f"   Output: {wav_path}")
            
            return wav_path, duration
            
        except Exception as e:
            print(f"[ERROR] Google TTS failed: {e}")
            # Fallback to pyttsx3 (offline TTS)
            try:
                return self._fallback_tts(text, output_path)
            except Exception as fallback_error:
                print(f"[ERROR] Fallback TTS also failed: {fallback_error}")
                raise Exception(f"Google TTS failed: {e}, Fallback failed: {fallback_error}")
    
    def _fallback_tts(self, text, output_path):
        """Fallback to pyttsx3 for offline TTS"""
        print("Using offline TTS fallback (pyttsx3)")
        
        engine = pyttsx3.init()
        
        # Configure voice settings
        engine.setProperty('rate', 150)  # Speed
        engine.setProperty('volume', 1.0)  # Volume
        
        # Save to file
        wav_path = f"{output_path}.wav"
        engine.save_to_file(text, wav_path)
        engine.runAndWait()
        
        # Estimate duration
        duration = len(text.split()) / 150.0 * 60.0
        
        print(f"[SUCCESS] Offline TTS generated")
        print(f"   Duration: {duration:.1f} seconds (estimated)")
        print(f"   Output: {wav_path}")
        
        return wav_path, duration
    
    def test_connection(self):
        """Test if Google TTS is available"""
        try:
            # Try to create a simple TTS
            test_tts = gTTS("test", lang="en")
            return True
        except Exception:
            return False

# Test function
if __name__ == "__main__":
    tts = GoogleTTS()
    
    print("Testing Google TTS...")
    if tts.test_connection():
        print("[SUCCESS] Google TTS is available")
        
        # Test generation
        text = "Hello, this is a test of Google Text to Speech. It's a free alternative to ElevenLabs."
        output_path = "data/out/test_google_tts"
        
        try:
            audio_path, duration = tts.generate_speech(text, voice="documentary", output_path=output_path)
            print(f"Success! Audio saved to: {audio_path}")
            print(f"Duration: {duration:.1f} seconds")
        except Exception as e:
            print(f"Test failed: {e}")
    else:
        print("[ERROR] Google TTS is not available")