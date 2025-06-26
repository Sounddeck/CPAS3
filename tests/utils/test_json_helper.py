"""
Test suite for JSON helper utilities.
"""

import json
import unittest
from modules.utils.json_helper import (
    JSONHelper, JSONParsingError, parse_json, 
    extract_json_from_response, clean_json_text
)


class TestJSONHelper(unittest.TestCase):
    """Test cases for JSONHelper class."""
    
    def test_clean_control_characters(self):
        """Test control character cleaning."""
        # Test with control characters
        text_with_controls = "Hello\x00\x01World\x0c"
        cleaned = JSONHelper.clean_control_characters(text_with_controls)
        self.assertEqual(cleaned, "Hello World ")
        
        # Test with normal text
        normal_text = "Hello World"
        cleaned = JSONHelper.clean_control_characters(normal_text)
        self.assertEqual(cleaned, normal_text)
        
        # Test with non-string input
        cleaned = JSONHelper.clean_control_characters(123)
        self.assertEqual(cleaned, "123")
    
    def test_normalize_json_text(self):
        """Test JSON text normalization."""
        # Test single quote to double quote conversion
        single_quotes = "{'key': 'value'}"
        normalized = JSONHelper.normalize_json_text(single_quotes)
        self.assertIn('"key"', normalized)
        self.assertIn('"value"', normalized)
        
        # Test trailing comma removal
        trailing_comma = '{"key": "value",}'
        normalized = JSONHelper.normalize_json_text(trailing_comma)
        self.assertEqual(normalized, '{"key": "value"}')
        
        # Test control character removal
        with_controls = '{"key\x01": "value"}'
        normalized = JSONHelper.normalize_json_text(with_controls)
        self.assertNotIn('\x01', normalized)
    
    def test_extract_json_from_text(self):
        """Test JSON extraction from text."""
        # Test with JSON object in text
        text_with_json = 'Here is some JSON: {"name": "test", "value": 123} and more text'
        candidates = JSONHelper.extract_json_from_text(text_with_json)
        self.assertTrue(len(candidates) > 0)
        self.assertIn('{"name": "test", "value": 123}', candidates)
        
        # Test with JSON array
        text_with_array = 'Array: [1, 2, 3] here'
        candidates = JSONHelper.extract_json_from_text(text_with_array)
        self.assertTrue(len(candidates) > 0)
        self.assertIn('[1, 2, 3]', candidates)
        
        # Test with no JSON
        no_json = 'This text has no JSON at all'
        candidates = JSONHelper.extract_json_from_text(no_json)
        self.assertEqual(len(candidates), 0)
    
    def test_try_parse_json(self):
        """Test basic JSON parsing."""
        # Test valid JSON
        valid_json = '{"key": "value"}'
        success, result = JSONHelper.try_parse_json(valid_json)
        self.assertTrue(success)
        self.assertEqual(result, {"key": "value"})
        
        # Test invalid JSON
        invalid_json = '{"key": "value",}'
        success, result = JSONHelper.try_parse_json(invalid_json)
        self.assertFalse(success)
        self.assertIsNone(result)
    
    def test_parse_json_robust_valid(self):
        """Test robust parsing with valid JSON."""
        valid_json = '{"name": "test", "value": 123}'
        result = JSONHelper.parse_json_robust(valid_json)
        self.assertEqual(result, {"name": "test", "value": 123})
    
    def test_parse_json_robust_malformed(self):
        """Test robust parsing with malformed JSON."""
        # Test trailing comma
        trailing_comma = '{"name": "test", "value": 123,}'
        result = JSONHelper.parse_json_robust(trailing_comma)
        self.assertEqual(result, {"name": "test", "value": 123})
        
        # Test single quotes
        single_quotes = "{'name': 'test', 'value': 123}"
        result = JSONHelper.parse_json_robust(single_quotes)
        self.assertEqual(result, {"name": "test", "value": 123})
    
    def test_parse_json_robust_from_text(self):
        """Test robust parsing with JSON embedded in text."""
        text_with_json = 'Here is the data: {"name": "test", "value": 123} end of data'
        result = JSONHelper.parse_json_robust(text_with_json)
        self.assertEqual(result, {"name": "test", "value": 123})
    
    def test_parse_json_robust_failure(self):
        """Test robust parsing failure cases."""
        # Test with completely invalid input
        with self.assertRaises(JSONParsingError):
            JSONHelper.parse_json_robust("This is not JSON at all")
        
        # Test with empty string
        with self.assertRaises(JSONParsingError):
            JSONHelper.parse_json_robust("")
        
        # Test with None
        with self.assertRaises(JSONParsingError):
            JSONHelper.parse_json_robust(None)
    
    def test_fix_common_json_issues(self):
        """Test common JSON issue fixes."""
        # Test trailing comma fix
        trailing_comma = '{"key": "value",}'
        fixed = JSONHelper.fix_common_json_issues(trailing_comma)
        self.assertEqual(fixed, '{"key": "value"}')
        
        # Test unquoted keys
        unquoted_keys = '{key: "value"}'
        fixed = JSONHelper.fix_common_json_issues(unquoted_keys)
        self.assertIn('"key"', fixed)
    
    def test_manual_json_extraction(self):
        """Test manual JSON extraction."""
        # Test with key-value pairs
        text = 'name: "test", value: 123, active: true'
        result = JSONHelper.manual_json_extraction(text)
        expected = {"name": "test", "value": 123, "active": True}
        self.assertEqual(result, expected)
        
        # Test with quoted keys
        text = '"name": "test", "count": 42'
        result = JSONHelper.manual_json_extraction(text)
        expected = {"name": "test", "count": 42}
        self.assertEqual(result, expected)
    
    def test_safe_json_loads(self):
        """Test safe JSON loading with defaults."""
        # Test valid JSON
        valid_json = '{"key": "value"}'
        result = JSONHelper.safe_json_loads(valid_json, {})
        self.assertEqual(result, {"key": "value"})
        
        # Test invalid JSON with default
        invalid_json = "not json"
        default_value = {"default": True}
        result = JSONHelper.safe_json_loads(invalid_json, default_value)
        self.assertEqual(result, default_value)
    
    def test_validate_json_structure(self):
        """Test JSON structure validation."""
        # Test with required keys
        data = {"name": "test", "value": 123}
        is_valid = JSONHelper.validate_json_structure(data, ["name", "value"])
        self.assertTrue(is_valid)
        
        # Test with missing required keys
        data = {"name": "test"}
        is_valid = JSONHelper.validate_json_structure(data, ["name", "value"])
        self.assertFalse(is_valid)
        
        # Test with non-dict data
        data = [1, 2, 3]
        is_valid = JSONHelper.validate_json_structure(data)
        self.assertTrue(is_valid)
    
    def test_pretty_print_json(self):
        """Test JSON pretty printing."""
        data = {"name": "test", "nested": {"value": 123}}
        pretty = JSONHelper.pretty_print_json(data)
        self.assertIn("{\n", pretty)  # Check for formatting
        self.assertIn('"name": "test"', pretty)
        
        # Test with non-serializable data
        class CustomObj:
            pass
        
        pretty = JSONHelper.pretty_print_json(CustomObj())
        self.assertIsInstance(pretty, str)  # Should not crash


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    def test_parse_json(self):
        """Test parse_json convenience function."""
        # Test valid JSON
        result = parse_json('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})
        
        # Test invalid JSON with default
        result = parse_json("not json", {"default": True})
        self.assertEqual(result, {"default": True})
    
    def test_extract_json_from_response(self):
        """Test extract_json_from_response function."""
        # Test with JSON in response
        response = 'The result is: {"name": "test", "value": 123}'
        result = extract_json_from_response(response)
        self.assertEqual(result, {"name": "test", "value": 123})
        
        # Test with malformed JSON
        response = 'Result: {"name": "test", "value": 123,}'
        result = extract_json_from_response(response)
        self.assertEqual(result, {"name": "test", "value": 123})
    
    def test_clean_json_text(self):
        """Test clean_json_text function."""
        dirty_json = "{'key': 'value',}"
        cleaned = clean_json_text(dirty_json)
        # Should be normalized
        self.assertIn('"key"', cleaned)
        self.assertNotIn(',}', cleaned)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and complex scenarios."""
    
    def test_deeply_nested_json(self):
        """Test with deeply nested JSON structures."""
        nested_json = '''
        {
            "level1": {
                "level2": {
                    "level3": {
                        "data": "value"
                    }
                }
            }
        }
        '''
        result = JSONHelper.parse_json_robust(nested_json)
        self.assertEqual(result["level1"]["level2"]["level3"]["data"], "value")
    
    def test_json_with_arrays(self):
        """Test JSON with complex array structures."""
        json_with_arrays = '''
        {
            "items": [
                {"id": 1, "name": "first"},
                {"id": 2, "name": "second"}
            ],
            "metadata": {
                "count": 2,
                "tags": ["test", "example"]
            }
        }
        '''
        result = JSONHelper.parse_json_robust(json_with_arrays)
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0]["name"], "first")
        self.assertEqual(result["metadata"]["tags"], ["test", "example"])
    
    def test_json_with_special_characters(self):
        """Test JSON with special characters and unicode."""
        special_json = '''
        {
            "unicode": "Hello 世界",
            "special": "String with \\"quotes\\" and \\\\backslash",
            "emoji": "😀🎉"
        }
        '''
        result = JSONHelper.parse_json_robust(special_json)
        self.assertEqual(result["unicode"], "Hello 世界")
        self.assertIn("quotes", result["special"])
        self.assertEqual(result["emoji"], "😀🎉")
    
    def test_malformed_llm_response(self):
        """Test parsing typical malformed LLM responses."""
        # Common case: JSON wrapped in code blocks
        llm_response1 = '''
        Here's the JSON you requested:
        
        ```json
        {
            "name": "example",
            "value": 42
        }
        ```
        
        This should work for your needs.
        '''
        result = JSONHelper.parse_json_robust(llm_response1)
        self.assertEqual(result["name"], "example")
        self.assertEqual(result["value"], 42)
        
        # Common case: JSON with trailing comma and extra text
        llm_response2 = '''
        The generated configuration is:
        
        {
            "settings": {
                "enabled": true,
                "timeout": 30,
            },
            "features": ["feature1", "feature2",]
        }
        
        Let me know if you need any changes!
        '''
        result = JSONHelper.parse_json_robust(llm_response2)
        self.assertTrue(result["settings"]["enabled"])
        self.assertEqual(len(result["features"]), 2)
    
    def test_multiple_json_objects(self):
        """Test text with multiple JSON objects."""
        multi_json = '''
        First object: {"name": "first", "id": 1}
        Second object: {"name": "second", "id": 2}
        '''
        # Should extract the first valid JSON object found
        result = JSONHelper.parse_json_robust(multi_json)
        self.assertIn("name", result)
        self.assertIn("id", result)


if __name__ == '__main__':
    unittest.main()