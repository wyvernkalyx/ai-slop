"""Topic classification module for Reddit posts."""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import Counter

from ..utils.config import get_config
from ..utils.logger import get_logger


class TopicClassifier:
    """Classifies Reddit posts into predefined topics."""
    
    def __init__(self):
        """Initialize topic classifier."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        
        # Load topic configuration
        self.topics_config = self.config.get('topics', {})
        self.default_topic = self.topics_config.get('default', 'explainer')
        self.rules = self.topics_config.get('rules', {})
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile regex patterns for topic keywords."""
        self.topic_patterns = {}
        
        for topic, config in self.rules.items():
            keywords = config.get('keywords', [])
            if keywords:
                # Create regex pattern from keywords
                pattern = '|'.join([re.escape(kw.lower()) for kw in keywords])
                self.topic_patterns[topic] = re.compile(pattern, re.IGNORECASE)
                
    def classify(self, post: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """Classify a Reddit post into a topic.
        
        Args:
            post: Reddit post dictionary
            
        Returns:
            Tuple of (topic_id, confidence_score, metadata)
        """
        # Extract text for analysis
        text = self._extract_text(post)
        
        # Try rule-based classification first
        topic, confidence, metadata = self._rule_based_classification(text, post)
        
        if confidence > 0.7:
            self.logger.info(f"Classified as '{topic}' with confidence {confidence:.2f}")
            return topic, confidence, metadata
            
        # Try subreddit-based classification
        topic_sub, confidence_sub = self._subreddit_classification(post)
        if confidence_sub > confidence:
            topic = topic_sub
            confidence = confidence_sub
            metadata['classification_method'] = 'subreddit'
            
        # If still low confidence, use default
        if confidence < 0.5:
            topic = self.default_topic
            confidence = 0.4
            metadata['classification_method'] = 'default'
            metadata['reason'] = 'No strong match found'
            
        self.logger.info(f"Classified as '{topic}' with confidence {confidence:.2f}")
        return topic, confidence, metadata
        
    def _extract_text(self, post: Dict[str, Any]) -> str:
        """Extract searchable text from post.
        
        Args:
            post: Reddit post dictionary
            
        Returns:
            Combined text for analysis
        """
        parts = []
        
        # Title (most important)
        if post.get('title'):
            parts.append(post['title'] * 3)  # Weight title more
            
        # Self text
        if post.get('selftext'):
            parts.append(post['selftext'])
            
        # Subreddit
        if post.get('subreddit'):
            parts.append(f"subreddit: {post['subreddit']}")
            
        # Flair
        if post.get('flair'):
            parts.append(f"flair: {post['flair']}")
            
        return ' '.join(parts).lower()
        
    def _rule_based_classification(self, text: str, post: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """Classify using keyword rules.
        
        Args:
            text: Text to analyze
            post: Original post data
            
        Returns:
            Tuple of (topic, confidence, metadata)
        """
        matches = {}
        match_details = {}
        
        # Check each topic's patterns
        for topic, pattern in self.topic_patterns.items():
            found_keywords = pattern.findall(text)
            if found_keywords:
                # Calculate match score
                unique_keywords = set(kw.lower() for kw in found_keywords)
                match_count = len(found_keywords)
                unique_count = len(unique_keywords)
                
                # Score based on frequency and uniqueness
                score = (match_count * 0.7 + unique_count * 0.3)
                matches[topic] = score
                match_details[topic] = {
                    'keywords_found': list(unique_keywords),
                    'match_count': match_count
                }
                
        if not matches:
            return self.default_topic, 0.3, {
                'classification_method': 'rule_based',
                'reason': 'No keyword matches'
            }
            
        # Get best match
        best_topic = max(matches, key=matches.get)
        best_score = matches[best_topic]
        
        # Calculate confidence (normalize score)
        max_possible_score = 20  # Adjust based on typical max matches
        confidence = min(best_score / max_possible_score, 1.0)
        
        metadata = {
            'classification_method': 'rule_based',
            'match_details': match_details[best_topic],
            'all_scores': matches
        }
        
        return best_topic, confidence, metadata
        
    def _subreddit_classification(self, post: Dict[str, Any]) -> Tuple[str, float]:
        """Classify based on subreddit.
        
        Args:
            post: Reddit post dictionary
            
        Returns:
            Tuple of (topic, confidence)
        """
        subreddit = post.get('subreddit', '').lower()
        
        # Subreddit to topic mapping
        subreddit_mappings = {
            'ai_news': ['artificialintelligence', 'machinelearning', 'openai', 'singularity', 'technology'],
            'listicle': ['todayilearned', 'interestingasfuck', 'mildlyinteresting', 'dataisbeautiful', 'coolguides'],
            'explainer': ['explainlikeimfive', 'askscience', 'askreddit', 'nostupidquestions', 'outoftheloop']
        }
        
        for topic, subreddits in subreddit_mappings.items():
            if subreddit in subreddits:
                return topic, 0.8
                
        # Check partial matches
        for topic, subreddits in subreddit_mappings.items():
            for sub in subreddits:
                if sub in subreddit or subreddit in sub:
                    return topic, 0.6
                    
        return self.default_topic, 0.3
        
    def get_topic_config(self, topic_id: str) -> Dict[str, Any]:
        """Get configuration for a specific topic.
        
        Args:
            topic_id: Topic identifier
            
        Returns:
            Topic configuration dictionary
        """
        base_config = {
            'topic_id': topic_id,
            'target_minutes': self.config.get('video.target_minutes', 10),
            'tone': 'neutral',
            'style': 'informative'
        }
        
        # Topic-specific configurations
        topic_configs = {
            'ai_news': {
                'tone': 'crisp',
                'style': 'current, lightly analytical',
                'hook_style': 'news_bulletin',
                'chapter_count': 5,
                'visual_style': 'tech_focused'
            },
            'listicle': {
                'tone': 'energetic',
                'style': 'curiosity-driven, punchy',
                'hook_style': 'countdown',
                'chapter_count': 10,
                'visual_style': 'dynamic'
            },
            'explainer': {
                'tone': 'patient',
                'style': 'teacher, plain language',
                'hook_style': 'question',
                'chapter_count': 5,
                'visual_style': 'educational'
            }
        }
        
        if topic_id in topic_configs:
            base_config.update(topic_configs[topic_id])
            
        return base_config
        
    def analyze_post_suitability(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze if post is suitable for video creation.
        
        Args:
            post: Reddit post dictionary
            
        Returns:
            Suitability analysis
        """
        issues = []
        warnings = []
        score = 100  # Start with perfect score
        
        # Check title length
        title_length = len(post.get('title', ''))
        if title_length < 20:
            issues.append("Title too short")
            score -= 20
        elif title_length > 200:
            warnings.append("Title very long")
            score -= 5
            
        # Check content availability
        selftext = post.get('selftext', '')
        if not selftext or len(selftext) < 50:
            if not post.get('url') or 'reddit.com' in post.get('url', ''):
                issues.append("Insufficient content")
                score -= 30
                
        # Check for problematic content
        text = self._extract_text(post)
        
        # Check for banned terms
        banned_terms = self.config.get('content_policy.banned_terms', [])
        found_banned = [term for term in banned_terms if term.lower() in text]
        if found_banned:
            issues.append(f"Contains banned terms: {', '.join(found_banned)}")
            score -= 50
            
        # Check for sensitive topics
        sensitive_topics = self.config.get('content_policy.sensitive_topics', [])
        found_sensitive = [topic for topic in sensitive_topics if topic.lower() in text]
        if found_sensitive:
            warnings.append(f"Contains sensitive topics: {', '.join(found_sensitive)}")
            score -= 15
            
        # Check engagement metrics
        if post.get('score', 0) < 100:
            warnings.append("Low engagement score")
            score -= 10
            
        if post.get('upvote_ratio', 1.0) < 0.7:
            warnings.append("Low upvote ratio")
            score -= 10
            
        # Determine if suitable
        is_suitable = score >= 50 and len(issues) == 0
        
        return {
            'is_suitable': is_suitable,
            'score': max(0, score),
            'issues': issues,
            'warnings': warnings,
            'recommendation': 'approved' if is_suitable else 'rejected',
            'requires_disclaimer': len(found_sensitive) > 0
        }


def main():
    """Test the classification module."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Topic classification')
    parser.add_argument('--input', type=str, help='Input JSON file with Reddit post')
    parser.add_argument('--test', action='store_true', help='Run with test data')
    args = parser.parse_args()
    
    classifier = TopicClassifier()
    
    if args.test:
        # Test posts
        test_posts = [
            {
                'title': 'OpenAI Announces GPT-5 with Revolutionary Capabilities',
                'selftext': 'The new model shows significant improvements in reasoning...',
                'subreddit': 'technology',
                'score': 5000
            },
            {
                'title': 'Top 10 Most Amazing Scientific Discoveries of 2024',
                'selftext': 'From quantum computing to gene therapy...',
                'subreddit': 'todayilearned',
                'score': 8000
            },
            {
                'title': 'ELI5: How does quantum entanglement work?',
                'selftext': 'I keep hearing about it but dont understand...',
                'subreddit': 'explainlikeimfive',
                'score': 3000
            }
        ]
        
        for post in test_posts:
            print(f"\n{'='*50}")
            print(f"Title: {post['title'][:60]}...")
            print(f"Subreddit: r/{post['subreddit']}")
            
            # Classify
            topic, confidence, metadata = classifier.classify(post)
            print(f"\nClassification: {topic} (confidence: {confidence:.2f})")
            print(f"Method: {metadata.get('classification_method')}")
            
            # Get topic config
            config = classifier.get_topic_config(topic)
            print(f"Tone: {config['tone']}")
            print(f"Style: {config['style']}")
            
            # Analyze suitability
            suitability = classifier.analyze_post_suitability(post)
            print(f"\nSuitability: {suitability['recommendation']} (score: {suitability['score']})")
            if suitability['issues']:
                print(f"Issues: {', '.join(suitability['issues'])}")
            if suitability['warnings']:
                print(f"Warnings: {', '.join(suitability['warnings'])}")
                
    elif args.input:
        # Load post from file
        with open(args.input, 'r') as f:
            post = json.load(f)
            
        # Classify
        topic, confidence, metadata = classifier.classify(post)
        
        # Output results
        result = {
            'topic_id': topic,
            'confidence': confidence,
            'metadata': metadata,
            'topic_config': classifier.get_topic_config(topic),
            'suitability': classifier.analyze_post_suitability(post)
        }
        
        print(json.dumps(result, indent=2))
        
        # Save to file
        output_file = Path(args.input).parent / f"classification_{Path(args.input).stem}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved classification to: {output_file}")
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()