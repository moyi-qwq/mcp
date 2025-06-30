"""
Base classes for MCP tools
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from mcp.types import Tool


@dataclass
class ToolResult:
    """Result from tool execution"""
    message: str
    success: bool = True
    properties: Optional[Dict[str, Any]] = None


class MCPTool(ABC):
    """Base class for MCP tools"""
    
    def __init__(self, workspace):
        self.workspace = workspace
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema"""
        pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the tool"""
        pass
    
    def to_mcp_tool(self) -> Tool:
        """Convert to MCP Tool format"""
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        )
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate tool arguments"""
        # Basic validation - can be overridden in subclasses
        schema = self.input_schema
        required = schema.get("required", [])
        
        for field in required:
            if field not in arguments:
                raise ValueError(f"Missing required argument: {field}")
    
    def format_error(self, error: Exception) -> ToolResult:
        """Format error as tool result"""
        return ToolResult(
            message=f"Error in {self.name}: {str(error)}",
            success=False
        )