"""
Tests for file operation tools
"""

import pytest
from pathlib import Path

from moatless_mcp.tools.file_operations import (
    ReadFileTool,
    WriteFileTool,
    ListFilesTool,
    StringReplaceTool
)


class TestReadFileTool:
    """Tests for ReadFileTool"""
    
    @pytest.fixture
    def tool(self, workspace_adapter):
        return ReadFileTool(workspace_adapter)
    
    @pytest.mark.asyncio
    async def test_read_entire_file(self, tool):
        """Test reading an entire file"""
        result = await tool.execute({"file_path": "src/main.py"})
        
        assert result.success
        assert "def hello_world():" in result.message
        assert "Main application module" in result.message
        assert result.properties["file_path"] == "src/main.py"
        assert result.properties["total_lines"] > 0
    
    @pytest.mark.asyncio
    async def test_read_line_range(self, tool):
        """Test reading a specific line range"""
        result = await tool.execute({
            "file_path": "src/main.py",
            "start_line": 4,
            "end_line": 6
        })
        
        assert result.success
        assert "def hello_world():" in result.message
        assert result.properties["start_line"] == 4
        assert result.properties["end_line"] == 6
        assert result.properties["displayed_lines"] == 3
    
    @pytest.mark.asyncio
    async def test_read_from_start_line(self, tool):
        """Test reading from a start line to end"""
        result = await tool.execute({
            "file_path": "src/utils.py",
            "start_line": 3
        })
        
        assert result.success
        assert "def format_string(text):" in result.message
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, tool):
        """Test reading a nonexistent file"""
        result = await tool.execute({"file_path": "nonexistent.py"})
        
        assert not result.success
        assert "not found" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_invalid_line_range(self, tool):
        """Test invalid line range"""
        result = await tool.execute({
            "file_path": "src/main.py",
            "start_line": 100,
            "end_line": 200
        })
        
        assert not result.success
        assert "out of range" in result.message


class TestWriteFileTool:
    """Tests for WriteFileTool"""
    
    @pytest.fixture
    def tool(self, workspace_adapter):
        return WriteFileTool(workspace_adapter)
    
    @pytest.mark.asyncio
    async def test_write_new_file(self, tool):
        """Test writing a new file"""
        content = "print('Hello from new file!')\n"
        
        result = await tool.execute({
            "file_path": "src/new_file.py",
            "content": content
        })
        
        assert result.success
        assert "Successfully wrote" in result.message
        assert result.properties["file_path"] == "src/new_file.py"
        assert result.properties["lines_written"] == 1
    
    @pytest.mark.asyncio
    async def test_write_with_subdirectory(self, tool):
        """Test writing a file in a new subdirectory"""
        content = "// New module\nexport default {};\n"
        
        result = await tool.execute({
            "file_path": "src/modules/new_module.js",
            "content": content
        })
        
        assert result.success
        assert result.properties["lines_written"] == 2
    
    @pytest.mark.asyncio
    async def test_overwrite_existing_file(self, tool):
        """Test overwriting an existing file"""
        content = "# New README\n\nThis replaces the old content.\n"
        
        result = await tool.execute({
            "file_path": "README.md",
            "content": content
        })
        
        assert result.success
        assert result.properties["lines_written"] == 3


class TestListFilesTool:
    """Tests for ListFilesTool"""
    
    @pytest.fixture
    def tool(self, workspace_adapter):
        return ListFilesTool(workspace_adapter)
    
    @pytest.mark.asyncio
    async def test_list_root_directory(self, tool):
        """Test listing files in root directory"""
        result = await tool.execute({})
        
        assert result.success
        assert "README.md" in result.message
        assert "config.json" in result.message
        assert result.properties["file_count"] >= 2
    
    @pytest.mark.asyncio
    async def test_list_subdirectory(self, tool):
        """Test listing files in subdirectory"""
        result = await tool.execute({"directory": "src"})
        
        assert result.success
        assert "main.py" in result.message
        assert "utils.py" in result.message
        assert result.properties["directory"] == "src"
    
    @pytest.mark.asyncio
    async def test_list_recursive(self, tool):
        """Test recursive file listing"""
        result = await tool.execute({"recursive": True})
        
        assert result.success
        assert "src/main.py" in result.message
        assert "tests/test_main.py" in result.message
        assert result.properties["recursive"] is True
    
    @pytest.mark.asyncio
    async def test_list_with_max_results(self, tool):
        """Test listing with max results limit"""
        result = await tool.execute({
            "recursive": True,
            "max_results": 2
        })
        
        assert result.success
        assert result.properties["file_count"] <= 2
    
    @pytest.mark.asyncio
    async def test_list_nonexistent_directory(self, tool):
        """Test listing nonexistent directory"""
        result = await tool.execute({"directory": "nonexistent"})
        
        assert not result.success
        assert "not found" in result.message.lower()


class TestStringReplaceTool:
    """Tests for StringReplaceTool"""
    
    @pytest.fixture
    def tool(self, workspace_adapter):
        return StringReplaceTool(workspace_adapter)
    
    @pytest.mark.asyncio
    async def test_simple_replacement(self, tool):
        """Test simple string replacement"""
        result = await tool.execute({
            "file_path": "src/main.py",
            "old_str": "Hello, World!",
            "new_str": "Hello, Universe!"
        })
        
        assert result.success
        assert result.properties["replacements_made"] == 1
        assert result.properties["old_str"] == "Hello, World!"
        assert result.properties["new_str"] == "Hello, Universe!"
    
    @pytest.mark.asyncio
    async def test_replace_all_occurrences(self, tool):
        """Test replacing all occurrences"""
        result = await tool.execute({
            "file_path": "config.json",
            "old_str": "localhost",
            "new_str": "production.example.com",
            "occurrence": 0
        })
        
        assert result.success
        assert result.properties["replacements_made"] >= 1
    
    @pytest.mark.asyncio
    async def test_replace_specific_occurrence(self, tool):
        """Test replacing specific occurrence"""
        # First, create a file with multiple occurrences
        write_tool = WriteFileTool(tool.workspace)
        await write_tool.execute({
            "file_path": "test_file.txt",
            "content": "test\ntest\ntest\n"
        })
        
        result = await tool.execute({
            "file_path": "test_file.txt",
            "old_str": "test",
            "new_str": "modified",
            "occurrence": 2
        })
        
        assert result.success
        assert result.properties["replacements_made"] == 1
        assert result.properties["total_occurrences"] == 3
    
    @pytest.mark.asyncio
    async def test_string_not_found(self, tool):
        """Test replacement when string not found"""
        result = await tool.execute({
            "file_path": "src/main.py",
            "old_str": "nonexistent_string",
            "new_str": "replacement"
        })
        
        assert not result.success
        assert "not found" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_occurrence_out_of_range(self, tool):
        """Test replacement with occurrence out of range"""
        result = await tool.execute({
            "file_path": "src/main.py",
            "old_str": "def",
            "new_str": "function",
            "occurrence": 100
        })
        
        assert not result.success
        assert "not found" in result.message.lower() or "occurrence" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_replace_nonexistent_file(self, tool):
        """Test replacement in nonexistent file"""
        result = await tool.execute({
            "file_path": "nonexistent.py",
            "old_str": "old",
            "new_str": "new"
        })
        
        assert not result.success
        assert "not found" in result.message.lower()