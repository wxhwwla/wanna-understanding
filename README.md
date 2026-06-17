# Wanna Understanding

> **AI 代码审阅员** — 桌面后台工具，只读不写，实时分析屏幕上可见的代码。
>
> 零操作、自动跟随、不绑定编辑器、不修改代码。

---

## 📖 项目简介

Wanna Understanding 是一个始终在后台运行的桌面程序，像一个沉静的「AI 代码审阅员」——它**只读不写**，自动监控当前屏幕上可见的代码，实时解释其功能、指出潜在 Bug 或逻辑问题，并提供改进建议。

**核心哲学**：不是 Copilot（不主动改代码），不是浏览器插件（不绑定编辑器），不是手动框选提问模式（自动跟随滚动/切换）。它是纯粹的**旁观者**，在你写代码时默默给出反馈。

---

## 🚀 快速开始

```powershell
# 1. 创建并激活虚拟环境
$env:PYTHONUTF8 = "1"
python -m venv .venv
.venv\Scripts\activate

# 2. 安装依赖（含 EasyOCR）
pip install -e ".[dev,ocr]"

# 2b. 预下载 OCR 模型（首次运行前推荐）
python scripts/ocr_download_models.py

# 3. 配置 DeepSeek API Key
$env:DEEPSEEK_API_KEY = "your-api-key-here"

# 4. 启动（或双击 启动.bat）
python -m wanna_understanding
```

启动后程序会监控**当前活动窗口**，滚动停止约 0.5 秒后自动 OCR 识别代码并调用 AI 分析，结果展示在右侧悬浮窗。

> **venv 损坏？** 双击 `修复venv.bat` 重建虚拟环境并重新安装依赖。

---

## 📦 目录结构

```
wanna-understanding/
├── src/
│   └── wanna_understanding/
│       ├── __init__.py
│       ├── __main__.py          # 入口点
│       ├── screen/              # 屏幕捕获模块
│       │   ├── __init__.py
│       │   ├── capturer.py      # 截图引擎（mss / win32gui）
│       │   └── region.py        # 区域定义与 DPI 适配
│       ├── ocr/                 # 文字识别模块
│       │   ├── __init__.py
│       │   ├── engine.py        # EasyOCR 封装
│       │   ├── recognizer.py    # EasyOCR 识别器（源自 endfield 项目）
│       │   └── preprocess.py    # 图像预处理（二值化/放大/反色）
│       ├── trigger/             # 触发控制模块
│       │   ├── __init__.py
│       │   ├── watcher.py       # 窗口变化轮询 / 事件监听
│       │   └── debounce.py      # 防抖调度器
│       ├── ai/                  # AI 分析模块
│       │   ├── __init__.py
│       │   ├── client.py        # DeepSeek API 客户端
│       │   ├── prompt.py        # Prompt 模板工程
│       │   └── cache.py         # 结果缓存（基于代码哈希）
│       ├── ui/                  # 展示模块
│       │   ├── __init__.py
│       │   ├── overlay.py       # 无边框置顶悬浮窗
│       │   └── theme.py         # 半透明/穿透/快捷键
│       └── config.py            # 全局配置
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_import.py
│   ├── test_region.py
│   ├── test_debounce.py
│   ├── test_watcher.py
│   ├── test_preprocess.py
│   ├── test_ocr_engine.py
│   ├── test_cache.py
│   ├── test_ai_client.py
│   ├── test_prompt.py
│   └── test_config.py
├── scripts/
│   ├── __init__.py
│   └── main.py                  # 开发入口
├── docs/
│   ├── adr/                     # 架构决策记录
│   ├── plans/                   # 计划文件
│   ├── 项目目标.md
│   ├── 技术方案.md              # 本文档
│   ├── 代码结构规范.md
│   ├── 文档规范.md
│   ├── 操作指令集.md
│   ├── 会话接续手册.md
│   └── 错误集.md
├── resources/
│   └── README.md
├── .claude/                     # Claude Code 配置
├── .github/workflows/           # CI
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── LICENSE
├── README.md                    # 本文件
├── ARCHITECTURE.md
├── CONTEXT.md
├── CONTRIBUTING.md
└── CLAUDE.md
```

---

## 🧩 核心功能

| 功能 | 说明 |
|------|------|
| **屏幕捕获** | 定时/事件触发截取整个屏幕或指定窗口，DPI 感知 |
| **代码文本提取** | OCR 识别屏幕中的代码，预处理优化（二值化/放大/反色） |
| **智能触发** | 滚动停止防抖、窗口切换检测，避免频繁分析 |
| **AI 分析** | 调用大模型 API，解释代码功能 + 指出潜在 Bug |
| **悬浮窗展示** | 无边框、半透明、置顶，可拖拽/隐藏，不干扰操作 |
| **结果缓存** | 基于代码哈希缓存分析结果，降低 token 消耗 |

---

## 📐 架构概览

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Screen  │───▶│   OCR    │───▶│   AI     │───▶│   UI     │
│ Capturer │    │ Engine   │    │  Client  │    │  Overlay │
│  (mss)   │    │(PaddleO) │    │(DeepSeek)│    │(tkinter) │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
      │                                              ▲
      ▼                                              │
┌──────────┐                                   ┌──────────┐
│ Trigger  │─── 防抖 + 哈希变化检测 ───────────▶│  Cache   │
│ Watcher  │                                   │ (LRU)    │
└──────────┘                                   └──────────┘
```

---

## 🧪 测试

```bash
pytest                          # 全量测试
pytest -m "not slow"            # 快速冒烟
pytest --cov=wanna_understanding # 覆盖率
```

---

## 🛣 路线图

| 阶段 | 内容 | 时间 |
|------|------|:----:|
| **MVP** | Python + PaddleOCR + DeepSeek + tkinter 悬浮窗 — 截图→OCR→AI→展示闭环 | 第 1-2 周 |
| **优化** | 防抖、缓存、局部发送、窗口自动跟随 | 第 3-4 周 |
| **扩展** | 适配多种 IDE、UI Automation 文本获取替代 OCR | 第 5-8 周 |
| **进阶** | C# / Rust 重写核心，追求更低 CPU 占用 | 长远 |

---

## 🤝 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 许可证

AGPL-3.0（默认）或书面商业许可。详见 [LICENSE](LICENSE)。
