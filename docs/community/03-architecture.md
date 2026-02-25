# 🏗️ Architecture Overview

**Category: Q&A**

---

A deep dive into how VigilOps is built and how the pieces fit together.

## System Architecture

```
                         ┌─────────────────┐
                         │   Web Browser    │
                         │  (React + Ant    │
                         │   Design + TS)   │
                         └────────┬─────────┘
                                  │ HTTP / WebSocket
                         ┌────────▼─────────┐
                         │  FastAPI Backend  │
                         │   (Python 3.11)  │
                         ├──────────────────┤
                         │  24 API Routers  │
                         │  7 Core Services │
                         │  Remediation     │
                         │    Engine        │
                         └───┬──────┬───┬───┘
                             │      │   │
                    ┌────────┘      │   └────────┐
                    ▼               ▼            ▼
              ┌──────────┐  ┌──────────┐  ┌──────────┐
              │PostgreSQL │  │  Redis   │  │ DeepSeek │
              │  (Data)   │  │ (Cache/  │  │   API    │
              │           │  │  PubSub) │  │  (AI)    │
              └──────────┘  └──────────┘  └──────────┘

        ┌─────────────────────────────────────────────┐
        │           Target Servers                     │
        │  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
        │  │ Agent 1 │  │ Agent 2 │  │ Agent N │     │
        │  │ (Python) │  │ (Python) │  │ (Python) │     │
        │  └─────────┘  └─────────┘  └─────────┘     │
        └─────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + TypeScript + Ant Design + ECharts |
| **Backend** | FastAPI (Python) + SQLAlchemy + Pydantic |
| **Database** | PostgreSQL 15 |
| **Cache** | Redis 7 |
| **AI Engine** | DeepSeek API |
| **Deployment** | Docker Compose (4 containers) |
| **Agent** | Python daemon, systemd managed, HTTP reporting |

## Backend Modules

### API Layer (24 Routers)
- **Auth & Users** — JWT authentication, RBAC
- **Infrastructure** — Hosts, servers, server groups, services
- **Monitoring** — Dashboard (WebSocket real-time), logs, databases
- **Intelligence** — AI analysis (conversation, root cause, insights)
- **Alerting** — Alert rules (metric/log/DB threshold), alert management
- **Notifications** — 5 channels (DingTalk, Feishu, WeCom, Email, Webhook) + templates
- **Operations** — Remediation, reports, SLA, audit logs
- **Visualization** — Service topology (force-directed & hierarchical layouts)
- **Agent** — Data ingestion + token management

### Core Services (7)
| Service | Responsibility |
|---------|---------------|
| AI Engine | DeepSeek integration — log analysis, root cause, topology suggestions |
| Anomaly Scanner | Automatic anomaly detection across metrics |
| Notifier | Notification dispatch with noise reduction (cooldown + silence periods) |
| Report Generator | Auto-generate daily/weekly ops reports |
| Memory Client | Integration with Engram memory system for operational context |
| Alert Seed | Generate seed data for demo/testing |
| Audit | Track all user and system actions |

### Auto-Remediation Engine
The crown jewel — a closed-loop system:

```
Alert Triggered → AI Diagnosis → Safety Check → Runbook Execution → Resolved
```

**6 Built-in Runbooks:**
1. `disk_cleanup` — Clear temp files, old logs
2. `service_restart` — Graceful service restart
3. `memory_pressure` — Mitigate memory hogs
4. `log_rotation` — Rotate and compress logs
5. `zombie_killer` — Terminate zombie processes
6. `connection_reset` — Reset stuck connections

## Frontend (22 Pages)
- Dashboard with real-time WebSocket metrics and health scoring
- Server & service management with detailed views
- Interactive service topology with drag-and-drop layout
- Log search with real-time streaming
- Database monitoring (slow queries, connections, QPS)
- AI analysis console with conversation interface
- Full notification and SLA management

## Data Flow

1. **Collection**: Agents on target servers report metrics via HTTP to the backend
2. **Storage**: Metrics stored in PostgreSQL, hot data cached in Redis
3. **Analysis**: Anomaly scanner + AI engine process incoming data
4. **Alerting**: Rules engine evaluates thresholds, triggers alerts
5. **Remediation**: AI diagnoses root cause → selects runbook → safety check → execute
6. **Notification**: Results sent via configured channels with dedup/cooldown

---

## 🇨🇳 中文版

详细架构说明请参考上方英文版。核心要点：

- **4 容器部署**: Backend + Frontend + PostgreSQL + Redis
- **24 个 API 路由** 覆盖监控全流程
- **AI 自动修复闭环**: 告警 → 诊断 → 安全检查 → 执行 → 修复
- **Agent 架构**: Python 守护进程部署在目标服务器，HTTP 上报数据

有架构相关问题？在下方回复讨论！
