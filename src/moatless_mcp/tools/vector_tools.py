"""
Vector database management tools for MCP server.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from mcp.types import Tool

from moatless_mcp.tools.base import MCPTool, ToolResult
from moatless_mcp.vector import VectorManager

logger = logging.getLogger(__name__)


class BuildVectorIndexTool(MCPTool):
    """Tool for building the vector index for semantic search."""
    
    @property
    def name(self) -> str:
        return "build_vector_index"
    
    @property
    def description(self) -> str:
        return "Build a vector index for semantic code search using tree-sitter and Jina embeddings"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "Jina AI API key for embeddings (can also be set via JINA_API_KEY env var)"
                },
                "force_rebuild": {
                    "type": "boolean",
                    "description": "Force rebuild even if index already exists",
                    "default": False
                },
                "file_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of glob patterns to filter files (e.g., ['**/*.py', '**/*.js'])"
                },
                "model": {
                    "type": "string",
                    "description": "Jina embedding model to use",
                    "default": "jina-embeddings-v3"
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the build_vector_index tool."""
        try:
            # Get API key from arguments or environment
            api_key = arguments.get("api_key") or os.getenv("JINA_API_KEY")
            if not api_key:
                return self.format_error(
                    "Jina API key is required. Provide it via 'api_key' parameter or JINA_API_KEY environment variable."
                )
            
            force_rebuild = arguments.get("force_rebuild", False)
            file_patterns = arguments.get("file_patterns")
            model = arguments.get("model", "jina-embeddings-v3")
            
            # Initialize vector manager
            vector_manager = VectorManager(
                workspace_root=str(self.workspace.workspace_path),
                config=self.workspace.config
            )
            
            # Initialize embeddings
            if not vector_manager.initialize_embeddings(api_key, model):
                return self.format_error("Failed to initialize embedding provider")
            
            # Build index
            message = "🔄 Building vector index for semantic search...\n"
            if force_rebuild:
                message += "🔄 Force rebuild enabled - recreating index from scratch\n"
            if file_patterns:
                message += f"📁 Filtering files with patterns: {', '.join(file_patterns)}\n"
            
            message += f"🤖 Using embedding model: {model}\n\n"
            
            result = vector_manager.build_index(file_patterns, force_rebuild)
            
            if result["success"]:
                stats = result["stats"]
                usage = result.get("embedding_usage", {})
                
                message += "✅ Vector index built successfully!\n\n"
                message += "📊 Index Statistics:\n"
                message += f"  • Total chunks: {stats['total_chunks']}\n"
                message += f"  • Total files: {stats['total_files']}\n"
                message += f"  • Average chunks per file: {stats['avg_chunks_per_file']:.1f}\n"
                
                if "chunk_types" in stats:
                    message += "  • Chunk types:\n"
                    for chunk_type, count in stats["chunk_types"].items():
                        message += f"    - {chunk_type}: {count}\n"
                
                if "languages" in stats:
                    message += "  • Languages:\n"
                    for language, count in stats["languages"].items():
                        message += f"    - {language}: {count}\n"
                
                if usage:
                    message += f"\n💰 Embedding Usage:\n"
                    if "total_tokens" in usage:
                        message += f"  • Total tokens: {usage['total_tokens']:,}\n"
                    if "prompt_tokens" in usage:
                        message += f"  • Prompt tokens: {usage['prompt_tokens']:,}\n"
                
                message += f"\n🔍 Semantic search is now available!\n"
                message += "Use the 'semantic_search' tool to search your codebase with natural language queries."
                
                return ToolResult(
                    success=True,
                    message=message,
                    properties={
                        "index_built": True,
                        "stats": stats,
                        "usage": usage,
                        "model": model
                    }
                )
            else:
                error_msg = result.get("error", "Unknown error")
                return self.format_error(f"Failed to build vector index: {error_msg}")
            
        except Exception as e:
            logger.error(f"Error in build_vector_index: {e}")
            return self.format_error(str(e))


