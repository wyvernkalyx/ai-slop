"""Thumbnail generation module for YouTube videos."""

import json
import random
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap

from ..utils.config import get_config
from ..utils.logger import get_logger


class ThumbnailGenerator:
    """Generates eye-catching thumbnails for videos."""
    
    def __init__(self):
        """Initialize thumbnail generator."""
        self.config = get_config()
        self.logger = get_logger(__name__)
        
        # Load thumbnail configuration
        self.thumb_config = self.config.get('thumbnail', {})
        self.width = self.thumb_config.get('width', 1280)
        self.height = self.thumb_config.get('height', 720)
        self.font_size = self.thumb_config.get('font_size', 120)
        self.font_family = self.thumb_config.get('font_family', 'Arial')
        self.text_color = self.thumb_config.get('text_color', '#FFFFFF')
        self.background_color = self.thumb_config.get('background_color', '#1E1E1E')
        self.text_position = self.thumb_config.get('text_position', 'center')
        self.max_words = self.thumb_config.get('max_words', 5)
        
    def generate_thumbnail(self,
                         script: Dict[str, Any],
                         metadata: Dict[str, Any],
                         output_dir: Path,
                         background_image: Optional[Path] = None) -> Path:
        """Generate thumbnail for video.
        
        Args:
            script: Script dictionary with title
            metadata: Video metadata dictionary
            output_dir: Output directory
            background_image: Optional background image path
            
        Returns:
            Path to generated thumbnail
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract thumbnail text
        thumbnail_text = self._extract_thumbnail_text(script, metadata)
        
        # Create base image
        if background_image and background_image.exists():
            img = self._create_from_background(background_image)
        else:
            img = self._create_gradient_background()
            
        # Add text overlay
        img = self._add_text_overlay(img, thumbnail_text)
        
        # Add decorative elements
        img = self._add_decorations(img, script.get('topic_id', 'general'))
        
        # Save thumbnail
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"thumbnail_{script.get('post_id', 'unknown')}_{timestamp}.jpg"
        filepath = output_dir / filename
        
        # Save with optimization
        img.save(filepath, 'JPEG', quality=95, optimize=True)
        
        self.logger.info(f"Generated thumbnail: {filepath}")
        
        # Save thumbnail metadata
        self._save_metadata(filepath, thumbnail_text, script)
        
        return filepath
        
    def _extract_thumbnail_text(self, script: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Extract text for thumbnail.
        
        Args:
            script: Script dictionary
            metadata: Metadata dictionary
            
        Returns:
            Thumbnail text
        """
        # Check if metadata has specific thumbnail text
        if 'thumbnail_text' in metadata:
            return metadata['thumbnail_text'].upper()
            
        # Extract from title
        title = script.get('title', '')
        
        # Find most impactful words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = title.split()
        
        # Filter and prioritize words
        important_words = []
        for word in words:
            clean_word = word.strip('.,!?:;').lower()
            if clean_word not in stop_words and len(clean_word) > 2:
                important_words.append(word.upper())
                
        # Limit to max words
        if len(important_words) > self.max_words:
            # Take first and last words plus middle ones
            selected = []
            if self.max_words >= 3:
                selected.append(important_words[0])
                selected.extend(important_words[1:self.max_words-1])
                selected.append(important_words[-1])
            else:
                selected = important_words[:self.max_words]
            important_words = selected
            
        return ' '.join(important_words[:self.max_words])
        
    def _create_gradient_background(self) -> Image.Image:
        """Create gradient background image.
        
        Returns:
            Background image
        """
        img = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(img)
        
        # Create gradient
        base_color = self._hex_to_rgb(self.background_color)
        
        # Darker version for gradient
        dark_color = tuple(int(c * 0.6) for c in base_color)
        
        # Vertical gradient
        for y in range(self.height):
            ratio = y / self.height
            r = int(dark_color[0] + (base_color[0] - dark_color[0]) * ratio)
            g = int(dark_color[1] + (base_color[1] - dark_color[1]) * ratio)
            b = int(dark_color[2] + (base_color[2] - dark_color[2]) * ratio)
            draw.rectangle([(0, y), (self.width, y + 1)], fill=(r, g, b))
            
        # Add noise/texture
        pixels = img.load()
        for x in range(0, self.width, 3):
            for y in range(0, self.height, 3):
                noise = random.randint(-10, 10)
                r, g, b = pixels[x, y]
                pixels[x, y] = (
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                )
                
        return img
        
    def _create_from_background(self, background_path: Path) -> Image.Image:
        """Create thumbnail from background image.
        
        Args:
            background_path: Path to background image
            
        Returns:
            Processed background image
        """
        img = Image.open(background_path)
        
        # Resize to thumbnail dimensions
        img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
            
        # Apply blur for text readability
        img = img.filter(ImageFilter.GaussianBlur(radius=3))
        
        # Darken the image
        overlay = Image.new('RGB', (self.width, self.height), (0, 0, 0))
        img = Image.blend(img, overlay, 0.4)
        
        return img
        
    def _add_text_overlay(self, img: Image.Image, text: str) -> Image.Image:
        """Add text overlay to image.
        
        Args:
            img: Base image
            text: Text to add
            
        Returns:
            Image with text
        """
        draw = ImageDraw.Draw(img)
        
        # Try to use a bold font
        try:
            # Try common font paths
            font_paths = [
                "C:/Windows/Fonts/arialbd.ttf",  # Arial Bold on Windows
                "C:/Windows/Fonts/Arial.ttf",     # Regular Arial
                "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # Linux
                "/System/Library/Fonts/Helvetica.ttc",  # macOS
            ]
            
            font = None
            for font_path in font_paths:
                if Path(font_path).exists():
                    font = ImageFont.truetype(font_path, self.font_size)
                    break
                    
            if not font:
                # Fallback to default font
                font = ImageFont.load_default()
                
        except:
            font = ImageFont.load_default()
            
        # Word wrap if needed
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] > self.width * 0.9:  # 90% of width
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []
                    
        if current_line:
            lines.append(' '.join(current_line))
            
        # Calculate text position
        total_height = 0
        line_bboxes = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_height = bbox[3] - bbox[1]
            line_bboxes.append(bbox)
            total_height += line_height + 10  # 10px spacing
            
        # Position text
        if self.text_position == 'center':
            y = (self.height - total_height) // 2
        elif self.text_position == 'top':
            y = self.height // 6
        else:  # bottom
            y = self.height - total_height - self.height // 6
            
        # Draw text with shadow
        text_color = self._hex_to_rgb(self.text_color)
        shadow_color = (0, 0, 0)
        
        for i, line in enumerate(lines):
            bbox = line_bboxes[i]
            line_width = bbox[2] - bbox[0]
            x = (self.width - line_width) // 2
            
            # Draw shadow
            for offset_x in range(-3, 4):
                for offset_y in range(-3, 4):
                    if offset_x != 0 or offset_y != 0:
                        draw.text((x + offset_x, y + offset_y), line, 
                                font=font, fill=shadow_color)
                        
            # Draw main text
            draw.text((x, y), line, font=font, fill=text_color)
            
            y += bbox[3] - bbox[1] + 10
            
        return img
        
    def _add_decorations(self, img: Image.Image, topic_id: str) -> Image.Image:
        """Add decorative elements based on topic.
        
        Args:
            img: Image to decorate
            topic_id: Topic identifier
            
        Returns:
            Decorated image
        """
        draw = ImageDraw.Draw(img)
        
        # Add corner accents
        accent_color = self._get_accent_color(topic_id)
        
        # Top-left corner
        draw.rectangle([(0, 0), (100, 10)], fill=accent_color)
        draw.rectangle([(0, 0), (10, 100)], fill=accent_color)
        
        # Bottom-right corner
        draw.rectangle([(self.width - 100, self.height - 10), 
                       (self.width, self.height)], fill=accent_color)
        draw.rectangle([(self.width - 10, self.height - 100), 
                       (self.width, self.height)], fill=accent_color)
        
        # Add subtle border
        border_width = 5
        draw.rectangle([(0, 0), (self.width - 1, border_width)], fill=accent_color)
        draw.rectangle([(0, self.height - border_width), 
                       (self.width - 1, self.height - 1)], fill=accent_color)
        draw.rectangle([(0, 0), (border_width, self.height - 1)], fill=accent_color)
        draw.rectangle([(self.width - border_width, 0), 
                       (self.width - 1, self.height - 1)], fill=accent_color)
        
        return img
        
    def _get_accent_color(self, topic_id: str) -> Tuple[int, int, int]:
        """Get accent color based on topic.
        
        Args:
            topic_id: Topic identifier
            
        Returns:
            RGB color tuple
        """
        colors = {
            'ai_news': (0, 123, 255),      # Blue
            'listicle': (255, 193, 7),     # Yellow
            'explainer': (40, 167, 69),    # Green
            'general': (108, 117, 125)     # Gray
        }
        return colors.get(topic_id, colors['general'])
        
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple.
        
        Args:
            hex_color: Hex color string
            
        Returns:
            RGB tuple
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
    def _save_metadata(self, thumbnail_path: Path, text: str, script: Dict[str, Any]):
        """Save thumbnail metadata.
        
        Args:
            thumbnail_path: Path to thumbnail file
            text: Text on thumbnail
            script: Original script
        """
        metadata = {
            'thumbnail_file': str(thumbnail_path.name),
            'thumbnail_text': text,
            'dimensions': f"{self.width}x{self.height}",
            'script_title': script.get('title', ''),
            'post_id': script.get('post_id', ''),
            'generated_at': datetime.now().isoformat()
        }
        
        metadata_path = thumbnail_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def generate(self, text: str, output_dir: Path, job_id: str = 'thumb',
                background_color: Optional[Tuple[int, int, int]] = None) -> Path:
        """Simple wrapper for generating thumbnails with just text.
        
        Args:
            text: Text to display on thumbnail
            output_dir: Output directory
            job_id: Job ID for filename
            background_color: Optional RGB background color tuple
            
        Returns:
            Path to generated thumbnail
        """
        # Override background color if provided
        if background_color:
            old_bg = self.background_color
            self.background_color = f"#{background_color[0]:02x}{background_color[1]:02x}{background_color[2]:02x}"
        
        # Create minimal script and metadata
        script = {'title': text, 'post_id': job_id}
        metadata = {'thumbnail_text': text}
        
        # Generate thumbnail
        thumbnail_path = self.generate_thumbnail(script, metadata, output_dir)
        
        # Restore original background color
        if background_color:
            self.background_color = old_bg
            
        return thumbnail_path


