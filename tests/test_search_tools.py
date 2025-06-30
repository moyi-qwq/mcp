"""
Tests for search tools
"""

import pytest

from moatless_mcp.tools.search_tools import (
    GrepTool,
    FindFilesTool,
    WorkspaceInfoTool
)


class TestGrepTool:
    """Tests for GrepTool"""
    
    @pytest.fixture
    def tool(self, workspace_adapter):
        return GrepTool(workspace_adapter)
    
    @pytest.mark.asyncio
    async def test_simple_pattern_search(self, tool):
        """Test searching for a simple pattern"""
        result = await tool.execute({
            "pattern": "def hello_world"
        })
        
        assert result.success
        assert "src/main.py" in result.message
        assert result.properties["match_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_regex_pattern_search(self, tool):
        """Test searching with regex pattern"""
        result = await tool.execute({
            "pattern": "def\\s+\\w+",
            "file_pattern": "*.py"
        })
        
        assert result.success
        assert result.properties["match_count"] >= 3  # Should find multiple function definitions
        assert "def hello_world" in result.message or "def process_data" in result.message
    
    @pytest.mark.asyncio
    async def test_file_pattern_filter(self, tool):
        """Test searching with file pattern filter"""
        result = await tool.execute({
            "pattern": "test",
            "file_pattern": "*test*"
        })
        
        assert result.success
        # Should only find matches in test files
        if result.properties["match_count"] > 0:
            assert "test_main.py" in result.message
    
    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, tool):
        """Test case insensitive search"""
        result = await tool.execute({
            "pattern": "TODO|FIXME",
            "file_pattern": "*.md"
        })
        
        assert result.success
        if result.properties["match_count"] > 0:
            assert "README.md" in result.message
    
    @pytest.mark.asyncio
    async def test_max_results_limit(self, tool):
        """Test max results limitation"""
        result = await tool.execute({
            "pattern": ".",  # Match any character (should match many lines)
            "max_results": 5
        })
        
        assert result.success
        assert result.properties["match_count"] <= 5
        if result.properties["match_count"] == 5:
            assert result.properties["truncated"] is True
    
    @pytest.mark.asyncio
    async def test_no_matches_found(self, tool):
        """Test when no matches are found"""
        result = await tool.execute({
            "pattern": "nonexistent_pattern_xyz123"
        })
        
        assert result.success  # Not finding matches is not an error
        assert result.properties["match_count"] == 0
        assert "No matches found" in result.message


class TestFindFilesTool:
    """Tests for FindFilesTool"""
    
    @pytest.fixture
    def tool(self, workspace_adapter):
        return FindFilesTool(workspace_adapter)
    
    @pytest.mark.asyncio
    async def test_find_python_files(self, tool):
        """Test finding Python files"""
        result = await tool.execute({
            "pattern": "*.py"
        })
        
        assert result.success
        assert result.properties["file_count"] >= 2
        assert "main.py" in result.message
        assert "utils.py" in result.message
    
    @pytest.mark.asyncio
    async def test_find_test_files(self, tool):
        """Test finding test files"""
        result = await tool.execute({
            "pattern": "*test*"
        })
        
        assert result.success
        assert result.properties["file_count"] >= 1
        assert "test_main.py" in result.message
    
    @pytest.mark.asyncio
    async def test_find_config_files(self, tool):
        """Test finding configuration files"""
        result = await tool.execute({
            "pattern": "*config*"
        })
        
        assert result.success
        assert "config.json" in result.message
    
    @pytest.mark.asyncio
    async def test_find_files_in_subdirectory(self, tool):
        """Test finding files in subdirectory"""
        result = await tool.execute({
            "pattern": "src/**/*.py"
        })
        
        assert result.success
        assert result.properties["file_count"] >= 2
        assert "src/main.py" in result.message
        assert "src/utils.py" in result.message
    
    @pytest.mark.asyncio
    async def test_max_results_limit(self, tool):
        """Test max results limitation"""
        result = await tool.execute({
            "pattern": "*",  # Match all files
            "max_results": 3
        })
        
        assert result.success
        assert result.properties["file_count"] <= 3
        if result.properties["file_count"] == 3:
            assert result.properties["truncated"] is True
    
    @pytest.mark.asyncio
    async def test_no_files_found(self, tool):
        """Test when no files match pattern"""
        result = await tool.execute({
            "pattern": "*.nonexistent"
        })
        
        assert result.success  # Not finding files is not an error
        assert result.properties["file_count"] == 0
        assert "No files found" in result.message


class TestWorkspaceInfoTool:
    """Tests for WorkspaceInfoTool"""
    
    @pytest.fixture
    def tool(self, workspace_adapter):
        return WorkspaceInfoTool(workspace_adapter)
    
    @pytest.mark.asyncio
    async def test_get_workspace_info(self, tool):
        """Test getting workspace information"""
        result = await tool.execute({})
        
        assert result.success
        assert "Workspace Path:" in result.message
        assert "Exists: true" in result.message
        assert result.properties["exists"] is True
        assert "path" in result.properties
    
    @pytest.mark.asyncio
    async def test_workspace_path_in_properties(self, tool):
        """Test that workspace path is in properties"""
        result = await tool.execute({})
        
        assert result.success
        assert isinstance(result.properties["path"], str)
        assert len(result.properties["path"]) > 0
    
    @pytest.mark.asyncio
    async def test_git_repo_detection(self, tool):
        """Test git repository detection"""
        result = await tool.execute({})
        
        assert result.success
        # Should be false for temp directory (not a git repo)
        assert result.properties["is_git_repo"] is False
        assert "Git Repository: false" in result.message or "Git Repository: False" in result.message