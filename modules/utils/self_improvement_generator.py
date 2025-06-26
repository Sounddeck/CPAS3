"""
Self-Improvement Tool Generator

This module demonstrates how to use the robust JSON parsing and Ollama service
utilities to generate tools dynamically for the Self-Improvement functionality.

It addresses JSON parsing issues by using the multi-stage fallback mechanisms
and improved Ollama prompting specifically designed for JSON generation.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from modules.utils.json_helper import JSONHelper, extract_json_from_response, JSONParsingError
from modules.utils.ollama_service import OllamaService, create_ollama_service, OllamaServiceError

logger = logging.getLogger(__name__)


class SelfImprovementToolGenerator:
    """
    Generates tools dynamically using AI with robust JSON parsing.
    
    This class addresses the JSON parsing issues mentioned in the problem statement by:
    1. Using multi-stage fallback JSON parsing mechanisms
    2. Employing better Ollama prompting for JSON generation
    3. Providing comprehensive error handling and retry logic
    """
    
    def __init__(self, ollama_service: Optional[OllamaService] = None):
        """
        Initialize the tool generator.
        
        Args:
            ollama_service: Optional OllamaService instance. If None, creates a default one.
        """
        self.ollama_service = ollama_service or create_ollama_service()
        self.generation_history = []
    
    def generate_tool_from_description(self, 
                                     description: str, 
                                     tool_name: Optional[str] = None,
                                     additional_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a tool definition from a natural language description.
        
        This method demonstrates robust JSON generation and parsing that handles
        the types of issues mentioned in the problem statement.
        
        Args:
            description: Natural language description of the desired tool
            tool_name: Optional specific name for the tool
            additional_context: Optional additional context or requirements
            
        Returns:
            Tool definition dictionary
            
        Raises:
            SelfImprovementError: If tool generation fails after all retries
        """
        logger.info(f"Generating tool from description: {description}")
        
        try:
            # Create comprehensive prompt context
            task_description = self._build_tool_generation_task(
                description, tool_name, additional_context
            )
            
            # Define the expected schema for tool definitions
            tool_schema = {
                "type": "object",
                "required": ["name", "description", "parameters", "implementation_hints"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Tool name (snake_case)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear description of what the tool does"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameter definitions for the tool"
                    },
                    "implementation_hints": {
                        "type": "array",
                        "description": "Hints for implementing the tool"
                    },
                    "use_cases": {
                        "type": "array", 
                        "description": "Example use cases"
                    }
                }
            }
            
            # Provide examples to guide generation
            examples = [
                {
                    "name": "file_analyzer",
                    "description": "Analyzes file content and provides insights",
                    "parameters": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to analyze"
                        },
                        "analysis_type": {
                            "type": "string",
                            "enum": ["structure", "content", "metadata"],
                            "description": "Type of analysis to perform"
                        }
                    },
                    "implementation_hints": [
                        "Use file extension to determine analysis approach",
                        "Handle large files by reading in chunks",
                        "Provide structured output with metrics"
                    ],
                    "use_cases": [
                        "Code quality analysis",
                        "Document structure review",
                        "Data file validation"
                    ]
                }
            ]
            
            # Generate the tool using robust JSON generation
            tool_definition = self.ollama_service.generate_json(
                task_description=task_description,
                schema=tool_schema,
                examples=examples,
                temperature=0.1,  # Low temperature for consistency
                max_json_retries=5  # More retries for complex JSON
            )
            
            logger.info(f"Successfully generated tool: {tool_definition.get('name', 'unnamed')}")
            
            # Validate the generated tool
            self._validate_tool_definition(tool_definition)
            
            # Store in history for potential learning
            self.generation_history.append({
                "description": description,
                "generated_tool": tool_definition,
                "timestamp": logger.name  # Simple timestamp placeholder
            })
            
            return tool_definition
            
        except OllamaServiceError as e:
            logger.error(f"Ollama service error during tool generation: {e}")
            raise SelfImprovementError(f"Failed to generate tool due to service error: {e}")
        
        except JSONParsingError as e:
            logger.error(f"JSON parsing error during tool generation: {e}")
            raise SelfImprovementError(f"Failed to parse generated tool JSON: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error during tool generation: {e}")
            raise SelfImprovementError(f"Unexpected error: {e}")
    
    def _build_tool_generation_task(self, 
                                   description: str, 
                                   tool_name: Optional[str], 
                                   additional_context: Optional[str]) -> str:
        """
        Build a comprehensive task description for tool generation.
        
        Args:
            description: Base description
            tool_name: Optional tool name
            additional_context: Optional additional context
            
        Returns:
            Formatted task description
        """
        task_parts = [
            "Generate a tool definition based on the following requirements:",
            f"Description: {description}"
        ]
        
        if tool_name:
            task_parts.append(f"Suggested name: {tool_name}")
        
        if additional_context:
            task_parts.append(f"Additional context: {additional_context}")
        
        task_parts.extend([
            "",
            "Requirements:",
            "- The tool name should be in snake_case format",
            "- Parameters should include type information and descriptions",
            "- Implementation hints should be practical and specific",
            "- Use cases should demonstrate real-world applications",
            "- All text should be clear and professional"
        ])
        
        return "\n".join(task_parts)
    
    def _validate_tool_definition(self, tool_definition: Dict[str, Any]) -> None:
        """
        Validate that a generated tool definition meets requirements.
        
        Args:
            tool_definition: The tool definition to validate
            
        Raises:
            SelfImprovementError: If validation fails
        """
        required_fields = ["name", "description", "parameters"]
        
        for field in required_fields:
            if field not in tool_definition:
                raise SelfImprovementError(f"Generated tool missing required field: {field}")
        
        # Validate name format
        name = tool_definition["name"]
        if not isinstance(name, str) or not name.replace("_", "").isalnum():
            raise SelfImprovementError(f"Invalid tool name format: {name}")
        
        # Validate parameters structure
        params = tool_definition["parameters"]
        if not isinstance(params, dict):
            raise SelfImprovementError("Tool parameters must be a dictionary")
        
        logger.info("Tool definition validation passed")
    
    def generate_multiple_tools(self, 
                               descriptions: List[str],
                               max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """
        Generate multiple tools from a list of descriptions.
        
        Args:
            descriptions: List of tool descriptions
            max_concurrent: Maximum number of tools to generate concurrently
            
        Returns:
            List of generated tool definitions
        """
        tools = []
        errors = []
        
        for i, description in enumerate(descriptions):
            try:
                tool = self.generate_tool_from_description(description)
                tools.append(tool)
                logger.info(f"Generated tool {i+1}/{len(descriptions)}: {tool['name']}")
            except Exception as e:
                error_msg = f"Failed to generate tool from description '{description}': {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        if errors:
            logger.warning(f"Tool generation completed with {len(errors)} errors")
        
        return tools
    
    def improve_existing_tool(self, 
                            existing_tool: Dict[str, Any], 
                            improvement_request: str) -> Dict[str, Any]:
        """
        Improve an existing tool based on feedback or requirements.
        
        Args:
            existing_tool: The existing tool definition
            improvement_request: Description of desired improvements
            
        Returns:
            Improved tool definition
        """
        logger.info(f"Improving tool: {existing_tool.get('name', 'unnamed')}")
        
        task_description = f"""
        Improve the following existing tool based on the improvement request:
        
        Existing Tool:
        {JSONHelper.pretty_print_json(existing_tool)}
        
        Improvement Request:
        {improvement_request}
        
        Provide an improved version of the tool that addresses the request while maintaining compatibility where possible.
        """
        
        try:
            improved_tool = self.ollama_service.generate_json(
                task_description=task_description,
                temperature=0.2,  # Slightly higher for creativity in improvements
                max_json_retries=3
            )
            
            self._validate_tool_definition(improved_tool)
            return improved_tool
            
        except Exception as e:
            logger.error(f"Failed to improve tool: {e}")
            raise SelfImprovementError(f"Tool improvement failed: {e}")
    
    def get_generation_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about tool generation history.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_tools_generated": len(self.generation_history),
            "recent_tools": [
                {
                    "name": item["generated_tool"].get("name", "unnamed"),
                    "description": item["description"][:100] + "..." if len(item["description"]) > 100 else item["description"]
                }
                for item in self.generation_history[-5:]  # Last 5 tools
            ]
        }


