#!/usr/bin/env python3
"""
Test script for enhanced semantic search features
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from moatless_mcp.adapters.workspace import WorkspaceAdapter
from moatless_mcp.utils.config import Config
from moatless_mcp.tools.semantic_search import EnhancedSemanticSearch
from moatless_mcp.tools.advanced_tools import CodeIndexTool


async def test_enhanced_semantic_search():
    """Test the enhanced semantic search functionality."""
    print("🧪 Testing Enhanced Semantic Search Features\n")
    
    # Setup workspace (use current directory as test workspace)
    workspace_path = "."
    config = Config()
    workspace = WorkspaceAdapter(workspace_path, config)
    
    print("1. 📊 Testing Workspace Info...")
    info = workspace.get_workspace_info()
    print(f"   Workspace: {info['path']}")
    print(f"   Moatless Available: {info.get('moatless_available', False)}")
    print(f"   Index Initialized: {info.get('index_initialized', False)}")
    
    print("\n2. 🔧 Testing Code Index Tool...")
    code_index_tool = CodeIndexTool(workspace)
    
    # Check status
    status_result = await code_index_tool.execute({"action": "status"})
    print(f"   Status Check: {'✅' if status_result.success else '❌'}")
    if status_result.message:
        # Print first few lines of status
        lines = status_result.message.split('\n')[:8]
        for line in lines:
            if line.strip():
                print(f"   {line}")
    
    print("\n3. 🔍 Testing Enhanced Semantic Search...")
    
    # Get code index if available
    code_index = workspace.code_index if hasattr(workspace, 'code_index') else None
    
    semantic_search = EnhancedSemanticSearch(
        config=config,
        workspace_root=workspace_path,
        code_index=code_index
    )
    
    # Test queries
    test_queries = [
        {
            "query": "file operations and reading",
            "description": "Test finding file operation code"
        },
        {
            "query": "semantic search implementation",
            "description": "Test finding semantic search code"
        },
        {
            "query": "configuration and settings",
            "description": "Test finding configuration code"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n   3.{i} Testing: {test_case['description']}")
        print(f"       Query: '{test_case['query']}'")
        
        try:
            result = await semantic_search.semantic_search(
                query=test_case["query"],
                max_results=3
            )
            
            if "error" in result:
                print(f"       ❌ Error: {result['error']}")
            else:
                print(f"       ✅ Found {result['total_results']} results")
                print(f"       Search Method: {result['search_method']}")
                
                # Show top result
                if result["results"]:
                    top_result = result["results"][0]
                    print(f"       Top Result: {top_result['file_path']}")
                    print(f"       Relevance: {top_result['relevance_score']:.2f}")
                    print(f"       Type: {top_result['match_type']}")
                
        except Exception as e:
            print(f"       ❌ Exception: {e}")
    
    print("\n4. 🎯 Testing Advanced Search Tools...")
    
    # Import and test other tools
    try:
        from moatless_mcp.tools.advanced_tools import FindClassTool, FindFunctionTool
        
        find_class_tool = FindClassTool(workspace)
        class_result = await find_class_tool.execute({
            "class_name": "WorkspaceAdapter"
        })
        print(f"   Find Class Tool: {'✅' if class_result.success else '❌'}")
        if class_result.success and hasattr(class_result, 'properties'):
            props = class_result.properties
            if isinstance(props, dict) and 'results' in props:
                print(f"   Found {len(props['results'])} class matches")
        
        find_function_tool = FindFunctionTool(workspace)
        function_result = await find_function_tool.execute({
            "function_name": "semantic_search"
        })
        print(f"   Find Function Tool: {'✅' if function_result.success else '❌'}")
        if function_result.success and hasattr(function_result, 'properties'):
            props = function_result.properties
            if isinstance(props, dict) and 'results' in props:
                print(f"   Found {len(props['results'])} function matches")
                
    except ImportError as e:
        print(f"   ⚠️  Advanced tools not available: {e}")
    
    print("\n✅ Enhanced Semantic Search Test Complete!")
    print("\n📖 For more details, see ENHANCED_FEATURES.md")


def check_requirements():
    """Check if required dependencies are available."""
    print("🔍 Checking Requirements...")
    
    try:
        import requests
        print("   ✅ Requests library available for Jina AI")
    except ImportError:
        print("   ❌ Requests library not found")
    
    try:
        import openai
        print("   ✅ OpenAI library available (legacy support)")
    except ImportError:
        print("   ⚠️  OpenAI library not found")
    
    try:
        import faiss
        print("   ✅ FAISS library available")
    except ImportError:
        print("   ⚠️  FAISS library not found (semantic search will use fallback)")
    
    # Check for API keys
    if os.getenv("JINA_API_KEY"):
        print("   ✅ Jina AI API key found")
    elif os.getenv("OPENAI_API_KEY"):
        print("   ⚠️  OpenAI API key found (consider migrating to Jina AI)")
    else:
        print("   ⚠️  No API key set (set JINA_API_KEY environment variable)")
    
    try:
        from moatless.index import CodeIndex
        print("   ✅ Moatless library available")
    except ImportError:
        print("   ⚠️  Moatless library not found (semantic search will use fallback)")
    
    print()


async def main():
    """Main test function."""
    print("🚀 Moatless MCP Server - Enhanced Features Test\n")
    
    check_requirements()
    await test_enhanced_semantic_search()


if __name__ == "__main__":
    asyncio.run(main()) 