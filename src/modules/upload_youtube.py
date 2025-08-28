"""
YouTube Upload Module for AI-Slop Pipeline
Handles authentication and video upload to YouTube
"""

import os
import json
import random
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from ..utils.logger import get_logger
from ..utils.config import get_config


class YouTubeUploader:
    """Handles YouTube video uploads with metadata and thumbnails"""
    
    # YouTube API scopes required for upload and channel info
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.readonly'
    ]
    
    # Valid privacy status options
    VALID_PRIVACY_STATUSES = ('private', 'unlisted', 'public')
    
    def __init__(self, credentials_file: Optional[str] = None):
        """
        Initialize YouTube uploader
        
        Args:
            credentials_file: Path to OAuth2 credentials JSON file
        """
        self.logger = get_logger(__name__)
        self.config = get_config()
        
        # Get credentials file path
        if credentials_file:
            self.credentials_file = Path(credentials_file)
        else:
            # Default to config/youtube_credentials.json
            self.credentials_file = Path('config/youtube_credentials.json')
        
        # Token storage path
        self.token_file = Path('config/youtube_token.json')
        
        # Initialize YouTube service
        self.youtube = None
        self.authenticated = False
        
    def authenticate(self) -> bool:
        """
        Authenticate with YouTube API using OAuth2
        
        Returns:
            True if authentication successful
        """
        try:
            creds = None
            
            # Load existing token
            if self.token_file.exists():
                creds = Credentials.from_authorized_user_file(
                    str(self.token_file), self.SCOPES
                )
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # Refresh expired token
                    creds.refresh(Request())
                else:
                    # Run OAuth2 flow
                    if not self.credentials_file.exists():
                        self.logger.error(f"Credentials file not found: {self.credentials_file}")
                        self.logger.info("Please set up YouTube OAuth2 credentials")
                        self._print_setup_instructions()
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), self.SCOPES
                    )
                    
                    # Run local server for authentication
                    # Try different ports if 8080 is in use
                    self.logger.info("Opening browser for YouTube authentication...")
                    ports_to_try = [8090, 8091, 8092, 9090, 0]  # 0 = random available port
                    
                    for port in ports_to_try:
                        try:
                            creds = flow.run_local_server(port=port)
                            break
                        except OSError as e:
                            if port == ports_to_try[-1]:  # Last port attempt
                                raise
                            self.logger.warning(f"Port {port} is in use, trying next port...")
                
                # Save credentials for next run
                self.token_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            # Build YouTube API service
            self.youtube = build('youtube', 'v3', credentials=creds)
            self.authenticated = True
            
            self.logger.info("Successfully authenticated with YouTube API")
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    def upload_video(self,
                    video_file: Path,
                    title: str,
                    description: str,
                    tags: List[str] = None,
                    category_id: str = "27",  # Education
                    privacy_status: str = "private",
                    thumbnail_file: Optional[Path] = None,
                    publish_at: Optional[datetime] = None,
                    progress_callback: Optional[callable] = None) -> Optional[str]:
        """
        Upload video to YouTube with metadata
        
        Args:
            video_file: Path to video file
            title: Video title (max 100 chars)
            description: Video description (max 5000 chars)
            tags: List of tags
            category_id: YouTube category ID (default: 27 = Education)
            privacy_status: 'private', 'unlisted', or 'public'
            thumbnail_file: Optional thumbnail image
            publish_at: Optional scheduled publish time (for private videos)
            
        Returns:
            Video ID if successful, None otherwise
        """
        if not self.authenticated:
            self.logger.error("Not authenticated. Call authenticate() first")
            return None
        
        if not video_file.exists():
            self.logger.error(f"Video file not found: {video_file}")
            return None
        
        # Validate privacy status
        if privacy_status not in self.VALID_PRIVACY_STATUSES:
            self.logger.warning(f"Invalid privacy status: {privacy_status}, using 'private'")
            privacy_status = 'private'
        
        # Truncate title if too long
        if len(title) > 100:
            title = title[:97] + "..."
        
        # Truncate description if too long
        if len(description) > 5000:
            description = description[:4997] + "..."
        
        # Build request body
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': category_id,
                'defaultLanguage': 'en',
                'defaultAudioLanguage': 'en'
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Add scheduled publish time if provided
        if publish_at and privacy_status == 'private':
            body['status']['publishAt'] = publish_at.isoformat()
        
        # Create media upload object
        media = MediaFileUpload(
            str(video_file),
            mimetype='video/mp4',
            resumable=True,
            chunksize=1024*1024  # 1MB chunks
        )
        
        try:
            # Initialize upload
            self.logger.info(f"Starting upload: {video_file.name}")
            self.logger.info(f"Title: {title}")
            self.logger.info(f"Privacy: {privacy_status}")
            
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            # Execute upload with resumable support
            response = None
            error = None
            retry = 0
            last_progress = 0
            
            while response is None:
                try:
                    status, response = request.next_chunk()
                    
                    if status:
                        progress = int(status.progress() * 100)
                        self.logger.info(f"Upload progress: {progress}%")
                        
                        # Call progress callback if provided
                        if progress_callback and progress != last_progress:
                            progress_callback(progress)
                            last_progress = progress
                        
                except HttpError as e:
                    if e.resp.status in [500, 502, 503, 504]:
                        # Retry on server errors
                        error = f"Server error: {e}"
                        retry += 1
                        if retry > 5:
                            raise
                        
                        wait_time = 2 ** retry
                        self.logger.warning(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise
                        
                except Exception as e:
                    self.logger.error(f"Upload error: {e}")
                    raise
            
            if response is not None:
                video_id = response.get('id')
                self.logger.info(f"Upload complete! Video ID: {video_id}")
                self.logger.info(f"URL: https://www.youtube.com/watch?v={video_id}")
                
                # Upload thumbnail if provided
                if thumbnail_file and thumbnail_file.exists():
                    self._upload_thumbnail(video_id, thumbnail_file)
                
                return video_id
            
        except HttpError as e:
            self.logger.error(f"YouTube API error: {e}")
            return None
            
        except Exception as e:
            self.logger.error(f"Upload failed: {e}")
            return None
    
    def _upload_thumbnail(self, video_id: str, thumbnail_file: Path) -> bool:
        """
        Upload custom thumbnail for video
        
        Args:
            video_id: YouTube video ID
            thumbnail_file: Path to thumbnail image
            
        Returns:
            True if successful
        """
        try:
            self.logger.info(f"Uploading thumbnail: {thumbnail_file.name}")
            
            media = MediaFileUpload(
                str(thumbnail_file),
                mimetype='image/jpeg',
                resumable=True
            )
            
            request = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=media
            )
            
            response = request.execute()
            
            self.logger.info("Thumbnail uploaded successfully")
            return True
            
        except Exception as e:
            self.logger.warning(f"Thumbnail upload failed: {e}")
            return False
    
    def update_video(self,
                    video_id: str,
                    title: Optional[str] = None,
                    description: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    category_id: Optional[str] = None) -> bool:
        """
        Update existing video metadata
        
        Args:
            video_id: YouTube video ID
            title: New title
            description: New description
            tags: New tags
            category_id: New category
            
        Returns:
            True if successful
        """
        try:
            # Get current video data
            request = self.youtube.videos().list(
                part='snippet',
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                self.logger.error(f"Video not found: {video_id}")
                return False
            
            snippet = response['items'][0]['snippet']
            
            # Update fields if provided
            if title:
                snippet['title'] = title[:100]
            if description:
                snippet['description'] = description[:5000]
            if tags:
                snippet['tags'] = tags
            if category_id:
                snippet['categoryId'] = category_id
            
            # Update video
            request = self.youtube.videos().update(
                part='snippet',
                body={
                    'id': video_id,
                    'snippet': snippet
                }
            )
            
            response = request.execute()
            
            self.logger.info(f"Video updated: {video_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Update failed: {e}")
            return False
    
    def _print_setup_instructions(self):
        """Print instructions for setting up YouTube API credentials"""
        
        instructions = """
        ============================================
        YouTube API Setup Instructions
        ============================================
        
        1. Go to Google Cloud Console:
           https://console.cloud.google.com/
        
        2. Create a new project or select existing one
        
        3. Enable YouTube Data API v3:
           https://console.cloud.google.com/apis/library/youtube.googleapis.com
        
        4. Create OAuth2 credentials:
           - Go to APIs & Services > Credentials
           - Click "Create Credentials" > "OAuth client ID"
           - Application type: Desktop app
           - Name: AI-Slop YouTube Uploader
        
        5. Download the credentials JSON file
        
        6. Save it as: config/youtube_credentials.json
        
        7. Run this script again to authenticate
        
        Note: First authentication will open a browser window
        ============================================
        """
        
        print(instructions)
    
    def get_channel_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about authenticated channel
        
        Returns:
            Channel info dictionary or None
        """
        if not self.authenticated:
            return None
        
        try:
            request = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            )
            response = request.execute()
            
            if response['items']:
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'description': channel['snippet']['description'],
                    'subscribers': channel['statistics'].get('subscriberCount', '0'),
                    'videos': channel['statistics'].get('videoCount', '0'),
                    'views': channel['statistics'].get('viewCount', '0')
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get channel info: {e}")
            return None


def main():
    """Test YouTube upload functionality"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload video to YouTube')
    parser.add_argument('--video', type=str, required=True, help='Video file path')
    parser.add_argument('--title', type=str, required=True, help='Video title')
    parser.add_argument('--description', type=str, required=True, help='Video description')
    parser.add_argument('--tags', type=str, help='Comma-separated tags')
    parser.add_argument('--thumbnail', type=str, help='Thumbnail image path')
    parser.add_argument('--privacy', type=str, default='private',
                       choices=['private', 'unlisted', 'public'],
                       help='Privacy status')
    parser.add_argument('--credentials', type=str, 
                       default='config/youtube_credentials.json',
                       help='OAuth2 credentials file')
    
    args = parser.parse_args()
    
    # Initialize uploader
    uploader = YouTubeUploader(args.credentials)
    
    # Authenticate
    if not uploader.authenticate():
        print("Authentication failed")
        return 1
    
    # Get channel info
    channel = uploader.get_channel_info()
    if channel:
        print(f"\nUploading to channel: {channel['title']}")
        print(f"Subscribers: {channel['subscribers']}")
        print(f"Total videos: {channel['videos']}")
    
    # Parse tags
    tags = []
    if args.tags:
        tags = [t.strip() for t in args.tags.split(',')]
    
    # Upload video
    video_id = uploader.upload_video(
        video_file=Path(args.video),
        title=args.title,
        description=args.description,
        tags=tags,
        privacy_status=args.privacy,
        thumbnail_file=Path(args.thumbnail) if args.thumbnail else None
    )
    
    if video_id:
        print(f"\nSuccess! Video uploaded: https://www.youtube.com/watch?v={video_id}")
        return 0
    else:
        print("\nUpload failed")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())