"""
Test suite for Ollama service utilities.
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from modules.utils.ollama_service import (
    OllamaService, OllamaServiceError, create_ollama_service,
    generate_json_with_ollama, generate_tool_with_ollama
)


class TestOllamaService(unittest.TestCase):
    """Test cases for OllamaService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the connection test to avoid requiring actual Ollama
        with patch.object(OllamaService, '_test_connection', return_value=True):
            self.service = OllamaService(
                base_url="http://localhost:11434",
                default_model="test-model"
            )
    
    def test_init(self):
        """Test OllamaService initialization."""
        self.assertEqual(self.service.base_url, "http://localhost:11434")
        self.assertEqual(self.service.default_model, "test-model")
        self.assertEqual(self.service.timeout, 120)
        self.assertEqual(self.service.max_retries, 3)
    
    def test_create_json_prompt_basic(self):
        """Test basic JSON prompt creation."""
        prompt = self.service._create_json_prompt("Generate a user object")
        
        self.assertIn("JSON generator", prompt)
        self.assertIn("Generate a user object", prompt)
        self.assertIn("valid JSON only", prompt)
        self.assertIn("double quotes", prompt)
        self.assertIn("No trailing commas", prompt)
    
    def test_create_json_prompt_with_schema(self):
        """Test JSON prompt creation with schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
        
        prompt = self.service._create_json_prompt("Generate a user", schema=schema)
        
        self.assertIn("Required JSON schema", prompt)
        self.assertIn('"name"', prompt)
        self.assertIn('"age"', prompt)
    
    def test_create_json_prompt_with_examples(self):
        """Test JSON prompt creation with examples."""
        examples = [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25}
        ]
        
        prompt = self.service._create_json_prompt("Generate a user", examples=examples)
        
        self.assertIn("Examples of expected output", prompt)
        self.assertIn("John", prompt)
        self.assertIn("Jane", prompt)
    
    def test_create_stricter_json_prompt(self):
        """Test stricter JSON prompt creation."""
        previous_response = "This is not valid JSON: {invalid: true,}"
        
        prompt = self.service._create_stricter_json_prompt(
            "Generate user data", 
            previous_response
        )
        
        self.assertIn("WRONG", prompt)
        self.assertIn("STRICT REQUIREMENTS", prompt)
        self.assertIn("double quotes only", prompt)
        self.assertIn("No trailing commas", prompt)
    
    def test_validate_against_schema(self):
        """Test schema validation."""
        schema = {
            "type": "object",
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }
        
        # Valid data
        valid_data = {"name": "John", "age": 30}
        self.assertTrue(self.service._validate_against_schema(valid_data, schema))
        
        # Missing required field
        invalid_data = {"name": "John"}
        self.assertFalse(self.service._validate_against_schema(invalid_data, schema))
        
        # Wrong type
        wrong_type_data = {"name": "John", "age": "thirty"}
        self.assertFalse(self.service._validate_against_schema(wrong_type_data, schema))
    
    def test_check_type(self):
        """Test type checking utility."""
        self.assertTrue(self.service._check_type("hello", "string"))
        self.assertTrue(self.service._check_type(42, "integer"))
        self.assertTrue(self.service._check_type(3.14, "number"))
        self.assertTrue(self.service._check_type(True, "boolean"))
        self.assertTrue(self.service._check_type([1, 2, 3], "array"))
        self.assertTrue(self.service._check_type({"key": "value"}, "object"))
        self.assertTrue(self.service._check_type(None, "null"))
        
        # Test wrong types
        self.assertFalse(self.service._check_type("hello", "integer"))
        self.assertFalse(self.service._check_type(42, "string"))
    
    @patch('requests.post')
    def test_make_request_success(self, mock_post):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "test response"}
        mock_post.return_value = mock_response
        
        response = self.service._make_request("generate", {"test": "data"})
        
        self.assertEqual(response.status_code, 200)
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_make_request_failure(self, mock_post):
        """Test failed API request with retries."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        with self.assertRaises(OllamaServiceError):
            self.service._make_request("generate", {"test": "data"})
        
        # Should retry max_retries + 1 times
        self.assertEqual(mock_post.call_count, self.service.max_retries + 1)
    
    @patch.object(OllamaService, '_make_request')
    def test_generate_text_success(self, mock_make_request):
        """Test successful text generation."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Generated text"}
        mock_make_request.return_value = mock_response
        
        result = self.service.generate_text("Test prompt")
        
        self.assertEqual(result, "Generated text")
        mock_make_request.assert_called_once()
    
    @patch.object(OllamaService, '_make_request')
    def test_generate_text_failure(self, mock_make_request):
        """Test failed text generation."""
        mock_make_request.side_effect = OllamaServiceError("Connection failed")
        
        with self.assertRaises(OllamaServiceError):
            self.service.generate_text("Test prompt")
    
    @patch.object(OllamaService, 'generate_text')
    def test_generate_json_success(self, mock_generate_text):
        """Test successful JSON generation."""
        mock_generate_text.return_value = '{"name": "John", "age": 30}'
        
        result = self.service.generate_json("Generate a user object")
        
        self.assertEqual(result, {"name": "John", "age": 30})
        mock_generate_text.assert_called_once()
    
    @patch.object(OllamaService, 'generate_text')
    def test_generate_json_with_retries(self, mock_generate_text):
        """Test JSON generation with retries on malformed JSON."""
        # First call returns malformed JSON, second call returns valid JSON
        mock_generate_text.side_effect = [
            '{"name": "John", "age": 30,}',  # Malformed (trailing comma)
            '{"name": "John", "age": 30}'     # Valid
        ]
        
        result = self.service.generate_json("Generate a user object")
        
        self.assertEqual(result, {"name": "John", "age": 30})
        self.assertEqual(mock_generate_text.call_count, 1)  # Should succeed on first try due to robust parsing
    
    @patch.object(OllamaService, 'generate_text')
    def test_generate_json_failure(self, mock_generate_text):
        """Test JSON generation failure after max retries."""
        mock_generate_text.return_value = "This is not JSON at all"
        
        with self.assertRaises(OllamaServiceError):
            self.service.generate_json("Generate invalid data", max_json_retries=1)
    
    @patch.object(OllamaService, 'generate_json')
    def test_generate_tool_definition(self, mock_generate_json):
        """Test tool definition generation."""
        expected_tool = {
            "name": "file_reader",
            "description": "Read file contents",
            "parameters": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file"
                }
            }
        }
        mock_generate_json.return_value = expected_tool
        
        result = self.service.generate_tool_definition("Read file contents")
        
        self.assertEqual(result, expected_tool)
        mock_generate_json.assert_called_once()
    
    @patch('requests.get')
    def test_list_models_success(self, mock_get):
        """Test successful model listing."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "model1"},
                {"name": "model2"}
            ]
        }
        mock_get.return_value = mock_response
        
        models = self.service.list_models()
        
        self.assertEqual(models, ["model1", "model2"])
    
    @patch('requests.get')
    def test_list_models_failure(self, mock_get):
        """Test failed model listing."""
        mock_get.side_effect = Exception("Connection failed")
        
        models = self.service.list_models()
        
        self.assertEqual(models, [])
    
    @patch.object(OllamaService, 'list_models')
    def test_is_model_available(self, mock_list_models):
        """Test model availability check."""
        mock_list_models.return_value = ["model1", "model2"]
        
        self.assertTrue(self.service.is_model_available("model1"))
        self.assertFalse(self.service.is_model_available("model3"))


