"""跨实现一致性：JS 引擎（内嵌于 web/index.html）跑共享 perft 数据。

用 node 提取 <script id="engine"> 块执行；机器上没有 node 则跳过。
"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="需要 node")
def test_js_perft_matches_shared_data():
    proc = subprocess.run(
        [NODE, str(ROOT / "scripts" / "perft_js.mjs"), "--max-depth", "3"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "全部通过" in proc.stdout