def main():
    """Test the thumbnail generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Thumbnail generation')
    parser.add_argument('--script', type=str, help='Input script JSON file')
    parser.add_argument('--text', type=str, help='Custom thumbnail text')
    parser.add_argument('--background', type=str, help='Background image path')
    parser.add_argument('--output', type=str, default='data/out', help='Output directory')
    args = parser.parse_args()
    
    generator = ThumbnailGenerator()
    
    # Load or create test script
    if args.script:
        with open(args.script, 'r') as f:
            script = json.load(f)
    else:
        script = {
            'title': 'Amazing Discovery Scientists Find New Species',
            'post_id': 'test123',
            'topic_id': 'explainer'
        }
        
    # Override thumbnail text if provided
    metadata = {}
    if args.text:
        metadata['thumbnail_text'] = args.text
        
    # Generate thumbnail
    print(f"Generating thumbnail...")
    print(f"Title: {script.get('title', 'Unknown')}")
    
    output_dir = Path(args.output)
    background = Path(args.background) if args.background else None
    
    thumbnail_path = generator.generate_thumbnail(
        script, metadata, output_dir, background
    )
    
    print(f"\nGenerated thumbnail: {thumbnail_path}")
    print(f"Dimensions: {generator.width}x{generator.height}")


if __name__ == '__main__':
    main()