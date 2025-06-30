"""
File operation tools for MCP
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from moatless_mcp.tools.base import MCPTool, ToolResult

logger = logging.getLogger(__name__)


class ReadFileTool(MCPTool):
    """Tool to read file contents with optional line range"""
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Read file contents with optional line range. Supports text files up to 10MB."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read (relative to workspace root)"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Start line number (1-based, optional)",
                    "minimum": 1
                },
                "end_line": {
                    "type": "integer", 
                    "description": "End line number (1-based, optional)",
                    "minimum": 1
                }
            },
            "required": ["file_path"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            self.validate_arguments(arguments)
            
            file_path = arguments["file_path"]
            start_line = arguments.get("start_line")
            end_line = arguments.get("end_line")
            
            # Get file content
            content = self.workspace.get_file_context().get_file_content(file_path)
            lines = content.splitlines()
            
            # Apply line range if specified
            if start_line is not None or end_line is not None:
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else len(lines)
                
                if start_idx < 0 or start_idx >= len(lines):
                    return ToolResult(
                        message=f"Start line {start_line} is out of range (file has {len(lines)} lines)",
                        success=False
                    )
                
                if end_idx > len(lines):
                    end_idx = len(lines)
                
                if start_line and end_line and start_line > end_line:
                    return ToolResult(
                        message=f"Start line ({start_line}) cannot be greater than end line ({end_line})",
                        success=False
                    )
                
                selected_lines = lines[start_idx:end_idx]
                content = "\n".join(selected_lines)
                
                result_msg = f"File: {file_path}"
                if start_line or end_line:
                    result_msg += f" (lines {start_line or 1}-{end_line or len(lines)})"
                result_msg += f"\n\n{content}"
                
                return ToolResult(
                    message=result_msg,
                    properties={
                        "file_path": file_path,
                        "total_lines": len(lines),
                        "displayed_lines": len(selected_lines),
                        "start_line": start_line or 1,
                        "end_line": end_line or len(lines)
                    }
                )
            else:
                return ToolResult(
                    message=f"File: {file_path}\n\n{content}",
                    properties={
                        "file_path": file_path,
                        "total_lines": len(lines),
                        "size_bytes": len(content.encode('utf-8'))
                    }
                )
                
        except Exception as e:
            logger.error(f"Error reading file {arguments.get('file_path', 'unknown')}: {e}")
            return self.format_error(e)


class WriteFileTool(MCPTool):
    """Tool to write content to files"""
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "Write content to a file. Creates parent directories if needed."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write (relative to workspace root)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["file_path", "content"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            self.validate_arguments(arguments)
            
            file_path = arguments["file_path"]
            content = arguments["content"]
            
            # Write file content
            self.workspace.get_file_context().write_file_content(file_path, content)
            
            lines = content.splitlines()
            size_bytes = len(content.encode('utf-8'))
            
            return ToolResult(
                message=f"Successfully wrote {len(lines)} lines ({size_bytes} bytes) to {file_path}",
                properties={
                    "file_path": file_path,
                    "lines_written": len(lines),
                    "size_bytes": size_bytes
                }
            )
            
        except Exception as e:
            logger.error(f"Error writing file {arguments.get('file_path', 'unknown')}: {e}")
            return self.format_error(e)


class ListFilesTool(MCPTool):
    """Tool to list files and directories"""
    
    @property
    def name(self) -> str:
        return "list_files"
    
    @property
    def description(self) -> str:
        return "List files and directories in the workspace with filtering options."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to list (relative to workspace root, default: root)",
                    "default": ""
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list files recursively",
                    "default": False
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of files to return",
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            directory = arguments.get("directory", "")
            recursive = arguments.get("recursive", False)
            max_results = arguments.get("max_results", 100)
            
            # List files
            files = self.workspace.get_file_context().list_files(
                directory=directory,
                recursive=recursive,
                max_results=max_results
            )
            
            if not files:
                return ToolResult(
                    message=f"No files found in directory: {directory or 'root'}",
                    properties={
                        "directory": directory,
                        "file_count": 0,
                        "recursive": recursive
                    }
                )
            
            file_list = "\n".join(f"  {file}" for file in files)
            
            result_msg = f"Files in {directory or 'root directory'}"
            if recursive:
                result_msg += " (recursive)"
            result_msg += f":\n\n{file_list}"
            
            if len(files) >= max_results:
                result_msg += f"\n\n... (showing first {max_results} files)"
            
            return ToolResult(
                message=result_msg,
                properties={
                    "directory": directory,
                    "file_count": len(files),
                    "recursive": recursive,
                    "truncated": len(files) >= max_results
                }
            )
            
        except Exception as e:
            logger.error(f"Error listing files in {arguments.get('directory', 'unknown')}: {e}")
            return self.format_error(e)


class StringReplaceTool(MCPTool):
    """Tool to perform string replacement in files"""
    
    @property
    def name(self) -> str:
        return "string_replace"
    
    @property
    def description(self) -> str:
        return "Replace occurrences of a string in a file with validation."
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to modify"
                },
                "old_str": {
                    "type": "string",
                    "description": "String to find and replace"
                },
                "new_str": {
                    "type": "string",
                    "description": "String to replace with"
                },
                "occurrence": {
                    "type": "integer",
                    "description": "Which occurrence to replace (1-based, 0 for all occurrences)",
                    "default": 1,
                    "minimum": 0
                }
            },
            "required": ["file_path", "old_str", "new_str"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        try:
            self.validate_arguments(arguments)
            
            file_path = arguments["file_path"]
            old_str = arguments["old_str"]
            new_str = arguments["new_str"]
            occurrence = arguments.get("occurrence", 1)
            
            # Read current content
            content = self.workspace.get_file_context().get_file_content(file_path)
            
            # Check if old_str exists
            if old_str not in content:
                return ToolResult(
                    message=f"String not found in {file_path}: '{old_str}'",
                    success=False
                )
            
            # Count occurrences
            count = content.count(old_str)
            
            if occurrence == 0:
                # Replace all occurrences
                new_content = content.replace(old_str, new_str)
                replacements = count
            else:
                # Replace specific occurrence
                if occurrence > count:
                    return ToolResult(
                        message=f"Occurrence {occurrence} not found (only {count} occurrences exist)",
                        success=False
                    )
                
                # Find and replace the nth occurrence
                parts = content.split(old_str, occurrence)
                if len(parts) > occurrence:
                    new_content = old_str.join(parts[:occurrence]) + new_str + old_str.join(parts[occurrence:])
                    replacements = 1
                else:
                    return ToolResult(
                        message=f"Could not find occurrence {occurrence}",
                        success=False
                    )
            
            # Write the modified content
            self.workspace.get_file_context().write_file_content(file_path, new_content)
            
            return ToolResult(
                message=f"Successfully replaced {replacements} occurrence(s) in {file_path}",
                properties={
                    "file_path": file_path,
                    "replacements_made": replacements,
                    "total_occurrences": count,
                    "old_str": old_str,
                    "new_str": new_str
                }
            )
            
        except Exception as e:
            logger.error(f"Error replacing string in {arguments.get('file_path', 'unknown')}: {e}")
            return self.format_error(e)