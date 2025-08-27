"""Deduplication management for preventing duplicate content processing."""

import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Set, Dict, Any, Optional


class DeduplicationManager:
    """Manages deduplication of processed content."""
    
    def __init__(self, cache_file: Optional[Path] = None, cache_days: int = 7):
        """Initialize deduplication manager.
        
        Args:
            cache_file: Path to cache file
            cache_days: Number of days to keep items in cache
        """
        from ..utils.config import get_config
        self.config = get_config()
        
        # Use config or defaults
        if cache_file is None:
            cache_file = Path(self.config.get('deduplication.cache_file', 'data/cache/dedup.json'))
        self.cache_file = cache_file
        
        self.cache_days = self.config.get('deduplication.cache_days', cache_days)
        self.enabled = self.config.get('deduplication.enabled', True)
        
        # Initialize cache
        self.cache: Dict[str, Any] = {}
        self._load_cache()
        
    def _load_cache(self):
        """Load cache from file."""
        if not self.enabled:
            return
            
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                self._clean_expired()
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load dedup cache: {e}")
                self.cache = {}
        else:
            # Create cache directory
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
    def _save_cache(self):
        """Save cache to file."""
        if not self.enabled:
            return
            
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save dedup cache: {e}")
            
    def _clean_expired(self):
        """Remove expired items from cache."""
        if not self.enabled:
            return
            
        cutoff_date = datetime.now() - timedelta(days=self.cache_days)
        cutoff_timestamp = cutoff_date.isoformat()
        
        # Remove expired items
        expired_keys = []
        for key, data in self.cache.items():
            if isinstance(data, dict) and 'timestamp' in data:
                if data['timestamp'] < cutoff_timestamp:
                    expired_keys.append(key)
                    
        for key in expired_keys:
            del self.cache[key]
            
        if expired_keys:
            self._save_cache()
            
    def is_duplicate(self, item_id: str) -> bool:
        """Check if item has been processed before.
        
        Args:
            item_id: Unique identifier for the item
            
        Returns:
            True if item is duplicate
        """
        if not self.enabled:
            return False
            
        # Clean expired items periodically
        if len(self.cache) % 100 == 0:
            self._clean_expired()
            
        return item_id in self.cache
        
    def add_item(self, item_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Add item to deduplication cache.
        
        Args:
            item_id: Unique identifier for the item
            metadata: Optional metadata to store with the item
        """
        if not self.enabled:
            return
            
        self.cache[item_id] = {
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        self._save_cache()
        
    def remove_item(self, item_id: str):
        """Remove item from deduplication cache.
        
        Args:
            item_id: Unique identifier for the item
        """
        if not self.enabled:
            return
            
        if item_id in self.cache:
            del self.cache[item_id]
            self._save_cache()
            
    def clear(self):
        """Clear all items from cache."""
        self.cache = {}
        self._save_cache()
        
    def get_stats(self) -> Dict[str, Any]:
        """Get deduplication statistics.
        
        Returns:
            Dictionary of statistics
        """
        if not self.enabled:
            return {'enabled': False, 'total_items': 0}
            
        # Count items by age
        now = datetime.now()
        age_buckets = {
            'today': 0,
            'yesterday': 0,
            'this_week': 0,
            'older': 0
        }
        
        for item_data in self.cache.values():
            if isinstance(item_data, dict) and 'timestamp' in item_data:
                timestamp = datetime.fromisoformat(item_data['timestamp'])
                age = now - timestamp
                
                if age.days == 0:
                    age_buckets['today'] += 1
                elif age.days == 1:
                    age_buckets['yesterday'] += 1
                elif age.days <= 7:
                    age_buckets['this_week'] += 1
                else:
                    age_buckets['older'] += 1
                    
        return {
            'enabled': self.enabled,
            'total_items': len(self.cache),
            'cache_file': str(self.cache_file),
            'cache_days': self.cache_days,
            'age_distribution': age_buckets
        }
        
    @staticmethod
    def generate_content_hash(content: str) -> str:
        """Generate hash for content.
        
        Args:
            content: Content to hash
            
        Returns:
            SHA256 hash of content
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
        
    @staticmethod
    def generate_url_hash(url: str) -> str:
        """Generate hash for URL.
        
        Args:
            url: URL to hash
            
        Returns:
            MD5 hash of URL
        """
        return hashlib.md5(url.encode('utf-8')).hexdigest()


def main():
    """Test the deduplication manager."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deduplication manager utility')
    parser.add_argument('--stats', action='store_true', help='Show deduplication stats')
    parser.add_argument('--clear', action='store_true', help='Clear deduplication cache')
    parser.add_argument('--test', action='store_true', help='Test deduplication')
    args = parser.parse_args()
    
    dedup = DeduplicationManager()
    
    if args.stats:
        stats = dedup.get_stats()
        print("\nDeduplication Statistics:")
        print(f"  Enabled: {stats['enabled']}")
        print(f"  Total items: {stats['total_items']}")
        print(f"  Cache file: {stats['cache_file']}")
        print(f"  Cache days: {stats['cache_days']}")
        print(f"\nAge distribution:")
        for age, count in stats['age_distribution'].items():
            print(f"    {age}: {count}")
            
    elif args.clear:
        dedup.clear()
        print("Deduplication cache cleared")
        
    elif args.test:
        # Test deduplication
        test_ids = ['test1', 'test2', 'test3']
        
        print("\nTesting deduplication:")
        for test_id in test_ids:
            is_dup = dedup.is_duplicate(test_id)
            print(f"  {test_id}: {'Duplicate' if is_dup else 'New'}")
            if not is_dup:
                dedup.add_item(test_id, {'test': True})
                
        print("\nChecking again:")
        for test_id in test_ids:
            is_dup = dedup.is_duplicate(test_id)
            print(f"  {test_id}: {'Duplicate' if is_dup else 'New'}")
            
        # Clean up test items
        for test_id in test_ids:
            dedup.remove_item(test_id)
        print("\nTest items removed")
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()