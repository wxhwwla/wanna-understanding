# SPDX-License-Identifier: MIT

"""验证包可正常导入的冒烟测试。"""


def test_import() -> None:
    """验证 wanna_understanding 包可导入且版本号正确。"""
    from wanna_understanding import __version__

    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_import_main() -> None:
    """验证主入口可调用。"""
    from wanna_understanding import __all__

    assert isinstance(__all__, list)
