# 第三方声明与署名（NOTICES）

> **本项目（Wanna Understanding）自身许可为 AGPL-3.0（或书面商业许可），见仓库根目录 [`LICENSE`](LICENSE)。**  
> 下表所列 **MIT / BSD 等是第三方库自己的许可证**，不是本项目的许可证。

本文件列明本仓库使用的第三方组件与素材来源。
完整合规说明：[`docs/数据来源与许可.md`](docs/数据来源与许可.md)

---

## 第三方依赖许可（非本项目许可）

| 组件 | 许可 | 说明 |
|------|------|------|
| Python | PSF License | https://www.python.org/psf-license/ |
| mss | MIT | 屏幕截图 |
| pywin32 | BSD-3-Clause | Windows API（窗口/DPI） |
| Pillow | PIL License | 图像预处理 |
| EasyOCR | Apache 2.0 | OCR 文字识别（可选组 `[ocr]`） |
| pystray | MIT | 系统托盘 |
| uiautomation | Apache 2.0 | UI Automation（可选组 `[uia]`） |
| httpx | BSD-3-Clause | HTTP 客户端（AI API） |
| pydantic | MIT | 数据模型 |
| pytest / pytest-cov | MIT | 仅开发/测试使用 |
| ruff | MIT | 仅开发/测试使用 |
| pyright | MIT | 仅开发/测试使用 |

**完整依赖许可信息**：详见各组件自身发行包中的 LICENSE 文件。

---

## 使用声明

Wanna Understanding 是一款开源桌面工具。AI 分析功能通过调用第三方 API（如 DeepSeek）实现，
代码截图和文本内容会被发送到相应的 API 服务处理。用户应了解并同意：
- 代码内容会离开本地计算机，传输到第三方服务
- 建议不要在分析敏感/专有代码时启用本工具
- 本工具不对 API 服务的数据处理方式承担责任

---

## 关于捐赠

本项目完全免费开源。如项目对你有帮助，欢迎通过项目主页提供的渠道进行捐赠。
捐赠系对开发者个人的无偿支持，不构成购买软件或获得商业许可的对价。
