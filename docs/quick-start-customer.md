# VigilOps 客户快速部署指南

> 从零到监控运行，10 分钟搞定。

## 第一步：部署 VigilOps 服务端

在你的监控主机上（推荐 4核4G 以上）：

```bash
git clone https://github.com/LinChuang2008/vigilops.git
cd vigilops
sudo ./install.sh
```

安装向导会交互式引导你完成端口、密码等配置。完成后访问 `http://YOUR_IP:3001`。

**默认管理员账号：** admin / admin（首次登录后请修改密码）

## 第二步：获取 Agent Token

1. 登录 VigilOps 控制台
2. 进入 **设置 → Agent Tokens**
3. 点击 **创建 Token**，复制生成的 token

## 第三步：在被监控服务器上安装 Agent

每台需要监控的服务器上执行：

```bash
curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/scripts/install-agent.sh | \
  sudo bash -s -- --server http://YOUR_VIGILOPS_IP:8001 --token YOUR_TOKEN
```

或下载后手动执行：

```bash
wget https://raw.githubusercontent.com/LinChuang2008/vigilops/main/scripts/install-agent.sh
chmod +x install-agent.sh
sudo ./install-agent.sh --server http://YOUR_VIGILOPS_IP:8001 --token YOUR_TOKEN
```

安装完成后，Agent 自动注册并开始上报指标。

## 第四步：查看监控数据

回到 VigilOps 控制台，你会看到：
- **仪表盘**：服务器健康评分、CPU/内存/磁盘趋势
- **服务器列表**：所有已注册服务器及实时状态
- **告警中心**：异常告警（支持钉钉/飞书/企微/邮件通知）

## 可选：启用 AI 分析

1. 获取 DeepSeek API Key：https://platform.deepseek.com
2. 编辑 `.env` 文件，添加 `AI_API_KEY=sk-your-key`
3. 重启：`docker compose restart backend`

启用后可使用：
- 🤖 AI 根因分析（一键分析告警原因）
- 💬 AI 运维助手（自然语言问答）
- 🔧 自动修复（AI 诊断 + Runbook 自动执行）

## Agent 管理命令

```bash
# 查看状态
systemctl status vigilops-agent

# 查看日志
journalctl -u vigilops-agent -f

# 重启
systemctl restart vigilops-agent

# 升级
/opt/vigilops-agent/scripts/install-agent.sh --upgrade

# 卸载
/opt/vigilops-agent/scripts/install-agent.sh --uninstall
```

## 常见问题

**Q: Agent 安装后控制台看不到服务器？**
- 检查网络：`curl http://YOUR_VIGILOPS_IP:8001/health`
- 检查 token 是否正确
- 查看日志：`journalctl -u vigilops-agent -f`

**Q: 需要监控数据库怎么办？**
- 编辑 `/etc/vigilops/agent.yaml`，添加数据库连接信息
- 重启 agent：`systemctl restart vigilops-agent`

**Q: 如何配置告警通知？**
- 控制台 → 通知渠道 → 添加渠道（钉钉/飞书/企微/邮件/Webhook）
- 控制台 → 告警规则 → 新建规则并关联通知渠道

---

**需要帮助？** 联系我们的运维团队获取一对一技术支持。
