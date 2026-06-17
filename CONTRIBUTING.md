# 贡献指南

> 感谢你考虑为 Wanna Understanding 项目贡献代码！🎉

---

## 行为准则

**互相尊重，就事论事。**

- 讨论时保持友善和理性
- 承认不同水平——欢迎新贡献者，也尊重资深开发者
- 不接受人身攻击、歧视性言论或恶意挑衅

---

## 快速开始

### 环境要求

| 工具 | 版本要求 |
|------|----------|
| [语言] | [版本] |
| [依赖管理] | [版本] |
| Git | 最新稳定版 |

### 1. 克隆仓库

```bash
git clone [仓库地址]
cd wanna-understanding
```

### 2. 创建虚拟环境

```powershell
# Windows PowerShell
$env:PYTHONUTF8 = "1"
chcp 65001 > $null
python -m venv .venv
.venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -e ".[dev]"
```

### 4. 验证安装

```bash
pytest tests/ -q
```

---

## 开发工作流

### 分支策略

- `main` — 稳定发布版
- `develop` — 开发分支
- `feature/xxx` — 新功能
- `fix/xxx` — Bug 修复

### 提交约定

```
概述本轮改动
- 具体改动 1
- 具体改动 2
```

- 提交消息使用中文

### 提交 PR 前检查清单

- [ ] 测试通过：`pytest` 通过
- [ ] Lint 通过
- [ ] 类型检查通过
- [ ] 无新增警告
- [ ] 遵循代码结构规范（目录 ≤20 项，文件 ≤400 行）
- [ ] API 变更时同步更新文档

### 代码规范

- **注释**：中文
- **命名**：Python `snake_case`，TypeScript `camelCase`
- **类型**：公开 API 必须有类型注解
- **结构**：见 `docs/代码结构规范.md`

---

## 项目架构

详见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。

| 层 | 说明 |
|----|------|
| `src/` | 核心业务逻辑 |
| `tests/` | 测试套件 |
| `scripts/` | 入口脚本 |
| `docs/` | 文档 |

---

## 测试

```bash
# 全量测试
pytest tests/ -q

# 快速冒烟测试
pytest -m "not slow" -q

# Lint
ruff check .
```

---

## 有问题？

- [GitHub Issues](链接) — Bug 报告 / 功能建议
- 内部文档：`docs/会话接续手册.md`
