"""Advanced MCP tools for code analysis and testing."""

import json
import logging
import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.types import Tool

from moatless_mcp.tools.base import MCPTool, ToolResult
from moatless_mcp.tools.advanced_search import AdvancedSearchTools
from moatless_mcp.tools.testing import TestingFramework
from moatless_mcp.tools.semantic_search import EnhancedSemanticSearch, SemanticSearch

logger = logging.getLogger(__name__)



class FindClassTool(MCPTool):
    """Tool for finding class definitions in the codebase."""
    
    @property
    def name(self) -> str:
        return "find_class"
    
    @property
    def description(self) -> str:
        return "Find class definitions by name"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "class_name": {
                    "type": "string",
                    "description": "Name of the class to find"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional file pattern to limit search"
                }
            },
            "required": ["class_name"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the find_class tool."""
        try:
            class_name = arguments.get("class_name")
            file_pattern = arguments.get("file_pattern")
            
            if not class_name:
                return self.format_error("class_name is required")
            
            search_tools = AdvancedSearchTools(self.workspace.config, self.workspace.workspace_path)
            result = await search_tools.find_class(class_name, file_pattern)
            
            if "error" in result:
                return self.format_error(result["error"])
            
            # Format the response
            if result['results']:
                message = f"Found {len(result['results'])} class definition(s) for '{class_name}':\n\n"
                for match in result['results']:
                    message += f"📁 {match['file_path']}:{match['line_number']}\n"
                    message += f"   {match['class_definition']}\n\n"
            else:
                message = f"No class definitions found for '{class_name}'"
                if file_pattern:
                    message += f" in files matching '{file_pattern}'"
            
            return ToolResult(
                success=True,
                message=message,
                properties=result
            )
            
        except Exception as e:
            logger.error(f"Error in find_class: {e}")
            return self.format_error(str(e))


class FindFunctionTool(MCPTool):
    """Tool for finding function definitions in the codebase."""
    
    @property
    def name(self) -> str:
        return "find_function"
    
    @property
    def description(self) -> str:
        return "Find function definitions by name"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "function_name": {
                    "type": "string",
                    "description": "Name of the function to find"
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional file pattern to limit search"
                }
            },
            "required": ["function_name"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the find_function tool."""
        try:
            function_name = arguments.get("function_name")
            file_pattern = arguments.get("file_pattern")
            
            if not function_name:
                return self.format_error("function_name is required")
            
            search_tools = AdvancedSearchTools(self.workspace.config, self.workspace.workspace_path)
            result = await search_tools.find_function(function_name, file_pattern)
            
            if "error" in result:
                return self.format_error(result["error"])
            
            # Format the response
            if result['results']:
                message = f"Found {len(result['results'])} function definition(s) for '{function_name}':\n\n"
                for match in result['results']:
                    message += f"📁 {match['file_path']}:{match['line_number']} ({match['language']})\n"
                    message += f"   {match['function_definition']}\n\n"
            else:
                message = f"No function definitions found for '{function_name}'"
                if file_pattern:
                    message += f" in files matching '{file_pattern}'"
            
            return ToolResult(
                success=True,
                message=message,
                properties=result
            )
            
        except Exception as e:
            logger.error(f"Error in find_function: {e}")
            return self.format_error(str(e))


class ViewCodeTool(MCPTool):
    """Tool for viewing specific code sections with intelligent context."""
    
    @property
    def name(self) -> str:
        return "view_code"
    
    @property
    def description(self) -> str:
        return "View specific code sections with context"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to view"
                },
                "start_line": {
                    "type": "integer",
                    "description": "Starting line number (1-indexed)"
                },
                "end_line": {
                    "type": "integer",
                    "description": "Ending line number (1-indexed)"
                },
                "span_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of span IDs to view (class names, function names, etc.)"
                }
            },
            "required": ["file_path"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the view_code tool."""
        try:
            file_path = arguments.get("file_path")
            start_line = arguments.get("start_line")
            end_line = arguments.get("end_line")
            span_ids = arguments.get("span_ids")
            
            if not file_path:
                return self.format_error("file_path is required")
            
            search_tools = AdvancedSearchTools(self.workspace.config, self.workspace.workspace_path)
            result = await search_tools.view_code(file_path, start_line, end_line, span_ids)
            
            if "error" in result:
                return self.format_error(result["error"])
            
            # Format the response
            message = f"Code view for {result['file_path']} (Total lines: {result['total_lines']}):\n\n"
            
            for section in result['content_sections']:
                if 'span_id' in section:
                    message += f"=== {section['span_type'].title()}: {section['span_id']} ===\n"
                    message += f"Lines {section['start_line']}-{section['end_line']}:\n"
                else:
                    message += f"=== Lines {section['start_line']}-{section['end_line']} ===\n"
                
                message += section['content']
                message += "\n\n"
            
            return ToolResult(
                success=True,
                message=message,
                properties=result
            )
            
        except Exception as e:
            logger.error(f"Error in view_code: {e}")
            return self.format_error(str(e))


class SemanticSearchTool(MCPTool):
    """Tool for enhanced semantic search using natural language queries."""
    
    @property
    def name(self) -> str:
        return "semantic_search"
    
    @property
    def description(self) -> str:
        return "Search for code using natural language descriptions with vector embeddings"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language description of what to find"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10)",
                    "default": 10
                },
                "filter_type": {
                    "type": "string",
                    "enum": ["class", "function", "method", "class_header", "context"],
                    "description": "Filter results by code chunk type"
                },
                "api_key": {
                    "type": "string",
                    "description": "Jina AI API key for embeddings (can also be set via JINA_API_KEY env var)"
                }
            },
            "required": ["query"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the semantic search using the new vector database."""
        try:
            import os
            from moatless_mcp.vector import VectorManager
            
            query = arguments.get("query")
            max_results = arguments.get("max_results", 10)
            filter_type = arguments.get("filter_type")
            api_key = arguments.get("api_key") or os.getenv("JINA_API_KEY")
            
            if not query:
                return self.format_error("query is required")
            
            # Initialize vector manager
            vector_manager = VectorManager(
                workspace_root=str(self.workspace.workspace_path),
                config=self.workspace.config
            )
            
            # Check if index exists
            status = vector_manager.get_index_status()
            if not status["index_exists"] or status["stats"].get("total_chunks", 0) == 0:
                return self.format_error(
                    "Vector index not found or empty. Please use 'build_vector_index' tool first to create the semantic search index."
                )
            
            # Initialize embeddings if API key provided
            if api_key:
                if not vector_manager.initialize_embeddings(api_key):
                    return self.format_error("Failed to initialize embedding provider with provided API key")
            elif not status["embedding_provider_ready"]:
                return self.format_error(
                    "Jina API key is required for semantic search. Provide it via 'api_key' parameter or JINA_API_KEY environment variable."
                )
            
            # Perform search
            result = vector_manager.search(query, max_results, filter_type)
            
            if not result["success"]:
                return self.format_error(result.get("error", "Search failed"))
            
            # Format the response
            message = f"🔍 Semantic Search Results for: '{result['query']}'\n"
            message += f"🧠 Using tree-sitter code analysis + Jina embeddings\n"
            if filter_type:
                message += f"🔍 Filter: {filter_type} chunks only\n"
            message += f"📊 Found {result['total_results']} relevant code sections\n\n"
            
            if result['results']:
                for i, match in enumerate(result['results'], 1):
                    message += f"{i}. 📁 {match['file_path']}:{match['start_line']}-{match['end_line']}\n"
                    message += f"   🎯 Similarity Score: {match['similarity_score']:.3f}\n"
                    message += f"   🏷️  Type: {match['chunk_type']}"
                    
                    if match['name']:
                        message += f" ({match['name']}"
                        if match['parent_name']:
                            message += f" in {match['parent_name']}"
                        message += ")"
                    message += "\n"
                    
                    if match['language'] != "unknown":
                        message += f"   💻 Language: {match['language']}\n"
                    
                    # Show metadata if available
                    if match.get('metadata'):
                        metadata = match['metadata']
                        if metadata.get('parameters'):
                            params = ", ".join(metadata['parameters'][:3])
                            if len(metadata['parameters']) > 3:
                                params += f", ... (+{len(metadata['parameters']) - 3} more)"
                            message += f"   📝 Parameters: {params}\n"
                        
                        if metadata.get('decorators'):
                            decorators = ", ".join(metadata['decorators'])
                            message += f"   🎨 Decorators: {decorators}\n"
                    
                    # Show preview
                    if match.get('content_preview'):
                        preview_lines = match['content_preview'].split('\n')[:2]
                        preview = ' '.join(line.strip() for line in preview_lines if line.strip())
                        if len(preview) > 150:
                            preview = preview[:150] + "..."
                        message += f"   📖 Preview: {preview}\n"
                    
                    message += "\n"
            else:
                message += "❌ No relevant code found for this query.\n"
                message += "💡 Try:\n"
                message += "  • Using different search terms\n"
                message += "  • Describing the functionality you're looking for\n"
                message += "  • Checking if the vector index needs rebuilding\n"
            
            # Add usage tip
            if result['results']:
                message += "💡 Use 'view_code' tool with the file path and line numbers to see the full code.\n"
            
            return ToolResult(
                success=True,
                message=message,
                properties={
                    "query": result['query'],
                    "total_results": result['total_results'],
                    "filter_type": filter_type,
                    "results": result['results']
                }
            )
            
        except Exception as e:
            logger.error(f"Error in semantic_search: {e}")
            return self.format_error(str(e))


class RunTestsTool(MCPTool):
    """Tool for running tests using various testing frameworks."""
    
    @property
    def name(self) -> str:
        return "run_tests"
    
    @property
    def description(self) -> str:
        return "Run tests using detected testing frameworks (pytest, jest, maven, etc.)"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "framework": {
                    "type": "string",
                    "description": "Testing framework to use (auto-detected if not specified)"
                },
                "test_path": {
                    "type": "string",
                    "description": "Specific test file or directory to run"
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional arguments to pass to the test runner"
                },
                "detect_only": {
                    "type": "boolean",
                    "description": "Only detect available frameworks without running tests",
                    "default": False
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the run_tests tool."""
        try:
            framework = arguments.get("framework")
            test_path = arguments.get("test_path")
            args = arguments.get("args", [])
            detect_only = arguments.get("detect_only", False)
            
            testing_framework = TestingFramework(self.workspace.config, self.workspace.workspace_path)
            
            # If detect_only is True, just return framework detection
            if detect_only:
                result = await testing_framework.detect_test_framework()
                
                message = "Detected testing frameworks:\n\n"
                if result['detected_frameworks']:
                    for fw_name in result['detected_frameworks']:
                        fw_info = result['frameworks'][fw_name]
                        message += f"✓ {fw_name.title()}\n"
                        if fw_info.get('config_files'):
                            message += f"  Config files: {', '.join(fw_info['config_files'])}\n"
                        if fw_info.get('test_command'):
                            message += f"  Test command: {fw_info['test_command']}\n"
                        if fw_info.get('test_files'):
                            message += f"  Test files: {len(fw_info['test_files'])} found\n"
                        message += "\n"
                else:
                    message += "No testing frameworks detected."
                
                return ToolResult(
                    success=True,
                    message=message,
                    properties=result
                )
            
            # Run tests
            result = await testing_framework.run_tests(framework, test_path, args)
            
            if "error" in result:
                return self.format_error(result["error"])
            
            # Format the response
            message = f"Test Results (Framework: {result['framework']})\n"
            message += f"Command: {result['command']}\n"
            message += f"Exit Code: {result['return_code']}\n\n"
            
            summary = result.get('summary', {})
            if summary:
                message += "Summary:\n"
                if summary.get('total'):
                    message += f"  Total tests: {summary['total']}\n"
                if summary.get('passed'):
                    message += f"  ✓ Passed: {summary['passed']}\n"
                if summary.get('failed'):
                    message += f"  ✗ Failed: {summary['failed']}\n"
                if summary.get('skipped'):
                    message += f"  ⊝ Skipped: {summary['skipped']}\n"
                if summary.get('errors'):
                    message += f"  ⚠ Errors: {summary['errors']}\n"
                if summary.get('duration'):
                    message += f"  Duration: {summary['duration']}s\n"
                message += "\n"
            
            # Add output if tests failed or if verbose
            if not result['success'] or result.get('stderr'):
                message += "Output:\n"
                if result.get('stderr'):
                    message += f"STDERR:\n{result['stderr']}\n"
                if result.get('stdout'):
                    # Truncate long output
                    stdout = result['stdout']
                    if len(stdout) > 2000:
                        stdout = stdout[:2000] + "\n... (output truncated)"
                    message += f"STDOUT:\n{stdout}\n"
            
            return ToolResult(
                success=result['success'],
                message=message,
                properties=result
            )
            
        except Exception as e:
            logger.error(f"Error in run_tests: {e}")
            return self.format_error(str(e))