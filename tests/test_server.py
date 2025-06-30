"""
Tests for the MCP server
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from moatless_mcp.server import MoatlessMCPServer
from moatless_mcp.utils.config import Config


class TestMoatlessMCPServer:
    """Tests for MoatlessMCPServer"""
    
    @pytest.fixture
    def server(self, temp_workspace):
        """Create a server instance for testing"""
        config = Config()
        return MoatlessMCPServer(str(temp_workspace), config)
    
    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test listing available tools"""
        tools = await server.list_tools()
        
        assert len(tools) > 0
        tool_names = [tool.name for tool in tools]
        
        # Check that core tools are available
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "list_files" in tool_names
        assert "string_replace" in tool_names
        assert "grep" in tool_names
        assert "find_files" in tool_names
        assert "workspace_info" in tool_names
    
    @pytest.mark.asyncio
    async def test_call_tool_success(self, server):
        """Test successful tool execution"""
        # Mock request
        request = MagicMock()
        request.params.name = "workspace_info"
        request.params.arguments = {}
        
        result = await server.call_tool(request)
        
        assert result.isError is False
        assert len(result.content) > 0
        assert result.content[0].type == "text"
        assert "Workspace Path:" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_call_tool_with_arguments(self, server):
        """Test tool execution with arguments"""
        # Mock request
        request = MagicMock()
        request.params.name = "list_files"
        request.params.arguments = {"directory": "", "recursive": False}
        
        result = await server.call_tool(request)
        
        assert result.isError is False
        assert len(result.content) > 0
        assert "Files in root directory" in result.content[0].text or "config.json" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self, server):
        """Test calling unknown tool"""
        # Mock request
        request = MagicMock()
        request.params.name = "unknown_tool"
        request.params.arguments = {}
        
        result = await server.call_tool(request)
        
        assert result.isError is True
        assert len(result.content) > 0
        assert "Unknown tool" in result.content[0].text
    
    @pytest.mark.asyncio
    async def test_call_tool_with_invalid_arguments(self, server):
        """Test tool execution with invalid arguments"""
        # Mock request
        request = MagicMock()
        request.params.name = "read_file"
        request.params.arguments = {}  # Missing required file_path
        
        result = await server.call_tool(request)
        
        assert result.isError is True
        assert len(result.content) > 0
        assert "Missing required argument" in result.content[0].text or "file_path" in result.content[0].text
    
    def test_server_initialization(self, temp_workspace):
        """Test server initialization"""
        config = Config()
        server = MoatlessMCPServer(str(temp_workspace), config)
        
        assert server.workspace is not None
        assert server.tool_registry is not None
        assert server.server is not None
        assert server.config is config
    
    def test_server_workspace_info(self, server):
        """Test server workspace information"""
        info = server.workspace.get_workspace_info()
        
        assert "path" in info
        assert "exists" in info
        assert "is_git_repo" in info
        assert info["exists"] is True