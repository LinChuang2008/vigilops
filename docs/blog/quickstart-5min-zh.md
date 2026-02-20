# 5 分钟搭建 AI 运维监控：VigilOps 快速上手教程

> 发布平台：知乎专栏 / 掘金 / CSDN / SegmentFault
> 关键词：运维监控、AI 运维、开源监控、Docker 部署、AIOps、服务器监控、自动修复
> 目标读者：运维工程师、后端开发、独立开发者、中小企业 IT 负责人

---

## 为什么要读这篇文章？

你是不是也遇到过这些场景：

- 半夜 3 点收到告警短信，爬起来一看——磁盘满了 😤
- 服务挂了 30 分钟才发现，老板问"为什么没人管？"
- Prometheus + Grafana + AlertManager 配了一天，还没接上告警通知
- 想用 Datadog，一看价格——算了算了

**VigilOps 解决的就是这些问题**：开源免费、Docker 一键部署、AI 自动分析根因、内置 6 个自动修复脚本。从部署到收到第一条智能告警，真的只要 5 分钟。

---

## 第 1 步：部署 VigilOps（2 分钟）

### 前置条件

- 一台 Linux 服务器（2 核 4G 起步，CentOS/Ubuntu/Debian 均可）
- Docker + Docker Compose 已安装

> 💡 **没有 Docker？** 一行命令搞定：`curl -fsSL https://get.docker.com | sh`

### 克隆 & 启动

```bash
# 克隆项目
git clone https://github.com/LinChuang2008/vigilops.git
cd vigilops

# 复制环境配置
cp .env.example .env

# 启动所有服务（后端 + 前端 + PostgreSQL + Redis）
docker compose up -d
```

等待约 1-2 分钟，四个容器全部启动：

```bash
docker compose ps
# NAME                STATUS
# vigilops-backend    Up
# vigilops-frontend   Up
# vigilops-postgres   Up
# vigilops-redis      Up
```

打开浏览器访问 `http://你的服务器IP:3001`，看到登录页就成功了 🎉

### 默认账号

- 用户名：`admin`
- 密码：`admin123`

> ⚠️ 生产环境请立即修改密码！

---

## 第 2 步：安装 Agent 到被监控服务器（1 分钟）

VigilOps 通过轻量 Agent 采集服务器指标。在**需要监控的服务器**上执行：

```bash
# 一键安装（替换为你的 VigilOps 地址和 Token）
curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/agent/install.sh | \
  bash -s -- --server http://你的VigilOps地址:8001 --token 你的AgentToken
```

Agent Token 在 VigilOps 后台 **设置 → Agent Token 管理** 中创建。

安装完成后，Agent 会自动以 systemd 服务运行，每 30 秒上报一次指标数据。

> 💡 **内网/离线环境？** 支持离线安装模式：
> ```bash
> bash install.sh --server http://内网地址:8001 --token TOKEN --local
> ```

---

## 第 3 步：配置告警规则 + 通知（1 分钟）

### 创建告警规则

进入 **告警规则** 页面，VigilOps 支持三种类型：

| 类型 | 场景举例 |
|------|---------|
| **指标告警** | CPU > 90%、磁盘 > 85%、内存 > 95% |
| **日志关键字** | 检测到 `ERROR`、`OOM`、`Connection refused` |
| **数据库阈值** | 慢查询 > 10/min、连接数 > 80% |

点击「新建规则」，选择指标和阈值，30 秒搞定一条规则。

### 接入通知渠道

VigilOps 内置 5 种通知渠道，按你团队的习惯选：

- 🔔 **钉钉机器人** — 填入 Webhook URL
- 📱 **飞书机器人** — 填入 Webhook URL
- 💬 **企业微信** — 填入 Webhook URL
- ✉️ **邮件** — 配置 SMTP
- 🌐 **Webhook** — 自定义 HTTP 回调

在 **通知渠道** 页面配置，测试发送成功就 OK。

---

