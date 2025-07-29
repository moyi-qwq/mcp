# Moatless MCP Server: Deployment and Development Guide

This document provides detailed instructions for deploying the Moatless MCP Server and for extending its functionality by adding new tools.

## 部署指南 (Deployment Guide)

Follow these steps to install and run the MCP server on your local machine.

### 步骤 1: 环境准备 (Prerequisites)

-   Python 3.10 or higher.
-   Git command-line tools.

### 步骤 2: 克隆并安装 (Clone and Install)

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/your-username/Industrial_Software_MCP.git
    cd Industrial_Software_MCP
    ```

2.  **创建并激活虚拟环境** (推荐):
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    # On Windows, use: venv\Scripts\activate
    ```

3.  **安装项目及其依赖**:
    `pyproject.toml`文件定义了所有必需的依赖。使用pip以“可编辑”模式进行安装。这也会将`Industrial_Software_MCP`命令安装到你���环境中。
    ```bash
    pip install -e .
    ```

### 步骤 3: 运行服务器 (Run the Server)

安装完成后，你可以使用以下命令启动服务器：

```bash
Industrial_Software_MCP --workspace /path/to/your/target/project
```

-   `--workspace`: **必需参数**。指定服务器应该管理的项目目录的绝对或相对路径。
-   `--jina-api-key`: (可选) 提供Jina AI的API密钥以启用语义搜索功能。
-   `--debug`: (可选) 启用详细的调试日志输出。

服务器将在标准输入/输出(stdio)上运行，等待MCP客户端的连接。

### 步骤 4: 配置MCP客户端 (Client Configuration)

你需要一个MCP客户端来与服务器交互，例如Claude Desktop或`cline`。以下是如何为`cline`配置的示例：

1.  找到`cline`的`mcp_settings.json`文件。通常位于：
    -   Linux/macOS: `~/.vscode-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`

2.  编辑该文件，添加或更新服务器配置：
    ```json
    {
      "mcpServers": {
        "moatless": {
          "command": "/path/to/your/venv/bin/Industrial_Software_MCP",
          "args": [
            "--workspace",
            "${workspaceFolder}"
          ],
          "transportType": "stdio"
        }
      }
    }
    ```
    -   将`command`路径替换为你虚拟环境中的`Industrial_Software_MCP`可执行文件的绝对路径。
    -   `${workspaceFolder}`是一个变量，`cline`会自动替换为当前在VS Code中打开的项目路径。

3.  重启VS Code，现在`cline`应该能够连接到并使用你的MCP服务器了。

---

## 开发指南：添加新工具 (Developer Guide: Adding a New Tool)

扩展此服务器功能的核心方式是添加新的工具。

### 工具的构成

一个工具由两部分组成：
1.  **工具实现**: 一个继承自`MCPTool`的Python类，定义了工具的逻辑。
2.  **工具注册**: 在`ToolRegistry`中将工具实例化，使其对服务器可用。

### 步骤 1: 创建工具文件

在`src/moatless_mcp/tools/`目录下创建一个新的Python文件，例如`my_new_tool.py`。

### 步骤 2: 实现工具类

在`my_new_tool.py`中，定义你的工具类。它必须继承自`MCPTool`并实现其抽象方法。

**示例: `EchoTool`**
这是一个简单的示例，它会回应收到的消息。

```python
# src/moatless_mcp/tools/my_new_tool.py

from typing import Any, Dict
from .base import MCPTool, ToolResult

class EchoTool(MCPTool):
    @property
    def name(self) -> str:
        # 工具的唯一名称，客户端将使用此名称调用它
        return "echo"

    @property
    def description(self) -> str:
        # 工具功能的简短描述
        return "Echoes back the input message provided by the user."

    @property
    def input_schema(self) -> Dict[str, Any]:
        # 定义工具期望的输入参数，使用JSON Schema格式
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to be echoed back."
                }
            },
            "required": ["message"]
        }

    async def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        # 工具的核心逻辑
        # 'arguments' 是一个包含已验证输入参数的字典
        self.workspace.get_workspace_info() # 可以通过 self.workspace 访问工作区

        message = arguments.get("message", "No message provided.")
        
        # 返回一个ToolResult对象
        return ToolResult(message=f"The server echoes: {message}")

```

### 步骤 3: 注册新工具

要让服务器知道你的新工具，你必须在`ToolRegistry`中注册它。

1.  打开 `src/moatless_mcp/tools/registry.py`。
2.  导入你的新工具类。
3.  在`_register_default_tools`方法中，将你的工具实例化并添加到`tools`列表中。

```python
# src/moatless_mcp/tools/registry.py

import logging
from typing import Dict, List

from mcp.types import Tool

# ... 其他工具的导入 ...
from moatless_mcp.tools.file_operations import ReadFileTool # (示例)
# 1. 导入你的新工具
from moatless_mcp.tools.my_new_tool import EchoTool

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self, workspace):
        self.workspace = workspace
        self.tools: Dict[str, MCPTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        """Register all default tools"""
        
        tools = [
            # ... 所有现有工具 ...
            ReadFileTool(self.workspace),
            
            # 2. 将你的新工具实例添加到列表中
            EchoTool(self.workspace),
        ]
        
        for tool in tools:
            self.register_tool(tool)
        
        logger.info(f"Registered {len(self.tools)} tools")

    # ... 其余代码 ...
```

### 步骤 4: 测试

重启MCP服务器。它现在会自动加载你的新工具。你可以通过客户端（如`cline`）调用它：

`@mcp-moatless(echo): {"message": "Hello World"}`

或者，如果你正在编写测试，可以为你的新工具添加单元测试到`tests/`目录中，以确保其行为符合预期。
