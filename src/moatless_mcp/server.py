#!/usr/bin/env python3
"""
Moatless MCP Server - Enhanced implementation with semantic search support
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Optional

import anyio
from mcp import stdio_server
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    ServerCapabilities,
    ToolsCapability,
    Tool,
    TextContent,
    CallToolResult,
)

from moatless_mcp.tools.registry import ToolRegistry
from moatless_mcp.adapters.workspace import WorkspaceAdapter
from moatless_mcp.utils.config import Config

logger = logging.getLogger(__name__)

# Create global server instance
server = Server("moatless-tools")

# Global state
workspace_adapter: Optional[WorkspaceAdapter] = None
tool_registry: Optional[ToolRegistry] = None


async def init_server(workspace_path: str) -> None:
    """Initialize the server with workspace"""
    global workspace_adapter, tool_registry
    
    config = Config()
    workspace_adapter = WorkspaceAdapter(workspace_path, config)
    
    # Vector index is now built on-demand using the build_vector_index tool
    logger.info("Server initialized with on-demand vector index building")
    
    tool_registry = ToolRegistry(workspace_adapter)
    
    logger.info(f"🚀 Initialized Moatless MCP Server with workspace: {workspace_path}")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    if not tool_registry:
        raise RuntimeError("Server not initialized")
    
    tools = tool_registry.get_tools()
    logger.debug(f"Listed {len(tools)} tools")
    
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None = None) -> list[TextContent]:
    """Call a tool"""
    if not tool_registry:
        raise RuntimeError("Server not initialized")
    
    arguments = arguments or {}
    logger.info(f"Executing tool: {name} with args: {arguments}")
    
    try:
        result = await tool_registry.execute_tool(name, arguments)
        
        content = []
        
        if result.message:
            content.append(TextContent(
                type="text",
                text=result.message
            ))
        
        # Add any additional properties as text
        if hasattr(result, 'properties') and result.properties:
            for key, value in result.properties.items():
                if key != 'message':
                    content.append(TextContent(
                        type="text",
                        text=f"{key}: {value}"
                    ))
        
        return content
        
    except Exception as e:
        error_msg = f"Tool execution failed for '{name}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return [TextContent(
            type="text",
            text=error_msg
        )]


async def main():
    """Main entry point for the MCP server"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(
        description="Moatless MCP Server with Enhanced Semantic Search",
        epilog="""
Examples:
  %(prog)s --workspace /path/to/project --jina-api-key "your-key"
  %(prog)s --workspace .  # Vector index built on-demand via build_vector_index tool
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--workspace", 
        type=str, 
        default=".", 
        help="Path to workspace directory (default: current directory)"
    )
    parser.add_argument(
        "--jina-api-key",
        type=str,
        help="Jina AI API key for embeddings (enables vector-based semantic search). Can also be set via JINA_API_KEY environment variable"
    )
    
    parser.add_argument(
        "--openai-api-key",
        type=str,
        help="OpenAI API key for embeddings (deprecated, use --jina-api-key instead). Can also be set via OPENAI_API_KEY environment variable"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    # Removed --no-index and --rebuild-index flags since vector index is now on-demand
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Set API key if provided
    import os  # Move import outside conditional blocks
    if args.jina_api_key:
        os.environ["JINA_API_KEY"] = args.jina_api_key
        logger.info("🔑 Jina AI API key configured for vector-based semantic search")
    elif args.openai_api_key:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key
        logger.warning("⚠️  Using deprecated OpenAI API key. Consider switching to Jina AI with --jina-api-key")
        logger.info("🔑 OpenAI API key configured for vector-based semantic search")
    elif not os.getenv("JINA_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        logger.warning("⚠️  No API key provided. Will use keyword-based search fallback.")
        logger.info("   💡 For enhanced semantic search, use: --jina-api-key 'your-key'")
        logger.info("   💡 Or set environment variable: export JINA_API_KEY='your-key'")
        logger.info("   💡 (OpenAI is also supported but deprecated)")
    
    # Validate workspace path
    workspace_path = Path(args.workspace).resolve()
    if not workspace_path.exists():
        logger.error(f"Workspace path does not exist: {workspace_path}")
        sys.exit(1)
    
    logger.info(f"🔧 Starting Moatless MCP Server with workspace: {workspace_path}")
    
    # Initialize server
    try:
        await init_server(str(workspace_path))
        logger.info("💡 Use 'build_vector_index' tool to create semantic search index when needed")
    except Exception as e:
        logger.error(f"❌ Failed to initialize server: {e}")
        sys.exit(1)
    
    try:
        # Run the MCP server
        async with stdio_server() as streams:
            await server.run(
                *streams,
                InitializationOptions(
                    server_name="moatless-tools",
                    server_version="0.2.0",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability(listChanged=True)
                    )
                )
            )
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}", exc_info=True)
        sys.exit(1)


def run_server():
    """Entry point for command line execution"""
    asyncio.run(main())


if __name__ == "__main__":
    run_server()