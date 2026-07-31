"""搜索与估值测试：找杀、抓吃、限时、终局处理。"""
import time

from xiangqi import Position, START_FEN, sq
from xiangqi.search import MATE, evaluate, search


def test_evaluate_startpos_is_symmetric():
    assert evaluate(Position.from_fen(START_FEN)) == 0


def test_search_finds_mate_in_one():
    # 两个车进底线均为杀着：王逃 (0,5)/(0,3) 时让开自身遮挡仍被将军
    pos = Position.from_fen("4k4/R7R/9/9/9/9/9/9/9/3K5 w - - 0 1")
    result = search(pos, time_limit=1.0)
    assert result.move in [(sq(1, 0), sq(0, 0)), (sq(1, 8), sq(0, 8))]
    assert result.score > MATE - 100
    pos.make_move(result.move)
    assert pos.is_checkmate()


def test_search_takes_hanging_rook():
    pos = Position.from_fen("3k5/9/9/9/9/R7r/9/9/9/5K3 w - - 0 1")
    result = search(pos, time_limit=1.0)
    assert result.move == (sq(5, 0), sq(5, 8))


def test_search_respects_time_limit():
    pos = Position.from_fen(START_FEN)
    fen_before = pos.to_fen()
    start = time.monotonic()
    result = search(pos, time_limit=0.3)
    assert time.monotonic() - start < 1.5
    assert result.move in pos.legal_moves()
    assert pos.to_fen() == fen_before  # 搜索不能破坏局面


def test_search_returns_none_when_game_over():
    pos = Position.from_fen("4k3R/R8/9/9/9/9/9/9/9/3K5 b - - 0 1")
    assert search(pos, time_limit=0.2) is None
