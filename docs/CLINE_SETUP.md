# Cline 部署指南

## 在 VS Code Cline 扩展中部署 Moatless MCP Server

### 前提条件

1. 安装 VS Code
2. 安装 Cline 扩展
3. Python 3.10+ 环境

### 步骤 1: 安装 MCP Server

```bash
# 克隆或进入项目目录
cd moatless-mcp-server

# 安装服务器
pip install -e .

# 验证安装
moatless-mcp-server --help
```

### 步骤 1.5: 准备 OpenAI API 密钥（用于语义搜索）

为了使用增强的语义搜索功能，您需要 OpenAI API 密钥：

1. 在 [OpenAI 平台](https://platform.openai.com/) 创建账户
2. 生成 API 密钥
3. 在配置中使用该密钥（见下面的步骤）

> **注意**: 如果没有 API 密钥，服务器将自动降级到关键词搜索模式。

### 步骤 2: 配置 VS Code Settings

#### 方法 A: 通过 Cline MCP 设置界面

1. 打开 VS Code
2. 打开 Cline 扩展 (侧边栏或 Ctrl/Cmd + Shift + P 搜索 "Cline")
3. 在 Cline 界面中点击设置按钮 (齿轮图标)
4. 选择 "MCP Servers" 
5. 点击 "Add Server" 添加新的 MCP 服务器
6. 填写以下配置：

```
Server Name: moatless
Command: moatless-mcp-server
Args: --workspace ${workspaceFolder} --openai-api-key YOUR_API_KEY_HERE
Transport Type: stdio
Timeout: 60
```

#### 方法 B: 直接编辑 MCP 设置文件

直接编辑 Cline 的 MCP 设置文件：
`~/.vscode-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json`

添加以下配置：

```json
{
  "mcpServers": {
    "moatless": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "command": "moatless-mcp-server",
      "args": [
        "--workspace",
        "${workspaceFolder}",
        "--openai-api-key",
        "YOUR_API_KEY_HERE"
      ],
      "transportType": "stdio",
      "alwaysAllow": []
    }
  }
}
```

### 步骤 3: 项目特定配置（可选）

如果您想为特定项目配置不同的设置，可以在项目根目录创建 `.vscode/settings.json`：

```json
{
  "cline.mcpServers": {
    "moatless": {
      "command": "moatless-mcp-server",
      "args": [
        "--workspace", "${workspaceFolder}",
        "--openai-api-key", "YOUR_API_KEY_HERE"
      ],
      "env": {
        "MOATLESS_MAX_FILE_SIZE": "5242880",
        "MOATLESS_MAX_SEARCH_RESULTS": "50"
      }
    }
  }
}
```

### 步骤 4: 重启 VS Code

配置完成后，重启 VS Code 以加载新的 MCP 服务器配置。

### 步骤 5: 验证配置

1. 打开一个项目文件夹
2. 启动 Cline (通过命令面板或侧边栏)
3. 在 Cline 中输入测试命令，例如：
   ```
   请使用 workspace_info 工具查看当前项目信息
   ```

### 可用工具

配置成功后，您可以在 Cline 中使用以下工具：

#### 文件操作
- `read_file`: 读取文件内容
- `write_file`: 写入文件
- `list_files`: 列出文件
- `string_replace`: 字符串替换

#### 搜索功能
- `grep`: 搜索文件内容
- `find_files`: 查找文件
- `workspace_info`: 工作空间信息

### 使用示例

#### 1. 探索项目结构
```
请使用 workspace_info 获取项目信息，然后用 list_files 递归列出所有 Python 文件
```

#### 2. 代码搜索
```
使用 grep 工具搜索所有包含 "def main" 的 Python 文件
```

#### 3. 文件操作
```
读取 src/main.py 文件的前 20 行内容
```

#### 4. 代码修改
```
在 config.py 文件中将 debug_mode = True 替换为 debug_mode = False
```

### 故障排除

#### 问题：工具未显示
- 确保 MCP 服务器已正确安装：`moatless-mcp-server --help`
- 检查 VS Code 设置中的配置是否正确
- 重启 VS Code 和 Cline 扩展

#### 问题：权限错误
- 确保工作空间路径存在且可访问
- 检查文件权限设置

#### 问题：文件大小限制
- 调整 `MOATLESS_MAX_FILE_SIZE` 环境变量
- 使用行范围参数读取大文件

### 高级配置

#### 多项目配置
```json
{
  "cline.mcpServers": {
    "moatless-python": {
      "command": "moatless-mcp-server",
      "args": ["--workspace", "${workspaceFolder}"],
      "env": {
        "MOATLESS_MAX_FILE_SIZE": "10485760"
      }
    },
    "moatless-large": {
      "command": "moatless-mcp-server", 
      "args": ["--workspace", "${workspaceFolder}"],
      "env": {
        "MOATLESS_MAX_FILE_SIZE": "52428800",
        "MOATLESS_MAX_SEARCH_RESULTS": "200"
      }
    }
  }
}
```

#### 调试模式
```json
{
  "cline.mcpServers": {
    "moatless": {
      "command": "moatless-mcp-server",
      "args": ["--workspace", "${workspaceFolder}", "--debug"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  }
}
```

### 性能优化建议

1. **设置合适的文件大小限制**：根据项目需要调整 `MOATLESS_MAX_FILE_SIZE`
2. **限制搜索结果**：使用 `max_results` 参数避免过多结果
3. **使用文件模式**：在搜索时指定文件类型（如 `*.py`）
4. **项目特定配置**：为不同类型的项目使用不同的配置