class VectorIndexStatusTool(MCPTool):
    """Tool for checking vector index status."""
    
    @property
    def name(self) -> str:
        return "vector_index_status"
    
    @property
    def description(self) -> str:
        return "Check the status of the vector index for semantic search"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the vector_index_status tool."""
        try:
            # Initialize vector manager
            vector_manager = VectorManager(
                workspace_root=str(self.workspace.workspace_path),
                config=self.workspace.config
            )
            
            status = vector_manager.get_index_status()
            
            message = "📊 Vector Index Status\n\n"
            
            if status.get("error"):
                message += f"❌ Error: {status['error']}\n"
                return ToolResult(success=False, message=message, properties=status)
            
            # Index existence and loading status
            if status["index_exists"]:
                message += "✅ Index files exist on disk\n"
            else:
                message += "❌ No index files found\n"
            
            if status["index_loaded"]:
                message += "✅ Index loaded in memory\n"
            else:
                message += "❌ Index not loaded\n"
            
            if status["embedding_provider_ready"]:
                message += "✅ Embedding provider ready\n"
            else:
                message += "❌ Embedding provider not initialized\n"
                message += "    (API key needed for search and index building)\n"
            
            # Statistics
            stats = status.get("stats", {})
            if stats.get("total_chunks", 0) > 0:
                message += f"\n📈 Index Statistics:\n"
                message += f"  • Total chunks: {stats['total_chunks']}\n"
                message += f"  • Total files: {stats['total_files']}\n"
                message += f"  • Index directory: {stats['index_dir']}\n"
                
                if "chunk_types" in stats:
                    message += "  • Chunk types:\n"
                    for chunk_type, count in stats["chunk_types"].items():
                        message += f"    - {chunk_type}: {count}\n"
                
                if "languages" in stats:
                    message += "  • Languages:\n"
                    for language, count in stats["languages"].items():
                        message += f"    - {language}: {count}\n"
            else:
                message += "\n📭 Index is empty\n"
            
            # Recommendations
            message += "\n💡 Recommendations:\n"
            if not status["index_exists"]:
                message += "  • Use 'build_vector_index' tool to create the semantic search index\n"
            elif not status["embedding_provider_ready"]:
                message += "  • Provide Jina API key to enable semantic search functionality\n"
            elif stats.get("total_chunks", 0) == 0:
                message += "  • Index exists but is empty - try rebuilding with 'build_vector_index'\n"
            else:
                message += "  • Vector index is ready for semantic search!\n"
                message += "  • Use 'semantic_search' tool to search your codebase\n"
            
            return ToolResult(
                success=True,
                message=message,
                properties=status
            )
            
        except Exception as e:
            logger.error(f"Error in vector_index_status: {e}")
            return self.format_error(str(e))


class ClearVectorIndexTool(MCPTool):
    """Tool for clearing the vector index."""
    
    @property
    def name(self) -> str:
        return "clear_vector_index"
    
    @property
    def description(self) -> str:
        return "Clear the vector index and delete all index files"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "confirm": {
                    "type": "boolean",
                    "description": "Confirm that you want to delete the vector index",
                    "default": False
                }
            }
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """Execute the clear_vector_index tool."""
        try:
            confirm = arguments.get("confirm", False)
            
            if not confirm:
                return self.format_error(
                    "Index clearing requires confirmation. Set 'confirm: true' to proceed."
                )
            
            # Initialize vector manager
            vector_manager = VectorManager(
                workspace_root=str(self.workspace.workspace_path),
                config=self.workspace.config
            )
            
            success = vector_manager.clear_index()
            
            if success:
                message = "✅ Vector index cleared successfully!\n"
                message += "🗑️  All index files have been deleted.\n"
                message += "💡 Use 'build_vector_index' to create a new index for semantic search."
                
                return ToolResult(
                    success=True,
                    message=message,
                    properties={"index_cleared": True}
                )
            else:
                return self.format_error("Failed to clear vector index")
            
        except Exception as e:
            logger.error(f"Error in clear_vector_index: {e}")
            return self.format_error(str(e))