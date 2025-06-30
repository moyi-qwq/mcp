#!/usr/bin/env python3
"""
Moatless MCP Server - Main server implementation
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

import anyio
from mcp import CallToolRequest, Tool, stdio_server
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.shared.context import RequestContext
from mcp.types import TextContent, ServerCapabilities, ToolsCapability

from moatless_mcp.tools.registry import ToolRegistry
from moatless_mcp.adapters.workspace import WorkspaceAdapter
from moatless_mcp.utils.config import Config

logger = logging.getLogger(__name__)


class MoatlessMCPServer:
    """Main MCP Server for Moatless Tools"""
    
    def __init__(self, workspace_path: str = ".", config: Optional[Config] = None):
        self.config = config or Config()
        self.workspace = WorkspaceAdapter(workspace_path, self.config)
        self.tool_registry = ToolRegistry(self.workspace)
        
        # Create MCP server
        self.server = Server("moatless-tools")
        
        # Register handlers
        self.server.request_handlers["tools/list"] = self.handle_list_tools
        self.server.request_handlers["tools/call"] = self.handle_call_tool
        
        logger.info(f"Initialized Moatless MCP Server with workspace: {workspace_path}")
    
    async def handle_list_tools(self, request, context: RequestContext) -> dict:
        """Handle tools/list request"""
        tools = self.tool_registry.get_tools()
        logger.debug(f"Listed {len(tools)} tools")
        
        return {
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools
            ]
        }
    
    async def handle_call_tool(self, request, context: RequestContext) -> dict:
        """Handle tools/call request"""
        tool_name = request["params"]["name"]
        arguments = request["params"].get("arguments", {})
        
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        try:
            result = await self.tool_registry.execute_tool(tool_name, arguments)
            
            content = []
            
            if result.message:
                content.append({
                    "type": "text",
                    "text": result.message
                })
            
            # Add any additional properties as text
            if hasattr(result, 'properties') and result.properties:
                for key, value in result.properties.items():
                    if key != 'message':
                        content.append({
                            "type": "text",
                            "text": f"{key}: {value}"
                        })
            
            return {
                "content": content,
                "isError": False
            }
            
        except Exception as e:
            error_msg = f"Tool execution failed for '{tool_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return {
                "content": [{
                    "type": "text",
                    "text": error_msg
                }],
                "isError": True
            }


async def main():
    """Main entry point for the MCP server"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Moatless MCP Server")
    parser.add_argument(
        "--workspace", 
        type=str, 
        default=".", 
        help="Path to workspace directory (default: current directory)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate workspace path
    workspace_path = Path(args.workspace).resolve()
    if not workspace_path.exists():
        logger.error(f"Workspace path does not exist: {workspace_path}")
        sys.exit(1)
    
    logger.info(f"Starting Moatless MCP Server with workspace: {workspace_path}")
    
    # Create server instance
    mcp_server = MoatlessMCPServer(str(workspace_path))
    
    try:
        # Run the MCP server
        async with stdio_server() as streams:
            initialization_options = InitializationOptions(
                server_name="moatless-tools",
                server_version="0.1.0",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(listChanged=True)
                )
            )
            await mcp_server.server.run(*streams, initialization_options)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


def run_server():
    """Entry point for command line execution"""
    asyncio.run(main())

if __name__ == "__main__":
    run_server()