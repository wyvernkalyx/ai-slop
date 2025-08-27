"""Configuration management utilities."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    """Configuration manager for the pipeline."""
    
    def __init__(self, config_path: str = "config/config.yaml", env_path: str = "config/.env"):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to the YAML configuration file
            env_path: Path to the .env file
        """
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self._config: Dict[str, Any] = {}
        self._load_env()
        self._load_config()
        
    def _load_env(self) -> None:
        """Load environment variables from .env file."""
        if self.env_path.exists():
            load_dotenv(self.env_path)
        else:
            print(f"Warning: {self.env_path} not found. Using environment variables.")
            
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key.
        
        Args:
            key: Configuration key (e.g., 'video.target_minutes')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
                
        return value
        
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable value.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)
        
    def get_required_env(self, key: str) -> str:
        """Get required environment variable value.
        
        Args:
            key: Environment variable name
            
        Returns:
            Environment variable value
            
        Raises:
            ValueError: If environment variable not found
        """
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Required environment variable not found: {key}")
        return value
        
    def get_api_keys(self) -> Dict[str, str]:
        """Get all API keys from environment.
        
        Returns:
            Dictionary of API keys
        """
        return {
            'reddit_client_id': self.get_env('REDDIT_CLIENT_ID', ''),
            'reddit_client_secret': self.get_env('REDDIT_CLIENT_SECRET', ''),
            'reddit_user_agent': self.get_env('REDDIT_USER_AGENT', 'AI-Slop/1.0'),
            'pexels_api_key': self.get_env('PEXELS_API_KEY', ''),
            'pixabay_api_key': self.get_env('PIXABAY_API_KEY', ''),
            'elevenlabs_api_key': self.get_env('ELEVENLABS_API_KEY', ''),
            'openai_api_key': self.get_env('OPENAI_API_KEY', ''),
            'anthropic_api_key': self.get_env('ANTHROPIC_API_KEY', ''),
        }
        
    def get_youtube_config(self) -> Dict[str, Any]:
        """Get YouTube-specific configuration.
        
        Returns:
            YouTube configuration dictionary
        """
        return {
            'client_secrets_file': self.get_env('GOOGLE_CLIENT_SECRETS_FILE', 'config/client_secrets.json'),
            'category_id': int(self.get_env('YT_CATEGORY_ID', '27')),
            'privacy_status': self.get_env('YT_VISIBILITY', 'unlisted'),
            'upload_enabled': self.get_env('ENABLE_UPLOAD', 'false').lower() == 'true',
            **self.get('youtube', {})
        }
        
    def get_video_config(self) -> Dict[str, Any]:
        """Get video processing configuration.
        
        Returns:
            Video configuration dictionary
        """
        return self.get('video', {})
        
    def get_tts_config(self) -> Dict[str, Any]:
        """Get TTS configuration.
        
        Returns:
            TTS configuration dictionary
        """
        config = self.get('tts', {})
        config['api_key'] = self.get_env('ELEVENLABS_API_KEY', '')
        return config
        
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled.
        
        Args:
            feature: Feature name
            
        Returns:
            True if feature is enabled
        """
        env_key = f"ENABLE_{feature.upper()}"
        env_value = self.get_env(env_key, 'true')
        return env_value.lower() in ('true', '1', 'yes', 'on')
        
    def get_paths(self) -> Dict[str, Path]:
        """Get all configured paths.
        
        Returns:
            Dictionary of paths
        """
        return {
            'temp_dir': Path(self.get_env('TEMP_DIR', 'data/temp')),
            'output_dir': Path(self.get_env('OUTPUT_DIR', 'data/out')),
            'log_dir': Path(self.get_env('LOG_DIR', 'data/logs')),
            'cache_dir': Path(self.get_env('CACHE_DIR', 'data/cache')),
        }
        
    def validate(self) -> bool:
        """Validate configuration and environment.
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If configuration is invalid
        """
        # Check required environment variables
        required_vars = []
        
        if self.is_feature_enabled('upload'):
            required_vars.extend(['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'])
            
        if self.is_feature_enabled('tts'):
            required_vars.append('ELEVENLABS_API_KEY')
            
        if self.is_feature_enabled('stock_media'):
            if not (self.get_env('PEXELS_API_KEY') or self.get_env('PIXABAY_API_KEY')):
                raise ValueError("At least one stock media API key required (PEXELS_API_KEY or PIXABAY_API_KEY)")
                
        missing_vars = [var for var in required_vars if not self.get_env(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        # Create required directories
        paths = self.get_paths()
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
            
        return True


# Global configuration instance
config = None


def get_config() -> Config:
    """Get the global configuration instance.
    
    Returns:
        Configuration instance
    """
    global config
    if config is None:
        config = Config()
    return config