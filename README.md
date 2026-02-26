<div align="center">

# 🛡️ VigilOps

**Your team is drowning in alerts. Most of them don't matter. VigilOps fixes that.**

[![Stars](https://img.shields.io/github/stars/LinChuang2008/vigilops?style=social)](https://github.com/LinChuang2008/vigilops)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v0.9.0-blue)](https://github.com/LinChuang2008/vigilops/releases)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://github.com/LinChuang2008/vigilops)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Live Demo](http://139.196.210.68:3001) · [Docs](#-documentation) · [中文](#-中文)

</div>

---

## The Problem

You set up Prometheus and Grafana. You configured alert rules. Now you get 200+ alerts per day, and 80% are noise. Your on-call engineer gets woken up at night for issues that either resolve themselves or could be fixed with a simple script.

**The monitoring industry has a dirty secret: most tools are great at telling you something is wrong, but terrible at doing anything about it.**

VigilOps takes a different approach. Instead of just sending you more alerts, it:

1. **Analyzes** each alert with AI (DeepSeek) to determine root cause
2. **Decides** if it can be auto-fixed using a built-in Runbook
3. **Fixes** the issue automatically (with safety checks and approval workflows)
4. **Learns** — so the same type of issue gets resolved faster next time

The result: fewer alerts that wake you up, faster resolution when something real happens.

> ⚠️ **Honest disclaimer**: VigilOps is an early-stage open source project. It works, it's deployed in real environments, but it's not battle-tested at scale yet. We're looking for early adopters who want to shape the product. If you need enterprise-grade reliability today, Datadog or PagerDuty are safer choices.

---

## See It In Action

```
  Alert Triggered        AI Diagnoses           Runbook Executes        Resolved
  ┌──────────┐        ┌───────────────┐        ┌────────────────┐     ┌──────────┐
  │ Disk 95% │───────▶│ Root Cause    │───────▶│ disk_cleanup   │────▶│ Disk 60% │
  │ Alert    │        │ Analysis      │        │ runbook runs   │     │ ✅ Fixed  │
  └──────────┘        └───────────────┘        └────────────────┘     └──────────┘
       │                      │                         │
   Monitors               DeepSeek AI             Safety checks +
   detect issue           correlates logs          approval before
                          & metrics                execution
```

**6 Built-in Runbooks** — ready out of the box:

| Runbook | What it does |
|---------|-------------|
| 🧹 `disk_cleanup` | Clears temp files, old logs, reclaims disk space |
| 🔄 `service_restart` | Gracefully restarts failed services |
| 💾 `memory_pressure` | Identifies and mitigates memory-hogging processes |
| 📝 `log_rotation` | Rotates and compresses oversized logs |
| 💀 `zombie_killer` | Detects and terminates zombie processes |
| 🔌 `connection_reset` | Resets stuck connections and connection pools |

---

## Quick Start

```bash
git clone https://github.com/LinChuang2008/vigilops.git
cd vigilops
cp .env.example .env   # Edit with your DeepSeek API key
docker compose up -d
```

Open `http://localhost:3001`. That's it.

**🎯 Don't want to install? Try the live demo:**

> [http://139.196.210.68:3001](http://139.196.210.68:3001)
> Login: `demo@vigilops.io` / `demo123` (read-only)
>
> ⚠️ This is a single demo server — it may be slow or temporarily down. For real evaluation, self-host it.

---

## What's Inside

- **AI Root Cause Analysis** — DeepSeek analyzes logs, metrics, and topology to explain *why* something broke
- **Auto-Remediation** — 6 built-in Runbooks with safety checks; AI picks the right one and runs it
- **MCP Server** — 5 MCP tools for AI Agent integration (query alerts, run diagnostics, execute runbooks)
- **Full-Stack Monitoring** — Servers (CPU/mem/disk/net), services (HTTP/TCP/gRPC), databases (PostgreSQL/MySQL)
- **Smart Alerting** — Metric, log keyword, and DB threshold rules with noise reduction and cooldown
- **Alert Escalation** — Auto-escalation policies with on-call calendar and coverage analysis
- **Log Management** — Multi-backend support: PostgreSQL, ClickHouse, or Loki
- **Service Topology** — Interactive dependency maps with health overlay
- **5 Notification Channels** — DingTalk, Feishu (Lark), WeCom, Email, Webhook
- **SLA Tracking** — Uptime SLOs, error budgets, violation alerts
- **i18n** — Chinese and English UI with ~300 translation keys
- **24 Dashboard Pages** — Built with React 19 + TypeScript + Ant Design 6

---

## Honest Comparison

We believe in transparent positioning. Here's how VigilOps compares — including where we fall short:

| | VigilOps | Nightingale (夜莺) | Prometheus+Grafana | Datadog | Zabbix |
|---|---|---|---|---|---|
| **AI Root Cause Analysis** | ✅ Built-in | ❌ | ❌ | 💰 Add-on | ❌ |
| **Auto-Remediation** | ✅ 6 Runbooks | ❌ | ❌ | 💰 Enterprise | ❌ |
| **MCP Integration** | ✅ 5 tools | ❌ | ❌ | 🟡 Early | ❌ |
| **Self-Hosted** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Open Source** | ✅ Apache 2.0 | ✅ Apache 2.0 | ✅ | ❌ | ✅ GPL |
| **Setup Complexity** | Low (Docker) | Low | High (multi-component) | Low (SaaS) | Medium |
| **Community Size** | 🔴 Small (new project) | ⭐ 8k+ stars | ⭐⭐⭐ Massive | N/A | ⭐⭐ Large |
| **Production Maturity** | 🔴 Early stage | ✅ 1000+ enterprises | ✅ Industry standard | ✅ Industry leader | ✅ Decades |
| **High Availability** | 🔴 Single-node only | ✅ | ✅ | ✅ | ✅ |
| **Scale (hosts)** | 🟡 Tested <50 | ✅ 1000+ | ✅ 10000+ | ✅ Unlimited | ✅ 10000+ |
| **Ecosystem / Plugins** | 🔴 Limited | 🟡 Growing | ✅ Huge | ✅ 700+ | ✅ Large |
| **Cost** | Free | Free / Enterprise paid | Free | $$$$ | Free / Enterprise paid |

**Where we're strong**: AI-driven alert analysis and auto-remediation in a single open-source package. No other open-source tool does this today.

**Where we're weak**: Community size, production maturity, and scale. We're honest about this — VigilOps is best suited for small-to-medium teams (< 50 hosts) who want to experiment with AI-powered operations.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 19, TypeScript, Vite, Ant Design 6, ECharts 6 |
| **Backend** | Python 3.9+, FastAPI, SQLAlchemy |
| **Database** | PostgreSQL 15+, Redis 7+ |
| **Log Storage** | PostgreSQL / ClickHouse / Loki (configurable) |
| **AI** | DeepSeek API (configurable LLM endpoint) |
| **Deployment** | Docker Compose |

## Architecture

```
┌──────────────────────────────────────────────────┐
│              React 19 Frontend                    │
│          (TypeScript + Vite + Ant Design 6)       │
└───────────────────┬──────────────────────────────┘
                    │ REST / WebSocket
┌───────────────────▼──────────────────────────────┐
│              FastAPI Backend                       │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────┐ │
│  │ 29       │ │ Alerting  │ │ AI Agent         │ │
│  │ Routers  │ │ + Escala- │ │ + Runbook Engine │ │
│  │          │ │ tion      │ │ + MCP Server     │ │
│  └────┬─────┘ └────┬──────┘ └────────┬─────────┘ │
│       └─────────────┼────────────────┘            │
│              Core Services (13)                    │
└──────┬──────────────┼────────────────────────────┘
       │              │
┌──────▼──────┐ ┌─────▼──────┐
│ PostgreSQL  │ │   Redis    │
│ (data +     │ │ (cache +   │
│  logs)      │ │  pub/sub)  │
└─────────────┘ └────────────┘
```

---

## Documentation

| Doc | Description |
|-----|-------------|
| [Getting Started](docs/getting-started.md) | First-time setup guide |
| [Installation](docs/installation.md) | Docker / manual deploy + env vars |
| [User Guide](docs/user-guide.md) | Full feature walkthrough |
| [API Reference](docs/api-reference.md) | REST API docs |
| [Architecture](docs/architecture.md) | System design + data flow |
| [Contributing](docs/contributing.md) | Dev environment + code standards |
| [Changelog](docs/changelog.md) | Version history |

## Contributing

We welcome contributions — especially from people who experience alert fatigue firsthand.

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
pip install -r requirements-dev.txt
cd frontend && npm install
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

[Apache 2.0](LICENSE) — use it, fork it, ship it.

---

## 🇨🇳 中文

### 你的团队每天被几百条告警淹没？

大多数运维工程师都经历过这样的场景：Prometheus 告警规则配好了，钉钉群每天弹出 200+ 条告警，其中 80% 是噪音。真正需要处理的问题被淹没在告警洪流中，值班工程师被反复叫醒处理那些本可以用一个脚本解决的问题。

**监控行业有个公开的秘密：大多数工具擅长告诉你出了问题，但不擅长解决问题。**

VigilOps 走了一条不同的路。它不只是发送更多告警，而是：

1. **用 AI 分析**每条告警的根因（基于 DeepSeek）
2. **判断**是否可以通过内置 Runbook 自动修复
3. **自动修复**问题（带安全检查和审批流程）
4. **持续学习**，同类问题下次更快解决

结果：更少的无效告警打扰你，真正的问题更快被解决。

> ⚠️ **诚实声明**：VigilOps 是一个早期开源项目。它能工作，已在真实环境部署，但还未经过大规模生产验证。我们正在寻找愿意一起打磨产品的早期用户。如果你现在就需要企业级可靠性，Datadog 或夜莺是更成熟的选择。

### 快速开始

```bash
git clone https://github.com/LinChuang2008/vigilops.git
cd vigilops
cp .env.example .env   # 填入你的 DeepSeek API Key
docker compose up -d
```

打开 `http://localhost:3001` 即可使用。

**🎯 在线体验：** [http://139.196.210.68:3001](http://139.196.210.68:3001) — 账号 `demo@vigilops.io` / `demo123`（只读）

### 核心差异化

**夜莺让你看到问题，VigilOps 帮你修好问题。**

- ✅ AI 根因分析 + 自动修复 — 开源方案中唯一提供此能力
- ✅ 6 个内置 Runbook — 磁盘清理、服务重启、内存释放、日志轮转、僵尸进程、连接重置
- ✅ MCP Server — 5 个工具，支持 AI Agent 集成
- ✅ 全栈监控 — 服务器 / 服务 / 数据库 / 日志 / 拓扑
- ✅ 中英双语 — 完整的国际化支持
- ✅ Docker 一键部署 — 无复杂依赖

### 我们的不足（诚实说）

- 🔴 社区很小 — 这是一个新项目，还没有大规模用户验证
- 🔴 仅支持单节点 — 没有高可用方案
- 🔴 测试规模有限 — 建议 50 台主机以内
- 🔴 生态有限 — 插件和集成还很少

如果这些对你来说可以接受，欢迎试用并告诉我们你的反馈。每一位早期用户的声音都非常重要。

### 联系我们

- [GitHub Discussions](https://github.com/LinChuang2008/vigilops/discussions) — 提问、建议、交流
- [报告 Bug](https://github.com/LinChuang2008/vigilops/issues/new)
- 📧 [support@lchuang.net](mailto:support@lchuang.net)

---

<div align="center">

<sub>Built with ❤️ by LinChuang · Apache 2.0</sub>

</div>
