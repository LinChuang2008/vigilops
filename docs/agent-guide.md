# VigilOps Agent 使用指南

## 目录

- [概述](#概述)
- [系统要求](#系统要求)
- [安装方式](#安装方式)
  - [一键安装脚本](#一键安装脚本)
  - [手动安装](#手动安装)
- [配置文件详解](#配置文件详解)
  - [server - 服务端连接](#server---服务端连接)
  - [host - 主机标识](#host---主机标识)
  - [metrics - 指标采集](#metrics---指标采集)
  - [services - 服务健康检查](#services---服务健康检查)
  - [log_sources - 日志采集](#log_sources---日志采集)
  - [discovery - 自动发现](#discovery---自动发现)
  - [databases - 数据库监控](#databases---数据库监控)
  - [完整配置示例](#完整配置示例)
- [Agent 模块说明](#agent-模块说明)
- [CLI 命令](#cli-命令)
- [systemd 服务管理](#systemd-服务管理)
- [多主机批量部署](#多主机批量部署)
- [升级与卸载](#升级与卸载)
- [故障排查](#故障排查)

---

## 概述

VigilOps Agent 是安装在被监控主机上的轻量级 Python 进程，负责：

- **系统指标采集** — CPU、内存、磁盘、网络
- **服务健康检查** — HTTP / TCP 端口探测
- **日志采集** — 文件 tail、多行合并、Docker json-log 解析
- **数据库指标采集** — PostgreSQL / MySQL / Oracle
- **Docker 容器自动发现** — 自动检测运行中的容器并注册为服务
- **宿主机服务发现** — 通过 `ss -tlnp` 自动发现监听端口的服务

Agent 通过 HTTP 将采集的数据上报到 VigilOps 后端，由后端统一处理告警、AI 分析和可视化展示。

---

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux（Ubuntu/Debian/CentOS/RHEL/Rocky/Alma/Fedora） |
| Python | ≥ 3.9 |
| 网络 | 能访问 VigilOps 后端（默认端口 8001） |
| 权限 | root（systemd 安装需要） |

---

## 安装方式

### 一键安装脚本

最简单的安装方式，一条命令搞定：

```bash
curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/scripts/install-agent.sh \
  | bash -s -- --server http://YOUR_SERVER:8001 --token YOUR_TOKEN
```

#### 参数说明

| 参数 | 简写 | 必填 | 说明 |
|------|------|------|------|
| `--server` | `-s` | ✅ | VigilOps 后端地址，如 `http://192.168.1.100:8001` |
| `--token` | `-t` | ✅ | Agent Token（在 VigilOps 后台「设置 → Agent Tokens」中获取） |
| `--hostname` | `-n` | ❌ | 自定义主机名，默认自动检测 |
| `--interval` | `-i` | ❌ | 指标采集间隔（秒），默认 15 |
| `--local` | `-l` | ❌ | 本地离线安装包路径（目录或 .tar.gz） |
| `--upgrade` | — | ❌ | 升级已有安装，保留配置文件 |
| `--uninstall` | — | ❌ | 完全卸载 Agent |

#### 安装目录结构

```
/opt/vigilops-agent/          # 安装目录
├── repo/                     # 源码（git clone）
└── venv/                     # Python 虚拟环境
    └── bin/vigilops-agent    # Agent 可执行文件

/etc/vigilops/                # 配置目录
└── agent.yaml                # 配置文件
```

安装脚本会自动：
1. 检测并安装 Python ≥ 3.9（如不存在）
2. 从 GitHub 克隆代码（GitHub 不通时回退到 Gitee 镜像）
3. 创建虚拟环境并安装依赖
4. 生成默认配置文件
5. 注册并启动 systemd 服务

### 手动安装

```bash
# 1. 克隆仓库
git clone https://github.com/LinChuang2008/vigilops.git
cd vigilops/agent

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 3. 安装（包含数据库监控依赖）
pip install ".[db]"

# 4. 编写配置文件
mkdir -p /etc/vigilops
cat > /etc/vigilops/agent.yaml <<EOF
server:
  url: http://YOUR_SERVER:8001
  token: YOUR_TOKEN
host:
  name: my-server-01
metrics:
  interval: 15s
EOF

# 5. 验证配置
vigilops-agent -c /etc/vigilops/agent.yaml check

# 6. 前台运行（测试）
vigilops-agent -c /etc/vigilops/agent.yaml run

# 7. 配置 systemd（见下方）
```

---

## 配置文件详解

配置文件为 YAML 格式，默认路径 `/etc/vigilops/agent.yaml`。时间间隔支持简写：`15s`（秒）、`1m`（分钟），也可直接写整数（按秒计算）。

### server - 服务端连接

```yaml
server:
  url: http://192.168.1.100:8001   # VigilOps 后端地址（必填）
  token: "your-agent-token"        # Agent Token（必填）
```

> **提示：** Token 也可通过环境变量 `VIGILOPS_TOKEN` 设置，优先级高于配置文件。

### host - 主机标识

```yaml
host:
  name: "web-server-01"            # 主机名（可选，默认自动检测）
  tags: ["production", "web"]      # 标签，用于分组筛选（可选）
```

### metrics - 指标采集

```yaml
metrics:
  interval: 15s                    # 采集间隔（可选，默认 15s）
```

### services - 服务健康检查

```yaml
services:
  # HTTP 检查
  - name: "My API"
    type: http                     # 检查类型：http / tcp
    url: http://localhost:8080/health
    interval: 30s                  # 检查间隔（默认 30s）
    timeout: 10                    # 超时时间，秒（默认 10）

  # TCP 端口检查
  - name: "Redis"
    type: tcp
    host: localhost
    port: 6379
    interval: 30s
```

`target` 简写格式也支持：
- `target: http://localhost:8080/health` → 自动解析为 HTTP 检查
- `target: localhost:6379` → 自动解析为 host + port

### log_sources - 日志采集

```yaml
log_sources:
  - path: /var/log/syslog          # 日志文件路径（必填）
    service: system                # 关联服务名（可选）
    multiline: false               # 是否启用多行合并（默认 false）
    multiline_pattern: "^\\d{4}-\\d{2}-\\d{2}|^\\["  # 新日志行起始正则
    docker: false                  # 是否为 Docker json-log 格式（默认 false）

  - path: /var/log/nginx/error.log
    service: nginx

  - path: /var/lib/docker/containers/abc123/abc123-json.log
    service: my-app
    docker: true                   # Docker JSON 日志格式
```

### discovery - 自动发现

```yaml
discovery:
  docker: true                     # 自动发现 Docker 容器（默认 true）
  host_services: true              # 自动发现宿主机监听服务（默认 true）
  interval: 30                     # 发现的服务默认检查间隔（默认 30s）
```

也可以简写为布尔值禁用所有发现：

```yaml
discovery: false
```

### databases - 数据库监控

```yaml
databases:
  # PostgreSQL
  - name: "主库"
    type: postgres                 # 数据库类型：postgres / mysql / oracle
    host: localhost
    port: 5432                     # 默认端口：postgres=5432, mysql=3306
    database: mydb
    username: monitor
    password: "monitor_pass"
    interval: 60s                  # 采集间隔（默认 60s）

  # MySQL
  - name: "业务数据库"
    type: mysql
    host: 10.0.0.10
    port: 3306
    database: app_db
    username: monitor
    password: "pass"

  # Oracle（支持容器方式）
  - name: "ERP Oracle"
    type: oracle
    host: 10.0.0.20
    port: 1521
    oracle_sid: ORCL
    username: monitor
    password: "pass"
    container_name: oracle-db      # Docker 容器名（可选）
    oracle_home: /opt/oracle       # ORACLE_HOME（可选）
```

### 完整配置示例

```yaml
server:
  url: http://192.168.1.100:8001
  token: "abc123-your-token"

host:
  name: "prod-web-01"
  tags: ["production", "web", "shanghai"]

metrics:
  interval: 15s

services:
  - name: "Nginx"
    type: http
    url: http://localhost/health
    interval: 30s
  - name: "Redis"
    type: tcp
    host: localhost
    port: 6379
    interval: 30s
  - name: "App API"
    type: http
    url: http://localhost:8080/api/health
    interval: 15s
    timeout: 5

log_sources:
  - path: /var/log/nginx/error.log
    service: nginx
  - path: /var/log/app/app.log
    service: app
    multiline: true

discovery:
  docker: true
  host_services: true

databases:
  - name: "PostgreSQL 主库"
    type: postgres
    host: localhost
    port: 5432
    database: app_db
    username: monitor
    password: "monitor123"
    interval: 60s
```

---

## Agent 模块说明

| 模块 | 文件 | 功能 |
|------|------|------|
| 系统指标采集 | `collector.py` | 采集 CPU 使用率、内存使用、磁盘空间与 IO、网络流量 |
| 服务健康检查 | `checker.py` | 执行 HTTP / TCP 端口健康检查，记录响应时间和状态 |
| 日志采集 | `log_collector.py` | Tail 日志文件，支持多行合并和 Docker json-log 格式解析 |
| 数据库指标 | `db_collector.py` | 采集 PostgreSQL / MySQL / Oracle 的连接数、QPS、慢查询等 |
| 自动发现 | `discovery.py` | 自动发现 Docker 容器和宿主机监听服务，注册为检查目标 |
| 数据上报 | `reporter.py` | 汇总所有采集数据，通过 HTTP POST 定期上报到后端 |
| 命令行入口 | `cli.py` | 提供 `run`、`check` 等 CLI 命令 |
| 配置加载 | `config.py` | 解析 YAML 配置，支持环境变量覆盖和时间简写 |

---

## CLI 命令

```bash
# 查看版本
vigilops-agent --version

# 验证配置文件
vigilops-agent -c /etc/vigilops/agent.yaml check

# 前台运行（调试用）
vigilops-agent -c /etc/vigilops/agent.yaml run

# 详细日志模式
vigilops-agent -v -c /etc/vigilops/agent.yaml run
```

---

## systemd 服务管理

一键安装脚本会自动创建 systemd 服务。手动安装时，创建 `/etc/systemd/system/vigilops-agent.service`：

```ini
[Unit]
Description=VigilOps Monitoring Agent
Documentation=https://github.com/LinChuang2008/vigilops
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=/opt/vigilops-agent/venv/bin/vigilops-agent -c /etc/vigilops/agent.yaml run
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vigilops-agent

# 安全加固
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=/opt/vigilops-agent /etc/vigilops /tmp

[Install]
WantedBy=multi-user.target
```

常用命令：

```bash
# 启用并启动
systemctl daemon-reload
systemctl enable vigilops-agent
systemctl start vigilops-agent

# 查看状态
systemctl status vigilops-agent

# 查看日志
journalctl -u vigilops-agent -f          # 实时日志
journalctl -u vigilops-agent --since today  # 今日日志

# 重启 / 停止
systemctl restart vigilops-agent
systemctl stop vigilops-agent
```

---

## 多主机批量部署

### 方式一：SSH 批量执行

创建主机列表文件 `hosts.txt`：

```
192.168.1.10
192.168.1.11
192.168.1.12
```

批量安装脚本：

```bash
#!/bin/bash
SERVER_URL="http://192.168.1.100:8001"
TOKEN="your-agent-token"

while IFS= read -r host; do
  echo "=== Installing on $host ==="
  ssh root@"$host" "curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/scripts/install-agent.sh \
    | bash -s -- --server $SERVER_URL --token $TOKEN"
done < hosts.txt
```

### 方式二：Ansible Playbook

```yaml
---
- name: Deploy VigilOps Agent
  hosts: monitored_servers
  become: yes
  vars:
    vigilops_server: "http://192.168.1.100:8001"
    vigilops_token: "your-agent-token"
  tasks:
    - name: Install VigilOps Agent
      shell: |
        curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/scripts/install-agent.sh \
          | bash -s -- --server {{ vigilops_server }} --token {{ vigilops_token }}
      args:
        creates: /opt/vigilops-agent/venv/bin/vigilops-agent
```

### 方式三：离线安装

适用于无法访问外网的环境：

```bash
# 在有网络的机器上打包
git clone https://github.com/LinChuang2008/vigilops.git
tar czf vigilops-agent.tar.gz vigilops/agent/

# 拷贝到目标机器
scp vigilops-agent.tar.gz root@target:/tmp/
scp install-agent.sh root@target:/tmp/

# 在目标机器上安装
ssh root@target "bash /tmp/install-agent.sh \
  --server http://192.168.1.100:8001 \
  --token YOUR_TOKEN \
  --local /tmp/vigilops-agent.tar.gz"
```

---

## 升级与卸载

### 升级

```bash
# 使用安装脚本升级（保留现有配置）
curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/scripts/install-agent.sh \
  | bash -s -- --upgrade
```

### 卸载

```bash
# 卸载 Agent（保留配置文件）
curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/scripts/install-agent.sh \
  | bash -s -- --uninstall

# 如需同时删除配置
rm -rf /etc/vigilops
```

---

## 故障排查

### Agent 无法启动

```bash
# 1. 检查服务状态
systemctl status vigilops-agent

# 2. 查看详细日志
journalctl -u vigilops-agent -n 50 --no-pager

# 3. 验证配置文件
/opt/vigilops-agent/venv/bin/vigilops-agent -c /etc/vigilops/agent.yaml check

# 4. 前台模式运行，查看实时输出
/opt/vigilops-agent/venv/bin/vigilops-agent -v -c /etc/vigilops/agent.yaml run
```

### Agent 运行但数据不上报

```bash
# 1. 确认网络连通性
curl -s http://YOUR_SERVER:8001/api/health

# 2. 检查 Token 是否正确（在 VigilOps 后台确认 Token 状态）

# 3. 查看 Agent 日志中的错误
journalctl -u vigilops-agent --since "10 minutes ago" | grep -i error
```

### 常见错误及解决

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `No agent token configured` | 未配置 Token | 在 `agent.yaml` 中设置 `server.token` 或设置环境变量 `VIGILOPS_TOKEN` |
| `Config file not found` | 配置文件路径错误 | 确认 `/etc/vigilops/agent.yaml` 存在，或用 `-c` 指定正确路径 |
| `Connection refused` | 后端不可达 | 检查 `server.url` 地址和端口，确认防火墙规则 |
| `401 Unauthorized` | Token 无效或过期 | 在 VigilOps 后台重新生成 Token |
| `Permission denied` 读日志 | Agent 无权读取日志文件 | 确保 Agent 以 root 运行，或将 Agent 用户加入相应文件组 |

### 查看 Agent 上报的原始数据

在 VigilOps 后端，进入「主机管理」页面可查看该 Agent 上报的所有数据，包括：

- 系统指标趋势图
- 服务健康状态
- 日志搜索
- 数据库指标
