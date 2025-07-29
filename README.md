# Moatless MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/protocol-MCP-green.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个基于模型上下文协议 (MCP) 的高级代码分析和编辑服务器，支持基于向量嵌入的语义搜索功能。该服务器为 AI 助手提供了通过标准化接口执行复杂代码操作的能力。

## 核心架构：模型上下文协议 (MCP)

本服务器是一个**MCP服务器**的实现。MCP是一个开放协议，旨在成为语言模型（LLM）与外部工具和数据源之间的标准中间件。它允许像IDE或聊天应用这样的客户端（MCP客户端）安全、动态地与服务器提供的能力（如文件系统访问、代码分析）进行交互。

### 架构流程

当一个MCP客户端（如Claude Desktop或`cline`）连接到本服务器时，其交互遵循以下流程：

```
+------------------+     1. Request (e.g., call_tool)     +-----------------------+
|   MCP Client     | -----------------------------------> |     MCP Server        |
| (IDE, cline etc.)|                                      |     (This Project)    |
+------------------+     6. Response (JSON-RPC)           +-----------+-----------+
        ^          <-----------------------------------          | 2. Dispatch
        |                                                        |
        |                                                        v
        |                                              +-----------------------+
        |                                              |     Tool Registry     |
        |                                              +-----------+-----------+
        |                                                        | 3. Execute Tool
        |                                                        |
        |                                                        v
        |                                              +-----------------------+
        |                                              |      Specific Tool    |
        |                                              | (e.g., ReadFileTool)  |
        |                                              +-----------+-----------+
        |                                                        | 4. Access Data
        |                                                        |
        |   +----------------------------------------------------+
        |   |
        v   v
+-----------------------+     5. Return Data/Result      +-----------------------+
|     Workspace         | <----------------------------- |    Workspace Adapter  |
| (File System, .git)   |                                | (Manages Project State) |
+-----------------------+                                +-----------------------+

```

1.  **请求(Request)**: 客户端向服务器发送一个JSON-RPC请求，例如`tool_run`，要求执行一个名为`read_file`的工具。
2.  **分发(Dispatch)**: `server.py`中的MCP服务器核心接收请求，并将其分派给`ToolRegistry`。
3.  **执行(Execute)**: `ToolRegistry`找到名为`read_file`的已注册工具实例，并调用其`execute`方法。
4.  **数据访问(Access Data)**: 工具通过`WorkspaceAdapter`请求访问项目文件。
5.  **返回结果(Return Data)**: `WorkspaceAdapter`从文件系统读取数据并返回给工具。工具将结果包装成`ToolResult`对象。
6.  **响应(Response)**: 服务器核心将`ToolResult`格式化为JSON-RPC响应，并将其发送回客户端。

### 组件详解

-   **Server Core (`server.py`)**:
    -   **职责**: 作为服务器的主入口，监听和响应MCP客户端的连接。
    -   **实现**: 使用`mcp.server`库来处理底层的JSON-RPC通信。它定义了`list_tools`和`call_tool`等协议处理器，并将具体的逻辑委托给`ToolRegistry`。

-   **Tool Registry (`tools/registry.py`)**:
    -   **职责**: 负责工具的生命周期管理。它在启动时实例化所有可用的工具，并将它们存储在一个字典中以便快速访问。
    -   **实现**: `ToolRegistry`类包含一个`_register_default_tools`方法，用于集中注册所有工具。当`execute_tool`被调用时，它会查找并执行相应的工具。

-   **Workspace Adapter (`adapters/workspace.py`)**:
    -   **职责**: 作为文件系统和项目状态的抽象层。所有对项目文件的��、写、搜索操作都必须通过这个适配器进行。
    -   **实现**: `WorkspaceAdapter`类提供了对文件、Git仓库和Moatless语义索引的访问接口，同时强制执行安全策略（如文件类型和路径限制）。

-   **Tools (`tools/*.py`)**:
    -   **职责**: 实现具体的业务逻辑单元。每个工具都是一个独立的类，负责一项特定的任务，如读写文件、代码搜索或运行测试。
    -   **实现**: 所有工具都继承自`MCPTool`基类(`tools/base.py`)，并实现`execute`方法。它们通过构造函数接收`WorkspaceAdapter`的实例来与项目数据交互。

-   **Vector System & Tree-sitter (`vector/`, `treesitter/`)**:
    -   **职责**: 提供高级代码理解能力。Vector System负责将代码转换为向量并进行语义搜索。Tree-sitter用于精确解析代码的语法结构（AST）。
    -   **实现**: 这些模块被高级工具（如`SemanticSearchTool`和`FindClassTool`）所使用，以提供比简单文本匹配更强大的功能。

## 关键技术特性

### 1. 语义搜索实现
- **向量嵌入**: 使用 Jina AI 1024 维嵌入 (推荐) 或 OpenAI 嵌入 (已弃用)。
- **按需构建**: 向量索引仅在需要时通过 `build_vector_index` 工具构建，避免不必要的启动延迟。
- **代码分割**: 基于 Moatless 库的智能代码块分割。
- **相似性搜索**: 使用 FAISS 向量数据库实现高效搜索。

### 2. 灵活的安全模型
- **白名单策略**: 默认允许访问多种常见代码、配置和文档文件类型。
- **智能路径过滤**: 仅禁止核心依赖和缓存目录 (`node_modules`, `.venv`, `__pycache__` 等)。
- **可配置性**: 可以通过`Config`类轻松调整安全设置。

### 3. 模块化和可扩展的工具系统
- **工具基类**: `MCPTool`提供了一个清晰的接口，用于创建新的自定义工具。
- **集中注册**: `ToolRegistry`使得添加和管理新工具变得简单。

## 使用示例

### 基础文件操作
```json
{
  "tool": "read_file",
  "arguments": {
    "file_path": "src/moatless_mcp/server.py",
    "start_line": 1,
    "end_line": 10
  }
}
```

### 语义搜索
```json
{
  "tool": "semantic_search",
  "arguments": {
    "query": "user authentication and login validation",
    "max_results": 5
  }
}
```

### 代码结构分析
```json
{
  "tool": "find_class",
  "arguments": {
    "class_name": "ToolRegistry",
    "file_pattern": "**/registry.py"
  }
}
```

## 部署与开发

关于如何运行此服务器、进行部署以及如何开发和添加新工具的详细说明，请参阅 **[README_deploy.md](README_deploy.md)**。

## 相关文档

- **[MCP 规范](https://spec.modelcontextprotocol.io/)** - 官方 MCP 协议规范
- **[Moatless Tools](https://github.com/aorwall/moatless-tools)** - 底层语义搜索库
- **[Tree-sitter](https://tree-sitter.github.io/tree-sitter/)** - 代码解析器
- **[FAISS](https://faiss.ai/)** - 向量相似性搜索
