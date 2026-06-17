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

# 4. 启动
# 推荐：双击 启动.bat（pythonw，无控制台，托盘常驻）
python -m wanna_understanding          # 命令行模式（关控制台即退出）
python -m wanna_understanding --no-tray  # 禁用托盘

# 5. 无 GUI 冒烟（在活动编辑器窗口前运行）
python -m wanna_understanding --smoke
```

启动后程序在**系统托盘**常驻（默认启用）。双击 `启动.bat` 使用 `pythonw`，无控制台窗口；退出请用**托盘右键 → 退出**。

命令行 `python -m wanna_understanding` 会保留控制台，关闭控制台将结束进程。

**快捷键**：`Ctrl+Shift+H` 显示/隐藏 | `J` 历史 | `S` 设置（均需按住 Ctrl+Shift）

**系统托盘**：默认启用；禁用：`$env:WU_TRAY_ENABLED = "false"` 或 `python -m wanna_understanding --no-tray`

默认 **流式输出** AI 回复；关闭：`$env:WU_STREAM_OUTPUT = "false"`。

**自定义监控区域**（框选后写入 `.env`）：

```powershell
python scripts/pick_region.py
# 输出 WU_MONITOR_MODE=custom 与 WU_MONITOR_RECT=left,top,width,height
```

**UI Automation**（可选，传统 Win32 编辑器效果更好）：

```powershell
pip install -e ".[uia]"
$env:WU_USE_UIA = "true"
```

**打包**（需 `pip install -e ".[build,ocr]"`）：

```powershell
python scripts/build_exe.py
# 默认无控制台；调试：python scripts/build_exe.py --console
# 输出 dist/WannaUnderstanding/WannaUnderstanding.exe
```

> **venv 损坏？** 双击 `修复venv.bat` 重建虚拟环境并重新安装依赖。

---

## 📦 目录结构（摘要）

```
src/wanna_understanding/
├── application.py       # 主编排
├── config.py            # 配置与 .env 读写
├── screen/              # 截图、区域、UIA 文本提取
├── ocr/                 # EasyOCR、预处理、编辑器配置
├── trigger/             # 轮询、防抖
├── ai/                  # DeepSeek 客户端、缓存、历史
└── ui/                  # 悬浮窗、托盘、设置/历史对话框
scripts/                 # 打包、OCR 模型下载、区域框选
tests/                   # pytest 单元测试
docs/                    # 设计与接续文档
```

完整说明见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。

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
| **分析历史** | 持久化到 `%APPDATA%/WannaUnderstanding/`，可浏览回看 |
| **系统托盘** | 后台常驻，右键菜单控制显示/设置/退出 |

---

## 📐 架构概览

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Screen  │───▶│   OCR    │───▶│   AI     │───▶│   UI     │
│ Capturer │    │ Engine   │    │  Client  │    │  Overlay │
│  (mss)   │    │(EasyOCR) │    │(DeepSeek)│    │(tkinter) │
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

| 阶段 | 内容 | 状态 |
|------|------|:----:|
| **MVP** | EasyOCR + DeepSeek + tkinter 悬浮窗闭环 | ✅ |
| **优化** | 防抖、缓存、流式、局部发送、快捷键 | ✅ |
| **扩展** | 多 IDE、UIA、自定义区域、历史/设置/托盘 | ✅ |
| **验收** | GUI 实机端到端验证 | 🟡 |
| **进阶** | C# / Rust 重写核心 | ⬜ |

---

## 🤝 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 许可证

AGPL-3.0（默认）或书面商业许可。详见 [LICENSE](LICENSE)。