## 第 4 步：体验 AI 分析（1 分钟）

这是 VigilOps 的杀手级功能。

### AI 根因分析

当告警触发时，点击告警详情中的 **「AI 分析」** 按钮：

1. AI 自动关联时间窗口内的日志、指标、拓扑信息
2. 给出根因分析报告（不只是"CPU 高"，而是"某个 Java 进程内存泄漏导致频繁 GC 引发 CPU 飙升"）
3. 推荐修复方案

### AI 自动修复

VigilOps 内置 6 个经过验证的 Runbook，常见问题自动处理：

| Runbook | 自动做什么 |
|---------|-----------|
| 🧹 磁盘清理 | 清理临时文件、旧日志，释放空间 |
| 🔄 服务重启 | 优雅重启故障服务 |
| 💾 内存释放 | 识别并处理内存占用异常进程 |
| 📝 日志轮转 | 切割压缩超大日志文件 |
| 💀 僵尸进程清理 | 检测并终止僵尸进程 |
| 🔌 连接重置 | 重置卡死的连接和连接池 |

所有自动修复操作都有**安全检查 + 审批流程**，不会乱来。

### 运维记忆系统

VigilOps 还有独特的**运维记忆功能**：

- 修复过的故障自动记录经验
- 下次遇到类似问题，AI 会参考历史处理方案
- 相当于给你的运维团队配了一个永远不忘事的「老师傅」

---

## 架构一图看懂

```
  被监控服务器           VigilOps 平台              你
  ┌─────────┐         ┌──────────────┐         ┌──────┐
  │  Agent   │──指标──▶│  Backend API │──告警──▶│ 钉钉  │
  │  (轻量)  │  上报   │  + AI Engine │  通知   │ 飞书  │
  └─────────┘         │  + 自动修复   │         │ 企微  │
                      └──────┬───────┘         └──────┘
                             │
                      ┌──────┴───────┐
                      │   前端 UI    │
                      │  22 个页面   │
                      └──────────────┘
```

---

## 和其他方案对比

| | VigilOps | Zabbix | Prometheus+Grafana | Datadog |
|---|---|---|---|---|
| **部署时间** | ~2 分钟 | 2-4 小时 | 1-2 小时 | 10 分钟 |
| **AI 分析** | ✅ 内置 | ❌ | ❌ | 💰 付费插件 |
| **自动修复** | ✅ 6 个 Runbook | ❌ | ❌ | 💰 企业版 |
| **通知渠道** | 5 种（钉飞企邮 Hook） | 需配置 | 需额外组件 | ✅ |
| **费用** | **免费开源** | 免费 | 免费 | $15/主机/月起 |
| **上手难度** | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

---

## 常见问题

### Q: 最低配置要求？
A: 2 核 4G 内存，20G 磁盘。监控 10 台以内服务器绰绰有余。

### Q: 支持哪些数据库监控？
A: PostgreSQL、MySQL、Oracle，开箱即用。

### Q: AI 分析用的什么模型？
A: 默认集成 DeepSeek API，也可以切换为其他兼容 OpenAI 格式的模型。

### Q: 数据安全吗？
A: 完全自托管，数据不出你的服务器。代码开源（Apache 2.0），可自行审计。

### Q: 能监控 K8s 吗？
A: 当前版本聚焦主机和服务监控。K8s 支持在路线图中。

---

## 下一步

- ⭐ **GitHub 点个 Star**: [github.com/LinChuang2008/vigilops](https://github.com/LinChuang2008/vigilops)
- 📖 **详细文档**: 查看项目 `docs/` 目录
- 💬 **提需求/报 Bug**: [GitHub Issues](https://github.com/LinChuang2008/vigilops/issues)
- 🤝 **贡献代码**: 欢迎 PR，查看 [CONTRIBUTING.md](https://github.com/LinChuang2008/vigilops/blob/main/CONTRIBUTING.md)

---

> **VigilOps** — 让 AI 帮你值班，让运维不再焦虑。
