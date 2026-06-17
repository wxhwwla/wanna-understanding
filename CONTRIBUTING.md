# Wanna Understanding — 贡献指南

> 感谢你考虑为 Wanna Understanding 项目贡献代码！

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
| Python | 3.11+ |
| Git | 最新稳定版 |
| 操作系统 | Windows 10/11（运行与集成测试） |

### 1. 克隆仓库

```bash
git clone https://github.com/wxhwwla/wanna-understanding.git
cd wanna-understanding
```

### 2. 创建虚拟环境

```powershell
# Windows PowerShell
$env:PYTHONUTF8 = "1"
chcp 65001 > $null
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev,ocr]"
python scripts/ocr_download_models.py
```

### 3. 配置与运行

```powershell
$env:DEEPSEEK_API_KEY = "your-key"
python -m wanna_understanding --smoke   # 终端冒烟
python -m wanna_understanding             # GUI
```

---

## 提交规范

- 遵循 `ruff` / `pyright` / `pytest`（CI 自动检查）
- 公共 API 与行为变更须同步更新 `docs/` 相关文档
- **不要**直接 `git push`；维护者使用 `python github_upload_module.py` 发布

### PR 检查清单

- [ ] 测试通过：`pytest -q`
- [ ] Lint 通过：`ruff check .`
- [ ] 类型检查通过：`pyright src/`
- [ ] 遵循代码结构规范（目录 ≤20 项，单文件 ≤400 行）
- [ ] API 或配置变更时同步更新文档

---

## 项目结构

详见 [`ARCHITECTURE.md`](ARCHITECTURE.md) 与 [`docs/代码结构规范.md`](docs/代码结构规范.md)。

| 目录 | 职责 |
|------|------|
| `src/wanna_understanding/` | 核心业务逻辑 |
| `tests/` | pytest 单元测试 |
| `scripts/` | 打包、OCR 模型、区域框选等工具 |
| `docs/` | 设计与接续文档 |

---

## 测试

```bash
pytest -q
pytest --cov=wanna_understanding
ruff check .
pyright src/
```

---

## 许可证

向本仓库贡献即表示同意在 **AGPL-3.0**（或项目书面商业许可框架）下授权。详见 [`LICENSE`](LICENSE)。

---

## 有问题？

- [GitHub Issues](https://github.com/wxhwwla/wanna-understanding/issues) — Bug 报告 / 功能建议
- 内部文档：[`docs/会话接续手册.md`](docs/会话接续手册.md)
