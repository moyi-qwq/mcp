# Moatless MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个基于模型上下文协议 (MCP) 的高级代码分析和编辑服务器，支持基于向量嵌入的语义搜索功能。该服务器为 AI 助手提供了通过标准化接口执行复杂代码操作的能力。

## 🏗️ MCP 架构概述

### 什么是 MCP (Model Context Protocol)

Model Context Protocol (MCP) 是一个开放标准，用于在 AI 应用程序和外部数据源及工具之间创建安全、受控的连接。MCP 使 AI 系统能够：

- 访问实时数据和外部系统
- 执行复杂的操作和工作流
- 与各种工具和服务集成
- 维护安全边界和访问控制

### MCP 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP 生态系统                              │
├─────────────────────────────────────────────────────────────┤
│  AI 客户端 (Claude Desktop, Cline, etc.)                   │
│  ├── MCP 客户端库                                           │
│  └── 通信层 (stdio, HTTP, SSE)                             │
├─────────────────────────────────────────────────────────────┤
│  MCP 服务器 (本项目)                                        │
│  ├── 服务器运行时                                           │
│  ├── 工具注册表                                             │
│  ├── 资源提供者                                             │
│  └── 功能处理器                                             │
├─────────────────────────────────────────────────────────────┤
│  底层系统 (文件系统, 数据库, API, etc.)                     │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 实现架构

### 核心架构设计

本项目采用模块化架构，主要包含以下组件：

```
MoatlessMCPServer
├── 🔧 Server Core (server.py)
│   ├── MCP 协议处理
│   ├── 工具生命周期管理
│   └── 错误处理和日志记录
│
├── 🗂️ Tool Registry (tools/registry.py)
│   ├── 工具注册和发现
│   ├── 工具执行调度
│   └── 工具参数验证
│
├── 🏠 Workspace Adapter (adapters/workspace.py)
│   ├── 工作空间管理
│   ├── 文件系统抽象
│   └── Git 集成
│
├── 🛠️ Tool Implementations (tools/)
│   ├── 文件操作工具
│   ├── 搜索和发现工具
│   ├── 代码分析工具
│   └── 向量搜索工具
│
├── 🔍 Vector System (vector/)
│   ├── 代码分割器
│   ├── 嵌入生成
│   └── 向量索引管理
│
└── 🌳 Tree-sitter Integration (treesitter/)
    ├── 语言解析器
    ├── AST 查询
    └── 代码结构分析
```

### MCP 服务器实现流程

#### 1. 服务器初始化
```python
# server.py:38-51
async def init_server(workspace_path: str) -> None:
    """初始化服务器和工作空间"""
    global workspace_adapter, tool_registry
    
    config = Config()
    workspace_adapter = WorkspaceAdapter(workspace_path, config)
    
    # 向量索引现在是按需构建的
    logger.info("Server initialized with on-demand vector index building")
    
    tool_registry = ToolRegistry(workspace_adapter)
    
    logger.info(f"🚀 Initialized Moatless MCP Server with workspace: {workspace_path}")
```

#### 2. 工具注册机制
```python
# tools/registry.py:46-77
def _register_default_tools(self):
    """注册所有默认工具"""
    tools = [
        # 文件操作工具
        ReadFileTool(self.workspace),
        WriteFileTool(self.workspace),
        ListFilesTool(self.workspace),
        StringReplaceTool(self.workspace),
        
        # 搜索工具
        GrepTool(self.workspace),
        FindFilesTool(self.workspace),
        WorkspaceInfoTool(self.workspace),
        
        # 高级工具
        FindClassTool(self.workspace),
        FindFunctionTool(self.workspace),
        ViewCodeTool(self.workspace),
        SemanticSearchTool(self.workspace),
        RunTestsTool(self.workspace),
        
        # 向量数据库工具
        BuildVectorIndexTool(self.workspace),
        VectorIndexStatusTool(self.workspace),
        ClearVectorIndexTool(self.workspace),
    ]
    
    for tool in tools:
        self.register_tool(tool)
```

#### 3. MCP 协议处理
```python
# server.py:53-104
@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """列出可用工具"""
    if not tool_registry:
        raise RuntimeError("Server not initialized")
    
    tools = tool_registry.get_tools()
    logger.debug(f"Listed {len(tools)} tools")
    
    return tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None = None) -> list[TextContent]:
    """执行工具调用"""
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
        
        # 添加任何额外属性作为文本
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
```

