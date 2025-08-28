"""Enhanced thumbnail generation with better design and text fitting."""

import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import requests
from io import BytesIO
import os

class EnhancedThumbnailGenerator:
    """Generates professional YouTube thumbnails with better design."""
    
    def __init__(self):
        """Initialize enhanced thumbnail generator."""
        self.width = 1280
        self.height = 720
        
    def generate(self, text: str, output_dir: Path, job_id: str, 
                background_color: tuple = None, use_stock_bg: bool = True) -> Path:
        """
        Generate professional thumbnail with better design.
        
        Args:
            text: Text for thumbnail (will be intelligently shortened)
            output_dir: Output directory
            job_id: Job ID for filename
            background_color: RGB tuple for background (if not using stock)
            use_stock_bg: Whether to use stock image background
            
        Returns:
            Path to generated thumbnail
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create base image
        if use_stock_bg:
            img = self._create_stock_background(text)
        else:
            img = self._create_gradient_background(background_color or (20, 20, 50))
        
        # Process text for thumbnail
        display_text = self._process_text(text)
        
        # Add text with better design
        img = self._add_enhanced_text(img, display_text)
        
        # Add YouTube-style elements
        img = self._add_youtube_elements(img)
        
        # Save thumbnail
        filepath = output_dir / f"thumbnail_{job_id}.jpg"
        img.save(filepath, 'JPEG', quality=95, optimize=True)
        
        print(f"Generated enhanced thumbnail: {filepath}")
        return filepath
    
    def _process_text(self, text: str) -> str:
        """
        Process text to fit thumbnail (3-5 impactful words).
        
        Args:
            text: Original text
            
        Returns:
            Processed text for thumbnail
        """
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
            'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'should', 'could', 'may', 'might', 'must',
            'shall', 'can', 'need', 'dare', 'ought', 'used', 'about'
        }
        
        # Split and filter words
        words = text.split()
        important_words = []
        
        for word in words:
            clean_word = word.strip('.,!?:;()[]{}"\'-').lower()
            if clean_word not in stop_words and len(clean_word) > 2:
                # Keep the original case but cleaned
                important_words.append(word.strip('.,!?:;()[]{}"\'-'))
        
        # If we have too many words, take the most impactful ones
        if len(important_words) > 5:
            # Prefer longer words (usually more specific/impactful)
            important_words.sort(key=len, reverse=True)
            important_words = important_words[:5]
        elif len(important_words) < 3 and len(words) > 0:
            # If too few important words, take first few original words
            important_words = [w.strip('.,!?:;()[]{}"\'-') for w in words[:4]]
        
        # Join and uppercase
        result = ' '.join(important_words[:5]).upper()
        
        # If still too long, take first 3 words
        if len(result) > 35:
            result = ' '.join(important_words[:3]).upper()
        
        return result
    
    def _create_stock_background(self, keywords: str) -> Image.Image:
        """
        Create background from stock image related to keywords.
        
        Args:
            keywords: Keywords for image search
            
        Returns:
            Background image
        """
        try:
            pexels_key = os.getenv('PEXELS_API_KEY')
            if pexels_key:
                # Search for an image
                headers = {'Authorization': pexels_key}
                search_term = keywords.split()[0] if keywords else 'technology'
                url = f'https://api.pexels.com/v1/search?query={search_term}&per_page=5'
                
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('photos'):
                        # Get a random photo
                        photo = random.choice(data['photos'])
                        img_url = photo['src']['large']
                        
                        # Download image
                        img_response = requests.get(img_url, timeout=10)
                        img = Image.open(BytesIO(img_response.content))
                        
                        # Process image
                        img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        
                        # Apply effects for text readability
                        img = img.filter(ImageFilter.GaussianBlur(radius=4))
                        
                        # Darken the image
                        enhancer = ImageEnhance.Brightness(img)
                        img = enhancer.enhance(0.4)
                        
                        # Add color overlay
                        overlay = Image.new('RGB', (self.width, self.height), (20, 20, 50))
                        img = Image.blend(img, overlay, 0.3)
                        
                        return img
        except:
            pass
        
        # Fallback to gradient
        return self._create_gradient_background((20, 20, 50))
    
    def _create_gradient_background(self, base_color: tuple) -> Image.Image:
        """
        Create attractive gradient background.
        
        Args:
            base_color: Base RGB color
            
        Returns:
            Gradient background image
        """
        img = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(img)
        
        # Create diagonal gradient
        for i in range(self.width + self.height):
            # Calculate color for this position
            progress = i / (self.width + self.height)
            
            # Create color variation
            r = int(base_color[0] + (100 - base_color[0]) * progress)
            g = int(base_color[1] + (30 - base_color[1]) * progress)
            b = int(base_color[2] + (120 - base_color[2]) * progress)
            
            # Ensure valid RGB values
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            # Draw diagonal line
            if i < self.width:
                draw.line([(i, 0), (0, i)], fill=(r, g, b), width=2)
            else:
                x = i - self.width
                draw.line([(self.width, x), (x, self.height)], fill=(r, g, b), width=2)
        
        # Add some noise texture
        pixels = img.load()
        for x in range(0, self.width, 2):
            for y in range(0, self.height, 2):
                if pixels[x, y]:
                    noise = random.randint(-15, 15)
                    r, g, b = pixels[x, y]
                    pixels[x, y] = (
                        max(0, min(255, r + noise)),
                        max(0, min(255, g + noise)),
                        max(0, min(255, b + noise))
                    )
        
        return img
    
    def _add_enhanced_text(self, img: Image.Image, text: str) -> Image.Image:
        """
        Add text with better styling and automatic sizing.
        
        Args:
            img: Base image
            text: Text to add
            
        Returns:
            Image with styled text
        """
        draw = ImageDraw.Draw(img)
        
        # Try to load a good font
        font = None
        font_size = 120  # Start with large size
        
        # Font paths to try
        font_paths = [
            "C:/Windows/Fonts/impact.ttf",     # Impact font (YouTube favorite)
            "C:/Windows/Fonts/arialbd.ttf",    # Arial Bold
            "C:/Windows/Fonts/calibrib.ttf",   # Calibri Bold
            "C:/Windows/Fonts/Arial.ttf",      # Regular Arial
        ]
        
        # Find and load font
        for font_path in font_paths:
            if Path(font_path).exists():
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        
        if not font:
            # Use default if no fonts found
            font = ImageFont.load_default()
        
        # Auto-size text to fit
        max_width = int(self.width * 0.85)
        max_height = int(self.height * 0.6)
        
        # Reduce font size until text fits
        while font_size > 40:
            try:
                font = ImageFont.truetype(font_path if font_path else "arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
                break
            
            # Get text size
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            if text_width <= max_width and text_height <= max_height:
                break
            
            font_size -= 5
        
        # Word wrap if needed
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Calculate position (centered)
        total_height = len(lines) * (font_size + 20)
        y = (self.height - total_height) // 2
        
        # Draw each line with effects
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
            
            # Draw thick black outline
            outline_width = 8
            for adj_x in range(-outline_width, outline_width + 1):
                for adj_y in range(-outline_width, outline_width + 1):
                    if adj_x != 0 or adj_y != 0:
                        draw.text((x + adj_x, y + adj_y), line, 
                                font=font, fill=(0, 0, 0))
            
            # Draw white text
            draw.text((x, y), line, font=font, fill=(255, 255, 255))
            
            # Add slight shadow
            draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 128))
            
            y += font_size + 20
        
        return img
    
    def _add_youtube_elements(self, img: Image.Image) -> Image.Image:
        """
        Add YouTube-style visual elements.
        
        Args:
            img: Base image
            
        Returns:
            Image with YouTube elements
        """
        draw = ImageDraw.Draw(img)
        
        # Add corner accent (red YouTube-style)
        corner_size = 150
        draw.polygon(
            [(0, 0), (corner_size, 0), (0, corner_size)],
            fill=(255, 0, 0, 180)
        )
        
        # Add play button suggestion in corner
        play_size = 40
        play_x, play_y = 30, 30
        draw.polygon([
            (play_x, play_y),
            (play_x + play_size, play_y + play_size // 2),
            (play_x, play_y + play_size)
        ], fill=(255, 255, 255))
        
        # Add bottom gradient for better text contrast
        gradient_height = 100
        for i in range(gradient_height):
            alpha = int(255 * (i / gradient_height) * 0.5)
            y = self.height - gradient_height + i
            draw.rectangle([(0, y), (self.width, y + 1)], 
                         fill=(0, 0, 0, alpha))
        
        return img