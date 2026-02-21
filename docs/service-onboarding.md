# VigilOps AI 运维托管服务 — 客户 Onboarding SOP

> 内部文档：服务交付标准流程

## 服务交付总览

```
客户签约 → 环境评估 → 部署实例 → Agent 安装 → 告警配置 → 验收交付 → 持续运维
  Day 0       Day 1      Day 1      Day 1-2     Day 2       Day 3       持续
```

---

## Phase 1: 客户签约 (Day 0)

### 收集信息
- [ ] 公司名称、联系人、联系方式
- [ ] 服务器数量和规格（OS、CPU、内存、磁盘）
- [ ] 服务器位置（云厂商/自建机房/混合）
- [ ] 核心业务系统清单
- [ ] 现有监控方案（如有）
- [ ] 告警通知渠道偏好（钉钉/飞书/企微/邮件/Webhook）
- [ ] 服务等级选择（基础版 ¥699/月 / 专业版 ¥1,599/月）

### 输出
- 服务合同（含 SLA 条款）
- 客户信息表

---

## Phase 2: 环境评估 + 部署 (Day 1)

### 评估服务器连通性
```bash
# 确认可 SSH 登录或有其他远程访问方式
ssh user@客户服务器 "uname -a && free -h && df -h"
```

### 部署 VigilOps 实例

**方式 A：客户服务器上直接部署（推荐小规模）**
```bash
curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/deploy/vigilops-deploy.sh \
  | sudo bash -s -- --ai-key $AI_KEY --domain $DOMAIN
```

**方式 B：我方管理服务器部署（推荐中大规模）**
```bash
# 在我方 ECS 上为客户创建独立实例
# 端口规划：每客户一组端口
# 客户A: backend:8101, frontend:3101
# 客户B: backend:8201, frontend:3201
docker compose -f docker-compose.prod.yml \
  --env-file .env.客户名 \
  -p vigilops-客户名 up -d
```

### 初始化配置
- [ ] 创建管理员账号
- [ ] 配置 AI 密钥（DeepSeek）
- [ ] 设置数据保留策略
- [ ] 配置备份

---

## Phase 3: Agent 安装 (Day 1-2)

### 在客户每台服务器上安装 Agent
```bash
# 生成 Agent Token（通过 VigilOps API）
curl -X POST http://vigilops:8001/api/v1/agent-tokens \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"name": "客户服务器-01"}'

# 一键安装 Agent
curl -fsSL https://raw.githubusercontent.com/LinChuang2008/vigilops/main/scripts/install-agent.sh \
  | sudo bash -s -- --server http://vigilops:8001 --token $AGENT_TOKEN
```

### 验证数据上报
- [ ] 每台服务器的 CPU/内存/磁盘数据正常上报
- [ ] 服务器在 Dashboard 中可见
- [ ] 健康状态显示正常

---

## Phase 4: 告警配置 (Day 2)

### 标准告警规则（按服务等级）

#### 托管基础版
| 指标 | 阈值 | 动作 |
|------|------|------|
| CPU > 90% | 持续 5 分钟 | 通知 |
| 内存 > 85% | 持续 5 分钟 | 通知 |
| 磁盘 > 90% | 立即 | 通知 |
| 服务宕机 | 立即 | 通知 |

#### 托管专业版（额外）
| 指标 | 阈值 | 动作 |
|------|------|------|
| 异常检测 | AI 判定 | AI 分析 + 通知 |
| 慢查询 | > 1s | AI 分析 |
| 日志异常 | 关键字匹配 | AI 分析 + 通知 |
| 自动修复 | 预设条件 | 自动执行 Runbook |
| SLA 违规预警 | 接近阈值 | 人工介入 |
| 定制 Runbook | 客户定义 | 自动/半自动 |
| 容量预测 | AI 预测 | 提前通知 |

### 配置通知渠道
- [ ] 根据客户偏好配置钉钉/飞书/企微/邮件
- [ ] 测试通知到达
- [ ] 设置告警升级策略

---

## Phase 5: 验收交付 (Day 3)

### 验收检查单
- [ ] 所有服务器数据正常采集
- [ ] Dashboard 展示正确
- [ ] 告警规则生效（模拟触发测试）
- [ ] 通知渠道畅通
- [ ] AI 分析功能正常（智能/企业包）
- [ ] 自动修复功能测试通过（智能/企业包）
- [ ] 客户管理员已培训

### 交付物
- 客户专属登录地址和账号
- 运维报告模板
- 紧急联系方式
- 服务使用手册

---

## Phase 6: 持续运维（交付后）

### 日常
- 告警监控和响应
- AI 自动分析和修复
- 月度运维报告发送

### 周期性
- 每周：异常趋势分析
- 每月：运维报告 + 容量评估
- 每季：服务回顾 + 优化建议

### 升级维护
- VigilOps 版本升级（每月一次）
- Agent 批量更新
- 告警规则优化

---

## 常见问题处理

### 客户服务器无法安装 Agent
- 确认网络连通性
- 确认 SSH 权限
- 提供离线安装包

### 告警过多（告警风暴）
- 调整阈值
- 启用告警降噪（冷却期 + 聚合）
- AI 自动分类优先级

### 客户要求定制化
- 评估工作量
- 企业包内免费定制（每月 X 小时）
- 超出部分单独报价
