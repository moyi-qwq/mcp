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
设置 MCP 服务器的核心组件，包括工作空间管理和工具注册表。这是服务器启动时的必要初始化步骤。

```python
async def init_server(workspace_path: str) -> None:
    global workspace_adapter, tool_registry
    
    config = Config()  # 加载配置，设置安全策略和文件访问权限
    workspace_adapter = WorkspaceAdapter(workspace_path, config)  # 创建工作空间适配器，管理文件操作
    tool_registry = ToolRegistry(workspace_adapter)  # 初始化工具注册表，自动注册所有可用工具
    
    logger.info(f"🚀 Initialized Moatless MCP Server with workspace: {workspace_path}")
```

#### 2. 工具注册机制
自动注册所有可用的 MCP 工具，使 AI 可以调用这些功能。每个工具都封装了特定的操作能力。

```python
def _register_default_tools(self):
    tools = [
        ReadFileTool(self.workspace),        # 文件读取工具，支持按行范围读取
        WriteFileTool(self.workspace),       # 文件写入工具，安全的文件操作
        GrepTool(self.workspace),            # 文本搜索工具，支持正则表达式
        SemanticSearchTool(self.workspace),  # 语义搜索工具，基于 AI 的代码理解
        # ... 更多工具
    ]
    
    for tool in tools:
        self.register_tool(tool)  # 将每个工具注册到系统中，使其可被 AI 调用
```

#### 3. MCP 协议处理
实现 MCP 协议的核心通信机制，处理 AI 客户端的请求并返回结果。这是连接 AI 和工具的桥梁。

```python
@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    # 向 AI 客户端提供所有可用工具的列表和描述
    return tool_registry.get_tools()

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    # 执行 AI 请求的工具，并将结果转换为 MCP 格式返回
    result = await tool_registry.execute_tool(name, arguments)
    return [TextContent(type="text", text=result.message)]
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
定义所有 MCP 工具的基础接口，规范工具的实现方式和数据格式。

```python
class MCPTool(ABC):
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        # 每个工具必须实现的执行方法，定义具体的功能逻辑
        pass
    
    def to_mcp_tool(self) -> Tool:
        # 将工具转换为 MCP 协议所需的标准格式，包含名称、描述和参数要求
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
管理服务器的安全策略和操作限制，确保文件访问的安全性和系统稳定性。

```python
@dataclass
class Config:
    # 文件操作配置，防止内存耗尽和性能问题
    max_file_size: int = 10 * 1024 * 1024  # 10MB 最大文件大小限制
    max_search_results: int = 100  # 限制搜索结果数量，提高响应速度
    
    # 安全设置 - 白名单机制，只允许访问安全的文件类型
    allowed_file_extensions: set = {
        ".py", ".java", ".js", ".ts", ".json", ".md", ".txt", ...  # 支持的文件类型
    }
    
    # 黑名单机制，禁止访问敏感目录和临时文件
    forbidden_paths: set = {
        "node_modules", ".venv", "venv", "__pycache__"  # 常见的敏感目录
    }
    
    def is_file_allowed(self, file_path: Path) -> bool:
        # 综合检查文件访问权限，确保安全性
        pass
```

## 🚀 实现一个 MCP 服务器的详细步骤

### 步骤 1: 项目结构设置
创建模块化的项目结构，将不同功能的代码分类组织，便于维护和扩展。

```bash
mkdir my-mcp-server && cd my-mcp-server  # 创建项目根目录
mkdir -p src/my_mcp/{tools,adapters,utils}  # 创建模块化的源代码结构
touch src/my_mcp/{__init__.py,server.py}  # 初始化 Python 包和主服务器文件
```

### 步骤 2: 创建项目配置 (`pyproject.toml`)
定义项目的依赖关系和打包信息，使项目可以被正确安装和分发。

```toml
[project]
name = "my-mcp-server"  # 项目名称，用于 pip 安装
version = "0.1.0"  # 版本号，遵循语义化版本规范
dependencies = [  # 必需的第三方库
    "mcp>=1.9.0",      # MCP 协议实现库
    "pydantic>=2.0.0", # 数据验证和序列化
    "aiofiles>=23.0.0", # 异步文件操作
]

[project.scripts]
my-mcp-server = "my_mcp.server:run_server"  # 命令行入口点，安装后可直接调用
```

### 步骤 3: 实现基础工具类
创建所有工具的基础类和结果格式，为后续开发各种具体工具提供统一的接口规范。

```python
@dataclass
class ToolResult:
    message: str  # 工具执行结果的文本内容
    success: bool = True  # 执行是否成功的标志

class MCPTool(ABC):  # 抽象基类，定义所有工具必须实现的方法
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        pass  # 每个工具的具体实现逻辑
    
    def to_mcp_tool(self) -> Tool:
        # 将内部工具转换为 MCP 协议所需的标准格式
        return Tool(name=self.name, description=self.description, inputSchema=self.input_schema)
```

