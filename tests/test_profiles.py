# SPDX-License-Identifier: AGPL-3.0

"""编辑器 OCR 配置检测测试。"""

from PIL import Image

from wanna_understanding.ocr.profiles import detect_editor_profile


def test_detect_vscode_dark_from_title_and_image() -> None:
    image = Image.new("RGB", (40, 20), color=(20, 20, 20))
    profile = detect_editor_profile("main.py - Visual Studio Code", image)
    assert profile.name == "vscode_dark"


def test_detect_cursor_uses_cursor_profile() -> None:
    image = Image.new("RGB", (40, 20), color=(20, 20, 20))
    profile = detect_editor_profile("app.py - Cursor", image)
    assert profile.name == "cursor_dark"


def test_detect_pycharm_dark() -> None:
    image = Image.new("RGB", (40, 20), color=(20, 20, 20))
    profile = detect_editor_profile("main.py - PyCharm", image)
    assert profile.name == "pycharm_dark"
    assert profile.strip_line_numbers is True


def test_detect_intellij_light() -> None:
    image = Image.new("RGB", (40, 20), color=(240, 240, 240))
    profile = detect_editor_profile("App - IntelliJ IDEA", image)
    assert profile.name == "pycharm_light"


def test_generic_for_unknown_editor() -> None:
    image = Image.new("RGB", (40, 20), color=(240, 240, 240))
    profile = detect_editor_profile("记事本", image)
    assert profile.name == "generic"
