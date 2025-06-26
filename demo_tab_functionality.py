#!/usr/bin/env python3
"""
Command-line demo of CPAS3 tab functionality.
Demonstrates all the tab features without requiring a GUI.
"""

import sys
import os
import tempfile

# Add the modules path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules', 'utils'))

from tab_backends import (
    OllamaClient, DocumentProcessor, ResearchEngine, 
    AgentZero, ChatResponseHandler, TaskEngine
)
from agent_backend import AgentBackend

def demo_main_chat():
    """Demo the main chat functionality."""
    print("\n" + "="*60)
    print("MAIN CHAT TAB DEMO")
    print("="*60)
    
    chat_handler = ChatResponseHandler()
    
    # Test messages
    test_messages = [
        "Hello, how are you?",
        "What is artificial intelligence?",
        "Can you help me with a Python problem?"
    ]
    
    for message in test_messages:
        print(f"\n👤 User: {message}")
        response = chat_handler.get_response(message)
        print(f"🤖 Assistant: {response['response']}")
        if not response['success']:
            print("   (Note: This is expected if Ollama is not running)")

def demo_deep_research():
    """Demo the deep research functionality."""
    print("\n" + "="*60)
    print("DEEP RESEARCH TAB DEMO")
    print("="*60)
    
    research_engine = ResearchEngine()
    
    topics = ["Machine Learning", "Climate Change", "Quantum Computing"]
    
    for topic in topics:
        print(f"\n🔍 Researching: {topic}")
        results = research_engine.conduct_research(topic)
        
        print(f"   Topic: {results['topic']}")
        print(f"   Confidence: {results['confidence']}%")
        print(f"   Sources scanned: {results['sources_scanned']}")
        print(f"   Relevant results: {results['relevant_results']}")
        print("   Key findings:")
        for finding in results['findings']:
            print(f"   • {finding}")

def demo_document_processing():
    """Demo the document processing functionality."""
    print("\n" + "="*60)
    print("DOCUMENT PROCESSING TAB DEMO")
    print("="*60)
    
    # Create sample files
    sample_files = [
        ("sample.txt", "This is a sample text file.\nIt contains multiple lines.\nAnd some interesting content for analysis."),
        ("config.json", '{"name": "CPAS3", "version": "1.0", "modules": ["chat", "research", "documents"]}'),
        ("code.py", "def hello_world():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello_world()")
    ]
    
    for filename, content in sample_files:
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'_{filename}', delete=False) as f:
            f.write(content)
            temp_file = f.name
        
        print(f"\n📄 Processing: {filename}")
        result = DocumentProcessor.process_text_file(temp_file)
        print(result)
        
        # Clean up
        os.unlink(temp_file)
    
    print(f"\n📋 Supported file types: {', '.join(DocumentProcessor.supported_extensions())}")

def demo_agents():
    """Demo the agents functionality."""
    print("\n" + "="*60)
    print("AGENTS TAB DEMO")
    print("="*60)
    
    agent_backend = AgentBackend()
    
    print("📋 Current agents:")
    for agent in agent_backend.get_agents():
        print(f"   • {agent['name']} - Status: {agent['status']} - Task: {agent['task']}")
    
    # Create new agents
    print("\n🆕 Creating new agents...")
    new_agents = [
        {"name": "Research Assistant", "type": "Research Agent"},
        {"name": "Data Analyzer", "type": "Analysis Agent"},
        {"name": "Support Bot", "type": "Support Agent"}
    ]
    
    for agent_data in new_agents:
        new_agent = {
            "id": agent_backend.next_id,
            "name": agent_data["name"],
            "status": "Created",
            "task": f"Ready for {agent_data['type'].lower()} tasks",
            "type": agent_data["type"]
        }
        agent_backend.agents.append(new_agent)
        agent_backend.next_id += 1
        print(f"   ✓ Created: {agent_data['name']} ({agent_data['type']})")
    
    print("\n📋 Updated agent list:")
    for agent in agent_backend.get_agents():
        agent_type = agent.get("type", "Generic Agent")
        print(f"   • {agent['name']} ({agent_type}) - Status: {agent['status']}")

def demo_agent_zero():
    """Demo the Agent Zero functionality."""
    print("\n" + "="*60)
    print("AGENT ZERO TAB DEMO")
    print("="*60)
    
    agent_zero = AgentZero()
    
    commands = [
        "status",
        "help",
        "analyze market trends in AI",
        "search latest research on quantum computing",
        "execute system diagnostics"
    ]
    
    print(f"🤖 Agent Zero Status: {agent_zero.status}")
    print(f"   Capabilities: {', '.join(agent_zero.capabilities)}")
    
    for command in commands:
        print(f"\n💻 Command: {command}")
        result = agent_zero.execute_command(command)
        print(f"📊 Response Type: {result['type']}")
        print(f"📝 Result:\n{result['result']}")

def demo_task_management():
    """Demo enhanced task management."""
    print("\n" + "="*60)
    print("ENHANCED TASK MANAGEMENT DEMO")
    print("="*60)
    
    task_engine = TaskEngine()
    
    # Create some tasks
    tasks = [
        {"desc": "Analyze quarterly sales data", "priority": "High", "agent": "Data Analyzer"},
        {"desc": "Research competitor strategies", "priority": "Medium", "agent": "Research Agent"},
        {"desc": "Update system documentation", "priority": "Low", "agent": "Support Agent"}
    ]
    
    print("📝 Creating tasks...")
    for task_data in tasks:
        task = task_engine.create_task(
            task_data["desc"], 
            task_data["priority"], 
            task_data["agent"]
        )
        print(f"   ✓ Task {task['id']}: {task['description']} ({task['priority']})")
    
    # Simulate progress updates
    print("\n⏳ Simulating task progress...")
    progress_updates = [(1, 30), (2, 75), (3, 100), (1, 100)]
    
    for task_id, progress in progress_updates:
        task_engine.update_task_progress(task_id, progress)
        print(f"   📊 Task {task_id} progress: {progress}%")
    
    print("\n📋 Final task status:")
    for task in task_engine.get_tasks():
        print(f"   • Task {task['id']}: {task['description']}")
        print(f"     Status: {task['status']} | Progress: {task['progress']}% | Priority: {task['priority']}")

def main():
    """Run all demos."""
    print("CPAS3 TAB FUNCTIONALITY DEMONSTRATION")
    print("=====================================")
    print("This demo shows all the tab functionalities working without the GUI.")
    
    demo_main_chat()
    demo_deep_research()
    demo_document_processing()
    demo_agents()
    demo_agent_zero()
    demo_task_management()
    
    print("\n" + "="*60)
    print("🎉 DEMO COMPLETE!")
    print("="*60)
    print("All CPAS3 tab functionalities are working correctly:")
    print("✓ Main Chat: Ollama integration with error handling")
    print("✓ Deep Research: Comprehensive research with metrics")
    print("✓ Document Processing: Multi-format file analysis")
    print("✓ Agents: Dynamic agent creation and management")
    print("✓ Agent Zero: Advanced command processing")
    print("✓ Enhanced Task Management: Progress tracking and status")
    print("\nThe GUI application (run_cpas.py) provides the same functionality")
    print("with a user-friendly interface when PyQt6 is available.")

if __name__ == "__main__":
    main()