"""Media picker module for selecting stock footage."""

import json
import requests
import random
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import time
import hashlib

from ..utils.config import get_config
from ..utils.logger import get_logger


class MediaPicker:
    """Selects and downloads stock media for video creation."""
    
    def __init__(self, dry_run: bool = False):
        """Initialize media picker.
        
        Args:
            dry_run: If True, use mock data instead of API calls
        """
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.dry_run = dry_run
        
        # Load stock media configuration
        self.media_config = self.config.get('stock_media', {})
        self.providers = self.media_config.get('providers', ['pexels', 'pixabay'])
        self.quality = self.media_config.get('quality', 'hd')
        self.min_clip_duration = self.media_config.get('min_clip_duration', 3)
        self.max_clip_duration = self.media_config.get('max_clip_duration', 7)
        self.fallback_keywords = self.media_config.get('fallback_keywords', ['technology', 'nature'])
        
        # API keys
        self.api_keys = self.config.get_api_keys()
        self.pexels_key = self.api_keys.get('pexels_api_key', '')
        self.pixabay_key = self.api_keys.get('pixabay_api_key', '')
        
    def select_media(self,
                    script: Dict[str, Any],
                    duration_minutes: float,
                    output_dir: Path) -> List[Dict[str, Any]]:
        """Select media clips for the video.
        
        Args:
            script: Script dictionary with b-roll keywords
            duration_minutes: Target video duration
            output_dir: Directory to save media files
            
        Returns:
            List of media clip metadata dictionaries
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate number of clips needed
        clips_per_minute = self.config.get('video.clips_per_minute', 6)
        num_clips = int(duration_minutes * clips_per_minute)
        
        # Extract keywords from script
        keywords = self._extract_keywords(script)
        
        self.logger.info(f"Selecting {num_clips} clips for {duration_minutes:.1f} minute video")
        self.logger.info(f"Keywords: {', '.join(keywords[:10])}")
        
        if self.dry_run:
            # Generate mock media data
            media_clips = self._generate_mock_media(keywords, num_clips)
        else:
            # Fetch real media from APIs
            media_clips = self._fetch_real_media(keywords, num_clips)
            
        # Download media files
        downloaded_clips = self._download_clips(media_clips, output_dir)
        
        # Save media metadata
        self._save_media_metadata(downloaded_clips, output_dir, script)
        
        return downloaded_clips
        
    def _extract_keywords(self, script: Dict[str, Any]) -> List[str]:
        """Extract keywords from script for media search.
        
        Args:
            script: Script dictionary
            
        Returns:
            List of search keywords
        """
        keywords = []
        
        # Start with b-roll keywords from script
        if 'broll_keywords' in script:
            keywords.extend(script['broll_keywords'])
            
        # Add keywords from title
        if 'title' in script:
            title_words = script['title'].lower().split()
            # Filter out common words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
            title_keywords = [w for w in title_words if w not in stop_words and len(w) > 3]
            keywords.extend(title_keywords[:5])
            
        # Add topic-specific keywords
        narration = script.get('narration', {})
        for chapter in narration.get('chapters', []):
            if 'heading' in chapter:
                heading_words = str(chapter['heading']).lower().split()
                keywords.extend([w for w in heading_words if len(w) > 4][:2])
                
        # Add fallback keywords
        keywords.extend(self.fallback_keywords)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
                
        return unique_keywords
        
    def _generate_mock_media(self, keywords: List[str], num_clips: int) -> List[Dict[str, Any]]:
        """Generate mock media data for testing.
        
        Args:
            keywords: Search keywords
            num_clips: Number of clips to generate
            
        Returns:
            List of mock media clip data
        """
        mock_clips = []
        
        for i in range(num_clips):
            keyword = keywords[i % len(keywords)] if keywords else 'stock'
            
            clip = {
                'id': f'mock_{i}_{keyword}',
                'url': f'https://example.com/video_{i}.mp4',
                'preview_url': f'https://example.com/preview_{i}.jpg',
                'duration': random.uniform(self.min_clip_duration, self.max_clip_duration),
                'width': 1920,
                'height': 1080,
                'provider': 'mock',
                'keyword': keyword,
                'description': f'Mock video clip for {keyword}',
                'license': 'CC0',
                'author': 'Mock Author',
                'download_url': f'https://example.com/download_{i}.mp4'
            }
            mock_clips.append(clip)
            
        return mock_clips
        
    def _fetch_real_media(self, keywords: List[str], num_clips: int) -> List[Dict[str, Any]]:
        """Fetch real media from stock APIs.
        
        Args:
            keywords: Search keywords
            num_clips: Number of clips needed
            
        Returns:
            List of media clip data
        """
        all_clips = []
        clips_per_keyword = max(3, num_clips // len(keywords)) if keywords else num_clips
        
        for keyword in keywords[:10]:  # Limit to 10 keywords
            if len(all_clips) >= num_clips:
                break
                
            # Try Pexels first
            if 'pexels' in self.providers and self.pexels_key:
                clips = self._search_pexels(keyword, clips_per_keyword)
                all_clips.extend(clips)
                
            # Try Pixabay if needed
            if len(all_clips) < num_clips and 'pixabay' in self.providers and self.pixabay_key:
                clips = self._search_pixabay(keyword, clips_per_keyword)
                all_clips.extend(clips)
                
        # Shuffle and trim to exact number needed
        random.shuffle(all_clips)
        return all_clips[:num_clips]
        
    def _search_pexels(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search Pexels for video clips.
        
        Args:
            keyword: Search term
            limit: Maximum number of results
            
        Returns:
            List of clip data
        """
        if not self.pexels_key:
            return []
            
        try:
            headers = {'Authorization': self.pexels_key}
            params = {
                'query': keyword,
                'per_page': limit,
                'size': 'medium' if self.quality == 'hd' else 'small'
            }
            
            response = requests.get(
                'https://api.pexels.com/videos/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Pexels API error: {response.status_code}")
                return []
                
            data = response.json()
            clips = []
            
            for video in data.get('videos', [])[:limit]:
                # Find appropriate quality file
                video_file = None
                for file in video.get('video_files', []):
                    if self.quality == 'hd' and file.get('quality') == 'hd':
                        video_file = file
                        break
                    elif self.quality != 'hd':
                        video_file = file
                        break
                        
                if video_file:
                    clips.append({
                        'id': f"pexels_{video['id']}",
                        'url': video.get('url', ''),
                        'preview_url': video.get('image', ''),
                        'duration': video.get('duration', 5),
                        'width': video_file.get('width', 1920),
                        'height': video_file.get('height', 1080),
                        'provider': 'pexels',
                        'keyword': keyword,
                        'description': video.get('url', ''),
                        'license': 'Pexels License',
                        'author': video.get('user', {}).get('name', 'Unknown'),
                        'download_url': video_file.get('link', '')
                    })
                    
            return clips
            
        except Exception as e:
            self.logger.error(f"Pexels search error: {e}")
            return []
            
    def _search_pixabay(self, keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search Pixabay for video clips.
        
        Args:
            keyword: Search term
            limit: Maximum number of results
            
        Returns:
            List of clip data
        """
        if not self.pixabay_key:
            return []
            
        try:
            params = {
                'key': self.pixabay_key,
                'q': keyword,
                'video_type': 'all',
                'per_page': limit
            }
            
            response = requests.get(
                'https://pixabay.com/api/videos/',
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Pixabay API error: {response.status_code}")
                return []
                
            data = response.json()
            clips = []
            
            for video in data.get('hits', [])[:limit]:
                # Select video quality
                video_url = video.get('videos', {}).get('medium', {}).get('url', '')
                if self.quality == 'hd' and 'large' in video.get('videos', {}):
                    video_url = video['videos']['large']['url']
                    
                clips.append({
                    'id': f"pixabay_{video['id']}",
                    'url': video.get('pageURL', ''),
                    'preview_url': f"https://i.vimeocdn.com/video/{video.get('picture_id', '')}_640x360.jpg",
                    'duration': video.get('duration', 5),
                    'width': video.get('videos', {}).get('medium', {}).get('width', 1920),
                    'height': video.get('videos', {}).get('medium', {}).get('height', 1080),
                    'provider': 'pixabay',
                    'keyword': keyword,
                    'description': video.get('tags', ''),
                    'license': 'Pixabay License',
                    'author': video.get('user', 'Unknown'),
                    'download_url': video_url
                })
                
            return clips
            
        except Exception as e:
            self.logger.error(f"Pixabay search error: {e}")
            return []
            
    def _download_clips(self, clips: List[Dict[str, Any]], output_dir: Path) -> List[Dict[str, Any]]:
        """Download media clips to local storage.
        
        Args:
            clips: List of clip metadata
            output_dir: Directory to save clips
            
        Returns:
            List of clips with local file paths
        """
        downloaded = []
        clips_dir = output_dir / 'clips'
        clips_dir.mkdir(exist_ok=True)
        
        for i, clip in enumerate(clips):
            if self.dry_run:
                # For dry run, just create empty files
                filename = f"clip_{i:03d}_{clip['keyword']}.mp4"
                filepath = clips_dir / filename
                filepath.touch()
                clip['local_path'] = str(filepath)
                clip['downloaded'] = True
                downloaded.append(clip)
                
            else:
                # Download real file
                download_url = clip.get('download_url', '')
                if download_url:
                    filename = f"clip_{i:03d}_{clip['keyword']}.mp4"
                    filepath = clips_dir / filename
                    
                    if self._download_file(download_url, filepath):
                        clip['local_path'] = str(filepath)
                        clip['downloaded'] = True
                        downloaded.append(clip)
                    else:
                        self.logger.warning(f"Failed to download clip: {clip['id']}")
                        
        self.logger.info(f"Downloaded {len(downloaded)}/{len(clips)} clips")
        return downloaded
        
    def _download_file(self, url: str, filepath: Path) -> bool:
        """Download a file from URL.
        
        Args:
            url: Download URL
            filepath: Local file path
            
        Returns:
            True if successful
        """
        try:
            # Check if file already exists
            if filepath.exists():
                return True
                
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return False
            
    def _save_media_metadata(self, clips: List[Dict[str, Any]], output_dir: Path, script: Dict[str, Any]):
        """Save media selection metadata.
        
        Args:
            clips: List of downloaded clips
            output_dir: Output directory
            script: Original script
        """
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'script_title': script.get('title', ''),
            'post_id': script.get('post_id', ''),
            'num_clips': len(clips),
            'total_duration': sum(c.get('duration', 0) for c in clips),
            'providers_used': list(set(c.get('provider', 'unknown') for c in clips)),
            'keywords_used': list(set(c.get('keyword', '') for c in clips)),
            'clips': clips
        }
        
        metadata_path = output_dir / f"media_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
        self.logger.info(f"Saved media metadata to {metadata_path}")


def main():
    """Test the media picker module."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stock media selection')
    parser.add_argument('--script', type=str, help='Input script JSON file')
    parser.add_argument('--duration', type=float, default=10, help='Video duration in minutes')
    parser.add_argument('--dry-run', action='store_true', help='Use mock data')
    parser.add_argument('--output', type=str, default='data/out', help='Output directory')
    args = parser.parse_args()
    
    picker = MediaPicker(dry_run=args.dry_run)
    
    # Load or create test script
    if args.script:
        with open(args.script, 'r') as f:
            script = json.load(f)
    else:
        script = {
            'title': 'Technology and Nature',
            'broll_keywords': ['technology', 'computer', 'nature', 'forest', 'innovation'],
            'post_id': 'test123'
        }
        
    # Select media
    print(f"Selecting media for {args.duration}-minute video...")
    print(f"Keywords: {', '.join(script.get('broll_keywords', []))}")
    
    output_dir = Path(args.output)
    clips = picker.select_media(script, args.duration, output_dir)
    
    print(f"\nSelected {len(clips)} clips:")
    for i, clip in enumerate(clips[:10], 1):
        print(f"  {i}. {clip.get('keyword', 'unknown')} - {clip.get('duration', 0):.1f}s - {clip.get('provider', 'unknown')}")
        
    total_duration = sum(c.get('duration', 0) for c in clips)
    print(f"\nTotal clips duration: {total_duration:.1f} seconds")
    print(f"Average clip duration: {total_duration/len(clips):.1f} seconds" if clips else "No clips")


if __name__ == '__main__':
    main()