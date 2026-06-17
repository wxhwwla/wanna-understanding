# SPDX-License-Identifier: AGPL-3.0

"""共享测试 fixture 配置。"""

import pytest


@pytest.fixture
def sample_data() -> dict:
    """提供示例测试数据。"""
    return {"name": "test", "value": 42}
