"""Reddit content ingestion module."""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import praw
from praw.models import Submission

from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.dedup import DeduplicationManager


class RedditIngestor:
    """Fetches and processes Reddit content."""
    
    def __init__(self, dry_run: bool = False):
        """Initialize Reddit ingestor.
        
        Args:
            dry_run: If True, use test data instead of real API
        """
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.dry_run = dry_run
        self.dedup = DeduplicationManager()
        
        if not dry_run:
            self._init_reddit_client()
        else:
            self.reddit = None
            
    def _init_reddit_client(self):
        """Initialize Reddit API client."""
        api_keys = self.config.get_api_keys()
        
        self.reddit = praw.Reddit(
            client_id=api_keys['reddit_client_id'],
            client_secret=api_keys['reddit_client_secret'],
            user_agent=api_keys['reddit_user_agent']
        )
        
        # Test authentication
        try:
            self.reddit.user.me()
        except Exception:
            # Read-only mode is fine for our purposes
            pass
            
    def fetch_trending_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch trending posts from Reddit.
        
        Args:
            limit: Maximum number of posts to fetch
            
        Returns:
            List of post dictionaries
        """
        if self.dry_run:
            return self._get_test_posts()
            
        subreddit_name = self.config.get('reddit.subreddit', 'popular')
        min_score = self.config.get('reddit.min_score', 1000)
        time_filter = self.config.get('reddit.time_filter', 'day')
        excluded_subreddits = self.config.get('reddit.excluded_subreddits', [])
        excluded_flairs = self.config.get('reddit.excluded_flairs', [])
        
        self.logger.info(f"Fetching posts from r/{subreddit_name}")
        
        subreddit = self.reddit.subreddit(subreddit_name)
        posts = []
        
        # Fetch posts based on time filter
        if time_filter == 'hour':
            submissions = subreddit.hot(limit=limit * 3)
        else:
            submissions = subreddit.top(time_filter=time_filter, limit=limit * 3)
            
        for submission in submissions:
            # Apply filters
            if submission.score < min_score:
                continue
                
            if submission.subreddit.display_name.lower() in [s.lower() for s in excluded_subreddits]:
                self.logger.debug(f"Skipping excluded subreddit: {submission.subreddit.display_name}")
                continue
                
            if submission.link_flair_text and submission.link_flair_text in excluded_flairs:
                self.logger.debug(f"Skipping excluded flair: {submission.link_flair_text}")
                continue
                
            if submission.over_18:
                self.logger.debug("Skipping NSFW post")
                continue
                
            # Check deduplication
            post_id = self._generate_post_id(submission.permalink)
            if self.dedup.is_duplicate(post_id):
                self.logger.debug(f"Skipping duplicate post: {submission.title}")
                continue
                
            # Extract post data
            post_data = self._extract_post_data(submission)
            posts.append(post_data)
            
            if len(posts) >= limit:
                break
                
        self.logger.info(f"Fetched {len(posts)} posts")
        return posts
        
    def _extract_post_data(self, submission: Submission) -> Dict[str, Any]:
        """Extract relevant data from Reddit submission.
        
        Args:
            submission: Reddit submission object
            
        Returns:
            Dictionary of post data
        """
        return {
            'id': submission.id,
            'title': submission.title,
            'selftext': submission.selftext[:5000] if submission.selftext else '',
            'url': f"https://reddit.com{submission.permalink}",
            'subreddit': submission.subreddit.display_name,
            'author': str(submission.author) if submission.author else '[deleted]',
            'score': submission.score,
            'num_comments': submission.num_comments,
            'created_utc': submission.created_utc,
            'captured_at': datetime.now().isoformat(),
            'flair': submission.link_flair_text,
            'is_video': submission.is_video,
            'is_self': submission.is_self,
            'domain': submission.domain,
            'upvote_ratio': submission.upvote_ratio
        }
        
    def _generate_post_id(self, permalink: str) -> str:
        """Generate unique ID for post.
        
        Args:
            permalink: Reddit post permalink
            
        Returns:
            Hash ID for deduplication
        """
        return hashlib.md5(permalink.encode()).hexdigest()
        
    def _get_test_posts(self) -> List[Dict[str, Any]]:
        """Get test posts for dry run mode.
        
        Returns:
            List of test post dictionaries
        """
        return [
            {
                'id': 'test123',
                'title': 'Scientists Discover New Species of Deep-Sea Fish That Glows in the Dark',
                'selftext': 'Researchers have discovered a new species of fish living at depths of over 3,000 meters...',
                'url': 'https://reddit.com/r/science/comments/test123',
                'subreddit': 'science',
                'author': 'test_user',
                'score': 15234,
                'num_comments': 523,
                'created_utc': datetime.now().timestamp(),
                'captured_at': datetime.now().isoformat(),
                'flair': 'Biology',
                'is_video': False,
                'is_self': True,
                'domain': 'self.science',
                'upvote_ratio': 0.97
            },
            {
                'id': 'test456',
                'title': 'Top 10 Programming Languages to Learn in 2024',
                'selftext': 'Based on job market demand and industry trends, here are the top programming languages...',
                'url': 'https://reddit.com/r/programming/comments/test456',
                'subreddit': 'programming',
                'author': 'tech_enthusiast',
                'score': 8934,
                'num_comments': 245,
                'created_utc': datetime.now().timestamp(),
                'captured_at': datetime.now().isoformat(),
                'flair': 'Discussion',
                'is_video': False,
                'is_self': True,
                'domain': 'self.programming',
                'upvote_ratio': 0.92
            }
        ]
        
    def get_best_post(self, posts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select the best post for video creation.
        
        Args:
            posts: List of post dictionaries
            
        Returns:
            Best post or None if no suitable posts
        """
        if not posts:
            return None
            
        # Score posts based on multiple factors
        scored_posts = []
        for post in posts:
            score = self._calculate_post_score(post)
            scored_posts.append((score, post))
            
        # Sort by score (highest first)
        scored_posts.sort(key=lambda x: x[0], reverse=True)
        
        best_post = scored_posts[0][1]
        self.logger.info(f"Selected post: {best_post['title']}")
        
        # Mark as processed
        post_id = self._generate_post_id(best_post['url'])
        self.dedup.add_item(post_id)
        
        return best_post
        
    def _calculate_post_score(self, post: Dict[str, Any]) -> float:
        """Calculate quality score for a post.
        
        Args:
            post: Post dictionary
            
        Returns:
            Quality score
        """
        score = 0.0
        
        # Reddit score (normalized)
        score += min(post['score'] / 10000, 2.0)
        
        # Engagement (comments)
        score += min(post['num_comments'] / 500, 1.0)
        
        # Upvote ratio
        score += post.get('upvote_ratio', 0.9)
        
        # Title length (prefer medium length)
        title_length = len(post['title'])
        if 50 <= title_length <= 100:
            score += 1.0
        elif 30 <= title_length <= 150:
            score += 0.5
            
        # Has content (selftext)
        if post.get('selftext') and len(post['selftext']) > 100:
            score += 1.0
            
        # Recency bonus
        created_time = datetime.fromtimestamp(post['created_utc'])
        hours_old = (datetime.now() - created_time).total_seconds() / 3600
        if hours_old < 6:
            score += 1.0
        elif hours_old < 12:
            score += 0.5
            
        return score
        
    def save_post(self, post: Dict[str, Any], output_dir: Path) -> Path:
        """Save post data to JSON file.
        
        Args:
            post: Post dictionary
            output_dir: Output directory
            
        Returns:
            Path to saved file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"reddit_post_{post['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(post, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Saved post to {filepath}")
        return filepath


def main():
    """Main function for testing the module."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Reddit content ingestion')
    parser.add_argument('--dry-run', action='store_true', help='Use test data')
    parser.add_argument('--limit', type=int, default=10, help='Number of posts to fetch')
    parser.add_argument('--output', type=str, default='data/out', help='Output directory')
    args = parser.parse_args()
    
    # Initialize ingestor
    ingestor = RedditIngestor(dry_run=args.dry_run)
    
    # Fetch posts
    posts = ingestor.fetch_trending_posts(limit=args.limit)
    
    if posts:
        print(f"\nFetched {len(posts)} posts:")
        for i, post in enumerate(posts, 1):
            print(f"{i}. [{post['score']}] {post['title'][:80]}...")
            
        # Select best post
        best_post = ingestor.get_best_post(posts)
        if best_post:
            print(f"\nSelected best post: {best_post['title']}")
            
            # Save to file
            output_dir = Path(args.output)
            filepath = ingestor.save_post(best_post, output_dir)
            print(f"Saved to: {filepath}")
    else:
        print("No suitable posts found")


if __name__ == '__main__':
    main()