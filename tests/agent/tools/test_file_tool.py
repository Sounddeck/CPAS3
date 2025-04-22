"""
Unit tests for the FileTool
"""

import os
import tempfile
import unittest
import shutil
import json
from modules.agent.tools.file_tool import FileTool

class TestFileTool(unittest.TestCase):
    """Test case for the FileTool class"""
    
    def setUp(self):
        """Set up the test environment"""
        # Create a temp directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.file_tool = FileTool(base_dir=self.temp_dir)
        
        # Create some test files
        self.test_file_path = os.path.join(self.temp_dir, "test.txt")
        with open(self.test_file_path, "w") as f:
            f.write("Test content")
        
        self.test_json_path = os.path.join(self.temp_dir, "test.json")
        with open(self.test_json_path, "w") as f:
            f.write('{"key": "value"}')
    
    def tearDown(self):
        """Clean up the test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_read_file(self):
        """Test reading a file"""
        content = self.file_tool.read_file("test.txt")
        self.assertEqual(content, "Test content")
    
    def test_write_file(self):
        """Test writing a file"""
        result = self.file_tool.write_file("new.txt", "New content")
        self.assertTrue(result)
        
        # Verify content was written
        with open(os.path.join(self.temp_dir, "new.txt"), "r") as f:
            content = f.read()
        self.assertEqual(content, "New content")
    
    def test_file_exists(self):
        """Test file existence check"""
        self.assertTrue(self.file_tool.file_exists("test.txt"))
        self.assertFalse(self.file_tool.file_exists("nonexistent.txt"))
    
    def test_create_and_delete_dir(self):
        """Test creating and deleting a directory"""
        # Create directory
        result = self.file_tool.create_dir("test_dir")
        self.assertTrue(result)
        self.assertTrue(os.path.isdir(os.path.join(self.temp_dir, "test_dir")))
        
        # Delete directory
        result = self.file_tool.delete_dir("test_dir")
        self.assertTrue(result)
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "test_dir")))
    
    def test_list_dir(self):
        """Test listing directory contents"""
        files = self.file_tool.list_dir(".")
        self.assertEqual(len(files), 2)
        
        # Verify file properties
        file_names = [f["name"] for f in files]
        self.assertIn("test.txt", file_names)
        self.assertIn("test.json", file_names)
    
    def test_move_file(self):
        """Test moving a file"""
        result = self.file_tool.move_file("test.txt", "moved.txt")
        self.assertTrue(result)
        
        # Verify the file was moved
        self.assertFalse(os.path.exists(self.test_file_path))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "moved.txt")))
    
    def test_copy_file(self):
        """Test copying a file"""
        result = self.file_tool.copy_file("test.txt", "copied.txt")
        self.assertTrue(result)
        
        # Verify the file was copied (original still exists)
        self.assertTrue(os.path.exists(self.test_file_path))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "copied.txt")))
    
    def test_get_file_info(self):
        """Test getting file information"""
        info = self.file_tool.get_file_info("test.txt")
        
        # Verify file info properties
        self.assertEqual(info["name"], "test.txt")
        self.assertEqual(info["extension"], ".txt")
        self.assertEqual(info["type"], "file")
        self.assertEqual(info["size"], 12)  # "Test content" is 12 bytes
    
    def test_json_operations(self):
        """Test JSON read/write operations"""
        # Read JSON
        data = self.file_tool.read_json("test.json")
        self.assertEqual(data["key"], "value")
        
        # Write JSON
        new_data = {"name": "test", "value": 123}
        result = self.file_tool.write_json("new.json", new_data)
        self.assertTrue(result)
        
        # Verify JSON was written correctly
        with open(os.path.join(self.temp_dir, "new.json"), "r") as f:
            content = json.load(f)
        self.assertEqual(content["name"], "test")
        self.assertEqual(content["value"], 123)

if __name__ == "__main__":
    unittest.main()
