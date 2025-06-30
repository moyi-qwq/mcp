"""
Test configuration and fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from moatless_mcp.utils.config import Config
from moatless_mcp.adapters.workspace import WorkspaceAdapter


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing"""
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir)
    
    # Create test files and directories
    (workspace_path / "src").mkdir()
    (workspace_path / "tests").mkdir()
    (workspace_path / "docs").mkdir()
    
    # Create some test files
    (workspace_path / "src" / "main.py").write_text("""#!/usr/bin/env python3
\"\"\"Main application module\"\"\"

def hello_world():
    print("Hello, World!")

def process_data(data):
    \"\"\"Process some data\"\"\"
    return data.upper()

class Calculator:
    def add(self, a, b):
        return a + b
    
    def multiply(self, a, b):
        return a * b

if __name__ == "__main__":
    hello_world()
""")
    
    (workspace_path / "src" / "utils.py").write_text("""\"\"\"Utility functions\"\"\"

def format_string(text):
    return text.strip().lower()

def validate_email(email):
    return "@" in email and "." in email
""")
    
    (workspace_path / "tests" / "test_main.py").write_text("""\"\"\"Tests for main module\"\"\"

import unittest
from src.main import Calculator, process_data

class TestCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = Calculator()
    
    def test_add(self):
        self.assertEqual(self.calc.add(2, 3), 5)
    
    def test_multiply(self):
        self.assertEqual(self.calc.multiply(4, 5), 20)

class TestProcessData(unittest.TestCase):
    def test_process_data(self):
        result = process_data("hello")
        self.assertEqual(result, "HELLO")
""")
    
    (workspace_path / "README.md").write_text("""# Test Project

This is a test project for the MCP server.

## Features

- Hello world functionality
- Data processing
- Calculator operations

## TODO

- Add more tests
- Implement error handling
- FIXME: Handle edge cases
""")
    
    (workspace_path / "config.json").write_text("""{
    "app_name": "test_app",
    "debug_mode": true,
    "database": {
        "host": "localhost",
        "port": 5432
    }
}""")
    
    yield workspace_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def config():
    """Create a test configuration"""
    return Config()


@pytest.fixture
def workspace_adapter(temp_workspace, config):
    """Create a workspace adapter for testing"""
    return WorkspaceAdapter(str(temp_workspace), config)


@pytest.fixture
def file_context(workspace_adapter):
    """Create a file context for testing"""
    return workspace_adapter.get_file_context()