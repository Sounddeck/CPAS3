#!/usr/bin/env python3
"""
Validation script for CPAS3 tab functionality.
Quick check to ensure all components are working correctly.
"""

import sys
import os

# Add the modules path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules', 'utils'))

def validate_imports():
    """Validate that all required modules can be imported."""
    try:
        from tab_backends import (
            OllamaClient, DocumentProcessor, ResearchEngine, 
            AgentZero, ChatResponseHandler, TaskEngine
        )
        from agent_backend import AgentBackend
        print("✓ All backend modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def validate_functionality():
    """Quick validation of core functionality."""
    try:
        # Test imports
        from tab_backends import OllamaClient, DocumentProcessor, ResearchEngine, AgentZero
        from agent_backend import AgentBackend
        
        # Quick functionality tests
        client = OllamaClient()
        processor = DocumentProcessor()
        research = ResearchEngine()
        agent_zero = AgentZero()
        backend = AgentBackend()
        
        # Test basic operations
        extensions = processor.supported_extensions()
        research_result = research.conduct_research("test")
        agent_response = agent_zero.execute_command("status")
        agents = backend.get_agents()
        
        # Validate results
        assert len(extensions) > 0, "Document processor should support file extensions"
        assert "confidence" in research_result, "Research should return confidence metrics"
        assert agent_response["type"] == "status", "Agent Zero should handle status commands"
        assert len(agents) > 0, "Agent backend should have initial agents"
        
        print("✓ All core functionality validated")
        return True
        
    except Exception as e:
        print(f"✗ Functionality validation failed: {e}")
        return False

def validate_file_structure():
    """Validate that all required files exist."""
    required_files = [
        "modules/utils/tab_backends.py",
        "modules/utils/agent_backend.py",
        "modules/utils/run_cpas.py",
        "test_tab_functionality.py",
        "demo_tab_functionality.py",
        "TAB_FUNCTIONALITY_README.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"✗ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print("✓ All required files present")
        return True

def main():
    """Run validation checks."""
    print("CPAS3 Tab Functionality Validation")
    print("==================================")
    
    checks = [
        ("File Structure", validate_file_structure),
        ("Module Imports", validate_imports), 
        ("Core Functionality", validate_functionality)
    ]
    
    results = []
    for check_name, check_func in checks:
        print(f"\nChecking {check_name}...")
        result = check_func()
        results.append(result)
    
    print("\n" + "="*50)
    if all(results):
        print("🎉 All validation checks passed!")
        print("CPAS3 tab functionality is ready for use.")
        print("\nNext steps:")
        print("1. Run 'python demo_tab_functionality.py' to see features")
        print("2. Run 'python test_tab_functionality.py' for full tests")  
        print("3. Run 'python modules/utils/run_cpas.py' for GUI (requires PyQt6)")
        return 0
    else:
        print("❌ Some validation checks failed.")
        print("Please review the errors above and ensure all components are properly installed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())