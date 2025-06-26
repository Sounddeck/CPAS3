"""
Ollama service with improved JSON generation capabilities.

This module provides enhanced Ollama integration specifically designed for:
- Better JSON generation prompting
- Structured output handling
- Retry mechanisms for malformed responses
- Integration with json_helper for robust parsing
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union, Callable
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout

from .json_helper import JSONHelper, JSONParsingError, extract_json_from_response

logger = logging.getLogger(__name__)


class OllamaServiceError(Exception):
    """Custom exception for Ollama service errors."""
    pass


class OllamaService:
    """Enhanced Ollama service with JSON-focused capabilities."""
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 default_model: str = "mistral:7b",
                 timeout: int = 120,
                 max_retries: int = 3):
        """
        Initialize the Ollama service.
        
        Args:
            base_url: Base URL for Ollama API
            default_model: Default model to use
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.default_model = default_model
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Test connection on initialization
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """
        Test connection to Ollama service.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("Successfully connected to Ollama service")
                return True
            else:
                logger.warning(f"Ollama service responded with status {response.status_code}")
                return False
        except Exception as e:
            logger.warning(f"Failed to connect to Ollama service: {e}")
            return False
    
    def _create_json_prompt(self, 
                           task_description: str, 
                           schema: Optional[Dict[str, Any]] = None,
                           examples: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Create a prompt optimized for JSON generation.
        
        Args:
            task_description: Description of the task
            schema: Optional JSON schema to follow
            examples: Optional examples of expected output
            
        Returns:
            Optimized prompt for JSON generation
        """
        prompt_parts = [
            "You are a precise JSON generator. Your task is to generate valid JSON only.",
            "CRITICAL: Your response must be valid JSON and nothing else.",
            "Do not include any explanatory text, markdown formatting, or code blocks.",
            "Do not start with ```json or end with ```.",
            "",
            f"Task: {task_description}",
            ""
        ]
        
        if schema:
            prompt_parts.extend([
                "Required JSON schema:",
                json.dumps(schema, indent=2),
                ""
            ])
        
        if examples:
            prompt_parts.append("Examples of expected output:")
            for i, example in enumerate(examples, 1):
                prompt_parts.extend([
                    f"Example {i}:",
                    json.dumps(example, indent=2),
                    ""
                ])
        
        prompt_parts.extend([
            "Remember:",
            "- Output ONLY valid JSON",
            "- Use double quotes for all strings",
            "- No trailing commas",
            "- No comments or extra text",
            "- Ensure proper JSON formatting",
            "",
            "JSON Output:"
        ])
        
        return "\n".join(prompt_parts)
    
    def _make_request(self, 
                     endpoint: str, 
                     data: Dict[str, Any], 
                     stream: bool = False) -> Union[requests.Response, requests.models.Response]:
        """
        Make a request to Ollama API with retry logic.
        
        Args:
            endpoint: API endpoint
            data: Request data
            stream: Whether to stream the response
            
        Returns:
            Response object
            
        Raises:
            OllamaServiceError: If request fails after all retries
        """
        url = f"{self.base_url}/api/{endpoint}"
        
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    url,
                    json=data,
                    timeout=self.timeout,
                    stream=stream
                )
                
                if response.status_code == 200:
                    return response
                else:
                    logger.warning(f"Ollama API returned status {response.status_code}: {response.text}")
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        raise OllamaServiceError(f"API request failed with status {response.status_code}")
            
            except (ConnectionError, Timeout) as e:
                logger.warning(f"Connection error (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise OllamaServiceError(f"Connection failed after {self.max_retries + 1} attempts: {e}")
            
            except RequestException as e:
                logger.error(f"Request error: {e}")
                raise OllamaServiceError(f"Request error: {e}")
    
    def generate_text(self, 
                     prompt: str, 
                     model: Optional[str] = None,
                     temperature: float = 0.1,
                     **kwargs) -> str:
        """
        Generate text using Ollama.
        
        Args:
            prompt: Input prompt
            model: Model to use (defaults to default_model)
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            Generated text
            
        Raises:
            OllamaServiceError: If generation fails
        """
        model = model or self.default_model
        
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                **kwargs
            }
        }
        
        try:
            response = self._make_request("generate", data)
            result = response.json()
            
            if "response" in result:
                return result["response"].strip()
            else:
                raise OllamaServiceError(f"Unexpected response format: {result}")
                
        except json.JSONDecodeError as e:
            raise OllamaServiceError(f"Failed to parse Ollama response: {e}")
    
    def generate_json(self, 
                     task_description: str,
                     schema: Optional[Dict[str, Any]] = None,
                     examples: Optional[List[Dict[str, Any]]] = None,
                     model: Optional[str] = None,
                     temperature: float = 0.1,
                     max_json_retries: int = 3) -> Any:
        """
        Generate JSON with optimized prompting and parsing.
        
        Args:
            task_description: Description of what JSON to generate
            schema: Optional JSON schema to follow
            examples: Optional examples of expected output
            model: Model to use
            temperature: Sampling temperature (lower for more consistent JSON)
            max_json_retries: Maximum retries for JSON parsing
            
        Returns:
            Parsed JSON data
            
        Raises:
            OllamaServiceError: If generation or parsing fails
        """
        prompt = self._create_json_prompt(task_description, schema, examples)
        
        for attempt in range(max_json_retries + 1):
            try:
                # Generate response
                response_text = self.generate_text(
                    prompt, 
                    model=model, 
                    temperature=temperature
                )
                
                logger.debug(f"Ollama response (attempt {attempt + 1}): {response_text[:200]}...")
                
                # Try to parse JSON from response
                try:
                    parsed_json = extract_json_from_response(response_text)
                    
                    # Validate schema if provided
                    if schema and isinstance(parsed_json, dict):
                        if not self._validate_against_schema(parsed_json, schema):
                            logger.warning(f"Generated JSON doesn't match schema (attempt {attempt + 1})")
                            if attempt < max_json_retries:
                                continue
                    
                    logger.info("Successfully generated and parsed JSON")
                    return parsed_json
                    
                except JSONParsingError as e:
                    logger.warning(f"JSON parsing failed (attempt {attempt + 1}): {e}")
                    
                    if attempt < max_json_retries:
                        # Modify prompt to be more explicit about JSON formatting
                        prompt = self._create_stricter_json_prompt(task_description, response_text)
                        continue
                    else:
                        raise OllamaServiceError(f"Failed to generate valid JSON after {max_json_retries + 1} attempts")
            
            except Exception as e:
                logger.error(f"Error in JSON generation (attempt {attempt + 1}): {e}")
                if attempt < max_json_retries:
                    continue
                else:
                    raise OllamaServiceError(f"JSON generation failed: {e}")
        
        raise OllamaServiceError("Unexpected error in JSON generation")
    
    def _create_stricter_json_prompt(self, task_description: str, previous_response: str) -> str:
        """
        Create a stricter prompt based on previous failed response.
        
        Args:
            task_description: Original task description
            previous_response: Previous response that failed to parse
            
        Returns:
            Stricter prompt for JSON generation
        """
        return f"""
You previously generated this response which was not valid JSON:
{previous_response[:200]}...

This is WRONG. You must generate ONLY valid JSON.

Task: {task_description}

STRICT REQUIREMENTS:
1. Output MUST be valid JSON only
2. Start with {{ or [ 
3. End with }} or ]
4. Use double quotes only, never single quotes
5. No trailing commas
6. No comments or explanatory text
7. No markdown code blocks
8. No additional text before or after JSON

Valid JSON Output:"""
    
    def _validate_against_schema(self, data: Any, schema: Dict[str, Any]) -> bool:
        """
        Basic schema validation.
        
        Args:
            data: Data to validate
            schema: Schema to validate against
            
        Returns:
            True if data matches schema structure
        """
        try:
            if not isinstance(data, dict) or not isinstance(schema, dict):
                return False
            
            # Check required fields if specified
            if "required" in schema:
                for field in schema["required"]:
                    if field not in data:
                        return False
            
            # Check properties if specified
            if "properties" in schema:
                for field, field_schema in schema["properties"].items():
                    if field in data:
                        field_type = field_schema.get("type")
                        if field_type and not self._check_type(data[field], field_type):
                            return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Schema validation error: {e}")
            return False
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """
        Check if value matches expected JSON type.
        
        Args:
            value: Value to check
            expected_type: Expected JSON type
            
        Returns:
            True if type matches
        """
        type_mapping = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None)
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, assume valid
        
        return isinstance(value, expected_python_type)
    
    def generate_tool_definition(self, 
                                description: str,
                                tool_name: Optional[str] = None,
                                parameters: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate a tool definition JSON using Ollama.
        
        Args:
            description: Description of what the tool should do
            tool_name: Optional specific tool name
            parameters: Optional list of parameter names
            
        Returns:
            Tool definition as dictionary
        """
        schema = {
            "type": "object",
            "required": ["name", "description", "parameters"],
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
        
        examples = [
            {
                "name": "file_reader",
                "description": "Read contents of a file",
                "parameters": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                }
            }
        ]
        
        task = f"Generate a tool definition for: {description}"
        if tool_name:
            task += f" The tool should be named '{tool_name}'."
        if parameters:
            task += f" It should have these parameters: {', '.join(parameters)}."
        
        return self.generate_json(
            task_description=task,
            schema=schema,
            examples=examples,
            temperature=0.1
        )
    
    def list_models(self) -> List[str]:
        """
        List available models.
        
        Returns:
            List of available model names
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            else:
                logger.warning(f"Failed to list models: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def is_model_available(self, model_name: str) -> bool:
        """
        Check if a specific model is available.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is available
        """
        available_models = self.list_models()
        return model_name in available_models


# Factory function for creating OllamaService instances
def create_ollama_service(base_url: Optional[str] = None, 
                         model: Optional[str] = None) -> OllamaService:
    """
    Create an OllamaService instance with default configuration.
    
    Args:
        base_url: Optional base URL override
        model: Optional default model override
        
    Returns:
        Configured OllamaService instance
    """
    # Try to get configuration from config manager if available
    try:
        from .config_manager import ConfigManager
        config = ConfigManager()
        
        default_base_url = config.get("llm_base_url", "http://localhost:11434")
        default_model = config.get("llm_model", "mistral:7b")
        
    except ImportError:
        logger.warning("ConfigManager not available, using hardcoded defaults")
        default_base_url = "http://localhost:11434"
        default_model = "mistral:7b"
    
    return OllamaService(
        base_url=base_url or default_base_url,
        default_model=model or default_model
    )


# Convenience functions
def generate_json_with_ollama(task_description: str, 
                            schema: Optional[Dict[str, Any]] = None,
                            **kwargs) -> Any:
    """
    Convenience function to generate JSON using Ollama.
    
    Args:
        task_description: What JSON to generate
        schema: Optional schema to follow
        **kwargs: Additional arguments for OllamaService.generate_json
        
    Returns:
        Parsed JSON data
    """
    service = create_ollama_service()
    return service.generate_json(task_description, schema=schema, **kwargs)


def generate_tool_with_ollama(description: str, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to generate tool definition using Ollama.
    
    Args:
        description: Description of the tool
        **kwargs: Additional arguments
        
    Returns:
        Tool definition dictionary
    """
    service = create_ollama_service()
    return service.generate_tool_definition(description, **kwargs)