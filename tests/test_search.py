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


def test_search_avoids_known_repetition():
    # 红方大优；把"车回 (5,3)"形成的局面标记为已出现过，搜索应绕开它
    pos = Position.from_fen("3k5/9/9/9/9/4R4/9/9/9/5K3 w - - 0 1")
    repeat_move = (sq(5, 4), sq(5, 3))
    undo = pos.make_move(repeat_move)
    seen = {"".join(pos.board) + pos.side_to_move: 2}
    pos.unmake_move(undo)
    result = search(pos, time_limit=0.5, history=seen)
    assert result.move != repeat_move


def test_search_develops_pieces_from_start():
    # 开局 2 秒内应走大子（马/炮/车），而不是仕相帅或边兵
    pos = Position.from_fen(START_FEN)
    result = search(pos, time_limit=2.0)
    piece = pos.board[result.move[0]]
    assert piece in "NCRP"
    if piece == "P":
        assert result.move[0] % 9 in (2, 4, 6)  # 至少是中路系兵，不是边兵


def test_search_returns_none_when_game_over():
    pos = Position.from_fen("4k3R/R8/9/9/9/9/9/9/9/3K5 b - - 0 1")
    assert search(pos, time_limit=0.2) is None
