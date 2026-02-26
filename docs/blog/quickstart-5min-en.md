# Deploy AI-Powered Server Monitoring in 10 Minutes with VigilOps

> Target: Hacker News, Reddit r/selfhosted r/devops, Dev.to
> Keywords: open source monitoring, AI ops, self-hosted, auto-remediation, server monitoring, observability

---

## The Problem

You're running a small team. Your monitoring setup is one of:

1. **Nothing** — you find out about outages from angry users
2. **Prometheus + Grafana + AlertManager** — took a day to set up, still no auto-remediation
3. **Datadog/New Relic** — works great, costs $15-50/host/month

What if you could have **Datadog-level intelligence** (AI root cause analysis, auto-remediation) with **self-hosted simplicity** (Docker Compose, 2 minutes)?

That's VigilOps.

---

## What You Get

- **AI Root Cause Analysis** — not just "CPU is high", but "Process X has a memory leak causing GC pressure"
- **6 Auto-Remediation Runbooks** — disk cleanup, service restart, memory pressure relief, log rotation, zombie process killer, connection reset
- **5 Notification Channels** — DingTalk, Feishu, WeCom, Email, Webhook
- **24 Dashboard Pages** — servers, services, databases, topology maps, SLA tracking
- **Ops Memory System** — AI remembers past incidents and references them for future diagnosis

All open source. Apache 2.0. Self-hosted. Your data never leaves your servers.

---

## Step 1: Deploy (2 minutes)

```bash
git clone https://github.com/LinChuang2008/vigilops.git
cd vigilops
cp .env.example .env
docker compose up -d
```

Four containers come up: backend (FastAPI), frontend (React), PostgreSQL, Redis.

Open `http://your-server:3001` → Login with `demo@vigilops.io` / `demo123`.

## Step 2: Install Agent (3 minutes)

On each server you want to monitor:

1. Copy `agent/agent.example.yaml` from the project and configure server URL + token
2. Run `python -m vigilops_agent` or set up as systemd service
3. Agent token can be created in VigilOps backend **Settings → Agent Token Management**

The agent reports metrics every 30 seconds. Lightweight (~20MB RAM).

See `agent/` directory for configuration examples.

## Step 3: Configure Alerts (1 minute)

Three alert types out of the box:

| Type | Example |
|------|---------|
| Metric threshold | CPU > 90%, Disk > 85% |
| Log keyword | `ERROR`, `OOM`, `Connection refused` |
| Database threshold | Slow queries > 10/min |

## Step 4: Watch the AI Work (1 minute)

When an alert fires, click **"AI Analysis"**:

1. AI correlates logs, metrics, and topology within the time window
2. Produces a root cause report with confidence scores
3. Suggests (or automatically executes) remediation

The built-in runbooks handle the most common incidents automatically, with safety checks and approval workflows.

---

## Architecture

```
  Monitored Servers        VigilOps Platform         You
  ┌──────────┐           ┌────────────────┐       ┌──────────┐
  │  Agent   │──metrics─▶│  FastAPI + AI  │─────▶│ DingTalk  │
  │  (light) │  report   │  + Remediation │ alert│ Email     │
  └──────────┘           └───────┬────────┘      │ Webhook   │
                                 │               └──────────┘
                          ┌──────┴───────┐
                          │  React UI    │
                          │  24 pages    │
                          └──────────────┘
```

## Comparison

| | VigilOps | Zabbix | Prom+Grafana | Datadog |
|---|---|---|---|---|
| Setup time | ~10 min | Hours | Hours | Minutes |
| AI analysis | ✅ Built-in | ❌ | ❌ | 💰 Add-on |
| Auto-remediation | ✅ 6 runbooks | ❌ | ❌ | 💰 Enterprise |
| Self-hosted | ✅ | ✅ | ✅ | ❌ |
| Cost | **Free** | Free | Free | $15/host/mo+ |
| License | Apache 2.0 | GPL | Apache | Proprietary |

## Tech Stack

- **Backend**: Python / FastAPI
- **Frontend**: React / TypeScript / Ant Design
- **Database**: PostgreSQL + Redis
- **AI**: DeepSeek API (swappable with any OpenAI-compatible model)
- **Deployment**: Docker Compose

---

## Links

- **GitHub**: [github.com/LinChuang2008/vigilops](https://github.com/LinChuang2008/vigilops)
- **Star the repo** if this is useful ⭐
- **Issues & PRs welcome**: [CONTRIBUTING.md](https://github.com/LinChuang2008/vigilops/blob/main/CONTRIBUTING.md)

---

*VigilOps — monitoring that watches, analyzes, and heals.*
