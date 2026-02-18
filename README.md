<div align="center">

# 🛡️ VigilOps

**AI-powered infrastructure monitoring that watches, analyzes, and heals your systems — automatically.**

[![Stars](https://img.shields.io/github/stars/LinChuang2008/vigilops?style=social)](https://github.com/LinChuang2008/vigilops)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://hub.docker.com/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Demo](https://vigilops.dev) · [Docs](https://docs.vigilops.dev) · [Discord](https://discord.gg/vigilops) · [中文](#-中文简介)

</div>

---

Most monitoring tools tell you something broke. **VigilOps tells you why — and fixes it.**

Built with an AI Agent at its core, VigilOps goes beyond dashboards and alerts. It understands your infrastructure topology, predicts failures before they happen, and autonomously remediates common issues — so your on-call team can finally sleep.

![Dashboard](docs/screenshots/dashboard.png)

## ✨ Features

- 🖥️ **Server Monitoring** — CPU, memory, disk, network with real-time metrics
- 🔌 **Service Health Checks** — HTTP, TCP, gRPC endpoint monitoring with latency tracking
- 🗄️ **Database Monitoring** — PostgreSQL, MySQL, Redis performance & connection pooling
- 🤖 **AI-Powered Analysis** — Root cause detection, anomaly prediction, intelligent correlation
- 🔧 **AI Agent Auto-Remediation** *(NEW)* — Autonomous incident response: restart services, scale resources, roll back deployments
- 🚨 **Smart Alerting** — Context-aware alerts with noise reduction, escalation policies
- 📊 **SLA Tracking** — Uptime SLOs, error budgets, compliance reports
- 📝 **Operations Reports** — Auto-generated daily/weekly runbooks and incident summaries
- 🗺️ **Service Topology** — Interactive dependency maps with real-time health overlay
- 🎨 **15+ Dashboard Pages** — Beautiful, responsive UI built with React + TypeScript

![Service Topology](docs/screenshots/topology.png)

## 🚀 Quick Start

Get VigilOps running in under 2 minutes:

```bash
# Clone the repository
git clone https://github.com/LinChuang2008/vigilops.git
cd vigilops

# Start all services
docker compose up -d

# Open the dashboard
open http://localhost:3000
```

Default credentials: `admin` / `vigilops`

That's it. No complex configuration needed.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  React Frontend                  │
│              (TypeScript + Vite)                  │
└─────────────────────┬───────────────────────────┘
                      │ REST / WebSocket
┌─────────────────────▼───────────────────────────┐
│               FastAPI Backend                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Monitors │ │ Alerting │ │   AI Agent       │ │
│  │ Engine   │ │ Engine   │ │   (Auto-Heal)    │ │
│  └────┬─────┘ └────┬─────┘ └────────┬─────────┘ │
│       │             │                │           │
│  ┌────▼─────────────▼────────────────▼─────────┐ │
│  │          Core Service Layer                  │ │
│  └──────┬──────────────────┬────────────────────┘ │
└─────────┼──────────────────┼────────────────────┘
          │                  │
  ┌───────▼──────┐   ┌──────▼───────┐
  │ PostgreSQL   │   │    Redis     │
  │ (persistent) │   │   (cache +   │
  │              │   │    pub/sub)  │
  └──────────────┘   └──────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Vite, Ant Design |
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy |
| **Database** | PostgreSQL 15+, Redis 7+ |
| **AI** | DeepSeek API, 自研 AI Agent (~500行) |
| **Infra** | Docker, Docker Compose, Nginx |

## 🤝 Contributing

We love contributions! Whether it's bug reports, feature requests, or pull requests — every bit helps.

Please read our [Contributing Guide](CONTRIBUTING.md) to get started.

```bash
# Set up dev environment
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
pip install -r requirements-dev.txt
cd frontend && npm install
```

## 📄 License

[Apache 2.0](LICENSE) — use it, fork it, ship it.

---

## 🇨🇳 中文简介

**VigilOps** 是一个 AI 驱动的基础设施监控平台。与传统监控工具不同，VigilOps 内置 AI Agent，不仅能发现问题、分析根因，还能**自动修复**常见故障——重启服务、扩容资源、回滚部署，无需人工介入。

**核心能力：**
- 服务器 / 服务 / 数据库全方位监控
- AI 智能分析与异常预测
- AI Agent 自动修复（全新功能）
- 告警降噪与升级策略
- SLA 追踪与运维报告自动生成
- 服务拓扑可视化

**快速体验：**
```bash
git clone https://github.com/LinChuang2008/vigilops.git
cd vigilops && docker compose up -d
```

访问 `http://localhost:3000`，默认账号 `admin` / `vigilops`。

欢迎 Star ⭐ 和贡献代码！

---

<div align="center">
  <sub>Built with ❤️ by the VigilOps community</sub>
</div>
