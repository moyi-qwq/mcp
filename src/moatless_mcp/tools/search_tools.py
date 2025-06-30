"""
Search and discovery tools for MCP
"""

import logging
from typing import Any, Dict, List

from moatless_mcp.tools.base import MCPTool, ToolResult

logger = logging.getLogger(__name__)


class GrepTool(MCPTool):
    """Tool to search for text patterns in files"""
    
    @property
    def name(self) -> str:
        return "grep"
    
    @property
    def description(self) -> str:
        return "Search for text patterns in files using regular expressions."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression pattern to search for"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File glob pattern to limit search (default: *)",
                    "default": "*"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                }
            },
            "required": ["pattern"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            self.validate_arguments(arguments)
            
            pattern = arguments["pattern"]
            file_pattern = arguments.get("file_pattern", "*")
            max_results = arguments.get("max_results", 100)
            
            # Search for pattern
            results = self.workspace.grep_files(
                pattern=pattern,
                file_pattern=file_pattern,
                max_results=max_results
            )
            
            if not results:
                return ToolResult(
                    message=f"No matches found for pattern: '{pattern}'",
                    properties={
                        "pattern": pattern,
                        "file_pattern": file_pattern,
                        "match_count": 0
                    }
                )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(
                    f"{result['file']}:{result['line']}: {result['content']}"
                )
            
            result_text = "\n".join(formatted_results)
            
            message = f"Found {len(results)} matches for pattern '{pattern}':\n\n{result_text}"
            
            if len(results) >= max_results:
                message += f"\n\n... (showing first {max_results} matches)"
            
            return ToolResult(
                message=message,
                properties={
                    "pattern": pattern,
                    "file_pattern": file_pattern,
                    "match_count": len(results),
                    "truncated": len(results) >= max_results
                }
            )
            
        except Exception as e:
            logger.error(f"Error in grep search: {e}")
            return self.format_error(e)


class FindFilesTool(MCPTool):
    """Tool to find files by name pattern"""
    
    @property
    def name(self) -> str:
        return "find_files"
    
    @property
    def description(self) -> str:
        return "Find files by name pattern using glob syntax."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match file names (e.g., '*.py', '*test*', 'src/**/*.java')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                }
            },
            "required": ["pattern"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            self.validate_arguments(arguments)
            
            pattern = arguments["pattern"]
            max_results = arguments.get("max_results", 100)
            
            # Search for files
            files = self.workspace.search_files(
                pattern=pattern,
                max_results=max_results
            )
            
            if not files:
                return ToolResult(
                    message=f"No files found matching pattern: '{pattern}'",
                    properties={
                        "pattern": pattern,
                        "file_count": 0
                    }
                )
            
            file_list = "\n".join(f"  {file}" for file in files)
            
            message = f"Found {len(files)} files matching pattern '{pattern}':\n\n{file_list}"
            
            if len(files) >= max_results:
                message += f"\n\n... (showing first {max_results} files)"
            
            return ToolResult(
                message=message,
                properties={
                    "pattern": pattern,
                    "file_count": len(files),
                    "truncated": len(files) >= max_results
                }
            )
            
        except Exception as e:
            logger.error(f"Error finding files: {e}")
            return self.format_error(e)


class WorkspaceInfoTool(MCPTool):
    """Tool to get workspace information"""
    
    @property
    def name(self) -> str:
        return "workspace_info"
    
    @property
    def description(self) -> str:
        return "Get information about the current workspace (path, git status, etc.)"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            info = self.workspace.get_workspace_info()
            
            message_parts = [
                f"Workspace Path: {info['path']}",
                f"Exists: {info['exists']}",
                f"Git Repository: {info['is_git_repo']}"
            ]
            
            if info.get('git_branch'):
                message_parts.append(f"Git Branch: {info['git_branch']}")
            
            if info.get('git_remote'):
                message_parts.append(f"Git Remotes: {', '.join(info['git_remote'])}")
            
            message = "\n".join(message_parts)
            
            return ToolResult(
                message=message,
                properties=info
            )
            
        except Exception as e:
            logger.error(f"Error getting workspace info: {e}")
            return self.format_error(e)