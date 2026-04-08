#!/bin/bash
################################################################################
# VigilOps Agent - CentOS 7 离线安装脚本
#
# 目录：
#   agent.tar (含 agent/ 和 yum.repos.d.tar.gz)
#   install-agent-offline.sh
#
# 用法：
#   sudo bash install-agent-offline.sh <SERVER_URL> <AGENT_TOKEN>
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查 root
if [ "$EUID" -ne 0 ]; then
    log_error "请使用 root 权限运行"
    exit 1
fi

# 参数
if [ -z "$1" ] || [ -z "$2" ]; then
    log_error "用法: $0 <SERVER_URL> <AGENT_TOKEN>"
    exit 1
fi

SERVER_URL="$1"
AGENT_TOKEN="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_TAR="$SCRIPT_DIR/agent.tar"

log_info "=========================================="
log_info "VigilOps Agent CentOS 7 离线安装"
log_info "=========================================="
log_info "服务器: $SERVER_URL"
echo ""

# 检查文件
if [ ! -f "$AGENT_TAR" ]; then
    log_error "未找到 agent.tar"
    exit 1
fi

################################################################################
# 检查是否已安装（跳过已完成的步骤）
################################################################################

log_info "检查环境..."

# 检查 Python 3.9
PYTHON_INSTALLED=false
if command -v python3.9 &> /dev/null; then
    PY_VER=$(python3.9 --version 2>&1)
    PYTHON_INSTALLED=true
    log_info "✓ Python 已安装: $PY_VER"
fi

# 检查编译工具
DEVTOOLS_INSTALLED=false
if command -v gcc &> /dev/null && rpm -q gcc &> /dev/null; then
    DEVTOOLS_INSTALLED=true
    log_info "✓ 编译工具已安装"
fi

