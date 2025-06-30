# 从 OpenAI 到 Jina AI 的迁移指南

本指南帮助您将 Moatless MCP Server 从 OpenAI embeddings 迁移到 Jina AI embeddings。

## 🔄 迁移概述

### 主要变化
- **嵌入服务**: OpenAI → Jina AI
- **模型**: `text-embedding-3-small` → `jina-embeddings-v3`
- **维度**: 1536 → 1024
- **API密钥**: `OPENAI_API_KEY` → `JINA_API_KEY`
- **命令行参数**: `--openai-api-key` → `--jina-api-key`

### 迁移优势
- ✅ **更高性能**: Jina AI 专为检索任务优化
- ✅ **更好的多语言支持**: 原生支持多种语言
- ✅ **成本效益**: 更具竞争力的定价
- ✅ **专业化**: 专门为搜索和检索设计

## 📝 迁移步骤

### 1. 获取 Jina AI API 密钥

1. 访问 [Jina AI 官网](https://jina.ai/)
2. 注册账户并获取 API 密钥
3. API 密钥格式: `jina_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 2. 更新环境变量

**替换环境变量:**
```bash
# 旧的 OpenAI 配置
export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 新的 Jina AI 配置
export JINA_API_KEY="jina_1647cb729b454f82ada95dedf18f5fbd_cxKj3hRLTs9MEwqUTxD64W3PbcF"
```

### 3. 更新命令行参数

**启动服务器:**
```bash
# 旧方式
moatless-mcp-server --workspace /path/to/project --openai-api-key "sk-..."

# 新方式
moatless-mcp-server --workspace /path/to/project --jina-api-key "jina_..."
```

### 4. 更新 MCP 客户端配置

#### Claude Desktop 配置

**旧配置 (~/.claude_desktop_config.json):**
```json
{
  "mcpServers": {
    "moatless": {
      "command": "moatless-mcp-server",
      "args": [
        "--workspace", "/path/to/your/project",
        "--openai-api-key", "sk-your-openai-key"
      ]
    }
  }
}
```

**新配置:**
```json
{
  "mcpServers": {
    "moatless": {
      "command": "moatless-mcp-server",
      "args": [
        "--workspace", "/path/to/your/project",
        "--jina-api-key", "jina_your-jina-key"
      ]
    }
  }
}
```

#### Cline 配置

**旧配置:**
```json
{
  "mcpServers": {
    "moatless": {
      "command": "moatless-mcp-server",
      "args": ["--workspace", "${workspaceFolder}", "--openai-api-key", "sk-..."],
      "timeout": 60,
      "transportType": "stdio"
    }
  }
}
```

**新配置:**
```json
{
  "mcpServers": {
    "moatless": {
      "command": "moatless-mcp-server",
      "args": ["--workspace", "${workspaceFolder}", "--jina-api-key", "jina_..."],
      "timeout": 60,
      "transportType": "stdio"
    }
  }
}
```

### 5. 重建索引

由于嵌入维度发生变化（1536 → 1024），需要重建索引：

```bash
# 方法 1: 使用 --rebuild-index 参数
moatless-mcp-server --workspace /path/to/project --jina-api-key "jina_..." --rebuild-index

# 方法 2: 删除旧索引，重新启动
rm -rf .moatless_index/
moatless-mcp-server --workspace /path/to/project --jina-api-key "jina_..."

# 方法 3: 使用 code_index 工具重建
# 在 MCP 客户端中调用:
{
  "tool": "code_index",
  "arguments": {
    "action": "rebuild"
  }
}
```

## 🔧 兼容性说明

### 向后兼容
- ✅ 旧的 `--openai-api-key` 参数仍然支持（但会显示弃用警告）
- ✅ 现有的工具和 API 接口保持不变
- ✅ 搜索语法和结果格式保持一致

### 弃用警告
当使用旧的 OpenAI 配置时，会看到如下警告：
```
⚠️  Using deprecated OpenAI API key. Consider switching to Jina AI with --jina-api-key
```

## 🧪 验证迁移

### 1. 测试 API 连接
```bash
# 测试 Jina AI API 连接
curl -H "Authorization: Bearer jina_your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"model": "jina-embeddings-v3", "task": "retrieval.query", "input": ["test"]}' \
     https://api.jina.ai/v1/embeddings
```

### 2. 运行测试脚本
```bash
# 设置 Jina AI API 密钥
export JINA_API_KEY="jina_your-api-key"

# 运行测试
python test_enhanced_features.py
```

### 3. 检查索引状态
使用 `code_index` 工具检查索引状态：
```json
{
  "tool": "code_index",
  "arguments": {
    "action": "status"
  }
}
```

应该看到:
- ✅ Model: jina-embeddings-v3
- ✅ Dimensions: 1024
- ✅ Index Status: Ready

## 🐛 故障排除

### 常见问题

**1. "JINA_API_KEY environment variable is not set"**
- 确保设置了正确的环境变量
- 检查 API 密钥格式是否正确

**2. "Failed to get embeddings from Jina AI"**
- 验证 API 密钥是否有效
- 检查网络连接
- 确认 API 配额是否足够

**3. "索引初始化失败"**
- 删除旧的 `.moatless_index/` 目录
- 使用 `--rebuild-index` 参数重新启动

**4. "搜索结果质量下降"**
- 重建索引以使用新的嵌入模型
- 调整搜索查询以适应新模型特性

### 回滚到 OpenAI (不推荐)

如果需要临时回滚到 OpenAI:
```bash
# 设置 OpenAI API 密钥
export OPENAI_API_KEY="sk-your-openai-key"

# 删除 Jina AI 密钥
unset JINA_API_KEY

# 重建索引
moatless-mcp-server --workspace /path/to/project --openai-api-key "sk-..." --rebuild-index
```

## 📞 获取帮助

如果在迁移过程中遇到问题:

1. 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. 检查 [BEST_PRACTICES.md](BEST_PRACTICES.md)
3. 运行调试模式: `--debug`
4. 查看日志输出获取详细错误信息

## 🎯 迁移检查清单

- [ ] 获取 Jina AI API 密钥
- [ ] 更新环境变量 (`JINA_API_KEY`)
- [ ] 更新命令行参数 (`--jina-api-key`)
- [ ] 更新 MCP 客户端配置文件
- [ ] 重建代码索引
- [ ] 测试语义搜索功能
- [ ] 验证搜索质量
- [ ] 清理旧的 OpenAI 配置（可选）

---

迁移完成后，您将享受到 Jina AI 提供的更好的搜索性能和多语言支持！ 
 