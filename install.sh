#!/usr/bin/env bash
# VigilOps One-Click Installer / 一键部署脚本
# https://github.com/LinChuang2008/vigilops
set -euo pipefail

# ── Constants ──────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"
COMPOSE_DEV_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"
MIGRATIONS_DIR="$SCRIPT_DIR/backend/migrations"
DEFAULT_BACKEND_PORT=8001
DEFAULT_FRONTEND_PORT=3001
DEFAULT_POSTGRES_PORT=5433
DEFAULT_REDIS_PORT=6380
VERSION="1.0.0"

# ── Colors ─────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

# ── Bilingual helpers ──────────────────────────────────────
msg()  { echo -e "${GREEN}[VigilOps]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }

banner() {
  echo -e "${CYAN}"
  echo "╔══════════════════════════════════════════════╗"
  echo "║       VigilOps — AI-Powered Monitoring       ║"
  echo "║       智能运维监控平台 · 一键部署脚本          ║"
  echo "╚══════════════════════════════════════════════╝"
  echo -e "${NC}"
}

# ── Usage / Help ───────────────────────────────────────────
usage() {
  cat <<EOF
VigilOps Installer v${VERSION}

Usage: ./install.sh [OPTIONS]

Options:
  (no args)       Interactive install / 交互式安装
  --help, -h      Show this help message / 显示帮助
  --status        Show running status / 显示运行状态
  --uninstall     Stop and remove containers / 停止并删除容器
  --upgrade       Pull latest and restart / 升级并重启

Port options (non-interactive):
  --backend-port PORT    Backend port  (default: ${DEFAULT_BACKEND_PORT})
  --frontend-port PORT   Frontend port (default: ${DEFAULT_FRONTEND_PORT})
  --postgres-port PORT   Postgres port (default: ${DEFAULT_POSTGRES_PORT})
  --redis-port PORT      Redis port    (default: ${DEFAULT_REDIS_PORT})

Examples:
  ./install.sh                                    # Interactive install
  ./install.sh --backend-port 9001                # Custom backend port
  ./install.sh --status                           # Check status
  ./install.sh --uninstall                        # Remove containers

EOF
  exit 0
}

# ── Status ─────────────────────────────────────────────────
show_status() {
  msg "VigilOps Service Status / 服务状态"
  echo ""
  cd "$SCRIPT_DIR"
  detect_compose
  if [[ -z "$COMPOSE_CMD" ]]; then
    err "Docker Compose not found."
    exit 1
  fi
  # Use prod compose if available, fallback to dev
  local cf="$COMPOSE_FILE"
  [[ ! -f "$cf" ]] && cf="$COMPOSE_DEV_FILE"
  $COMPOSE_CMD -f "$cf" ps 2>/dev/null || echo "  No containers running. / 没有运行中的容器。"
  echo ""

  # Show ports from .env or defaults
  if [[ -f "$ENV_FILE" ]]; then
    local bp fp pp rp
    bp=$(grep "^BACKEND_PORT_HOST=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "$DEFAULT_BACKEND_PORT")
    fp=$(grep "^FRONTEND_PORT_HOST=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "$DEFAULT_FRONTEND_PORT")
    pp=$(grep "^POSTGRES_PORT_HOST=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "$DEFAULT_POSTGRES_PORT")
    rp=$(grep "^REDIS_PORT_HOST=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "$DEFAULT_REDIS_PORT")
    bp="${bp:-$DEFAULT_BACKEND_PORT}"; fp="${fp:-$DEFAULT_FRONTEND_PORT}"
    pp="${pp:-$DEFAULT_POSTGRES_PORT}"; rp="${rp:-$DEFAULT_REDIS_PORT}"
    echo "  Configured Ports / 配置端口:"
    echo "    Backend:  ${bp}"
    echo "    Frontend: ${fp}"
    echo "    Postgres: ${pp}"
    echo "    Redis:    ${rp}"
  fi
  exit 0
}

# ── Uninstall ──────────────────────────────────────────────
uninstall() {
  msg "Uninstalling VigilOps… / 卸载 VigilOps…"
  cd "$SCRIPT_DIR"
  detect_compose
  local cf="$COMPOSE_FILE"
  [[ ! -f "$cf" ]] && cf="$COMPOSE_DEV_FILE"

  $COMPOSE_CMD -f "$cf" down 2>/dev/null || true
  echo ""
  msg "Containers and networks removed. / 容器和网络已删除。"
  echo ""
  warn "Data volumes are preserved. To remove them manually: / 数据卷已保留，手动删除："
  echo "  docker volume rm \$(docker volume ls -q | grep vigilops)"
  echo ""
  read -rp "Delete .env file? 删除配置文件？(y/N): " del_env
  if [[ "${del_env,,}" == "y" ]]; then
    rm -f "$ENV_FILE"
    msg ".env removed. / 配置文件已删除。"
  fi
  msg "Uninstall complete. / 卸载完成。"
  exit 0
}

# ── Upgrade ────────────────────────────────────────────────
upgrade() {
  msg "Upgrading VigilOps… / 升级 VigilOps…"
  cd "$SCRIPT_DIR"
  detect_compose
  local cf="$COMPOSE_FILE"
  [[ ! -f "$cf" ]] && cf="$COMPOSE_DEV_FILE"

  git pull --ff-only 2>/dev/null || warn "Git pull failed, skipping. / Git 拉取失败，跳过。"
  $COMPOSE_CMD -f "$cf" up -d
  run_migrations
  msg "Upgrade complete! / 升级完成！"
  exit 0
}

# ── Detect Docker Compose command ──────────────────────────
detect_compose() {
  if docker compose version &>/dev/null; then
    COMPOSE_CMD="docker compose"
  elif command -v docker-compose &>/dev/null; then
    COMPOSE_CMD="docker-compose"
  else
    COMPOSE_CMD=""
  fi
}

# ── Check prerequisites ───────────────────────────────────
check_prerequisites() {
  msg "Checking prerequisites… / 检查系统环境…"

  if ! command -v docker &>/dev/null; then
    err "Docker not found. / 未找到 Docker。"
    echo ""
    echo "Install Docker / 安装 Docker:"
    echo "  curl -fsSL https://get.docker.com | sh"
    echo "  sudo systemctl enable --now docker"
    echo "  sudo usermod -aG docker \$USER"
    echo ""
    exit 1
  fi

  detect_compose
  if [[ -z "$COMPOSE_CMD" ]]; then
    err "Docker Compose not found. / 未找到 Docker Compose。"
    echo "Install: https://docs.docker.com/compose/install/"
    exit 1
  fi

  if ! docker info &>/dev/null; then
    err "Docker daemon not running. / Docker 服务未启动。"
    echo "  sudo systemctl start docker"
    exit 1
  fi

  msg "✅ Docker $(docker --version | sed -n 's/.*version \([0-9.]*\).*/\1/p') detected"
  msg "✅ $COMPOSE_CMD ready"
}

# ── Generate random password ──────────────────────────────
rand_pw() {
  tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24 2>/dev/null || openssl rand -base64 18
}

# ── Interactive configuration ─────────────────────────────
configure() {
  msg "Configuration / 配置向导"
  echo "Press Enter to use [default]. / 按回车使用 [默认值]。"
  echo ""

  # Ports (may be pre-set via CLI args)
  if [[ -z "${BACKEND_PORT:-}" ]]; then
    read -rp "Backend port  后端端口 [$DEFAULT_BACKEND_PORT]: " BACKEND_PORT
    BACKEND_PORT="${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}"
  fi
  if [[ -z "${FRONTEND_PORT:-}" ]]; then
    read -rp "Frontend port 前端端口 [$DEFAULT_FRONTEND_PORT]: " FRONTEND_PORT
    FRONTEND_PORT="${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}"
  fi
  if [[ -z "${POSTGRES_PORT:-}" ]]; then
    read -rp "Postgres port 数据库端口 [$DEFAULT_POSTGRES_PORT]: " POSTGRES_PORT
    POSTGRES_PORT="${POSTGRES_PORT:-$DEFAULT_POSTGRES_PORT}"
  fi
  if [[ -z "${REDIS_PORT:-}" ]]; then
    read -rp "Redis port    缓存端口 [$DEFAULT_REDIS_PORT]: " REDIS_PORT
    REDIS_PORT="${REDIS_PORT:-$DEFAULT_REDIS_PORT}"
  fi

  # DB password
  DB_PASSWORD="$(rand_pw)"
  JWT_SECRET="$(rand_pw)"

  # AI config (optional)
  echo ""
  msg "AI Configuration (optional) / AI 配置（可选，可跳过）"
  read -rp "AI API Key (e.g. DeepSeek) [skip]: " AI_KEY
  AI_KEY="${AI_KEY:-}"
  read -rp "AI API Base URL [https://api.deepseek.com/v1]: " AI_BASE
  AI_BASE="${AI_BASE:-https://api.deepseek.com/v1}"
  read -rp "AI Model [deepseek-chat]: " AI_MODEL
  AI_MODEL="${AI_MODEL:-deepseek-chat}"

  write_env
}

# ── Write .env file ───────────────────────────────────────
write_env() {
  cat > "$ENV_FILE" <<EOF
# VigilOps Configuration — auto-generated $(date +%Y-%m-%d)

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=vigilops
POSTGRES_USER=vigilops
POSTGRES_PASSWORD=${DB_PASSWORD}

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# JWT
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

# Host-mapped ports (used by docker-compose.prod.yml)
BACKEND_PORT_HOST=${BACKEND_PORT}
FRONTEND_PORT_HOST=${FRONTEND_PORT}
POSTGRES_PORT_HOST=${POSTGRES_PORT}
REDIS_PORT_HOST=${REDIS_PORT}

# AI (optional)
AI_PROVIDER=deepseek
AI_API_KEY=${AI_KEY}
AI_API_BASE=${AI_BASE}
AI_MODEL=${AI_MODEL}
AI_MAX_TOKENS=2000
AI_AUTO_SCAN=false
EOF
  msg "✅ .env generated / 配置文件已生成"
}

# ── Load images (offline mode) ────────────────────────────
load_images() {
  msg "Loading Docker images… / 加载 Docker 镜像…"
  local loaded=0
  for tarball in "$SCRIPT_DIR"/backend.tar.gz "$SCRIPT_DIR"/frontend.tar.gz; do
    if [[ -f "$tarball" ]]; then
      echo -n "  Loading $(basename "$tarball")… "
      docker load -i "$tarball" &>/dev/null && echo -e "${GREEN}✅${NC}" || echo -e "${RED}❌${NC}"
      loaded=$((loaded+1))
    fi
  done
  if [[ $loaded -gt 0 ]]; then
    msg "✅ Loaded $loaded image(s) / 已加载 $loaded 个镜像"
  fi
}

# ── Start services ────────────────────────────────────────
start_services() {
  msg "Starting services… / 启动服务…"
  cd "$SCRIPT_DIR"

  # Prefer prod compose (uses image:), fallback to dev (uses build:)
  local cf="$COMPOSE_FILE"
  if [[ ! -f "$cf" ]]; then
    warn "docker-compose.prod.yml not found, using docker-compose.yml"
    cf="$COMPOSE_DEV_FILE"
  fi

  # Export ports for docker-compose.prod.yml variable substitution
  export BACKEND_PORT="${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}"
  export FRONTEND_PORT="${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}"
  export POSTGRES_PORT="${POSTGRES_PORT:-$DEFAULT_POSTGRES_PORT}"
  export REDIS_PORT="${REDIS_PORT:-$DEFAULT_REDIS_PORT}"

  $COMPOSE_CMD -f "$cf" --env-file "$ENV_FILE" up -d
}

# ── Health check ──────────────────────────────────────────
wait_healthy() {
  msg "Waiting for services to be healthy… / 等待服务就绪…"
  local max_wait=120
  local elapsed=0

  echo -n "  PostgreSQL: "
  while ! docker compose exec -T postgres pg_isready -U vigilops &>/dev/null; do
    sleep 2; elapsed=$((elapsed+2))
    if [[ $elapsed -ge $max_wait ]]; then
      err "PostgreSQL timeout / 数据库启动超时"; exit 1
    fi
    echo -n "."
  done
  echo -e " ${GREEN}✅${NC}"

  echo -n "  Redis:      "
  elapsed=0
  while ! docker compose exec -T redis redis-cli ping &>/dev/null; do
    sleep 2; elapsed=$((elapsed+2))
    if [[ $elapsed -ge $max_wait ]]; then
      err "Redis timeout / Redis 启动超时"; exit 1
    fi
    echo -n "."
  done
  echo -e " ${GREEN}✅${NC}"

  echo -n "  Backend:    "
  elapsed=0
  while ! curl -sf "http://localhost:${BACKEND_PORT}/docs" &>/dev/null; do
    sleep 3; elapsed=$((elapsed+3))
    if [[ $elapsed -ge $max_wait ]]; then
      warn "Backend may still be starting / 后端可能仍在启动"; break
    fi
    echo -n "."
  done
  echo -e " ${GREEN}✅${NC}"

  echo -n "  Frontend:   "
  elapsed=0
  while ! curl -sf "http://localhost:${FRONTEND_PORT}" &>/dev/null; do
    sleep 3; elapsed=$((elapsed+3))
    if [[ $elapsed -ge $max_wait ]]; then
      warn "Frontend may still be starting / 前端可能仍在启动"; break
    fi
    echo -n "."
  done
  echo -e " ${GREEN}✅${NC}"
}

# ── Database migrations ───────────────────────────────────
run_migrations() {
  msg "Running database migrations… / 执行数据库迁移…"

  $COMPOSE_CMD exec -T postgres psql -U vigilops -d vigilops -c "
    CREATE TABLE IF NOT EXISTS schema_migrations (
      filename VARCHAR(255) PRIMARY KEY,
      applied_at TIMESTAMP DEFAULT NOW()
    );" 2>/dev/null || true

  local count=0
  for sql_file in $(ls "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort); do
    local fname
    fname="$(basename "$sql_file")"
    local applied
    applied=$($COMPOSE_CMD exec -T postgres psql -U vigilops -d vigilops -tAc \
      "SELECT COUNT(*) FROM schema_migrations WHERE filename='$fname';" 2>/dev/null || echo "0")
    applied=$(echo "$applied" | tr -d '[:space:]')
    if [[ "$applied" == "0" ]]; then
      echo -n "  Applying $fname … "
      if $COMPOSE_CMD exec -T postgres psql -U vigilops -d vigilops < "$sql_file" &>/dev/null; then
        $COMPOSE_CMD exec -T postgres psql -U vigilops -d vigilops -c \
          "INSERT INTO schema_migrations (filename) VALUES ('$fname');" &>/dev/null
        echo -e "${GREEN}✅${NC}"
        count=$((count+1))
      else
        warn "Failed: $fname / 失败: $fname"
      fi
    fi
  done

  if [[ $count -eq 0 ]]; then
    msg "All migrations already applied. / 所有迁移已执行。"
  else
    msg "✅ Applied $count migration(s). / 已执行 $count 个迁移。"
  fi
}

# ── Print summary ─────────────────────────────────────────
print_summary() {
  local ip
  ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
  [[ -z "$ip" ]] && ip="localhost"

  echo ""
  echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║         🎉 Installation Complete! 🎉         ║${NC}"
  echo -e "${CYAN}║            安装完成！                         ║${NC}"
  echo -e "${CYAN}╠══════════════════════════════════════════════╣${NC}"
  echo -e "${CYAN}║${NC} Frontend 前端:  ${GREEN}http://${ip}:${FRONTEND_PORT}${NC}"
  echo -e "${CYAN}║${NC} Backend  后端:  ${GREEN}http://${ip}:${BACKEND_PORT}${NC}"
  echo -e "${CYAN}║${NC} API Docs 文档:  ${GREEN}http://${ip}:${BACKEND_PORT}/docs${NC}"
  echo -e "${CYAN}╠══════════════════════════════════════════════╣${NC}"
  echo -e "${CYAN}║${NC} Default Admin 默认管理员:"
  echo -e "${CYAN}║${NC}   User 用户: admin"
  echo -e "${CYAN}║${NC}   Pass 密码: admin123"
  echo -e "${CYAN}║${NC}   ${RED}⚠ Change password after first login!${NC}"
  echo -e "${CYAN}║${NC}   ${RED}⚠ 首次登录后请修改密码！${NC}"
  echo -e "${CYAN}╠══════════════════════════════════════════════╣${NC}"
  echo -e "${CYAN}║${NC} Commands 常用命令:"
  echo -e "${CYAN}║${NC}   View logs 查看日志:  cd $(basename "$SCRIPT_DIR") && docker compose logs -f"
  echo -e "${CYAN}║${NC}   Status 状态:         ./install.sh --status"
  echo -e "${CYAN}║${NC}   Uninstall 卸载:      ./install.sh --uninstall"
  echo -e "${CYAN}║${NC}   Upgrade 升级:        ./install.sh --upgrade"
  echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
}

# ── Parse arguments ────────────────────────────────────────
BACKEND_PORT=""
FRONTEND_PORT=""
POSTGRES_PORT=""
REDIS_PORT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)       usage ;;
    --status)        detect_compose; show_status ;;
    --uninstall)     detect_compose; uninstall ;;
    --upgrade)       detect_compose; upgrade ;;
    --backend-port)  BACKEND_PORT="$2"; shift 2 ;;
    --frontend-port) FRONTEND_PORT="$2"; shift 2 ;;
    --postgres-port) POSTGRES_PORT="$2"; shift 2 ;;
    --redis-port)    REDIS_PORT="$2"; shift 2 ;;
    *)
      err "Unknown option: $1"
      echo "Run './install.sh --help' for usage."
      exit 1 ;;
  esac
