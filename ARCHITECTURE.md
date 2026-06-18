# Wanna Understanding — 架构概述

> 本文档是项目架构的根级入口。
> 架构决策记录：[`docs/adr/`](docs/adr/)。

---

## 技术栈

| 组件 | MVP 技术选型 | 未来可选 |
|------|-------------|----------|
| 屏幕捕获 | mss + win32gui | Rust 原生截图 |
| OCR 识别 | EasyOCR | Windows.Media.Ocr (C#) |
| 系统托盘 | pystray | 原生 Shell 图标 |
| AI 分析 | DeepSeek API (OpenAI 兼容) | 替换为本地模型 |
| 悬浮窗 | tkinter | WPF / Webview2 |
| 事件监听 | polling 轮询 | pynput / Windows 钩子 |
| 测试 | pytest + pytest-cov | — |
| 代码检查 | ruff + pyright | — |
| 打包 | PyInstaller (onedir) | .NET / Rust 原生 |

---

## 系统分层

```
┌─────────────────────────────────────────────────────────┐
│                      UI Layer                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Overlay Window (tkinter)                        │   │
│  │  · 无边框置顶 · 半透明 · 可拖拽 · 快捷键隐藏     │   │
│  │  · 流式渲染 AI 回复 · 显示/隐藏动画              │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                   Analysis Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  AI Client   │  │  Cache       │  │  Prompt      │   │
│  │  · DeepSeek  │  │  · LRU 缓存  │  │  · 结构化    │   │
│  │  · 流式      │  │  · 哈希键    │  │  · 功能/建议  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
├─────────────────────────────────────────────────────────┤
│              Text Extraction Layer                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │  OCR Engine (EasyOCR) + 可选 UIA (TextExtractor) │   │
│  │  · 图像预处理：灰度/放大/二值化/反色            │   │
│  │  · 编辑器配置 profiles + 行号裁剪               │   │
│  │  · 后处理：缩进修复、特殊符号校正                │   │
│  └──────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                 Capture Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Screen      │  │  Window      │  │  Trigger     │   │
│  │  Capturer    │  │  Region      │  │  · 防抖      │   │
│  │  · mss       │  │  · DPI 适配  │  │  · 哈希变化  │   │
│  │  · win32gui  │  │  · 中间 70%  │  │  · 定时轮询  │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
├─────────────────────────────────────────────────────────┤
│                   Config & Utils                        │
│  ┌──────────────┐  ┌──────────────┐                     │
│  │  Config      │  │  Utils       │                     │
│  │  · .env      │  │  · 哈希      │                     │
│  │  · API Key   │  │  · 版本号    │                     │
│  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
src/wanna_understanding/
├── __init__.py                 # 包声明 + 版本号
├── __main__.py                 # 程序入口点（python -m）
├── analysis_coordinator.py     # 分析工作流（从 application.py 拆分）
├── application.py              # 应用编排主类
├── config.py                   # 全局配置（API Key / 截图频率 / 模型参数）
├── logger.py                   # 日志系统（文件轮转 + hook 未捕获异常）
├── smoke.py                    # 端到端冒烟测试（无 GUI 模式）
├── tcl_bootstrap.py            # DPI 感知引导（自动调用 SetProcessDPIAware）

├── ai/                         # AI 分析模块
│   ├── __init__.py
│   ├── cache.py                # LRU 结果缓存（基于代码 SHA256）
│   ├── client.py               # DeepSeek API 客户端（支持流式）
│   ├── context.py              # 局部代码裁剪（默认 20 行）
│   ├── history.py              # 分析历史持久化（JSON 文件）
│   ├── prompt.py               # Prompt 模板 + 结构化输出解析
│   └── stream.py               # SSE 流式 API 解析

├── ocr/                        # 文字识别模块
│   ├── __init__.py
│   ├── engine.py               # EasyOCR 封装（初始化/调用/释放）
│   ├── preprocess.py           # 图像预处理管线（灰度/放大/二值化/反色）
│   ├── profiles.py             # 编辑器 OCR 配置（VS Code / Cursor / PyCharm / Trae）
│   ├── recognizer.py           # 识别器（源自 endfield 项目）
│   └── theme.py                # 深色主题自动检测

├── screen/                     # 屏幕捕获模块
│   ├── __init__.py
│   ├── capture_plan.py         # 截图区域规划（全屏/窗口/自定义区域）
│   ├── capturer.py             # mss 截图核心
│   ├── code_region_detector.py # 自动代码区域检测（已不启用，保留参考）
│   ├── custom_region.py        # 自定义监控区域管理
│   ├── monitor.py              # 多显示器支持
│   ├── region.py               # 区域定义 + DPI 适配
│   ├── region_confirm.py       # 手动框选代码区域（用户交互）
│   ├── region_picker.py        # 区域选择器（供设置与 CLI 复用）
│   ├── text_extract.py         # 文本提取（OCR / UIA 统一接口）
│   └── window.py               # win32gui 活动窗口定位 + DPI 适配

├── trigger/                    # 触发控制模块
│   ├── __init__.py
│   ├── debounce.py             # 防抖调度器（可配置延迟）
│   └── watcher.py              # 窗口变化轮询 + 哈希比较

└── ui/                         # 展示模块
    ├── __init__.py
    ├── history_dialog.py       # 历史浏览对话框
    ├── hotkey.py               # 全局快捷键检测（Alt+Shift+* 系列）
    ├── overlay.py              # tkinter 无边框悬浮窗
    ├── position.py             # 悬浮窗定位/偏移计算
    ├── settings_dialog.py      # 设置 GUI 对话框
    ├── streaming.py            # 流式 UI 节流更新
    └── tray.py                 # 系统托盘（pystray）
```

---

## 数据流

```
用户滚动代码
     │
     ▼
[Trigger Watcher] ── 检测到变化（防抖 0.5s）
     │
     ▼
[Screen Capturer] ── 截取活动窗口（DPI 补偿）
     │
     ▼
[Region Crop] ── 裁剪中间 70% 区域 → 放大 2x
     │
     ▼
[Preprocess] ── 灰度 → 二值化 → 反色（深色模式）
     │
     ▼
[OCR / UIA] ── 提取代码文本
     │
     ▼
[Cache Lookup] ── SHA256(代码) → 命中？→ 直接返回
     │ (未命中)
     ▼
[AI Client] ── 构造 Prompt → 调用 DeepSeek API → 解析回复
     │
     ▼
[Overlay UI] ── 更新悬浮窗内容（半透明置顶展示）
```

---

## 核心设计决策（ADR）

| ADR | 主题 | 状态 |
|-----|------|:----:|
| [ADR-0001](docs/adr/0001-mvp-scope-and-tech-stack.md) | MVP 范围与技术选型 | ✅ 已接受 |
| [ADR-0002](docs/adr/0002-ocr-vs-uia.md) | OCR vs UI Automation 路线选择 | ✅ 已接受 |
| — | 更多待补充 | — |

---

## 关键抽象

| 组件 | 路径 | 说明 |
|------|------|------|
| `ScreenCapturer` | `screen.capturer` | 截图抽象：mss 实现，支持全屏/指定窗口 |
| `WindowRegion` | `screen.region` | 区域值对象：xywh + DPI 缩放 |
| `CapturePlan` | `screen.capture_plan` | 截图区域规划：全屏/窗口/自定义区域 |
| `RegionPicker` | `screen.region_picker` | 区域选择器（供设置与 CLI 复用） |
| `select_code_region` | `screen.region_confirm` | 手动框选取代自动裁剪（用户交互） |
| `OCREngine` | `ocr.engine` | OCR 引擎封装：初始化 / 识别 / 后处理 |
| `ImagePreprocessor` | `ocr.preprocess` | 图像预处理管线（灰度/放大/二值化/反色） |
| `OCRProfiles` | `ocr.profiles` | 多编辑器 OCR 配置（VS Code/Cursor/PyCharm/Trae） |
| `detect_dark_theme` | `ocr.theme` | 深色主题自动检测 |
| `ContentWatcher` | `trigger.watcher` | 窗口内容变化检测：轮询 + SHA256 哈希 |
| `DebounceScheduler` | `trigger.debounce` | 防抖调度器：可配置延迟 + 防抖节流 |
| `AIClient` | `ai.client` | API 客户端：流式调用、重试、超时 |
| `PromptTemplate` | `ai.prompt` | Prompt 工程：系统/用户消息模板 + 输出解析 |
| `ResultCache` | `ai.cache` | LRU 缓存：基于代码 SHA256 键 |
| `trim_to_context` | `ai.context` | 局部代码裁剪（默认 20 行） |
| `HistoryStore` | `ai.history` | 分析历史 JSON 持久化 |
| `iter_sse_deltas` | `ai.stream` | SSE 流式 API 解析 |
| `AnalysisCoordinator` | `analysis_coordinator` | 分析工作流编排（提取自 Application） |
| `OverlayWindow` | `ui.overlay` | 悬浮窗控件：tkinter 顶层窗口 |
| `hotkey_*` | `ui.hotkey` | 全局快捷键检测（Alt+Shift+H/J/O/F） |
| `StreamUpdateThrottler` | `ui.streaming` | 流式 UI 节流更新 |
| `TrayController` | `ui.tray` | 系统托盘图标与菜单 |
| `HistoryDialog` | `ui.history_dialog` | 历史浏览对话框 |
| `SettingsDialog` | `ui.settings_dialog` | 设置 GUI 对话框 |
| `Logger` | `logger` | 日志系统：文件轮转 + hook 未捕获异常 |
| `Application` | `application` | 主编排：串联截图、OCR、触发、AI 与悬浮窗 |

---

## 贡献

见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。
