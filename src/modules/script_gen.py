"""LLM-based script generation module."""

import json
import math
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import re

from openai import OpenAI
from jinja2 import Environment, FileSystemLoader, Template

from ..utils.config import get_config
from ..utils.logger import get_logger


class ScriptGenerator:
    """Generates YouTube video scripts using LLM and templates."""
    
    def __init__(self, dry_run: bool = False):
        """Initialize script generator.
        
        Args:
            dry_run: If True, use templates without LLM
        """
        self.config = get_config()
        self.logger = get_logger(__name__)
        self.dry_run = dry_run
        
        # Initialize LLM client
        if not dry_run:
            api_key = self.config.get_env('OPENAI_API_KEY')
            if api_key:
                self.client = OpenAI(api_key=api_key)
            else:
                self.logger.warning("No OpenAI API key found, using template-only mode")
                self.client = None
                self.dry_run = True
        else:
            self.client = None
            
        # Initialize Jinja2 environment
        template_dir = Path(__file__).parent.parent / 'templates'
        template_dir.mkdir(exist_ok=True)
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
        # Load LLM configuration
        self.llm_config = self.config.get('llm', {})
        self.model = self.llm_config.get('model', 'gpt-4')
        self.temperature = self.llm_config.get('temperature', 0.3)
        self.top_p = self.llm_config.get('top_p', 0.9)
        self.max_tokens = self.llm_config.get('max_tokens', 2000)
        
    def generate_script(self, 
                       post: Dict[str, Any], 
                       topic_config: Dict[str, Any],
                       target_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Generate script for video.
        
        Args:
            post: Reddit post data
            topic_config: Topic configuration
            target_minutes: Target video duration
            
        Returns:
            Script dictionary in script.v1 format
        """
        if target_minutes is None:
            target_minutes = self.config.get('video.target_minutes', 10)
            
        # Calculate word count (150-180 wpm)
        target_words = target_minutes * 165  # Average 165 wpm
        
        self.logger.info(f"Generating {target_minutes}-minute script ({target_words} words)")
        
        if self.dry_run or not self.client:
            # Use template-based generation
            script = self._generate_from_template(post, topic_config, target_words)
        else:
            # Use LLM generation
            script = self._generate_with_llm(post, topic_config, target_words)
            
        # Validate and adjust script
        script = self._validate_script(script)
        
        # Add metadata
        script['generated_at'] = datetime.now().isoformat()
        script['post_id'] = post.get('id', 'unknown')
        script['target_minutes'] = target_minutes
        
        return script
        
    def _generate_from_template(self, 
                               post: Dict[str, Any], 
                               topic_config: Dict[str, Any],
                               target_words: int) -> Dict[str, Any]:
        """Generate script using templates only.
        
        Args:
            post: Reddit post data
            topic_config: Topic configuration
            target_words: Target word count
            
        Returns:
            Script dictionary
        """
        topic_id = topic_config.get('topic_id', 'explainer')
        
        # Calculate chapter distribution
        chapter_count = topic_config.get('chapter_count', 5)
        words_per_chapter = (target_words - 250) // chapter_count  # Reserve 250 for intro/outro
        
        # Generate based on topic type
        if topic_id == 'listicle':
            script = self._generate_listicle_script(post, chapter_count, words_per_chapter)
        elif topic_id == 'ai_news':
            script = self._generate_news_script(post, chapter_count, words_per_chapter)
        else:
            script = self._generate_explainer_script(post, chapter_count, words_per_chapter)
            
        return script
        
    def _generate_listicle_script(self, post: Dict[str, Any], chapters: int, words_per: int) -> Dict[str, Any]:
        """Generate listicle-style script."""
        title = post.get('title', 'Top Amazing Facts')
        
        # Extract number from title if present
        numbers = re.findall(r'\d+', title)
        if numbers:
            chapters = min(int(numbers[0]), 10)  # Cap at 10
            
        return {
            'version': 'script.v1',
            'title': title[:100],
            'hook': f"You won't believe number {chapters//2}! Today we're counting down {title.lower()}. Let's dive right in!",
            'narration': {
                'intro': f"Welcome back to our channel! {title} has captured everyone's attention. "
                        f"We've researched the most fascinating aspects to bring you this countdown. "
                        f"From surprising revelations to mind-blowing facts, we've got it all covered. "
                        f"Make sure to watch until the end for the most amazing one!",
                'chapters': [
                    {
                        'id': i + 1,
                        'heading': f"Number {chapters - i}",
                        'body': self._generate_chapter_content(post, i, words_per)
                    }
                    for i in range(chapters)
                ],
                'outro': "That wraps up our countdown! Which one surprised you the most? "
                        "Let us know in the comments below. If you enjoyed this video, "
                        "please give it a thumbs up and subscribe for more amazing content. "
                        "Click the bell icon to never miss an update. See you in the next one!"
            },
            'broll_keywords': ['countdown', 'numbers', 'facts', 'discovery', 'amazing'],
            'disclaimers': [],
            'policy_checklist': {
                'copyright_risk': False,
                'medical_or_financial_claims': False,
                'nsfw': False,
                'shocking_or_graphic': False
            }
        }
        
    def _generate_news_script(self, post: Dict[str, Any], chapters: int, words_per: int) -> Dict[str, Any]:
        """Generate news-style script."""
        title = post.get('title', 'Breaking News')
        
        return {
            'version': 'script.v1',
            'title': title[:100],
            'hook': f"Breaking developments today: {title}. Here's what you need to know right now.",
            'narration': {
                'intro': f"In today's tech news, {title.lower()}. This development could change everything we know. "
                        f"Industry experts are already weighing in on the implications. "
                        f"Let's break down what this means for you and what to expect next.",
                'chapters': [
                    {
                        'id': i + 1,
                        'heading': ['The Announcement', 'Key Features', 'Industry Impact', 'Expert Analysis', 'What\'s Next'][i % 5],
                        'body': self._generate_chapter_content(post, i, words_per)
                    }
                    for i in range(min(chapters, 5))
                ],
                'outro': "That's all for today's update. This story is developing rapidly, "
                        "so make sure to subscribe and hit the notification bell for the latest. "
                        "Share your thoughts in the comments. Thanks for watching!"
            },
            'broll_keywords': ['technology', 'innovation', 'future', 'digital', 'breakthrough'],
            'disclaimers': ['Information based on current reports and may be subject to change.'],
            'policy_checklist': {
                'copyright_risk': False,
                'medical_or_financial_claims': False,
                'nsfw': False,
                'shocking_or_graphic': False
            }
        }
        
    def _generate_explainer_script(self, post: Dict[str, Any], chapters: int, words_per: int) -> Dict[str, Any]:
        """Generate explainer-style script."""
        title = post.get('title', 'How It Works')
        
        return {
            'version': 'script.v1',
            'title': title[:100],
            'hook': f"Ever wondered about {title.lower()}? Today we'll explain it in simple terms that anyone can understand.",
            'narration': {
                'intro': f"Welcome! Today's topic is {title.lower()}. "
                        f"We'll break this down step by step, using everyday examples. "
                        f"By the end of this video, you'll have a clear understanding. "
                        f"No technical background required - let's get started!",
                'chapters': [
                    {
                        'id': i + 1,
                        'heading': ['The Basics', 'How It Works', 'Real-World Examples', 'Common Misconceptions', 'Key Takeaways'][i % 5],
                        'body': self._generate_chapter_content(post, i, words_per)
                    }
                    for i in range(min(chapters, 5))
                ],
                'outro': "And that's the complete explanation! Hopefully, this cleared things up. "
                        "If you have questions, drop them in the comments. "
                        "Subscribe for more explainers, and check out our other videos. "
                        "Thanks for learning with us today!"
            },
            'broll_keywords': ['education', 'learning', 'explanation', 'diagram', 'concept'],
            'disclaimers': [],
            'policy_checklist': {
                'copyright_risk': False,
                'medical_or_financial_claims': False,
                'nsfw': False,
                'shocking_or_graphic': False
            }
        }
        
    def _generate_chapter_content(self, post: Dict[str, Any], chapter_index: int, target_words: int) -> str:
        """Generate content for a single chapter."""
        selftext = post.get('selftext', '')
        sentences = selftext.split('.')[:3]  # Use first 3 sentences as base
        
        base_content = '. '.join(sentences) if sentences else f"This is fascinating point number {chapter_index + 1}."
        
        # Pad to target word count
        current_words = len(base_content.split())
        if current_words < target_words:
            padding = [
                "This is particularly interesting when you consider the broader implications.",
                "Experts in the field have noted the significance of this development.",
                "The data shows a clear trend that supports this conclusion.",
                "Many people don't realize how important this actually is.",
                "Let's take a moment to understand what this really means.",
            ]
            
            while current_words < target_words and padding:
                base_content += " " + padding.pop(0)
                current_words = len(base_content.split())
                
        return base_content[:target_words * 6]  # Rough char limit
        
    def _generate_with_llm(self, 
                          post: Dict[str, Any], 
                          topic_config: Dict[str, Any],
                          target_words: int) -> Dict[str, Any]:
        """Generate script using LLM.
        
        Args:
            post: Reddit post data
            topic_config: Topic configuration
            target_words: Target word count
            
        Returns:
            Script dictionary
        """
        # Load system prompt from Claude.md
        system_prompt = self._get_system_prompt()
        
        # Prepare input for LLM
        llm_input = {
            'topic_id': topic_config.get('topic_id'),
            'target_minutes': target_words // 165,
            'source': {
                'title': post.get('title', ''),
                'selftext': post.get('selftext', '')[:2000],
                'url': post.get('url', ''),
                'subreddit': post.get('subreddit', ''),
                'captured_at': post.get('captured_at', datetime.now().isoformat())
            },
            'brand': {
                'channel_name': 'AI Slop Channel',
                'style_notes': topic_config.get('style', ''),
                'banned_terms': self.config.get('content_policy.banned_terms', []),
                'voice_name': 'Rachel'
            },
            'output_format': 'script.v1'
        }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(llm_input)}
                ],
                temperature=self.temperature,
                top_p=self.top_p,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            script = json.loads(response.choices[0].message.content)
            
            # Validate it matches our schema
            if script.get('version') != 'script.v1':
                raise ValueError("Invalid script version")
                
            return script
            
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            # Fallback to template generation
            return self._generate_from_template(post, topic_config, target_words)
            
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM."""
        # This would normally load from Claude.md, but we'll use a simplified version
        return """You are a YouTube script generator for a faceless channel. 
        Generate scripts that are engaging, informative, and YouTube-friendly.
        Output must be valid JSON matching the script.v1 schema.
        Keep content PG-13, avoid copyright issues, and optimize for retention.
        Target the specified duration precisely. Return ONLY valid JSON."""
        
    def _validate_script(self, script: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix script structure.
        
        Args:
            script: Script dictionary
            
        Returns:
            Validated script dictionary
        """
        # Ensure required fields
        required = ['version', 'title', 'hook', 'narration', 'broll_keywords', 'disclaimers', 'policy_checklist']
        for field in required:
            if field not in script:
                if field == 'version':
                    script['version'] = 'script.v1'
                elif field == 'disclaimers':
                    script['disclaimers'] = []
                elif field == 'broll_keywords':
                    script['broll_keywords'] = ['general', 'content']
                elif field == 'policy_checklist':
                    script['policy_checklist'] = {
                        'copyright_risk': False,
                        'medical_or_financial_claims': False,
                        'nsfw': False,
                        'shocking_or_graphic': False
                    }
                    
        # Validate narration structure
        if 'narration' in script:
            if 'chapters' not in script['narration']:
                script['narration']['chapters'] = []
            if 'intro' not in script['narration']:
                script['narration']['intro'] = "Welcome to our video!"
            if 'outro' not in script['narration']:
                script['narration']['outro'] = "Thanks for watching!"
                
        # Ensure title length
        if 'title' in script:
            script['title'] = script['title'][:100]
            
        return script
        
    def save_script(self, script: Dict[str, Any], output_dir: Path) -> Path:
        """Save script to JSON file.
        
        Args:
            script: Script dictionary
            output_dir: Output directory
            
        Returns:
            Path to saved file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"script_{script.get('post_id', 'unknown')}_{timestamp}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(script, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Saved script to {filepath}")
        return filepath
        
    def calculate_duration(self, script: Dict[str, Any]) -> float:
        """Calculate estimated duration of script in minutes.
        
        Args:
            script: Script dictionary
            
        Returns:
            Duration in minutes
        """
        total_words = 0
        
        # Count words in narration
        narration = script.get('narration', {})
        
        # Hook
        total_words += len(script.get('hook', '').split())
        
        # Intro
        total_words += len(narration.get('intro', '').split())
        
        # Chapters
        for chapter in narration.get('chapters', []):
            total_words += len(chapter.get('body', '').split())
            
        # Outro
        total_words += len(narration.get('outro', '').split())
        
        # Calculate duration (165 wpm average)
        duration_minutes = total_words / 165
        
        return round(duration_minutes, 1)
    
    def generate_script_manual(self, post: Dict[str, Any], topic_config: Dict[str, Any], 
                               script_json: Dict[str, Any]) -> Dict[str, Any]:
        """Process a manually provided script"""
        # Validate and enhance the script
        script = script_json.copy()
        
        # Add metadata if missing
        if 'post_id' not in script:
            script['post_id'] = post.get('id', 'unknown')
        
        if 'generated_at' not in script:
            script['generated_at'] = datetime.now().isoformat()
        
        if 'target_minutes' not in script:
            script['target_minutes'] = topic_config.get('target_minutes', 10)
        
        # Ensure version
        if 'version' not in script:
            script['version'] = 'script.v1'
        
        # Add default values for missing fields
        if 'disclaimers' not in script:
            script['disclaimers'] = []
        
        if 'policy_checklist' not in script:
            script['policy_checklist'] = {
                'copyright_risk': False,
                'medical_or_financial_claims': False,
                'nsfw': False,
                'shocking_or_graphic': False
            }
        
        # Add default broll_keywords if missing
        if 'broll_keywords' not in script:
            # Extract keywords from title
            title_words = script.get('title', '').lower().split()
            keywords = [w for w in title_words if len(w) > 4][:5]
            script['broll_keywords'] = keywords if keywords else ['education', 'learning', 'explanation']
        
        return script


def main():
    """Test the script generation module."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Script generation')
    parser.add_argument('--input', type=str, help='Input JSON file with Reddit post')
    parser.add_argument('--topic', type=str, default='explainer', 
                       choices=['ai_news', 'listicle', 'explainer'])
    parser.add_argument('--minutes', type=int, default=10, help='Target duration')
    parser.add_argument('--dry-run', action='store_true', help='Use templates only')
    parser.add_argument('--output', type=str, default='data/out', help='Output directory')
    args = parser.parse_args()
    
    generator = ScriptGenerator(dry_run=args.dry_run)
    
    # Load post
    if args.input:
        with open(args.input, 'r') as f:
            post = json.load(f)
    else:
        # Use test post
        post = {
            'id': 'test123',
            'title': 'Amazing Discovery: Scientists Find New Species',
            'selftext': 'Researchers have made an incredible discovery...',
            'subreddit': 'science',
            'url': 'https://reddit.com/test'
        }
        
    # Topic configuration
    topic_config = {
        'topic_id': args.topic,
        'chapter_count': 10 if args.topic == 'listicle' else 5,
        'style': 'engaging and informative'
    }
    
    # Generate script
    print(f"Generating {args.minutes}-minute {args.topic} script...")
    script = generator.generate_script(post, topic_config, args.minutes)
    
    # Calculate duration
    duration = generator.calculate_duration(script)
    print(f"\nGenerated script:")
    print(f"  Title: {script['title']}")
    print(f"  Hook: {script['hook'][:100]}...")
    print(f"  Chapters: {len(script['narration']['chapters'])}")
    print(f"  Estimated duration: {duration} minutes")
    print(f"  B-roll keywords: {', '.join(script['broll_keywords'][:5])}")
    
    # Save script
    output_dir = Path(args.output)
    filepath = generator.save_script(script, output_dir)
    print(f"\nSaved to: {filepath}")


if __name__ == '__main__':
    main()