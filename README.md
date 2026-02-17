# VigilOps

🛡️ **开源 AI 智能运维监控平台**

服务器监控 · 服务监控 · 日志管理 · 数据库监控 · AI 智能分析 · 多渠道告警通知

一个 `docker compose up` 即可启动完整平台。

---

## ✨ 功能特性

### 基础监控
- 📊 **服务器监控** — CPU / 内存 / 磁盘 / 网络带宽实时采集与图表展示
- 🔍 **服务监控** — HTTP / TCP 拨测，自动健康检查，状态追踪
- 📝 **日志管理** — Docker 日志自动发现采集，全文搜索，实时流式查看
- 🗄️ **数据库监控** — PostgreSQL / MySQL / Oracle 连接数、QPS、慢查询 Top 10

### AI 智能分析
- 🧠 **AI 对话** — 基于当前监控数据的智能问答
- 🔎 **日志异常扫描** — AI 自动检测异常日志模式
- 🎯 **告警根因分析** — 一键 AI 分析告警根因并给出修复建议
- 📋 **AI 运维报告** — 自动生成日报 / 周报（每天 2:00 / 每周一 3:00）

### 告警与通知
- 🔔 **统一告警中心** — 指标告警 + 日志关键字告警 + 数据库告警
- 🤫 **告警降噪** — Cooldown 冷却 + 静默期，避免告警风暴
- 📱 **多渠道通知** — 邮件 / 钉钉 / 飞书 / 企业微信 Webhook
- 📄 **通知模板** — 可自定义告警通知内容模板

### 团队管理
- 👥 **用户管理** — RBAC 三级权限（Admin / Operator / Viewer）
- 📜 **审计日志** — 完整操作审计追踪
- ⚙️ **系统设置** — 全局参数配置

---

## 🏗️ 架构

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│  PostgreSQL   │
│  React + TS  │     │   FastAPI    │     │              │
│  Ant Design  │     │              │────▶│    Redis      │
│   ECharts    │     │              │     └──────────────┘
└──────────────┘     │              │
                     │              │◀──── DeepSeek / OpenAI
┌──────────────┐     │              │      (AI 分析)
│    Agent     │────▶│              │
│  Python 轻量  │     └──────────────┘
│  采集端       │
└──────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Ant Design 5 + ECharts + Zustand |
| 后端 | Python 3.12 + FastAPI + SQLAlchemy + Pydantic |
| Agent | Python 3.9+（轻量采集端，支持 Docker 自动发现） |
| 数据库 | PostgreSQL 16 + Redis 7 |
| AI | DeepSeek / OpenAI / Anthropic / Ollama（可配置） |
| 部署 | Docker Compose |

---

## 🚀 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose v2+
- 2GB+ 可用内存

### 1. 克隆项目

```bash
git clone https://github.com/your-org/vigilops.git
cd vigilops
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少修改以下配置：

```bash
# 数据库密码（必改）
POSTGRES_PASSWORD=your-secure-password

# JWT 密钥（必改，生产环境使用随机字符串）
JWT_SECRET_KEY=your-random-secret-key

# AI 配置（可选，启用 AI 分析功能需要）
AI_PROVIDER=deepseek
AI_API_KEY=your-api-key
AI_API_BASE=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
AI_MAX_TOKENS=2000
```

### 3. 启动服务

```bash
docker compose up -d
```

等待所有容器启动完成（约 1-2 分钟）：

```bash
docker compose ps
```

### 4. 访问平台

- 🌐 **前端界面**: http://localhost:3001
- 📡 **后端 API**: http://localhost:8001/docs（Swagger 文档）

首次注册的用户自动成为管理员（Admin）。

### 5. 部署 Agent（采集端）

在需要监控的服务器上部署 Agent：

```bash
# 复制 Agent 配置
cp agent/agent.example.yaml /etc/vigilops/agent.yaml

# 编辑配置，填入后端地址和 Token
vim /etc/vigilops/agent.yaml
```

```yaml
server:
  url: http://your-backend-host:8001
  token: your-agent-token    # 在平台「设置」页面生成

collect:
  interval: 60               # 采集间隔（秒）

discovery:
  docker: true               # 自动发现 Docker 容器
