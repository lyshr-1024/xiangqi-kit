"""FEN 序列化/反序列化测试。

坐标约定：row 0 = 黑方底线（FEN 第一段），row 9 = 红方底线；
col 0 = FEN 每段的第一个格子。红方为大写字母，走子方 'w' = 红。
"""
import pytest

from xiangqi import Position, START_FEN, sq


def test_start_fen_roundtrip():
    pos = Position.from_fen(START_FEN)
    assert pos.to_fen() == START_FEN


def test_start_position_pieces():
    pos = Position.from_fen(START_FEN)
    assert pos.board[sq(0, 4)] == "k"
    assert pos.board[sq(9, 4)] == "K"
    assert pos.board[sq(2, 1)] == "c"
    assert pos.board[sq(2, 7)] == "c"
    assert pos.board[sq(7, 1)] == "C"
    assert pos.board[sq(3, 0)] == "p"
    assert pos.board[sq(6, 8)] == "P"
    assert pos.board[sq(1, 4)] == "."
    assert pos.side_to_move == "w"
    assert pos.fullmove_number == 1


def test_black_to_move_roundtrip():
    fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR b - - 3 7"
    pos = Position.from_fen(fen)
    assert pos.side_to_move == "b"
    assert pos.halfmove_clock == 3
    assert pos.fullmove_number == 7
    assert pos.to_fen() == fen


def test_sparse_position_roundtrip():
    fen = "3k5/9/9/9/4p4/C2P2r1p/9/9/9/5K3 w - - 0 1"
    pos = Position.from_fen(fen)
    assert pos.board[sq(5, 0)] == "C"
    assert pos.board[sq(5, 6)] == "r"
    assert pos.to_fen() == fen


def test_invalid_fen_rejected():
    with pytest.raises(ValueError):
        Position.from_fen("9/9/9 w - - 0 1")
    with pytest.raises(ValueError):
        Position.from_fen("rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR x - - 0 1")