class TestFactoryFunctions(unittest.TestCase):
    """Test factory and convenience functions."""
    
    @patch.object(OllamaService, '_test_connection', return_value=True)
    def test_create_ollama_service(self, mock_test):
        """Test OllamaService factory function."""
        service = create_ollama_service()
        
        self.assertIsInstance(service, OllamaService)
        self.assertEqual(service.base_url, "http://localhost:11434")
    
    @patch.object(OllamaService, '_test_connection', return_value=True)
    @patch.object(OllamaService, 'generate_json')
    def test_generate_json_with_ollama(self, mock_generate_json, mock_test):
        """Test convenience function for JSON generation."""
        expected_result = {"name": "test"}
        mock_generate_json.return_value = expected_result
        
        result = generate_json_with_ollama("Generate test data")
        
        self.assertEqual(result, expected_result)
    
    @patch.object(OllamaService, '_test_connection', return_value=True)
    @patch.object(OllamaService, 'generate_tool_definition')
    def test_generate_tool_with_ollama(self, mock_generate_tool, mock_test):
        """Test convenience function for tool generation."""
        expected_tool = {"name": "test_tool", "description": "Test tool"}
        mock_generate_tool.return_value = expected_tool
        
        result = generate_tool_with_ollama("Test tool description")
        
        self.assertEqual(result, expected_tool)


class TestOllamaServiceError(unittest.TestCase):
    """Test OllamaServiceError exception."""
    
    def test_ollama_service_error(self):
        """Test OllamaServiceError creation and handling."""
        error = OllamaServiceError("Test error message")
        
        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)


if __name__ == '__main__':
    unittest.main()