"""skill/xq 入口测试：用环境里的 python3（而非测试解释器）跑，保证零依赖可分发。"""
import shutil
import subprocess
from pathlib import Path

import pytest

XQ = Path(__file__).parent.parent / "skill" / "xq"
PYTHON3 = shutil.which("python3")


def run(args, tmp_path):
    return subprocess.run(
        [PYTHON3, str(XQ), *args],
        capture_output=True,
        text=True,
        env={"XIANGQI_HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
    )


@pytest.mark.skipif(PYTHON3 is None, reason="需要 python3")
def test_skill_entry_runs_with_system_python(tmp_path):
    assert run(["new"], tmp_path).returncode == 0
    legal = run(["legal"], tmp_path)
    assert legal.returncode == 0
    assert len(legal.stdout.strip().splitlines()) == 44
    move = run(["move", "炮二平五"], tmp_path)
    assert move.returncode == 0
    assert "已走：炮二平五" in move.stdout


def test_skill_md_has_frontmatter():
    text = (XQ.parent / "SKILL.md").read_text()
    assert text.startswith("---\n")
    assert "name: xiangqi" in text
