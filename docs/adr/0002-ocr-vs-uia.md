# ADR-0002：OCR vs UI Automation 路线选择

- **状态**：已接受
- **提出日期**：2026-06-17
- **最后更新**：2026-06-17

---

## 上下文

从屏幕获取代码文本有两种主流技术路线：
1. **OCR 光学字符识别**：截图后用 AI 模型识别文字
2. **UI Automation**：通过 Windows 辅助功能 API 直接获取编辑器的文本内容

两者各有优劣，需要确定在项目不同阶段的取舍。

## 决策

### MVP 阶段：纯 OCR

| 维度 | OCR | UI Automation |
|------|-----|---------------|
| 通用性 | ✅ 任何 UI 都适用 | ❌ 需要编辑器暴露文本控件 |
| 实现成本 | ⭐⭐ 中 | ⭐⭐⭐ 高（需适配不同编辑器） |
| 准确率 | ⭐⭐⭐⭐（EasyOCR） | ⭐⭐⭐⭐⭐ |
| 速度 | ⭐⭐⭐（200-500ms） | ⭐⭐⭐⭐⭐（< 10ms） |
| 维护成本 | 低 | 高（各编辑器更新后控件树可能变化） |

**理由**：
- MVP 目标是验证可行性，OCR 一次实现到处运行
- 不需要为 VS Code、Cursor、PyCharm、记事本分别写适配
- 如果 OCR 准确率足够（95%+），UI Automation 可能根本不需要

### 扩展阶段：UI Automation 补充（Phase 3 已实现）

已实现 `screen/text_extract.py`：`WU_USE_UIA=true` 时 UIA 优先，失败回退 OCR。

当以下条件满足时，可继续加深 UIA 适配：
1. MVP 闭环验证通过
2. 用户反馈 OCR 延迟或准确率不够
3. 有明确的 1-2 个目标编辑器需要深度支持

### 长期：混合策略

```
OCR（兜底）   ←  适用于任何窗口
    ↑
分析请求
    ↓
UI Automation ← 优先使用，当目标编辑器有适配时
```

## 理由

UI Automation 是「优化项」而非「必须项」。如果 OCR 在 MVP 阶段表现良好（> 95% 准确率），UI Automation 的优先级应低于其他体验优化（防抖、缓存、窗口跟随）。

## 影响

- MVP 全部精力聚焦在 OCR 管线上
- 架构上已实现 `TextExtractor` 抽象（`UIAutomationTextExtractor` / `OCRTextExtractor`）
- MVP 阶段未投入 UI Automation；Phase 3 作为可选优化层落地

## 相关 ADR

- [ADR-0001](0001-mvp-scope-and-tech-stack.md)：MVP 范围与技术选型
