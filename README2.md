# MCP 服务器开发完整指南

[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

从零开始构建 MCP (Model Context Protocol) 服务器的完整指南，专注 Python 实现，简单易懂，涵盖所有核心要点。

## 📖 目录

- [🎯 MCP 基础](#-mcp-基础)
- [🚀 快速开始](#-快速开始)
- [🏗️ 架构设计](#️-架构设计)
- [🛠️ 开发步骤](#️-开发步骤)
- [🔧 实战示例](#-实战示例)
- [🚀 部署配置](#-部署配置)

## 🎯 MCP 基础

### 什么是 MCP
MCP 是连接 AI 和外部系统的标准协议，让 AI 助手能够：

```
🤖 AI 客户端 ←→ 📡 MCP 服务器 ←→ 💾 你的系统/数据
```

- **工具 (Tools)** - AI 可以调用的功能
- **资源 (Resources)** - AI 可以读取的数据
- **提示 (Prompts)** - AI 可以使用的模板

### 为什么选择 Python
- **官方支持** - Anthropic 提供完整的 Python SDK
- **丰富生态** - 海量第三方库和工具
- **简单易用** - 语法简洁，开发效率高
- **异步支持** - 原生支持 async/await

## 🚀 快速开始

**1. 安装依赖**
```bash
pip install mcp pydantic
```

**2. 最简服务器**
```python
# server.py
from mcp.server import Server
from mcp.types import Tool, Resource, Prompt, TextContent
import asyncio

server = Server("my-mcp-server")

# 工具：执行操作
@server.list_tools()
async def list_tools():
    return [Tool(
        name="echo",
        description="Echo back a message",
        inputSchema={
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"]
        }
    )]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "echo":
        return [TextContent(type="text", text=f"Echo: {arguments['message']}")]

# 资源：提供数据
@server.list_resources()
async def list_resources():
    return [Resource(
        uri="config://settings",
        name="Server Settings",
        mimeType="application/json"
    )]

@server.read_resource()
async def read_resource(uri: str):
    if uri == "config://settings":
        return '{"version": "1.0", "debug": false}'

# 提示：模板化内容
@server.list_prompts()
async def list_prompts():
    return [Prompt(
        name="analyze",
        description="Analyze code or text"
    )]

@server.get_prompt()
async def get_prompt(name: str, arguments: dict):
    if name == "analyze":
        return "Please analyze the following content and provide insights."

if __name__ == "__main__":
    asyncio.run(server.run())
```

**3. 运行测试**
```bash
python server.py
```

## 🏗️ 架构设计

### 核心组件

```
MCP 服务器架构
├── 🔧 服务器核心 - MCP 协议的核心实现，负责与客户端的所有通信和消息处理
│   ├── 协议处理 - 实现 JSON-RPC 协议解析，确保与 MCP 客户端的标准化通信
│   ├── 消息路由 - 将客户端请求智能分发到对应的工具、资源或提示处理器
│   └── 生命周期 - 管理服务器从启动到关闭的完整生命周期和状态转换
│
├── 🛠️ 工具系统 - 管理所有可调用功能，为 AI 提供执行各种操作的能力
│   ├── 工具注册 - 动态注册和管理工具，支持运行时添加新功能而无需重启
│   ├── 参数验证 - 使用 JSON Schema 严格验证工具参数，确保类型安全和数据完整性
│   └── 安全执行 - 提供错误处理和异常捕获，防止单个工具故障影响整个服务器
│
├── 📚 资源系统 - 提供统一的数据访问接口，让 AI 能够读取各种数据源
│   ├── 数据提供 - 支持文件、API、数据库等多种数据源的统一访问接口
│   ├── URI 路由 - 通过唯一资源标识符精确定位和访问特定的数据资源
│   └── 缓存机制 - 智能缓存频繁访问的资源，显著提升数据读取性能
│
└── 🎯 提示系统 - 管理可重用的提示模板，帮助 AI 生成结构化和定制化的内容
    ├── 模板管理 - 存储和组织各类提示模板，支持模块化和可重用的提示设计
    ├── 参数注入 - 将动态数据无缝注入到静态模板中，生成个性化的提示内容
    └── 条件逻辑 - 支持基于输入条件的智能提示生成和分支逻辑处理
```

### 设计原则
- **模块化** - 每个组件职责单一
- **可扩展** - 插件化架构
- **异步** - 全异步处理
- **类型安全** - 强类型系统

## 🛠️ 开发步骤

### 第1步：项目初始化

**Python 项目**
```bash
mkdir my-mcp-server && cd my-mcp-server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install mcp pydantic aiofiles

# 项目结构
mkdir -p src/my_mcp/{tools,resources,prompts}
touch src/my_mcp/{__init__.py,server.py}
touch pyproject.toml
```

**pyproject.toml**
```toml
[project]
name = "my-mcp-server"
version = "0.1.0"
dependencies = ["mcp>=1.0.0", "pydantic>=2.0.0"]

[project.scripts]
my-mcp-server = "my_mcp.server:main"
```

### 第2步：工具开发

**基础工具类**
```python
# src/my_mcp/tools/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @property
    @abstractmethod
    def description(self) -> str: pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]: pass
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Any: pass
```

**示例工具**
```python
# src/my_mcp/tools/calculator.py
class CalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculate"
    
    @property
    def description(self) -> str:
        return "Perform basic calculations"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "operation": {"type": "string", "enum": ["+", "-", "*", "/"]}
            },
            "required": ["a", "b", "operation"]
        }
    
    async def execute(self, arguments: Dict[str, Any]) -> float:
        a, b, op = arguments['a'], arguments['b'], arguments['operation']
        if op == "+": return a + b
        elif op == "-": return a - b
        elif op == "*": return a * b
        elif op == "/": return a / b if b != 0 else None
```

### 第3步：资源管理

**资源基类**
```python
# src/my_mcp/resources/base.py
class BaseResource(ABC):
    @property
    @abstractmethod
    def uri(self) -> str: pass
    
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @property
    @abstractmethod
    def mime_type(self) -> str: pass
    
    @abstractmethod
    async def read(self) -> str: pass
```

**示例资源**
```python
# 文件资源
class FileResource(BaseResource):
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    @property
    def uri(self) -> str:
        return f"file://{self.file_path}"
    
    async def read(self) -> str:
        with open(self.file_path, 'r') as f:
            return f.read()

# API 资源
class APIResource(BaseResource):
    def __init__(self, url: str):
        self.url = url
    
    async def read(self) -> str:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                return await response.text()
```

### 第4步：提示模板

**提示基类**
```python
# src/my_mcp/prompts/base.py
from jinja2 import Template

class BasePrompt(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @abstractmethod
    async def render(self, arguments: Dict[str, Any]) -> str: pass

class TemplatePrompt(BasePrompt):
    def __init__(self, name: str, template: str):
        self._name = name
        self.template = Template(template)
    
    @property
    def name(self) -> str:
        return self._name
    
    async def render(self, arguments: Dict[str, Any]) -> str:
        return self.template.render(**arguments)
```

### 第5步：服务器集成

**完整服务器**
```python
# src/my_mcp/server.py
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability

class MCPServer:
    def __init__(self, name: str):
        self.server = Server(name)
        self.tools = {}
        self.resources = {}
        self.prompts = {}
        self._setup_handlers()
    
    def register_tool(self, tool: BaseTool):
        self.tools[tool.name] = tool
    
    def register_resource(self, resource: BaseResource):
        self.resources[resource.uri] = resource
    
    def register_prompt(self, prompt: BasePrompt):
        self.prompts[prompt.name] = prompt
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools():
            return [self._tool_to_mcp(tool) for tool in self.tools.values()]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            tool = self.tools[name]
            result = await tool.execute(arguments)
            return [{"type": "text", "text": str(result)}]
        
        # 类似地设置资源和提示处理器...
    
    async def run(self):
        from mcp.server.stdio import stdio_server
        async with stdio_server() as streams:
            await self.server.run(*streams, InitializationOptions(
                server_name="my-mcp-server",
                server_version="1.0.0",
                capabilities=ServerCapabilities(tools=ToolsCapability())
            ))

def main():
    server = MCPServer("my-mcp-server")
    
    # 注册组件
    server.register_tool(CalculatorTool())
    server.register_resource(FileResource("config.json"))
    
    # 运行
    asyncio.run(server.run())
```

## 🔧 实战示例

### 文件管理服务器
```python
# 集成文件操作的完整示例
class FileManagerServer(MCPServer):
    def __init__(self, workspace: str):
        super().__init__("file-manager")
        self.workspace = Path(workspace)
        self._setup_file_tools()
    
    def _setup_file_tools(self):
        # 注册文件操作工具
        self.register_tool(ReadFileTool(self.workspace))
        self.register_tool(WriteFileTool(self.workspace))
        self.register_tool(ListFilesTool(self.workspace))
        
        # 注册工作空间资源
        for file in self.workspace.glob("*.json"):
            self.register_resource(FileResource(str(file)))

# 使用示例
if __name__ == "__main__":
    server = FileManagerServer("/path/to/workspace")
    asyncio.run(server.run())
```

### 数据库查询服务器
```python
class DatabaseServer(MCPServer):
    def __init__(self, db_url: str):
        super().__init__("database-server")
        self.db_url = db_url
        self._setup_db_tools()
    
    def _setup_db_tools(self):
        self.register_tool(QueryTool(self.db_url))
        self.register_resource(SchemaResource(self.db_url))
        self.register_prompt(SQLPrompt())
```

## 🚀 部署配置

### 客户端配置

**Claude Desktop** (`~/.claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["-m", "my_mcp.server"],
      "env": {
        "DEBUG": "true"
      }
    }
  }
}
```

**VS Code Cline** (`.vscode/settings.json`)
```json
{
  "cline.mcpServers": {
    "my-server": {
      "command": "my-mcp-server",
      "args": ["--workspace", "${workspaceFolder}"]
    }
  }
}
```

### 环境配置
```bash
# 环境变量
export MCP_DEBUG=true
export MCP_LOG_LEVEL=INFO
export MCP_TIMEOUT=30

# 启动选项
my-mcp-server --workspace . --debug --port 8000
```

### Docker 部署
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "my_mcp.server"]
```

### 开发技巧

1. **渐进开发** - 从一个工具开始，逐步添加功能
2. **测试驱动** - 先写测试，确保功能正常
3. **错误处理** - 优雅处理所有异常情况
4. **性能优化** - 使用异步和缓存
5. **安全考虑** - 验证输入，限制权限
6. **文档完善** - 为每个工具写清楚的描述

### 常见问题

**Q: 如何调试 MCP 服务器？**
A: 使用 `--debug` 标志启用详细日志，或在代码中添加 `logging` 输出。

**Q: 工具参数验证失败怎么办？**
A: 检查 `input_schema` 是否正确，使用 JSON Schema 验证器测试。

**Q: 如何处理大文件资源？**
A: 实现流式读取，添加大小限制，使用缓存策略。

**Q: 多个客户端可以连接同一个服务器吗？**
A: MCP 设计为一对一连接，每个客户端需要独立的服务器实例。

---

🎉 **恭喜！** 你现在掌握了 MCP 服务器开发的完整知识。从简单的 echo 服务器到复杂的企业级应用，这个指南涵盖了所有必要的概念和实践。开始构建你的第一个 MCP 服务器吧！