## 📁 代码结构详解

### 核心模块说明

#### 1. 服务器核心 (`server.py`)
- **功能**: MCP 协议实现和服务器运行时
- **关键特性**:
  - 异步 MCP 服务器实现
  - 命令行参数解析
  - 全局状态管理
  - 错误处理和日志记录

#### 2. 工具系统 (`tools/`)

**基础工具类** (`base.py`)
```python
class MCPTool(ABC):
    """MCP 工具基类"""
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        """执行工具逻辑"""
        pass
    
    def to_mcp_tool(self) -> Tool:
        """转换为 MCP 工具格式"""
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        )
```

**工具分类**:
- **文件操作** (`file_operations.py`): 读写文件、目录列表、字符串替换
- **搜索工具** (`search_tools.py`): 文本搜索、文件查找、工作空间信息
- **高级工具** (`advanced_tools.py`): 类查找、函数查找、语义搜索
- **向量工具** (`vector_tools.py`): 向量索引构建、状态查询、索引清理

#### 3. 工作空间适配器 (`adapters/workspace.py`)
- **文件上下文管理**: 缓存和文件访问
- **Git 集成**: 仓库状态和版本控制信息
- **Moatless 集成**: 语义搜索和代码索引

#### 4. 向量搜索系统 (`vector/`)
- **代码分割** (`code_splitter.py`): 智能代码块分割
- **嵌入生成** (`embeddings.py`): Jina AI / OpenAI 嵌入
- **向量索引** (`index.py`): FAISS 向量数据库管理

#### 5. Tree-sitter 集成 (`treesitter/`)
- **多语言支持**: Python, Java, JavaScript, TypeScript 等
- **AST 查询**: 代码结构分析和提取
- **语法解析**: 精确的代码理解

### 配置系统 (`utils/config.py`)
```python
@dataclass
class Config:
    """Moatless MCP 服务器配置"""
    
    # 文件操作配置
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_lines_per_file: int = 10000
    
    # 搜索配置
    max_search_results: int = 100
    search_timeout: int = 30  # 秒
    
    # 安全设置 - 更宽松的文件访问策略
    allowed_file_extensions: set = {
        # 编程语言
        ".py", ".java", ".js", ".ts", ".jsx", ".tsx", 
        ".c", ".cpp", ".h", ".hpp", ".cs", ".php", 
        ".rb", ".go", ".rs", ".swift", ".kt", ".scala",
        # Web 技术
        ".html", ".css", ".scss", ".sass", ".less",
        # 数据和配置
        ".json", ".yaml", ".yml", ".toml", ".xml",
        ".sql", ".graphql", ".proto",
        # 文档
        ".md", ".txt", ".rst", ".adoc", ".tex",
        # 构建和项目文件
        ".dockerfile", ".gitignore", ".editorconfig",
        # 无扩展名文件
        ""
    }
    
    # 仅核心禁止路径
    forbidden_paths: set = {
        "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache"
    }
    
    # 允许访问隐藏文件和版本控制
    allow_hidden_files: bool = True
    allow_version_control: bool = True
    
    def is_file_allowed(self, file_path: Path) -> bool:
        """检查文件是否允许访问"""
        # 检查禁止路径
        for part in file_path.parts:
            if part in self.forbidden_paths:
                return False
        
        # 检查文件扩展名
        file_ext = file_path.suffix.lower()
        if file_ext not in self.allowed_file_extensions:
            # 允许无扩展名文件或检查是否为文本文件
            if file_ext == "" or self._is_likely_text_file(file_path):
                return True
            return False
        
        return True
```

## 🚀 实现一个 MCP 服务器的详细步骤

### 步骤 1: 项目结构设置

```bash
# 创建项目目录
mkdir my-mcp-server
cd my-mcp-server

# 创建目录结构
mkdir -p src/my_mcp/{tools,adapters,utils}
mkdir -p tests docs

# 创建文件
touch src/my_mcp/{__init__.py,server.py}
touch src/my_mcp/tools/{__init__.py,base.py,registry.py}
touch src/my_mcp/adapters/{__init__.py,workspace.py}
touch src/my_mcp/utils/{__init__.py,config.py}
```

