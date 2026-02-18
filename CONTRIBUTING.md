# Contributing to VigilOps

感谢你对 VigilOps 的关注！无论是提 Bug、建议功能还是贡献代码，我们都非常欢迎。

Thank you for your interest in contributing to VigilOps! Every contribution matters.

## 🐛 Reporting Bugs

1. 先搜索 [existing issues](https://github.com/LinChuang2008/vigilops/issues) 确认没有重复
2. 使用 **Bug Report** 模板创建新 Issue
3. 提供：复现步骤、期望行为、实际行为、环境信息

## 💡 Feature Requests

1. 使用 **Feature Request** 模板创建 Issue
2. 说明使用场景和期望效果
3. 欢迎讨论实现方案

## 🔀 Pull Requests

```bash
# 1. Fork 并克隆
git clone https://github.com/YOUR_USERNAME/vigilops.git
cd vigilops

# 2. 创建功能分支
git checkout -b feat/your-feature

# 3. 开发并提交
git add .
git commit -m "feat: add your feature description"

# 4. 推送并创建 PR
git push origin feat/your-feature
```

然后在 GitHub 上创建 Pull Request，填写变更说明。

### PR 规范

- 分支命名：`feat/xxx`、`fix/xxx`、`docs/xxx`
- Commit 遵循 [Conventional Commits](https://www.conventionalcommits.org/)：
  - `feat:` 新功能
  - `fix:` 修复
  - `docs:` 文档
  - `refactor:` 重构
  - `test:` 测试
- 确保通过 CI 检查

## 🛠️ 开发环境搭建

### 前置条件

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+ (或使用 Docker)
- Redis 7+ (或使用 Docker)

### 启动开发环境

```bash
# 启动依赖服务
docker compose -f docker-compose.dev.yml up -d

# 后端
cp .env.example .env
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

访问：
- 前端：http://localhost:5173
- API 文档：http://localhost:8000/docs

## 📏 代码规范

### Python (Backend)
- 使用 `ruff` 进行 lint 和格式化
- 类型注解（Type Hints）必须
- 运行 `ruff check .` 和 `ruff format .`

### TypeScript (Frontend)
- 使用 ESLint + Prettier
- 运行 `npm run lint` 和 `npm run format`

### 通用
- 有意义的变量命名
- 关键逻辑写注释
- 新功能配测试

## ❓ 有问题？

- 创建 [Discussion](https://github.com/LinChuang2008/vigilops/discussions)
- 加入 [Discord](https://discord.gg/vigilops)

再次感谢你的贡献！🎉
