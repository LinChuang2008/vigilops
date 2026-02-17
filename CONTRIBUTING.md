# 贡献指南

感谢你对 VigilOps 的关注！欢迎任何形式的贡献。

## 🚀 快速开始

### 开发环境搭建

```bash
# 1. Fork 并克隆
git clone https://github.com/your-username/vigilops.git
cd vigilops

# 2. 启动开发环境
cp .env.example .env
docker compose up -d

# 3. 前端开发（热重载）
cd frontend
npm install
npm run dev

# 4. 后端开发（自动重载，已通过 volume mount 实现）
# 修改 backend/ 下的代码后容器自动重载
```

### 访问

- 前端: http://localhost:3001
- 后端 API: http://localhost:8001/docs
- PostgreSQL: localhost:5433
- Redis: localhost:6380

## 📋 贡献流程

1. **Fork** 本仓库
2. **创建分支**: `git checkout -b feature/your-feature` 或 `fix/your-fix`
3. **编写代码** 并确保通过测试
4. **提交**: 使用规范的 commit message
5. **推送**: `git push origin feature/your-feature`
6. **发起 Pull Request**

## 📝 Commit Message 规范

采用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>: <description>

[optional body]
```

### Type

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 重构 |
| `perf` | 性能优化 |
| `test` | 测试 |
| `chore` | 构建/工具变更 |

### 示例

```
feat: 添加服务拓扑图页面
fix: 修复告警规则重复触发问题
docs: 更新 API 文档
```

## 🏗️ 项目结构

```
vigilops/
├── backend/          # Python FastAPI 后端
│   ├── app/
│   │   ├── core/     # 配置、数据库、认证
│   │   ├── models/   # SQLAlchemy 模型
│   │   ├── routers/  # API 路由
│   │   ├── schemas/  # Pydantic 模型
│   │   └── services/ # 业务逻辑
│   └── migrations/   # SQL 迁移脚本
├── frontend/         # React + TypeScript 前端
│   └── src/
│       ├── pages/    # 页面组件
│       ├── components/ # 公共组件
│       ├── store/    # Zustand 状态
│       └── api/      # API 调用
├── agent/            # 采集 Agent
└── docs/             # 文档
```

## 🎯 代码规范

### 后端 (Python)

- 代码注释使用**中文**
- 类型注解使用 `Optional[X]`（兼容 Python 3.9）
- 遵循 PEP 8 风格
- API 路由放在 `routers/`，业务逻辑放在 `services/`

### 前端 (TypeScript)

- 代码注释使用**中文**
- 使用函数式组件 + Hooks
- 状态管理使用 Zustand
- UI 组件使用 Ant Design 5
- 图表使用 ECharts

## 🐛 Bug 报告

提交 Issue 时请包含：

1. **环境信息** — OS、Docker 版本、浏览器
2. **复现步骤** — 最小可复现步骤
3. **期望行为** vs **实际行为**
4. **截图 / 日志**（如有）

## 💡 功能建议

欢迎提交 Feature Request！请说明：

1. **使用场景** — 为什么需要这个功能？
2. **期望方案** — 你理想中的实现方式
3. **替代方案** — 是否考虑过其他方式？

## 📄 License

贡献的代码将遵循 [Apache License 2.0](LICENSE)。
