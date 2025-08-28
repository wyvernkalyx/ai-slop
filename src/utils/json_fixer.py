"""
JSON Fixer - Repairs common JSON formatting issues from LLMs
"""

import json
import re
from typing import Any, Dict, Optional

class JSONFixer:
    """Fix common JSON errors from LLM outputs"""
    
    @staticmethod
    def fix_json(text: str) -> str:
        """
        Fix common JSON formatting issues
        
        Args:
            text: Potentially malformed JSON string
            
        Returns:
            Fixed JSON string
        """
        original_text = text
        
        # Remove any text before the first { or [
        json_start = -1
        for i, char in enumerate(text):
            if char in '{[':
                json_start = i
                break
        
        if json_start > 0:
            text = text[json_start:]
        
        # Remove any text after the last } or ]
        json_end = -1
        for i in range(len(text) - 1, -1, -1):
            if text[i] in '}]':
                json_end = i + 1
                break
        
        if json_end > 0 and json_end < len(text):
            text = text[:json_end]
        
        # Fix common issues
        
        # 1. Fix smart quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        # 2. Fix em dashes and en dashes that might break parsing
        text = text.replace('—', '--').replace('–', '-')
        
        # 3. Remove trailing commas before closing brackets
        text = re.sub(r',\s*([}\]])', r'\1', text)
        
        # 4. Fix missing commas between array elements or object properties
        # This is tricky - look for patterns like "}" followed by "{"
        text = re.sub(r'}\s*{', r'},{', text)
        text = re.sub(r']\s*\[', r'],[', text)
        
        # 5. Escape unescaped quotes inside strings (very basic)
        # This is complex, so we'll try parsing first
        
        # 6. Remove any stray characters like 'e' between objects
        text = re.sub(r'}\s*[a-zA-Z]\s*{', r'},{', text)
        
        # 7. Fix missing quotes around property names (basic attempt)
        # Look for patterns like: property: "value"
        text = re.sub(r'([,{]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', text)
        
        # 8. Remove BOM and other invisible characters
        text = text.replace('\ufeff', '').replace('\u200b', '')
        
        # 9. Handle control characters
        text = text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        
        # Then fix the escaped characters in the actual content
        text = text.replace('\\\\n', '\\n').replace('\\\\r', '\\r').replace('\\\\t', '\\t')
        
        return text
    
    @staticmethod
    def parse_with_fixes(text: str, max_attempts: int = 5) -> Optional[Dict[str, Any]]:
        """
        Try to parse JSON with automatic fixes
        
        Args:
            text: Potentially malformed JSON string
            max_attempts: Maximum number of fix attempts
            
        Returns:
            Parsed JSON object or None if all attempts fail
        """
        
        # First, try parsing as-is
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"Initial parse failed: {str(e)[:100]}")
        
        # Try with basic fixes
        fixed_text = JSONFixer.fix_json(text)
        
        for attempt in range(max_attempts):
            try:
                return json.loads(fixed_text)
            except json.JSONDecodeError as e:
                error_msg = str(e)
                print(f"Attempt {attempt + 1} failed: {error_msg[:100]}")
                
                # Try to fix based on the specific error
                if "Expecting property name" in error_msg:
                    # Missing quotes around property names
                    fixed_text = re.sub(r'([,{]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed_text)
                
                elif "Expecting ',' delimiter" in error_msg:
                    # Missing comma - try to find the position
                    match = re.search(r'char (\d+)', error_msg)
                    if match:
                        pos = int(match.group(1))
                        # Insert a comma before the position
                        if pos > 0 and pos < len(fixed_text):
                            if fixed_text[pos-1] in '}]':
                                fixed_text = fixed_text[:pos] + ',' + fixed_text[pos:]
                
                elif "Invalid \\escape" in error_msg:
                    # Unescaped backslashes
                    fixed_text = fixed_text.replace('\\', '\\\\')
                
                elif "Unterminated string" in error_msg:
                    # This is harder to fix automatically
                    # Try to find unclosed quotes
                    pass
                
                # If we've made changes, try again
                continue
        
        # Last resort: try to extract structured data even if JSON is broken
        try:
            return JSONFixer._extract_structure(text)
        except:
            return None
    
    @staticmethod
    def _extract_structure(text: str) -> Dict[str, Any]:
        """
        Extract script structure even from badly formatted text
        
        Args:
            text: Text that might contain script elements
            
        Returns:
            Dictionary with extracted script structure
        """
        
        # Look for key patterns
        title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
        hook_match = re.search(r'"hook"\s*:\s*"([^"]+)"', text)
        intro_match = re.search(r'"intro"\s*:\s*"([^"]+)"', text)
        outro_match = re.search(r'"outro"\s*:\s*"([^"]+)"', text)
        
        # Extract chapters
        chapters = []
        chapter_pattern = r'"heading"\s*:\s*"([^"]+)"[^}]*"body"\s*:\s*"([^"]+)"'
        for match in re.finditer(chapter_pattern, text, re.DOTALL):
            chapters.append({
                "heading": match.group(1),
                "body": match.group(2)
            })
        
        # Extract keywords
        keywords = []
        keyword_match = re.search(r'"broll_keywords"\s*:\s*\[([^\]]+)\]', text)
        if keyword_match:
            keyword_text = keyword_match.group(1)
            keywords = [k.strip().strip('"') for k in keyword_text.split(',')]
        
        return {
            "version": "script.v1",
            "title": title_match.group(1) if title_match else "Untitled",
            "hook": hook_match.group(1) if hook_match else "",
            "narration": {
                "intro": intro_match.group(1) if intro_match else "",
                "chapters": chapters,
                "outro": outro_match.group(1) if outro_match else "Thanks for watching!"
            },
            "broll_keywords": keywords,
            "policy_checklist": {
                "copyright_risk": False,
                "medical_or_financial_claims": False,
                "nsfw": False,
                "shocking_or_graphic": False
            }
        }
    
    @staticmethod
    def validate_script(script: Dict[str, Any]) -> bool:
        """
        Validate that a script has the required structure
        
        Args:
            script: Script dictionary
            
        Returns:
            True if valid
        """
        required_fields = ['title', 'narration']
        narration_fields = ['intro', 'outro']
        
        # Check top-level fields
        for field in required_fields:
            if field not in script:
                print(f"Missing required field: {field}")
                return False
        
        # Check narration structure
        if not isinstance(script.get('narration'), dict):
            print("Narration must be a dictionary")
            return False
        
        for field in narration_fields:
            if field not in script['narration']:
                print(f"Missing narration field: {field}")
                return False
        
        return True


def test_json_fixer():
    """Test the JSON fixer with common errors"""
    
    # Test case 1: Extra character between objects (like your 'e' error)
    bad_json1 = '''
    {
      "chapters": [
        {"id": 1, "body": "text"},
        {"id": 2, "body": "text"}
      e {"id": 3, "body": "text"}
      ]
    }
    '''
    
    # Test case 2: Smart quotes
    bad_json2 = '''
    {
      "title": "Test's Title",
      "body": "He said "hello" to me"
    }
    '''
    
    # Test case 3: Trailing comma
    bad_json3 = '''
    {
      "items": [1, 2, 3,],
      "name": "test",
    }
    '''
    
    fixer = JSONFixer()
    
    for i, test_json in enumerate([bad_json1, bad_json2, bad_json3], 1):
        print(f"\nTest case {i}:")
        result = fixer.parse_with_fixes(test_json)
        if result:
            print(f"✓ Successfully fixed and parsed")
            print(f"  Result: {json.dumps(result, indent=2)[:200]}...")
        else:
            print(f"✗ Failed to parse")


if __name__ == "__main__":
    test_json_fixer()