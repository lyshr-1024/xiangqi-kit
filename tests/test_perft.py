"""perft 走法数校验：唯一能证明走法生成写对的方法。

数据在 tests/data/perft.json，与 JS 实现共享。
depth >= 4 标记 slow，用 `pytest -m slow` 单独跑。
"""
import json
from pathlib import Path

import pytest

from xiangqi import Position

DATA = json.loads((Path(__file__).parent / "data" / "perft.json").read_text())

CASES = [
    (p["name"], p["fen"], int(d), expected)
    for p in DATA["positions"]
    for d, expected in p["depths"].items()
]

FAST = [c for c in CASES if c[2] <= 3]
SLOW = [c for c in CASES if c[2] == 4]


@pytest.mark.parametrize("name,fen,depth,expected", FAST, ids=lambda v: str(v))
def test_perft_fast(name, fen, depth, expected):
    assert Position.from_fen(fen).perft(depth) == expected


@pytest.mark.slow
@pytest.mark.parametrize("name,fen,depth,expected", SLOW, ids=lambda v: str(v))
def test_perft_slow(name, fen, depth, expected):
    assert Position.from_fen(fen).perft(depth) == expected