### 步骤 4: 创建示例工具
实现一个简单的测试工具，验证整个 MCP 系统的正常工作，也可作为开发其他工具的参考模板。

```python
class EchoTool(MCPTool):  # 继承基础工具类，实现具体功能
    @property
    def name(self) -> str:
        return "echo"  # 工具的唯一标识符，供 AI 调用时使用
    
    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        message = arguments.get("message", "")  # 获取用户输入的消息
        return ToolResult(message=f"Echo: {message}")  # 原样返回消息，用于测试连接
```

### 步骤 5: 实现工具注册表
管理所有可用工具的中心系统，负责工具的注册、查找和执行，是 MCP 服务器的核心组件。

```python
class ToolRegistry:
    def __init__(self, workspace):
        self.tools: Dict[str, MCPTool] = {}  # 存储所有注册的工具
        self._register_default_tools()  # 自动注册默认工具集
    
    def register_tool(self, tool: MCPTool):
        self.tools[tool.name] = tool  # 将工具按名称存储，供后续查找使用
    
    async def execute_tool(self, name: str, arguments: Dict) -> ToolResult:
        tool = self.tools[name]  # 根据名称查找对应工具
        return await tool.execute(arguments)  # 异步执行工具逻辑
```

### 步骤 6: 创建工作空间适配器
管理工作空间目录和文件操作，提供统一的文件系统接口，封装底层的文件操作复杂性。

```python
class WorkspaceAdapter:
    def __init__(self, workspace_path: str, config=None):
        self.workspace_path = Path(workspace_path).resolve()  # 解析为绝对路径，避免路径歧义
        self.config = config or {}  # 加载配置，控制文件访问权限和行为
```

### 步骤 7: 实现 MCP 服务器
组装所有组件，实现完整的 MCP 服务器功能，处理 AI 客户端的连接和调用请求。

```python
server = Server("moatless-tools")  # 创建 MCP 服务器实例

async def init_server(workspace_path: str) -> None:
    # 初始化服务器所需的所有组件
    global workspace_adapter, tool_registry
    config = Config()  # 加载配置
    workspace_adapter = WorkspaceAdapter(workspace_path, config)  # 创建工作空间管理器
    tool_registry = ToolRegistry(workspace_adapter)  # 创建工具注册表

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    # 处理 AI 客户端请求工具列表的请求
    return tool_registry.get_tools()

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    # 处理 AI 客户端调用具体工具的请求
    result = await tool_registry.execute_tool(name, arguments)
    return [TextContent(type="text", text=result.message)]

def run_server():
    asyncio.run(main())  # 启动异步事件循环，开始监听连接
```

### 步骤 8: 安装和测试
安装项目并启动服务器，验证所有组件是否正常工作，为后续的 AI 客户端连接做准备。

```bash
pip install -e .  # 以开发模式安装，支持代码实时更新
my-mcp-server --workspace .  # 启动服务器，使用当前目录作为工作空间
```

### 步骤 9: 客户端配置
配置 AI 客户端连接到你的 MCP 服务器，使 AI 能够发现和使用你提供的工具。

**Claude Desktop 配置** (`~/.claude_desktop_config.json`):
```json
{
  "mcpServers": {  // MCP 服务器配置区域
    "my-mcp-server": {  // 服务器的唯一标识符
      "command": "my-mcp-server",  // 启动命令，对应安装的可执行文件
      "args": ["--workspace", "/path/to/your/project"]  // 命令行参数，指定工作目录
    }
  }
}
```

### 步骤 10: 扩展功能
在基础框架上添加更多高级功能，根据实际需求定制和优化 MCP 服务器。

1. **添加更多工具**: 实现 `MCPTool` 子类，添加文件操作、搜索等具体功能
2. **添加资源**: 实现 MCP 资源提供者，让 AI 可以读取数据库、API 等数据源
3. **添加提示**: 实现 MCP 提示模板，为 AI 提供结构化的内容生成模板
4. **添加配置**: 扩展配置系统，支持更细粒度的权限控制和性能调优
5. **添加测试**: 编写单元测试和集成测试，确保代码质量和稳定性

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
pip install -e ".[dev]"
pytest tests/
```

### 代码质量
```bash
black src/ tests/
ruff check src/ tests/
```

### 调试模式
```bash
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

## 📖 相关文档

- **[MCP 规范](https://spec.modelcontextprotocol.io/)** - 官方 MCP 协议规范
- **[Moatless Tools](https://github.com/aorwall/moatless-tools)** - 底层语义搜索库
- **[Tree-sitter](https://tree-sitter.github.io/tree-sitter/)** - 代码解析器
- **[FAISS](https://faiss.ai/)** - 向量相似性搜索

