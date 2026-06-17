# SPDX-License-Identifier: AGPL-3.0

"""验证包可正常导入的冒烟测试。"""


def test_import() -> None:
    """验证 wanna_understanding 包可导入且版本号与 _version 一致。"""
    from scripts._version import get_version
    from wanna_understanding import __version__

    assert isinstance(__version__, str)
    assert __version__ == get_version()


def test_import_main() -> None:
    """验证主入口可调用。"""
    from wanna_understanding import __all__

    assert isinstance(__all__, list)