```

```bash
# 安装依赖并启动
pip install -r agent/requirements.txt
python agent/main.py
```

---

## 📸 界面截图

> 截图即将添加

<!-- 
![Dashboard](docs/screenshots/dashboard.png)
![Host Detail](docs/screenshots/host-detail.png)
![AI Analysis](docs/screenshots/ai-analysis.png)
![Alert Center](docs/screenshots/alerts.png)
-->

---

## 📁 项目结构

```
vigilops/
├── backend/                # 后端服务
│   ├── app/
│   │   ├── core/           # 配置、数据库、认证、依赖注入
│   │   ├── models/         # SQLAlchemy 数据模型
│   │   ├── routers/        # API 路由（18 个模块）
│   │   ├── schemas/        # Pydantic 请求/响应模型
│   │   └── services/       # 业务逻辑（AI 引擎、通知、报告等）
│   ├── migrations/         # 数据库迁移（001-011）
│   └── Dockerfile
├── frontend/               # 前端应用
│   └── src/
│       ├── pages/          # 18 个页面组件
│       ├── components/     # 公共组件
│       ├── store/          # Zustand 状态管理
│       └── api/            # API 调用层
├── agent/                  # 轻量采集 Agent
│   ├── collectors/         # 指标采集器（系统/Docker/网络/数据库）
│   ├── discovery/          # Docker 容器自动发现
│   └── agent.example.yaml  # 配置模板
├── docker-compose.yml      # 一键部署编排
├── .env.example            # 环境变量模板
└── docs/                   # 文档
```

---

## 🔌 API 概览

所有 API 均以 `/api/v1` 为前缀，完整文档访问 `http://localhost:8001/docs`。

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `POST /auth/register` | 注册（首个用户为 Admin） |
| | `POST /auth/login` | 登录获取 JWT |
| 服务器 | `GET /hosts` | 服务器列表 |
| | `GET /hosts/{id}/metrics` | 服务器指标数据 |
| 服务 | `GET /services` | 服务监控列表 |
| 日志 | `GET /logs` | 日志搜索 |
| | `WS /logs/stream` | 实时日志流 |
| 数据库 | `GET /databases` | 数据库列表 |
| 告警 | `GET /alerts` | 告警列表 |
| | `GET /alert-rules` | 告警规则管理 |
| AI | `POST /ai/chat` | AI 对话 |
| | `POST /ai/scan-logs` | 日志异常扫描 |
| 报告 | `GET /reports` | 运维报告列表 |
| 用户 | `GET /users` | 用户管理（Admin） |
| 审计 | `GET /audit-logs` | 审计日志 |

---

## ⚙️ 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `POSTGRES_HOST` | `postgres` | PostgreSQL 主机（Docker 内用服务名） |
| `POSTGRES_PORT` | `5432` | PostgreSQL 端口 |
| `POSTGRES_DB` | `vigilops` | 数据库名 |
| `POSTGRES_USER` | `vigilops` | 数据库用户 |
| `POSTGRES_PASSWORD` | — | 数据库密码（必填） |
| `REDIS_HOST` | `redis` | Redis 主机 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `JWT_SECRET_KEY` | — | JWT 签名密钥（必填） |
| `AI_PROVIDER` | `deepseek` | AI 提供商 |
| `AI_API_KEY` | — | AI API 密钥（启用 AI 功能需要） |
| `AI_API_BASE` | `https://api.deepseek.com/v1` | AI API 地址 |
| `AI_MODEL` | `deepseek-chat` | AI 模型名称 |

### Agent 配置

Agent 支持以下采集能力（在 `agent.yaml` 中配置）：

- **系统指标** — CPU、内存、磁盘、网络
- **Docker 自动发现** — 零配置监控所有容器
- **网络带宽** — 发送/接收速率、丢包率
- **数据库监控** — PostgreSQL / MySQL / Oracle

---

## 🛣️ Roadmap

- [x] Phase 1: 基础监控（服务器 + 服务 + 告警）
- [x] Phase 2: 日志管理 + 数据库监控
- [x] Phase 3: AI 智能分析
- [x] Phase 4: 团队管理 + 运维报告 + 多渠道通知
- [ ] Phase 5: 自定义仪表盘 + 服务拓扑图
- [ ] Phase 6: SLA 管理 + 可用性报告

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交代码 (`git commit -m 'feat: add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

---

## 📄 License

[Apache License 2.0](LICENSE)

---

<p align="center">
  <b>VigilOps</b> — 让运维更智能 🛡️
</p>