### 步骤 2: 创建项目配置 (`pyproject.toml`)

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "my-mcp-server"
version = "0.1.0"
description = "My custom MCP server"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.9.0",
    "pydantic>=2.0.0",
    "aiofiles>=23.0.0",
    "anyio>=4.0.0",
]

[project.scripts]
my-mcp-server = "my_mcp.server:run_server"
```

### 步骤 3: 实现基础工具类

```python
# src/my_mcp/tools/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from mcp.types import Tool

@dataclass
class ToolResult:
    message: str
    success: bool = True
    properties: Optional[Dict[str, Any]] = None

class MCPTool(ABC):
    def __init__(self, workspace):
        self.workspace = workspace
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        pass
    
    def to_mcp_tool(self) -> Tool:
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        )
```

### 步骤 4: 创建示例工具

```python
# src/my_mcp/tools/example_tool.py
from typing import Any, Dict
from .base import MCPTool, ToolResult

class EchoTool(MCPTool):
    @property
    def name(self) -> str:
        return "echo"
    
    @property
    def description(self) -> str:
        return "Echo back the input message"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Message to echo back"
                }
            },
            "required": ["message"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        message = arguments.get("message", "")
        return ToolResult(message=f"Echo: {message}")
```

### 步骤 5: 实现工具注册表

```python
# src/my_mcp/tools/registry.py
import logging
from typing import Dict, List
from mcp.types import Tool
from .base import MCPTool, ToolResult
from .example_tool import EchoTool

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self, workspace):
        self.workspace = workspace
        self.tools: Dict[str, MCPTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        tools = [
            EchoTool(self.workspace),
        ]
        
        for tool in tools:
            self.register_tool(tool)
        
        logger.info(f"Registered {len(self.tools)} tools")
    
    def register_tool(self, tool: MCPTool):
        self.tools[tool.name] = tool
    
    def get_tools(self) -> List[Tool]:
        return [tool.to_mcp_tool() for tool in self.tools.values()]
    
    async def execute_tool(self, name: str, arguments: Dict) -> ToolResult:
        if name not in self.tools:
            raise ValueError(f"Unknown tool '{name}'")
        
        tool = self.tools[name]
        return await tool.execute(arguments)
```

### 步骤 6: 创建工作空间适配器

```python
# src/my_mcp/adapters/workspace.py
from pathlib import Path

class WorkspaceAdapter:
    def __init__(self, workspace_path: str, config=None):
        self.workspace_path = Path(workspace_path).resolve()
        self.config = config or {}
    
    def get_workspace_info(self):
        return {
            "path": str(self.workspace_path),
            "exists": self.workspace_path.exists(),
            "is_dir": self.workspace_path.is_dir(),
        }
```

### 步骤 7: 实现 MCP 服务器

```python
# src/my_mcp/server.py
import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from mcp import stdio_server
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    ServerCapabilities,
    ToolsCapability,
    Tool,
    TextContent,
)

from .tools.registry import ToolRegistry
from .adapters.workspace import WorkspaceAdapter
from .utils.config import Config

logger = logging.getLogger(__name__)

# 创建全局服务器实例
server = Server("moatless-tools")

# 全局状态
workspace_adapter: Optional[WorkspaceAdapter] = None
tool_registry: Optional[ToolRegistry] = None

