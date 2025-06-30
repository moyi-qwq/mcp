"""
Tests for workspace adapter and file context
"""

import pytest
from pathlib import Path

from moatless_mcp.adapters.workspace import WorkspaceAdapter, FileContext
from moatless_mcp.utils.config import Config


class TestFileContext:
    """Tests for FileContext"""
    
    @pytest.mark.asyncio
    async def test_get_file_content(self, file_context):
        """Test getting file content"""
        content = file_context.get_file_content("src/main.py")
        
        assert "def hello_world():" in content
        assert "Main application module" in content
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, file_context):
        """Test getting nonexistent file"""
        with pytest.raises(FileNotFoundError):
            file_context.get_file_content("nonexistent.py")
    
    @pytest.mark.asyncio
    async def test_write_file_content(self, file_context):
        """Test writing file content"""
        content = "print('New file content')\n"
        file_context.write_file_content("new_file.py", content)
        
        # Verify it was written
        written_content = file_context.get_file_content("new_file.py")
        assert written_content == content
    
    @pytest.mark.asyncio
    async def test_write_file_with_subdirectory(self, file_context):
        """Test writing file in new subdirectory"""
        content = "// New module\nexport default {};\n"
        file_context.write_file_content("src/modules/new.js", content)
        
        # Verify it was written
        written_content = file_context.get_file_content("src/modules/new.js")
        assert written_content == content
    
    @pytest.mark.asyncio
    async def test_list_files_root(self, file_context):
        """Test listing files in root"""
        files = file_context.list_files()
        
        assert "README.md" in files
        assert "config.json" in files
        assert len(files) >= 2
    
    @pytest.mark.asyncio
    async def test_list_files_subdirectory(self, file_context):
        """Test listing files in subdirectory"""
        files = file_context.list_files("src")
        
        assert "main.py" in files
        assert "utils.py" in files
        assert "src/main.py" not in files  # Should be relative to subdirectory
    
    @pytest.mark.asyncio
    async def test_list_files_recursive(self, file_context):
        """Test recursive file listing"""
        files = file_context.list_files(recursive=True)
        
        assert "src/main.py" in files
        assert "tests/test_main.py" in files
        assert "README.md" in files
    
    @pytest.mark.asyncio
    async def test_list_files_with_limit(self, file_context):
        """Test file listing with max results"""
        files = file_context.list_files(recursive=True, max_results=3)
        
        assert len(files) <= 3
    
    @pytest.mark.asyncio
    async def test_list_nonexistent_directory(self, file_context):
        """Test listing nonexistent directory"""
        with pytest.raises(FileNotFoundError):
            file_context.list_files("nonexistent")


class TestWorkspaceAdapter:
    """Tests for WorkspaceAdapter"""
    
    @pytest.mark.asyncio
    async def test_workspace_info(self, workspace_adapter):
        """Test getting workspace information"""
        info = workspace_adapter.get_workspace_info()
        
        assert "path" in info
        assert "exists" in info
        assert "is_git_repo" in info
        assert info["exists"] is True
        assert info["is_git_repo"] is False  # Temp directory is not a git repo
    
    @pytest.mark.asyncio
    async def test_search_files(self, workspace_adapter):
        """Test searching files by pattern"""
        files = workspace_adapter.search_files("*.py")
        
        assert len(files) >= 2
        assert any("main.py" in f for f in files)
        assert any("utils.py" in f for f in files)
    
    @pytest.mark.asyncio
    async def test_search_files_with_pattern(self, workspace_adapter):
        """Test searching files with specific pattern"""
        files = workspace_adapter.search_files("*test*")
        
        assert any("test_main.py" in f for f in files)
    
    @pytest.mark.asyncio
    async def test_search_files_no_matches(self, workspace_adapter):
        """Test searching files with no matches"""
        files = workspace_adapter.search_files("*.nonexistent")
        
        assert len(files) == 0
    
    @pytest.mark.asyncio
    async def test_grep_files(self, workspace_adapter):
        """Test grep functionality"""
        results = workspace_adapter.grep_files("def hello_world")
        
        assert len(results) >= 1
        assert any("main.py" in r["file"] for r in results)
        assert any("def hello_world" in r["content"] for r in results)
    
    @pytest.mark.asyncio
    async def test_grep_with_file_pattern(self, workspace_adapter):
        """Test grep with file pattern"""
        results = workspace_adapter.grep_files("test", "*.py")
        
        # Should find matches in Python files
        for result in results:
            assert result["file"].endswith(".py")
    
    @pytest.mark.asyncio
    async def test_grep_no_matches(self, workspace_adapter):
        """Test grep with no matches"""
        results = workspace_adapter.grep_files("nonexistent_pattern_xyz")
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_grep_with_max_results(self, workspace_adapter):
        """Test grep with max results limit"""
        results = workspace_adapter.grep_files("def", max_results=2)
        
        assert len(results) <= 2


class TestConfig:
    """Tests for Config class"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = Config()
        
        assert config.max_file_size > 0
        assert config.max_search_results > 0
        assert len(config.allowed_file_extensions) > 0
        assert len(config.forbidden_paths) > 0
    
    def test_is_file_allowed(self):
        """Test file permission checking"""
        config = Config()
        
        # Allowed files
        assert config.is_file_allowed(Path("test.py"))
        assert config.is_file_allowed(Path("src/main.py"))
        assert config.is_file_allowed(Path("config.json"))
        
        # Forbidden files
        assert not config.is_file_allowed(Path("test.exe"))
        assert not config.is_file_allowed(Path(".git/config"))
        assert not config.is_file_allowed(Path("node_modules/package.json"))
    
    def test_get_language_for_file(self):
        """Test language detection"""
        config = Config()
        
        assert config.get_language_for_file(Path("test.py")) == "python"
        assert config.get_language_for_file(Path("Test.java")) == "java"
        assert config.get_language_for_file(Path("test.txt")) is None