done

# ── Main ──────────────────────────────────────────────────
main() {
  banner
  check_prerequisites

  # Load offline images if tar files present
  load_images

  # If .env exists, ask to reconfigure
  if [[ -f "$ENV_FILE" ]]; then
    warn "Existing .env found. / 已存在配置文件。"
    read -rp "Reconfigure? 重新配置？(y/N): " reconf
    if [[ "${reconf,,}" == "y" ]]; then
      configure
    else
      # Read existing ports from .env
      BACKEND_PORT="${BACKEND_PORT:-$(grep '^BACKEND_PORT_HOST=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || true)}"
      FRONTEND_PORT="${FRONTEND_PORT:-$(grep '^FRONTEND_PORT_HOST=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || true)}"
      POSTGRES_PORT="${POSTGRES_PORT:-$(grep '^POSTGRES_PORT_HOST=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || true)}"
      REDIS_PORT="${REDIS_PORT:-$(grep '^REDIS_PORT_HOST=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || true)}"
      BACKEND_PORT="${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}"
      FRONTEND_PORT="${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}"
      POSTGRES_PORT="${POSTGRES_PORT:-$DEFAULT_POSTGRES_PORT}"
      REDIS_PORT="${REDIS_PORT:-$DEFAULT_REDIS_PORT}"
      msg "Using existing configuration. / 使用现有配置。"
    fi
  elif [[ -f "$ENV_EXAMPLE" ]]; then
    # Copy .env.example as starting point, then run interactive config
    msg "Creating .env from .env.example… / 从模板创建配置…"
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    configure
  else
    configure
  fi

  start_services
  wait_healthy
  run_migrations
  print_summary
}

main
