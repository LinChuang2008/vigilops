# VigilOps Consensus

## Last Updated
2026-02-25 20:50

## Current Phase
P0 技术债清偿 → P1 功能完善 → Cycle 9 收尾

## 记忆系统
- **API**: `http://localhost:8002`
- **Namespace**: `vigilops`
- 所有运营循环：开始 recall → 结束 store

---

## CTO 全面评估（2026-02-25）
- **总代码**: 2.5 万行，133 文件
- **综合评分**: 7.2/10
- **亮点**: AI 分析 8/10, 自动修复 8/10, Dashboard/WS 8/10, 通知系统 8/10
- **短板**: 错误处理薄弱, 日志存 PG 不可扩展, API 无限流, 数据无保留策略
- **战略**: 把 AI 做深不做广，先还技术债再推广

## 已完成 Cycle

| Cycle | 内容 | 状态 |
|-------|------|------|
| 1-3 | 核心监控 + AI 分析 | ✅ |
| 4 | 自动修复系统 | ✅ |
| 5 | Dashboard WebSocket + 健康评分 + 拓扑图 | ✅ |
| 5.5 | ECS 部署 | ✅ |
| 6 | AI 记忆增强（Engram 集成） | ✅ |
| 7 | GitHub 开源运营物料 | ✅ |
| 8 | 多服务器拓扑（分层钻取） | ✅ |
| 9 (部分) | Agent 安装脚本、客户文档、CI/CD、获客文章 9 篇 | ✅ |

---

## 🔴 P0 必须做（当前执行中）

| # | 任务 | 工作量 | 状态 |
|---|------|--------|------|
| 1 | 全局错误处理中间件 | 0.5天 | ✅ commit 3974010 |
| 2 | JWT 密钥安全加固 | 0.5天 | ✅ commit 3974010 |
| 3 | 备份/恢复脚本 | 0.5天 | ✅ commit 3974010 |
| 4 | API 限流 + 安全加固 | 1天 | ✅ commit d14338a |
| 5 | 监控数据保留策略（自动清理旧数据） | 1天 | ⏳ 待做 |
| 6 | 告警去重/聚合 | 1天 | ⏳ 待做 |
| 7 | MCP Server 接入（FastMCP，暴露核心运维工具给 AI Agent） | 0.5天 | ⏳ 待做 |

## 🟡 P1 应该做（P0 完成后）

| # | 任务 |
|---|------|
| 1 | NotificationLogs 完善（当前仅 57 行半成品） |
| 2 | 告警升级 + 值班排期 |
| 3 | Dashboard 可定制 |
| 4 | AI 反馈闭环 |
| 5 | 暗色主题 |
| 6 | HTTPS 支持 |
| 7 | 前端空状态/错误状态优化 |
| 8 | Login 页面美化 |

## 🟢 P2 锦上添花

| # | 任务 |
|---|------|
| 1 | 日志后端切换（ClickHouse/Loki） |
| 2 | 移动端适配 |
| 3 | Prometheus 兼容 |
| 4 | OAuth/LDAP |
| 5 | 国际化 i18n |

## ECS 连通性（2026-02-25 20:10 测试）
- ✅ 前端 :3001 → HTTP 200（可访问）
- ❌ 后端 :8001 → 直接访问超时（通过 nginx 反代正常）
- ❌ SSH :22 → 超时（阿里云安全组白名单限制）
- **结论**: 服务器正常运行，SSH 需要加 IP 白名单

## Cycle 9 收尾（P0/P1 完成后）

### 已完成
- ✅ 定价调研报告 + Onboarding SOP + CI/CD 工作流
- ✅ Agent 一键安装脚本（含离线模式）
- ✅ 客户快速部署文档 + Landing Page
- ✅ 获客文章 9 篇
- ✅ Docker Compose 端口变量化 + quickstart 模板
- ✅ Demo 账号 + 自定义 favicon + CHANGELOG.md
- ✅ 代码已 push GitLab + GitHub

### 待做（需董事长操作）
- Docker 镜像推送到 GHCR（需 GitHub PAT）
- GitHub repo 添加 topic 标签（需 PAT 或手动）
- 获客文章正式发布（董事长审核中）
- ECS SSH 白名单（加当前 IP）

## MCP Server 接入方案（P0-7）
- **技术方案**: FastMCP (Python) 原生集成，独立模块 `backend/app/mcp/`
- **代码量**: ~150-200 行，1 轮 Coder
- **CEO 评估**: 可行性 9/10，战略价值 10/10
- **核心 Tools（第一版）**:
  1. `get_servers_health` — 服务器健康状态+关键指标
  2. `get_alerts` — 告警列表，支持严重程度过滤
  3. `search_logs` — 日志搜索，支持关键词+时间范围
  4. `analyze_incident` — AI 根因分析（差异化杀手锏）
  5. `get_topology` — 服务拓扑数据
- **P1 扩展**: `trigger_remediation`(自动修复), `get_sla_status`, `generate_report`
- **竞品**: Grafana 有官方 MCP，Zabbix 仅社区版，Prometheus 无。VigilOps 可打"首个原生支持 MCP 的开源运维平台+AI分析"
- **约束**: Python 3.9 兼容，`pip install fastmcp`，不引入重量级依赖

## 决策日志
- **2026-02-25 20:50**: 董事长批准 MCP Server 接入方案，排入 P0-7。CEO 评估：可行性 9/10，战略价值 10/10，0.5 天工作量。
- **2026-02-25 16:20**: AI 公司 cron 模型从 opus 切换为 sonnet（省配额、避免 timeout）。CEO 层用 sonnet，遇到复杂架构任务可用 opus 派子 Agent。
- **2026-02-25 15:57**: 董事长确认按 CTO 评估的 P0→P1→P2 清单排期推进，AI 公司 cron 自动执行。
- **2026-02-25 15:55**: P0 第一批完成（JWT/错误处理/备份），commit 3974010。
- **2026-02-25**: Engram 决定不独立开源。GitHub Discussions 开通 + 5 篇种子帖。README 修复。

## Company State
- **Product**: VigilOps (开源, GitHub + ECS 已部署)
- **Revenue**: ¥0
- **Users**: 0
- **Monthly Cost**: ¥388
- **Demo**: http://139.196.210.68:3001 (demo@vigilops.io / demo123)
- **Score**: 7.2/10 (CTO 评估 2026-02-25)