# 检查 yum 源
YUM_REPOS_COUNT=$(ls /etc/yum.repos.d/*.repo 2>/dev/null | wc -l)
YUM_CONFIGURED=false
if [ "$YUM_REPOS_COUNT" -gt 0 ]; then
    YUM_CONFIGURED=true
    log_info "✓ yum 源已配置 ($YUM_REPOS_COUNT 个 repo 文件)"
fi

# 判断是否可以跳过
if [ "$PYTHON_INSTALLED" = true ] && [ "$DEVTOOLS_INSTALLED" = true ]; then
    log_warn "检测到 Python 和编译工具已安装"
    log_warn "将跳过环境配置步骤，直接安装 Agent"
    echo ""
    SKIP_SETUP=true
else
    SKIP_SETUP=false
    echo ""
fi

################################################################################
# 步骤 1: 解压 agent.tar
################################################################################

log_info "步骤 1: 解压 agent.tar"

EXTRACT_DIR="$SCRIPT_DIR/agent_install_temp"
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"
tar -xf "$AGENT_TAR" -C "$EXTRACT_DIR"

# 找到 agent 目录（可能直接在根目录或有子文件夹）
if [ -d "$EXTRACT_DIR/agent" ]; then
    AGENT_DIR="$EXTRACT_DIR/agent"
    YUM_TAR="$EXTRACT_DIR/agent/yum.repos.d.tar.gz"
elif [ -f "$EXTRACT_DIR/yum.repos.d.tar.gz" ]; then
    AGENT_DIR="$EXTRACT_DIR"
    YUM_TAR="$EXTRACT_DIR/yum.repos.d.tar.gz"
else
    log_error "agent.tar 结构异常"
    ls -R "$EXTRACT_DIR"
    exit 1
fi

if [ ! -f "$YUM_TAR" ]; then
    log_error "未找到 yum.repos.d.tar.gz"
    exit 1
fi

log_info "✓ Agent: $AGENT_DIR"

# 如果检测到已安装，跳过环境配置步骤
if [ "$SKIP_SETUP" = true ]; then
    log_warn "检测到环境已配置，跳过步骤 2-4"
    echo ""
else
    log_info "✓ YUM源: $YUM_TAR"
    echo ""

################################################################################
# 步骤 2: 备份并替换 yum 源
################################################################################

log_info "步骤 2: 配置 yum 源"

# 把整个目录改成 .bak
YUM_BACKUP="/etc/yum.repos.d.bak.$(date +%Y%m%d%H%M%S)"
mv /etc/yum.repos.d "$YUM_BACKUP"

# 创建新的空目录
mkdir -p /etc/yum.repos.d

# 解压 yum 源进去
tar -xzf "$YUM_TAR" -C /etc/yum.repos.d/

# 处理可能的嵌套结构（如果解压出 yum.repos.d/yum.repos.d/）
if [ -d "/etc/yum.repos.d/yum.repos.d" ]; then
    mv /etc/yum.repos.d/yum.repos.d/*.repo /etc/yum.repos.d/
    rm -rf "/etc/yum.repos.d/yum.repos.d"
fi

yum clean all -q > /dev/null 2>&1 || true
yum makecache -q > /dev/null 2>&1 || true

log_info "✓ yum 源已配置，备份: $YUM_BACKUP"

################################################################################
# 步骤 3: 安装编译依赖
################################################################################

log_info "步骤 3: 安装编译依赖（需要几分钟）"
log_info "正在安装 Development Tools..."
yum groupinstall -y "Development Tools" || {
    log_error "Development Tools 安装失败"
    exit 1
}

log_info "正在安装编译依赖包..."
yum install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel \
    xz-devel readline-devel sqlite-devel tk-devel gdbm-devel \
    db4-devel libpcap-devel ncurses-devel wget || {
    log_error "编译依赖安装失败"
    exit 1
}

log_info "✓ 编译依赖安装完成"

################################################################################
# 步骤 4: 编译 Python 3.9.18
################################################################################

log_info "步骤 4: 编译 Python 3.9.18（需要几分钟）"

PYTHON_VER="3.9.18"
cd /root

if [ ! -d "Python-$PYTHON_VER" ]; then
    log_info "下载 Python $PYTHON_VER (约25MB)..."
    wget "https://www.python.org/ftp/python/$PYTHON_VER/Python-$PYTHON_VER.tgz" || {
        log_error "Python 下载失败"
        exit 1
    }
    log_info "解压..."
    tar -xzf "Python-$PYTHON_VER.tgz"
    rm -f "Python-$PYTHON_VER.tgz"
fi

log_info "配置编译选项..."
cd "Python-$PYTHON_VER"
./configure --prefix=/usr/local --enable-shared --with-ssl || {
    log_error "configure 失败"
    exit 1
}

log_info "编译中（使用 $(nproc) 核心，需要几分钟）..."
make -j$(nproc) || {
    log_error "编译失败"
    exit 1
}

log_info "安装中..."
make altinstall || {
    log_error "安装失败"
    exit 1
}

log_info "配置动态库..."
echo "/usr/local/lib" > /etc/ld.so.conf.d/python3.9.conf
ldconfig

python3.9 --version || {
    log_error "Python 安装失败"
    exit 1
}

log_info "✓ Python 3.9.18 安装完成"
echo ""
fi # END SKIP_SETUP

################################################################################
# 步骤 5: 安装 Agent
################################################################################

log_info "步骤 5: 安装 Agent"

VENV_DIR="/opt/vigilops/venv"
AGENT_FINAL_DIR="/opt/vigilops/agent"

mkdir -p /opt/vigilops

# 复制 agent 到最终目录
log_info "复制 Agent 到 $AGENT_FINAL_DIR"
rm -rf "$AGENT_FINAL_DIR"
mkdir -p "$AGENT_FINAL_DIR"
cp -r "$AGENT_DIR"/* "$AGENT_FINAL_DIR/"
# 以 root 运行，无需修改所有权

log_info "创建虚拟环境..."
python3.9 -m venv "$VENV_DIR" || {
    log_error "虚拟环境创建失败"
    exit 1
}

log_info "安装 Agent 包..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip || {
    log_error "pip 升级失败"
    exit 1
}
pip install -e "$AGENT_FINAL_DIR" || {
    log_error "Agent 安装失败"
    exit 1
}
deactivate

log_info "✓ Agent 安装完成"

################################################################################
# 步骤 6: 配置
################################################################################

log_info "步骤 6: 配置 Agent"

CONFIG="/etc/vigilops/agent.yaml"
mkdir -p /etc/vigilops

cat > "$CONFIG" << EOF
server:
  url: $SERVER_URL
  token: "$AGENT_TOKEN"

host:
  name: ""
  display_name: "$(hostname)"
  tags:
    - centos7

metrics:
  interval: 15s

discovery:
  docker: true
  process: true
  host_services: true
EOF

chmod 644 "$CONFIG"
log_info "✓ 配置文件已创建"

################################################################################
# 步骤 7: 创建服务
################################################################################

log_info "步骤 7: 创建服务"

# Agent 以 root 运行（支持 AI 操作等需要高权限的功能）

cat > /etc/systemd/system/vigilops-agent.service << EOF
[Unit]
Description=VigilOps Monitoring Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vigilops
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_DIR/bin/vigilops-agent run
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

log_info "✓ 服务文件已创建"

################################################################################
# 步骤 8: 启动
################################################################################

log_info "步骤 8: 启动服务"

log_info "重新加载 systemd..."
systemctl daemon-reload

log_info "启动 vigilops-agent..."
systemctl start vigilops-agent

log_info "设置开机自启..."
systemctl enable vigilops-agent >/dev/null 2>&1

log_info "等待服务启动..."
sleep 3

log_info "清理临时文件..."
rm -rf "$EXTRACT_DIR"

echo ""
log_info "=========================================="
log_info "安装完成！"
log_info "=========================================="
echo ""
echo "配置: $CONFIG"
echo "Python: $(python3.9 --version)"
echo ""
echo "常用命令:"
echo "  状态: systemctl status vigilops-agent"
echo "  日志: journalctl -u vigilops-agent -f"
echo "  重启: systemctl restart vigilops-agent"
echo ""
echo "yum 备份: $YUM_BACKUP"
echo ""
echo "服务状态:"
systemctl status vigilops-agent --no-pager