class SelfImprovementError(Exception):
    """Exception raised by Self-Improvement functionality."""
    pass


# Example usage and demonstration functions
def demonstrate_robust_json_parsing():
    """
    Demonstrate how the robust JSON parsing handles problematic responses.
    
    This function shows how the new JSON parsing utilities handle the types
    of issues mentioned in the problem statement.
    """
    print("=== Demonstrating Robust JSON Parsing ===")
    
    # Simulate problematic LLM responses that would cause parsing issues
    problematic_responses = [
        # Trailing comma issue
        '''Here's your tool:
        {
            "name": "example_tool",
            "description": "Does something useful",
            "parameters": {
                "input": "string",
            },
        }''',
        
        # JSON wrapped in code blocks
        '''```json
        {
            "name": "code_block_tool", 
            "description": "Tool from code block",
            "parameters": {}
        }
        ```''',
        
        # Control characters and formatting issues
        '''{
            "name": "messy\x01_tool",
            "description": "Tool with\x0ccontrol chars",
            "parameters": {}
        }''',
        
        # Single quotes instead of double quotes
        '''
        {
            'name': 'single_quote_tool',
            'description': 'Uses single quotes',
            'parameters': {}
        }
        '''
    ]
    
    for i, response in enumerate(problematic_responses, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Problematic response: {response[:100]}...")
        
        try:
            parsed = extract_json_from_response(response)
            print(f"✅ Successfully parsed: {parsed['name']}")
        except JSONParsingError as e:
            print(f"❌ Failed to parse: {e}")


def example_self_improvement_usage():
    """
    Example of how to use the Self-Improvement tool generator.
    
    This demonstrates the complete workflow for generating tools with
    robust JSON parsing and error handling.
    """
    print("\n=== Self-Improvement Tool Generator Example ===")
    
    try:
        # Create the tool generator (this would normally connect to Ollama)
        # For this example, we'll create it but won't actually call Ollama
        generator = SelfImprovementToolGenerator()
        
        print("✅ Self-Improvement Tool Generator initialized")
        print(f"📊 Statistics: {generator.get_generation_statistics()}")
        
        # Example tool descriptions that might come from the Self-Improvement tab
        example_descriptions = [
            "A tool that analyzes code quality and suggests improvements",
            "A tool that monitors system resources and alerts on high usage",
            "A tool that automatically formats and validates JSON data"
        ]
        
        print(f"\n📝 Example tool descriptions prepared: {len(example_descriptions)} tools")
        
        # In a real implementation, this would call the actual generation methods
        print("🔧 Ready to generate tools (actual generation requires Ollama connection)")
        
    except Exception as e:
        print(f"❌ Error in example setup: {e}")


if __name__ == "__main__":
    """
    Run demonstrations of the robust JSON parsing and tool generation capabilities.
    """
    demonstrate_robust_json_parsing()
    example_self_improvement_usage()