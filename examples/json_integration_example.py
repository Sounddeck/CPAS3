"""
Example integration showing how to update existing JSON parsing code 
to use the new robust utilities.

This demonstrates how to migrate from standard json.loads() calls
to the new robust JSON parsing system.
"""

import json
import logging
from typing import Any, Dict, Optional

# Import the new robust utilities
from modules.utils.json_helper import JSONHelper, parse_json, extract_json_from_response
from modules.utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class ExampleIntegration:
    """
    Example showing how to integrate the new JSON parsing utilities
    into existing code that previously used standard json.loads().
    """
    
    def __init__(self):
        self.config = ConfigManager()
    
    def old_json_parsing_method(self, json_text: str) -> Dict[str, Any]:
        """
        Example of OLD method that could fail with malformed JSON.
        
        This is the type of code that would experience the parsing issues
        mentioned in the problem statement.
        """
        try:
            # This would fail with trailing commas, control characters, etc.
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"Standard JSON parsing failed: {e}")
            raise
    
    def new_robust_json_parsing_method(self, json_text: str) -> Dict[str, Any]:
        """
        NEW method using robust JSON parsing with fallback mechanisms.
        
        This handles all the edge cases mentioned in the problem statement.
        """
        try:
            # Use the robust parsing with multiple fallback strategies
            return JSONHelper.parse_json_robust(json_text)
        except Exception as e:
            logger.error(f"Robust JSON parsing failed (all strategies exhausted): {e}")
            # Still raise, but we've tried much harder to parse it
            raise
    
    def process_llm_response_old_way(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        OLD way of processing LLM responses that could contain JSON.
        
        This would often fail when LLM responses contain extra text,
        code blocks, or malformed JSON.
        """
        try:
            # Try to find JSON in the response (naive approach)
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_part = response_text[start:end]
                return json.loads(json_part)
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to extract JSON from LLM response: {e}")
            return None
    
    def process_llm_response_new_way(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        NEW way of processing LLM responses using robust extraction and parsing.
        
        This handles all the common issues with LLM-generated JSON.
        """
        try:
            # Use the robust extraction and parsing
            return extract_json_from_response(response_text)
        except Exception as e:
            logger.error(f"Failed to extract JSON from LLM response (all methods tried): {e}")
            return None
    
    def load_config_file_old_way(self, file_path: str) -> Dict[str, Any]:
        """
        OLD way of loading config files that could have formatting issues.
        """
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Config file has invalid JSON: {e}")
            raise
        except FileNotFoundError:
            logger.error(f"Config file not found: {file_path}")
            raise
    
    def load_config_file_new_way(self, file_path: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        NEW way of loading config files with robust parsing and fallbacks.
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                # Use robust parsing that can handle formatting issues
                return JSONHelper.parse_json_robust(content)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {file_path}")
            return default or {}
        except Exception as e:
            logger.error(f"Failed to load config file {file_path}: {e}")
            return default or {}
    
    def safe_json_operations(self, data: Any, default_return: Any = None) -> Any:
        """
        Example of safe JSON operations using the new utilities.
        """
        # Safe parsing with default
        if isinstance(data, str):
            return parse_json(data, default_return)
        
        # Safe serialization
        try:
            return JSONHelper.pretty_print_json(data)
        except Exception:
            return str(data)


def demonstrate_improvements():
    """
    Demonstrate the improvements in JSON parsing reliability.
    """
    print("=== JSON Parsing Improvements Demo ===")
    
    integration = ExampleIntegration()
    
    # Test cases that would fail with old method but work with new method
    test_cases = [
        '{"name": "test", "value": 123,}',  # Trailing comma
        "{'name': 'test', 'value': 123}",   # Single quotes  
        '{"name\x01": "test"}',             # Control character
        '''
        Here is the JSON you requested:
        {
            "name": "embedded",
            "value": 456
        }
        Please use this data.
        ''',  # JSON embedded in text
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Input: {repr(test_case[:50])}...")
        
        # Try old method
        try:
            old_result = integration.old_json_parsing_method(test_case)
            print(f"Old method: ✅ {old_result}")
        except Exception as e:
            print(f"Old method: ❌ {type(e).__name__}: {e}")
        
        # Try new method
        try:
            new_result = integration.new_robust_json_parsing_method(test_case)
            print(f"New method: ✅ {new_result}")
        except Exception as e:
            print(f"New method: ❌ {type(e).__name__}: {e}")


def show_migration_guide():
    """
    Show how to migrate existing code to use the new utilities.
    """
    print("\n=== Migration Guide ===")
    
    print("""
    BEFORE (prone to parsing failures):
    -----------------------------------
    import json
    
    def parse_response(text):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    
    AFTER (robust parsing with fallbacks):
    -------------------------------------
    from modules.utils.json_helper import parse_json, extract_json_from_response
    
    def parse_response(text):
        # For simple JSON strings
        return parse_json(text, default={})
        
        # For LLM responses that may contain JSON
        return extract_json_from_response(text)
    
    BENEFITS:
    ---------
    ✅ Handles trailing commas
    ✅ Handles single quotes
    ✅ Removes control characters
    ✅ Extracts JSON from text
    ✅ Multiple fallback strategies
    ✅ Better error logging
    ✅ Consistent return values
    """)


if __name__ == "__main__":
    demonstrate_improvements()
    show_migration_guide()