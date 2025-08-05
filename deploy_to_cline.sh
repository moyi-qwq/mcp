#!/bin/bash
# 部署 Moatless MCP Server 到 Cline 的脚本

set -e

echo "🚀 开始部署 Moatless MCP Server 到 Cline..."

# 1. 检查并激活虚拟环境
echo "📋 检查虚拟环境..."
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建虚拟环境"
    exit 1
fi

source venv/bin/activate
echo "✅ 当前 Python 版本: $(python --version)"
echo "✅ 当前 pip 版本: $(pip --version)"

# 2. 升级 pip 和安装编译工具
echo "🔧 升级 pip 和安装编译工具..."
pip install --upgrade pip setuptools wheel

# 3. 检查系统依赖（macOS）
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 检测到 macOS 系统，检查编译依赖..."
    
    # 检查是否安装了 Xcode Command Line Tools
    if ! xcode-select -p &> /dev/null; then
        echo "⚠️  未检测到 Xcode Command Line Tools"
        echo "请运行: xcode-select --install"
        echo "然后重新运行此脚本"
        exit 1
    fi
    
    # 检查是否安装了 Homebrew
    if ! command -v brew &> /dev/null; then
        echo "⚠️  未检测到 Homebrew"
        echo "请先安装 Homebrew: https://brew.sh"
        exit 1
    fi
    
    # 安装 faiss 编译依赖
    echo "📦 安装 faiss 编译依赖..."
    brew install cmake swig libomp
    
    # 设置编译环境变量
    export CMAKE_PREFIX_PATH="$(brew --prefix)"
    export LDFLAGS="-L$(brew --prefix)/lib"
    export CPPFLAGS="-I$(brew --prefix)/include"
    export CC=clang
    export CXX=clang++
fi

# 4. 尝试安装预编译的 faiss-cpu
echo "📦 尝试安装预编译的 faiss-cpu..."
pip install --no-cache-dir --force-reinstall faiss-cpu

# 5. 安装其他依赖
echo "📦 安装其他项目依赖..."
pip install --no-cache-dir -e .

# 6. 验证安装
echo "🔍 验证安装..."
if command -v Industrial_Software_MCP &> /dev/null; then
    echo "✅ MCP Server 安装成功"
    Industrial_Software_MCP --help
else
    echo "❌ MCP Server 安装失败"
    exit 1
fi

# 7. 配置 Cline MCP 设置
MCP_SETTINGS_FILE="$HOME/.vscode-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json"
PYTHON_PATH=$(which python)

echo "🔧 配置 Cline MCP 设置..."

# 创建目录如果不存在
mkdir -p "$(dirname "$MCP_SETTINGS_FILE")"

# 检查是否已存在配置文件
if [ -f "$MCP_SETTINGS_FILE" ]; then
    echo "📄 发现现有的 MCP 设置文件"
    # 备份现有文件
    cp "$MCP_SETTINGS_FILE" "${MCP_SETTINGS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "✅ 已备份现有配置"
    
    # 读取现有配置，添加 moatless 服务器
    python -c "
import json
import sys

config_file = '$MCP_SETTINGS_FILE'
try:
    with open(config_file, 'r') as f:
        config = json.load(f)
except:
    config = {'mcpServers': {}}

if 'mcpServers' not in config:
    config['mcpServers'] = {}

config['mcpServers']['moatless'] = {
    'autoApprove': [],
    'disabled': False,
    'timeout': 60,
    'command': '$PYTHON_PATH',
    'args': [
        '-m', 'moatless_mcp.server',
        '--workspace', '\${workspaceFolder}'
    ],
    'transportType': 'stdio',
    'alwaysAllow': []
}

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)

print('✅ 已更新 MCP 配置')
"
else
    echo "📝 创建新的 MCP 设置文件..."
    cat > "$MCP_SETTINGS_FILE" << EOF
{
  "mcpServers": {
    "moatless": {
      "autoApprove": [],
      "disabled": false,
      "timeout": 60,
      "command": "$PYTHON_PATH",
      "args": [
        "-m", "moatless_mcp.server",
        "--workspace", "\${workspaceFolder}"
      ],
      "transportType": "stdio",
      "alwaysAllow": []
    }
  }
}
EOF
    echo "✅ 已创建 MCP 配置文件"
fi

echo "📍 MCP 配置文件位置: $MCP_SETTINGS_FILE"
echo "🔧 配置内容:"
cat "$MCP_SETTINGS_FILE"

echo ""
echo "🎉 部署完成！"
echo ""
echo "📋 接下来的步骤："
echo "1. 重启 VS Code"
echo "2. 打开一个项目文件夹"
echo "3. 启动 Cline 扩展"
echo "4. 测试命令: '请使用 workspace_info 工具查看当前项目信息'"
echo ""
echo "🔧 如果遇到问题："
echo "- 检查 VS Code 终端中是否有错误信息"
echo "- 确保项目文件夹已打开"
echo "- 尝试在 Cline 中执行: '列出所有可用的工具'"
echo ""
echo "📚 更多信息请查看: docs/CLINE_SETUP.md"