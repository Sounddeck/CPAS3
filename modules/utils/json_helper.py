"""
Robust JSON parsing utilities with multi-stage fallback mechanisms.

This module provides comprehensive JSON parsing capabilities that can handle:
- Standard JSON parsing
- JSON with control characters and formatting issues
- Malformed JSON extraction from text
- Multiple fallback strategies for maximum reliability
"""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Union, Tuple

logger = logging.getLogger(__name__)


class JSONParsingError(Exception):
    """Custom exception for JSON parsing failures."""
    pass


class JSONHelper:
    """Comprehensive JSON parsing utility with multiple fallback strategies."""
    
    @staticmethod
    def clean_control_characters(text: str) -> str:
        """
        Remove or replace problematic control characters from text.
        
        Args:
            text: The input text to clean
            
        Returns:
            Cleaned text with control characters handled
        """
        if not isinstance(text, str):
            return str(text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Replace problematic control characters with spaces
        control_chars = ['\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', 
                        '\x0b', '\x0c', '\x0e', '\x0f', '\x10', '\x11', '\x12', '\x13', 
                        '\x14', '\x15', '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', 
                        '\x1c', '\x1d', '\x1e', '\x1f']
        
        for char in control_chars:
            text = text.replace(char, ' ')
        
        return text
    
    @staticmethod
    def normalize_json_text(text: str) -> str:
        """
        Normalize JSON text for better parsing.
        
        Args:
            text: The JSON text to normalize
            
        Returns:
            Normalized JSON text
        """
        # Clean control characters
        text = JSONHelper.clean_control_characters(text)
        
        # Fix common JSON formatting issues
        # Replace single quotes with double quotes (for simple cases)
        text = re.sub(r"'([^']*)':", r'"\1":', text)
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)
        
        # Fix trailing commas
        text = re.sub(r',(\s*[}\]])', r'\1', text)
        
        # Fix missing commas between objects/arrays
        text = re.sub(r'}(\s*){', r'},\1{', text)
        text = re.sub(r'](\s*)[{[]', r'],\1{', text)
        
        return text.strip()
    
    @staticmethod
    def extract_json_from_text(text: str) -> List[str]:
        """
        Extract potential JSON objects/arrays from text using regex.
        
        Args:
            text: Text that may contain JSON
            
        Returns:
            List of potential JSON strings found in the text, ordered by preference (objects first)
        """
        json_candidates = []
        
        # Pattern for JSON objects (prioritize these)
        object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        objects = re.findall(object_pattern, text, re.DOTALL)
        
        # Try to find more complex nested structures
        nested_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
        nested_objects = re.findall(nested_pattern, text, re.DOTALL)
        
        # Combine and prioritize objects
        all_objects = list(set(objects + nested_objects))
        # Sort by length (longer objects are likely more complete)
        all_objects.sort(key=len, reverse=True)
        json_candidates.extend(all_objects)
        
        # Pattern for JSON arrays (add after objects)
        array_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
        arrays = re.findall(array_pattern, text, re.DOTALL)
        json_candidates.extend(arrays)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for candidate in json_candidates:
            if candidate not in seen:
                seen.add(candidate)
                unique_candidates.append(candidate)
        
        return unique_candidates
    
    @staticmethod
    def try_parse_json(text: str) -> Tuple[bool, Optional[Any]]:
        """
        Attempt to parse JSON with a single strategy.
        
        Args:
            text: JSON text to parse
            
        Returns:
            Tuple of (success, parsed_data)
        """
        try:
            parsed = json.loads(text)
            return True, parsed
        except json.JSONDecodeError as e:
            logger.debug(f"Standard JSON parsing failed: {e}")
            return False, None
        except Exception as e:
            logger.debug(f"Unexpected error in JSON parsing: {e}")
            return False, None
    
    @staticmethod
    def parse_json_robust(text: str, extract_from_text: bool = True) -> Any:
        """
        Parse JSON with multiple fallback strategies.
        
        Args:
            text: The text containing JSON to parse
            extract_from_text: Whether to attempt extraction from surrounding text
            
        Returns:
            Parsed JSON data
            
        Raises:
            JSONParsingError: If all parsing strategies fail
        """
        if not text or not isinstance(text, str):
            raise JSONParsingError("Invalid input: text must be a non-empty string")
        
        original_text = text
        strategies_tried = []
        
        # Strategy 1: Direct JSON parsing
        strategies_tried.append("direct_parsing")
        success, result = JSONHelper.try_parse_json(text)
        if success:
            logger.debug("Successfully parsed JSON using direct parsing")
            return result
        
        # Strategy 2: Clean and normalize, then parse
        strategies_tried.append("normalized_parsing")
        normalized_text = JSONHelper.normalize_json_text(text)
        success, result = JSONHelper.try_parse_json(normalized_text)
        if success:
            logger.debug("Successfully parsed JSON using normalized parsing")
            return result
        
        # Strategy 3: Extract JSON from text and parse candidates
        if extract_from_text:
            strategies_tried.append("extraction_parsing")
            json_candidates = JSONHelper.extract_json_from_text(text)
            
            for candidate in json_candidates:
                # Try direct parsing of candidate
                success, result = JSONHelper.try_parse_json(candidate)
                if success:
                    logger.debug("Successfully parsed JSON using extraction parsing")
                    return result
                
                # Try normalized parsing of candidate
                normalized_candidate = JSONHelper.normalize_json_text(candidate)
                success, result = JSONHelper.try_parse_json(normalized_candidate)
                if success:
                    logger.debug("Successfully parsed JSON using extraction + normalization")
                    return result
        
        # Strategy 4: Try to fix common JSON issues manually
        strategies_tried.append("manual_fix_parsing")
        manually_fixed = JSONHelper.fix_common_json_issues(text)
        if manually_fixed != text:
            success, result = JSONHelper.try_parse_json(manually_fixed)
            if success:
                logger.debug("Successfully parsed JSON using manual fixes")
                return result
        
        # Strategy 5: Last resort - try to extract key-value pairs manually
        strategies_tried.append("manual_extraction")
        try:
            result = JSONHelper.manual_json_extraction(text)
            if result:
                logger.debug("Successfully extracted JSON using manual extraction")
                return result
        except Exception as e:
            logger.debug(f"Manual extraction failed: {e}")
        
        # All strategies failed
        error_msg = f"Failed to parse JSON after trying strategies: {', '.join(strategies_tried)}"
        logger.error(f"{error_msg}. Original text: {original_text[:200]}...")
        raise JSONParsingError(error_msg)
    
    @staticmethod
    def fix_common_json_issues(text: str) -> str:
        """
        Attempt to fix common JSON formatting issues.
        
        Args:
            text: The JSON text to fix
            
        Returns:
            Fixed JSON text
        """
        fixed_text = text
        
        # Fix missing quotes around keys (simple case)
        fixed_text = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', fixed_text)
        
        # Fix single quotes to double quotes (simple strings only)
        fixed_text = re.sub(r"'([^']*)'", r'"\1"', fixed_text)
        
        # Fix trailing commas
        fixed_text = re.sub(r',(\s*[}\]])', r'\1', fixed_text)
        
        # Fix missing commas between elements
        fixed_text = re.sub(r'([}\]"])(\s*)([{\[]|")', r'\1,\2\3', fixed_text)
        
        return fixed_text
    
    @staticmethod
    def manual_json_extraction(text: str) -> Optional[Dict[str, Any]]:
        """
        Last resort manual extraction of key-value pairs from text.
        
        Args:
            text: Text to extract from
            
        Returns:
            Dictionary of extracted key-value pairs or None
        """
        result = {}
        
        # Try to find key-value patterns
        patterns = [
            r'"([^"]+)"\s*:\s*"([^"]*)"',  # "key": "value"
            r'"([^"]+)"\s*:\s*(\d+\.?\d*)',  # "key": number
            r'"([^"]+)"\s*:\s*(true|false|null)',  # "key": boolean/null
            r'([a-zA-Z_]\w*)\s*:\s*"([^"]*)"',  # key: "value" (unquoted key)
            r'([a-zA-Z_]\w*)\s*:\s*(\d+\.?\d*)',  # key: number (unquoted key)
            r'([a-zA-Z_]\w*)\s*:\s*(true|false|null)',  # key: boolean/null (unquoted key)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                key, value = match[0], match[1]
                
                # Try to parse value appropriately
                if value.lower() == 'true':
                    result[key] = True
                elif value.lower() == 'false':
                    result[key] = False
                elif value.lower() == 'null':
                    result[key] = None
                elif value.isdigit():
                    result[key] = int(value)
                elif re.match(r'^\d+\.\d+$', value):
                    result[key] = float(value)
                else:
                    result[key] = value
        
        return result if result else None
    
    @staticmethod
    def safe_json_loads(text: str, default: Any = None) -> Any:
        """
        Safely load JSON with a default value on failure.
        
        Args:
            text: JSON text to parse
            default: Default value to return on parsing failure
            
        Returns:
            Parsed JSON data or default value
        """
        try:
            return JSONHelper.parse_json_robust(text)
        except JSONParsingError:
            logger.warning(f"Failed to parse JSON, returning default value: {default}")
            return default
    
    @staticmethod
    def validate_json_structure(data: Any, required_keys: Optional[List[str]] = None) -> bool:
        """
        Validate that parsed JSON has expected structure.
        
        Args:
            data: Parsed JSON data
            required_keys: List of required keys (for dict data)
            
        Returns:
            True if structure is valid, False otherwise
        """
        if required_keys and isinstance(data, dict):
            return all(key in data for key in required_keys)
        
        # Basic validation - just check if it's valid Python data
        return data is not None
    
    @staticmethod
    def pretty_print_json(data: Any, indent: int = 2) -> str:
        """
        Pretty print JSON data.
        
        Args:
            data: Data to format as JSON
            indent: Number of spaces for indentation
            
        Returns:
            Pretty-formatted JSON string
        """
        try:
            return json.dumps(data, indent=indent, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to pretty print JSON: {e}")
            return str(data)


# Convenience functions for common use cases
def parse_json(text: str, default: Any = None) -> Any:
    """
    Parse JSON text with robust error handling.
    
    Args:
        text: JSON text to parse
        default: Default value on parsing failure
        
    Returns:
        Parsed JSON data or default value
    """
    return JSONHelper.safe_json_loads(text, default)


def extract_json_from_response(response_text: str) -> Any:
    """
    Extract and parse JSON from LLM response text.
    
    Args:
        response_text: Response text that may contain JSON
        
    Returns:
        Parsed JSON data
        
    Raises:
        JSONParsingError: If no valid JSON could be extracted
    """
    return JSONHelper.parse_json_robust(response_text, extract_from_text=True)


def clean_json_text(text: str) -> str:
    """
    Clean and normalize JSON text for parsing.
    
    Args:
        text: JSON text to clean
        
    Returns:
        Cleaned JSON text
    """
    return JSONHelper.normalize_json_text(text)