async def init_server(workspace_path: str) -> None:
    """初始化服务器和工作空间"""
    global workspace_adapter, tool_registry
    
    config = Config()
    workspace_adapter = WorkspaceAdapter(workspace_path, config)
    
    # 向量索引现在是按需构建的
    logger.info("Server initialized with on-demand vector index building")
    
    tool_registry = ToolRegistry(workspace_adapter)
    
    logger.info(f"🚀 Initialized Moatless MCP Server with workspace: {workspace_path}")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """列出可用工具"""
    if not tool_registry:
        raise RuntimeError("Server not initialized")
    
    tools = tool_registry.get_tools()
    logger.debug(f"Listed {len(tools)} tools")
    
    return tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None = None) -> list[TextContent]:
    """执行工具调用"""
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
        
        # 添加任何额外属性作为文本
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
    """主入口点"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(
        description="Moatless MCP Server with Enhanced Semantic Search"
    )
    parser.add_argument(
        "--workspace", 
        type=str, 
        default=".", 
        help="工作空间目录路径 (默认: 当前目录)"
    )
    parser.add_argument(
        "--jina-api-key",
        type=str,
        help="Jina AI API 密钥用于嵌入 (启用基于向量的语义搜索)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="启用调试日志"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 设置 API 密钥
    import os
    if args.jina_api_key:
        os.environ["JINA_API_KEY"] = args.jina_api_key
        logger.info("🔑 Jina AI API key configured for vector-based semantic search")
    elif not os.getenv("JINA_API_KEY"):
        logger.warning("⚠️  No API key provided. Will use keyword-based search fallback.")
        logger.info("   💡 For enhanced semantic search, use: --jina-api-key 'your-key'")
    
    # 验证工作空间路径
    workspace_path = Path(args.workspace).resolve()
    if not workspace_path.exists():
        logger.error(f"Workspace path does not exist: {workspace_path}")
        sys.exit(1)
    
    logger.info(f"🔧 Starting Moatless MCP Server with workspace: {workspace_path}")
    
    # 初始化服务器
    try:
        await init_server(str(workspace_path))
        logger.info("💡 Use 'build_vector_index' tool to create semantic search index when needed")
    except Exception as e:
        logger.error(f"❌ Failed to initialize server: {e}")
        sys.exit(1)
    
    try:
        # 运行 MCP 服务器
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
    """命令行执行入口点"""
    asyncio.run(main())

if __name__ == "__main__":
    run_server()
```

### 步骤 8: 安装和测试

```bash
# 安装开发模式
pip install -e .

# 测试运行
my-mcp-server --workspace .

# 在另一个终端测试 (需要 MCP 客户端)
# 或使用 Claude Desktop 配置文件
```

### 步骤 9: 客户端配置

**Claude Desktop 配置** (`~/.claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "my-mcp-server": {
      "command": "my-mcp-server",
      "args": ["--workspace", "/path/to/your/project"]
    }
  }
}
```

### 步骤 10: 扩展功能

1. **添加更多工具**: 实现 `MCPTool` 子类
2. **添加资源**: 实现 MCP 资源提供者
3. **添加提示**: 实现 MCP 提示模板
4. **添加配置**: 扩展配置系统
5. **添加测试**: 编写单元测试和集成测试

## 🔍 关键技术特性

### 1. 语义搜索实现
- **向量嵌入**: 使用 Jina AI 1024 维嵌入 (推荐) 或 OpenAI 嵌入 (已弃用)
- **按需构建**: 向量索引仅在需要时通过 `build_vector_index` 工具构建
- **代码分割**: 基于 Moatless 库的智能代码块分割
- **相似性搜索**: FAISS 向量数据库实现高效搜索
- **混合搜索**: 语义搜索 + 关键字回退机制
- **索引管理**: 支持索引状态查询和清理操作

### 2. 改进的安全模型
- **更宽松的文件访问**: 支持更多文件类型和隐藏文件
- **智能路径过滤**: 仅禁止核心敏感目录 (`node_modules`, `.venv`, `__pycache__` 等)
- **版本控制友好**: 允许访问 `.git` 和其他版本控制文件
- **文件大小限制**: 防止内存耗尽 (默认 10MB)
- **扩展名检查**: 支持编程语言、配置文件、文档等多种类型

### 3. 性能和可靠性优化
- **全异步架构**: 基于 asyncio 的高性能实现
- **按需加载**: 向量索引按需构建，避免启动延迟
- **错误处理**: 完善的异常捕获和错误恢复机制
- **详细日志**: 结构化日志输出，支持调试模式
- **工具验证**: 输入参数验证和类型检查
- **缓存机制**: 文件内容智能缓存

### 4. 工具生态系统

**文件操作工具**:
- `read_file`: 支持行范围读取的文件读取
- `write_file`: 安全的文件写入操作
- `list_files`: 目录内容列举
- `string_replace`: 智能字符串替换

**搜索和发现工具**:
- `grep`: 正则表达式文本搜索
- `find_files`: 文件名模式匹配
- `find_class`: 类定义查找
- `find_function`: 函数定义查找
- `semantic_search`: 基于语义的代码搜索

**向量数据库工具**:
- `build_vector_index`: 构建语义搜索索引
- `vector_index_status`: 查询索引状态
- `clear_vector_index`: 清理索引数据

**工作空间工具**:
- `workspace_info`: 工作空间信息概览
- `view_code`: 代码段查看
- `run_tests`: 测试执行 (如果可用)

## 🧪 测试和开发

### 运行测试
```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_server.py -v

# 测试覆盖率
pytest tests/ --cov=moatless_mcp --cov-report=html
```

### 代码质量
```bash
# 代码格式化
black src/ tests/

# 代码检查
ruff check src/ tests/

# 类型检查
mypy src/
```

### 调试模式
```bash
# 启用调试日志
moatless-mcp-server --workspace /path/to/project --debug
```

## 📚 使用示例

### 基础文件操作
```python
# 读取文件
{
  "tool": "read_file",
  "arguments": {
    "file_path": "src/main.py",
    "start_line": 1,
    "end_line": 50
  }
}

# 写入文件
{
  "tool": "write_file",
  "arguments": {
    "file_path": "src/new_feature.py",
    "content": "def new_function():\n    pass"
  }
}
```

### 语义搜索
```python
# 搜索认证相关代码
{
  "tool": "semantic_search",
  "arguments": {
    "query": "user authentication and login validation",
    "max_results": 5,
    "category": "implementation"
  }
}
```

### 代码结构分析
```python
# 查找类定义
{
  "tool": "find_class",
  "arguments": {
    "class_name": "UserManager",
    "file_pattern": "*.py"
  }
}

# 查找函数定义
{
  "tool": "find_function",
  "arguments": {
    "function_name": "authenticate_user"
  }
}
```

## 🔧 配置选项

### 环境变量
```bash
# API 密钥配置
export JINA_API_KEY="your-jina-api-key"          # 推荐使用
export OPENAI_API_KEY="your-openai-api-key"      # 已弃用，仍支持

# 服务器配置
export MOATLESS_MAX_FILE_SIZE=10485760           # 最大文件大小 (10MB)
export MOATLESS_MAX_SEARCH_RESULTS=100           # 最大搜索结果数
export MOATLESS_SEARCH_TIMEOUT=30                # 搜索超时 (秒)

# 安全配置
export MOATLESS_ALLOW_HIDDEN_FILES=true          # 允许访问隐藏文件
export MOATLESS_ALLOW_VERSION_CONTROL=true       # 允许访问版本控制文件
```

### 命令行选项
```bash
# 基础启动 (向量索引按需构建)
moatless-mcp-server --workspace /path/to/project

# 使用 Jina AI API 密钥启用语义搜索
moatless-mcp-server --workspace . --jina-api-key "your-key"

# 调试模式
moatless-mcp-server --workspace . --debug

# 组合使用
moatless-mcp-server --workspace /path/to/project --jina-api-key "your-key" --debug
```

### 按需向量索引构建

与之前的版本不同，现在的实现采用按需构建向量索引的策略：

- **启动时**: 服务器快速启动，不预先构建向量索引
- **首次使用**: 当需要语义搜索时，使用 `build_vector_index` 工具构建索引
- **性能优化**: 避免不必要的启动延迟，仅在实际需要时构建索引

```bash
# 服务器启动后，在 AI 客户端中使用以下工具构建索引
{
  "tool": "build_vector_index",
  "arguments": {
    "force_rebuild": false
  }
}
```

## 🤝 贡献指南

1. **Fork** 本仓库
2. **创建功能分支**: `git checkout -b feature/new-feature`
3. **提交更改**: `git commit -am 'Add new feature'`
4. **推送分支**: `git push origin feature/new-feature`
5. **创建 Pull Request**

### 开发规范
- 遵循 PEP 8 代码风格
- 编写单元测试
- 更新文档
- 确保类型注解完整

## 📖 相关文档

- **[MCP 规范](https://spec.modelcontextprotocol.io/)** - 官方 MCP 协议规范
- **[Moatless Tools](https://github.com/aorwall/moatless-tools)** - 底层语义搜索库
- **[Tree-sitter](https://tree-sitter.github.io/tree-sitter/)** - 代码解析器
- **[FAISS](https://faiss.ai/)** - 向量相似性搜索

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

本项目基于以下优秀的开源项目：
- [Moatless Tools](https://github.com/aorwall/moatless-tools) - 语义搜索核心
- [Model Context Protocol](https://modelcontextprotocol.io/) - 协议标准
- [Tree-sitter](https://tree-sitter.github.io/) - 代码解析
- [FAISS](https://faiss.ai/) - 向量搜索引擎