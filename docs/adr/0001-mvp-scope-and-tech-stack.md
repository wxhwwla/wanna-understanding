# ADR-0001：MVP 范围与技术选型

- **状态**：已接受
- **提出日期**：2026-06-17
- **最后更新**：2026-06-17

---

## 上下文

Wanna Understanding 项目刚启动，需要在短时间内验证「屏幕截图 → OCR → AI 分析 → 悬浮窗展示」的技术可行性。需要确定 MVP 的范围和技术选型，避免过度工程。

### 关键约束

- **时间**：MVP 应在 1-2 周内完成
- **技术**：团队成员最擅长 Python
- **目标**：验证端到端闭环可行性

## 决策（MVP 当时）

### 1. MVP 范围

**核心闭环（必须完成）**：

| 模块 | MVP 范围 | 说明 |
|------|----------|------|
| 屏幕捕获 | 截取活动窗口 | 多显示器、自定义区域为 Phase 3 扩展 |
| OCR | EasyOCR + 基本预处理 | 已从 PaddleOCR 迁移；深色模式在 Phase 2/3 优化 |
| 触发 | 定时轮询（2s）+ 哈希比较 + 防抖 0.5s | 事件驱动留待未来 |
| AI 分析 | DeepSeek API + 结构化 Prompt + LRU 缓存 | 流式输出为 Phase 2 扩展 |
| 悬浮窗 | tkinter 无边框置顶 | 跟随定位、托盘为后续扩展 |

### 2. 技术选型

| 组件 | 选型 | 替代方案 | 理由 |
|------|------|----------|------|
| 截图 | mss + pywin32 | PIL.ImageGrab（慢） | mss 性能最好 |
| OCR | **EasyOCR** | PaddleOCR / Tesseract | 复用 endfield 封装，安装较轻 |
| AI API | DeepSeek | GPT-4o（贵） | 性价比最高 |
| 悬浮窗 | tkinter + pystray | PyQt5（依赖重） | 轻量、满足 MVP |
| 触发 | 轮询 + 哈希 | pynput 事件（复杂） | 轮询实现最简单 |

### 3. 架构风格

**管道架构（Pipeline）**：数据单向流动，每个模块独立可测。

```
Capturer → TextExtract(OCR/UIA) → AI → UI
```

模块间通过数据类通信；`TextExtractor` 抽象便于 OCR 与 UIA 切换（见 ADR-0002）。

## 理由

1. **Python MVP**：快速验证风险点后再考虑 C#/Rust 重写。
2. **OCR 优先**：横跨编辑器；UIA 作为 Phase 3 可选补充。
3. **DeepSeek API**：性价比与速度平衡。
4. **tkinter**：零/轻依赖。

## 影响

- MVP 后已按 Phase 2/3 路线图扩展流式、多 IDE、历史、设置 GUI、托盘、打包等。
- OCR 引擎在实现阶段由 PaddleOCR **替换为 EasyOCR**（见 `docs/会话接续手册.md`），ADR 原则不变。

## 实现状态（2026-06-17 追加）

| 原「不纳入 MVP」项 | 当前状态 |
|-------------------|----------|
| 多 IDE / 深色主题 | ✅ `ocr/profiles.py` |
| 用户配置 GUI | ✅ `ui/settings_dialog.py` |
| UI Automation | ✅ 可选 `WU_USE_UIA` |
| 流式输出 | ✅ 默认开启 |
| 打包 exe | ✅ `scripts/build_exe.py` |
| 多显示器 / 自定义区域 | ✅ `screen/monitor.py`、`pick_region` |

## 相关 ADR

- [ADR-0002](0002-ocr-vs-uia.md)：OCR vs UI Automation 路线
