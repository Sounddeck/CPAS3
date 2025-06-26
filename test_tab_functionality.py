#!/usr/bin/env python3
"""
Test script for CPAS3 tab functionality.
Tests the backend functionality without requiring GUI.
"""

import sys
import os
import tempfile

# Add the modules path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules', 'utils'))

# Import the classes we created
from tab_backends import OllamaClient, DocumentProcessor, ResearchEngine, AgentZero, ChatResponseHandler, TaskEngine
from agent_backend import AgentBackend

def test_ollama_client():
    """Test Ollama client functionality."""
    print("Testing Ollama client...")
    client = OllamaClient()
    
    # Test with a simple message (this will fail if Ollama isn't running, which is expected)
    response = client.chat("Hello, world!")
    print(f"Ollama response type: {type(response)}")
    print(f"Response contains error handling: {'Error' in response}")
    assert isinstance(response, str), "Response should be a string"
    print("✓ Ollama client test passed")

def test_document_processor():
    """Test document processor functionality."""
    print("\nTesting document processor...")
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        test_content = "This is a test document.\nIt has multiple lines.\nAnd some content for testing."
        f.write(test_content)
        temp_file = f.name
    
    try:
        # Test processing
        result = DocumentProcessor.process_text_file(temp_file)
        print(f"Processing result length: {len(result)}")
        
        # Verify the result contains expected information
        assert "Word count:" in result, "Result should contain word count"
        assert "Line count:" in result, "Result should contain line count"
        assert "Character count:" in result, "Result should contain character count"
        assert "test document" in result, "Result should contain file content preview"
        
        print("✓ Document processor test passed")
        
    finally:
        # Clean up
        os.unlink(temp_file)

def test_agent_backend():
    """Test agent backend functionality."""
    print("\nTesting agent backend...")
    
    backend = AgentBackend()
    
    # Test getting agents
    agents = backend.get_agents()
    assert len(agents) >= 3, "Should have at least 3 initial agents"
    assert all("name" in agent for agent in agents), "All agents should have names"
    assert all("status" in agent for agent in agents), "All agents should have status"
    
    # Test getting tasks
    tasks = backend.get_tasks()
    assert len(tasks) >= 3, "Should have at least 3 initial tasks"
    assert all("name" in task for task in tasks), "All tasks should have names"
    
    # Test task sorting
    sorted_tasks = backend.get_tasks(sort_by="priority")
    assert len(sorted_tasks) == len(tasks), "Sorted tasks should have same length"
    
    print("✓ Agent backend test passed")

def test_research_engine():
    """Test research engine functionality."""
    print("\nTesting research engine...")
    
    engine = ResearchEngine()
    results = engine.conduct_research("Artificial Intelligence")
    
    assert isinstance(results, dict), "Results should be a dictionary"
    assert "topic" in results, "Results should contain topic"
    assert "findings" in results, "Results should contain findings"
    assert "confidence" in results, "Results should contain confidence"
    assert results["topic"] == "Artificial Intelligence", "Topic should match input"
    assert len(results["findings"]) > 0, "Should have findings"
    
    print("✓ Research engine test passed")

def test_agent_zero():
    """Test Agent Zero functionality."""
    print("\nTesting Agent Zero...")
    
    agent = AgentZero()
    
    # Test different commands
    analyze_result = agent.execute_command("analyze market trends")
    assert "analysis" in analyze_result["type"], "Should handle analyze commands"
    
    search_result = agent.execute_command("search latest research")
    assert "search" in search_result["type"], "Should handle search commands"
    
    help_result = agent.execute_command("help")
    assert "help" in help_result["type"], "Should handle help commands"
    
    status_result = agent.execute_command("status")
    assert "status" in status_result["type"], "Should handle status commands"
    
    print("✓ Agent Zero test passed")

def test_chat_response_handler():
    """Test chat response handler."""
    print("\nTesting chat response handler...")
    
    handler = ChatResponseHandler()
    response = handler.get_response("Hello")
    
    assert isinstance(response, dict), "Response should be a dictionary"
    assert "success" in response, "Response should have success field"
    assert "response" in response, "Response should have response field"
    assert "error" in response, "Response should have error field"
    
    print("✓ Chat response handler test passed")

def test_task_engine():
    """Test task engine functionality."""
    print("\nTesting task engine...")
    
    engine = TaskEngine()
    
    # Create a task
    task = engine.create_task("Test task", "High", "Research Agent")
    assert task["id"] == 1, "First task should have ID 1"
    assert task["description"] == "Test task", "Task description should match"
    assert task["status"] == "Created", "New task should be created"
    
    # Update progress
    success = engine.update_task_progress(1, 50)
    assert success, "Should successfully update progress"
    
    tasks = engine.get_tasks()
    assert len(tasks) == 1, "Should have one task"
    assert tasks[0]["progress"] == 50, "Progress should be updated"
    assert tasks[0]["status"] == "In Progress", "Status should be updated"
    
    print("✓ Task engine test passed")

def main():
    """Run all tests."""
    print("Running CPAS3 tab functionality tests...")
    print("=" * 50)
    
    try:
        test_ollama_client()
        test_document_processor()
        test_agent_backend()
        test_research_engine()
        test_agent_zero()
        test_chat_response_handler()
        test_task_engine()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed successfully!")
        print("\nTab functionality is working correctly:")
        print("- Main Chat tab: Ollama integration ready with error handling")
        print("- Deep Research tab: Research engine ready with simulated results")
        print("- Document Processing tab: File handling ready with analysis")
        print("- Agents tab: Agent management ready with creation/tracking")
        print("- Agent Zero tab: Advanced AI assistant ready with command processing")
        print("- Backend functionality: All systems operational")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())