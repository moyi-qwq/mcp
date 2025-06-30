# Moatless MCP Server 最佳实践指南

本文档提供使用 Moatless MCP Server 的最佳实践建议，帮助您安全、高效地使用该工具。

## 🔒 安全最佳实践

### API 密钥管理

1. **不要将 API 密钥硬编码在配置文件中**
   ```bash
   # ❌ 不推荐：直接在命令行中暴露密钥
   moatless-mcp-server --openai-api-key sk-1234567890abcdef
   
   # ✅ 推荐：使用环境变量
   export OPENAI_API_KEY="sk-1234567890abcdef"
   moatless-mcp-server --workspace /path/to/project
   ```

2. **使用项目特定的配置**
   ```bash
   # 为每个项目创建单独的配置文件
   ~/.config/moatless/project1_config.json
   ~/.config/moatless/project2_config.json
   ```

3. **定期轮换 API 密钥**
   - 至少每 90 天更换一次 API 密钥
   - 如果怀疑密钥泄露，立即更换

### 文件系统安全

1. **限制工作区范围**
   ```bash
   # ✅ 指定具体项目目录
   moatless-mcp-server --workspace /home/user/projects/myproject
   
   # ❌ 避免使用根目录或用户主目录
   moatless-mcp-server --workspace /
   ```

2. **配置 .gitignore**
   在项目根目录添加以下内容到 `.gitignore`：
   ```gitignore
   # Moatless 索引文件
   .moatless_index/
   
   # 配置文件（如果包含密钥）
   moatless_config.json
   claude_desktop_config.json
   ```

## ⚡ 性能最佳实践

### 索引管理

1. **首次设置优化**
   ```bash
   # 第一次运行时使用快速启动
   moatless-mcp-server --workspace /path/to/project --no-index
   
   # 稍后初始化索引
   # 通过 MCP 工具调用 code_index 初始化
   ```

2. **索引维护**
   ```bash
   # 代码变更较多时重建索引
   moatless-mcp-server --workspace /path/to/project --rebuild-index
   ```

3. **内存管理**
   ```bash
   # 对于大型项目，可以调整文件大小限制
   export MOATLESS_MAX_FILE_SIZE=5242880  # 5MB
   export MOATLESS_MAX_SEARCH_RESULTS=50
   ```

### 搜索优化

1. **使用具体的文件模式**
   ```json
   {
     "tool": "semantic_search",
     "arguments": {
       "query": "authentication",
       "file_pattern": "src/**/*.py",  // 限制搜索范围
       "max_results": 10
     }
   }
   ```

2. **选择合适的搜索类别**
   ```json
   {
     "tool": "semantic_search",
     "arguments": {
       "query": "login function",
       "category": "implementation"  // 明确指定类别
     }
   }
   ```

## 🔧 配置最佳实践

### MCP 客户端配置

1. **Claude Desktop 配置**
   ```json
   {
     "mcpServers": {
       "moatless": {
         "command": "moatless-mcp-server",
         "args": [
           "--workspace", "/absolute/path/to/project",
           "--no-index"  // 首次使用推荐
         ],
         "env": {
           "OPENAI_API_KEY": "从环境变量读取"
         }
       }
     }
   }
   ```

2. **Cline 配置**
   ```json
   {
     "mcpServers": {
       "moatless": {
         "command": "moatless-mcp-server",
         "args": [
           "--workspace", "${workspaceFolder}",
           "--openai-api-key", "${env:OPENAI_API_KEY}"
         ],
         "timeout": 60,
         "transportType": "stdio"
       }
     }
   }
   ```

### 环境变量配置

```bash
# 创建 .env 文件（不要提交到 git）
cat > .env << EOF
OPENAI_API_KEY=your-api-key-here
MOATLESS_MAX_FILE_SIZE=10485760
MOATLESS_MAX_SEARCH_RESULTS=100
MOATLESS_SEARCH_TIMEOUT=30
EOF

# 在启动脚本中加载
source .env
moatless-mcp-server --workspace /path/to/project
```

## 🚀 使用场景最佳实践

### 代码探索

1. **项目初次分析**
   ```json
   // 1. 获取项目概览
   {"tool": "workspace_info"}
   
   // 2. 查看目录结构
   {"tool": "list_files", "arguments": {"recursive": true}}
   
   // 3. 搜索关键组件
   {"tool": "semantic_search", "arguments": {"query": "main entry point"}}
   ```

2. **功能定位**
   ```json
   // 先用语义搜索定位
   {"tool": "semantic_search", "arguments": {"query": "user authentication"}}
   
   // 再用精确搜索确认
   {"tool": "find_function", "arguments": {"function_name": "authenticate"}}
   ```

### 代码修改

1. **安全的修改流程**
   ```json
   // 1. 查看当前实现
   {"tool": "read_file", "arguments": {"file_path": "src/auth.py"}}
   
   // 2. 理解上下文
   {"tool": "view_code", "arguments": {"file_path": "src/auth.py", "line": 50, "context": 10}}
   
   // 3. 执行修改
   {"tool": "string_replace", "arguments": {...}}
   
   // 4. 验证修改
   {"tool": "read_file", "arguments": {"file_path": "src/auth.py", "start_line": 45, "end_line": 55}}
   ```

## 🐛 故障排除最佳实践

### 日志和调试

1. **启用调试模式**
   ```bash
   moatless-mcp-server --workspace /path/to/project --debug
   ```

2. **检查工具状态**
   ```json
   {"tool": "code_index", "arguments": {"action": "status"}}
   ```

### 常见问题预防

1. **避免权限问题**
   ```bash
   # 确保有正确的文件权限
   chmod 755 /path/to/project
   chmod -R 644 /path/to/project/*
   ```

2. **网络连接检查**
   ```bash
   # 测试 OpenAI API 连接
   curl -H "Authorization: Bearer $OPENAI_API_KEY" \
        https://api.openai.com/v1/models
   ```

## 📊 监控和维护

### 性能监控

1. **索引大小监控**
   ```bash
   du -sh .moatless_index/
   ```

2. **搜索性能跟踪**
   - 关注搜索响应时间
   - 监控内存使用情况
   - 定期清理过期索引

### 定期维护

1. **每周任务**
   - 检查 API 密钥使用量
   - 清理临时文件
   - 更新依赖包

2. **每月任务**
   - 重建代码索引
   - 检查配置文件
   - 更新文档

## 🤝 团队协作

### 配置标准化

1. **团队配置模板**
   ```bash
   # 创建团队配置模板
   cp docs/examples/claude_desktop_config.json.template \
      team_config_template.json
   ```

2. **文档化约定**
   - 工作区路径约定
   - 索引管理策略
   - 搜索查询规范

### 知识分享

1. **最佳查询分享**
   - 记录有效的搜索查询
   - 分享搜索技巧
   - 建立查询模式库

2. **错误处理经验**
   - 记录常见问题解决方案
   - 分享配置技巧
   - 建立故障排除手册

---

遵循这些最佳实践将帮助您更安全、高效地使用 Moatless MCP Server，并避免常见的配置和使用问题。 