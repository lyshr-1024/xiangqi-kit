"""中文记谱法双向转换测试。

红方：汉字数字，路数从红方右侧数（col 8 = 一路，file = 9 - col）。
黑方：阿拉伯数字，路数从黑方右侧数（col 0 = 1 路，file = col + 1）。
直行子（车炮兵帅）进退记步数；斜行子（马象士）进退记到达路数。
"""
import pytest

from xiangqi import Position, START_FEN, sq
from xiangqi.notation import parse_notation, to_notation


def play(pos: Position, *texts: str) -> Position:
    for t in texts:
        pos.make_move(parse_notation(pos, t))
    return pos


@pytest.mark.parametrize(
    "text,frm,to",
    [
        ("炮二平五", (7, 7), (7, 4)),
        ("马二进三", (9, 7), (7, 6)),
        ("车九进一", (9, 0), (8, 0)),
        ("兵三进一", (6, 6), (5, 6)),
        ("相三进五", (9, 6), (7, 4)),
        ("仕四进五", (9, 5), (8, 4)),
        ("帅五进一", (9, 4), (8, 4)),
    ],
)
def test_red_startpos_roundtrip(text, frm, to):
    pos = Position.from_fen(START_FEN)
    mv = parse_notation(pos, text)
    assert mv == (sq(*frm), sq(*to))
    assert to_notation(pos, mv) == text


@pytest.mark.parametrize(
    "text,frm,to",
    [
        ("马8进7", (0, 7), (2, 6)),
        ("卒3进1", (3, 2), (4, 2)),
        ("士4进5", (0, 3), (1, 4)),
        ("象7进5", (0, 6), (2, 4)),
        ("炮8平5", (2, 7), (2, 4)),
    ],
)
def test_black_roundtrip(text, frm, to):
    pos = play(Position.from_fen(START_FEN), "炮二平五")
    mv = parse_notation(pos, text)
    assert mv == (sq(*frm), sq(*to))
    assert to_notation(pos, mv) == text


def test_parse_is_lenient_about_variants():
    pos = Position.from_fen(START_FEN)
    canonical = parse_notation(pos, "炮二平五")
    assert parse_notation(pos, "炮2平5") == canonical
    assert parse_notation(pos, "砲二平五") == canonical
    assert parse_notation(pos, "馬八進七") == (sq(9, 1), sq(7, 2))
    assert parse_notation(pos, "士四进五") == (sq(9, 5), sq(8, 4))


def test_game_sequence_roundtrip():
    # 当头炮对屏风马开局走几步，逐步解析并反向生成一致
    texts = ["炮二平五", "马8进7", "马二进三", "车9平8", "车一平二", "炮8进4"]
    pos = Position.from_fen(START_FEN)
    for t in texts:
        mv = parse_notation(pos, t)
        assert to_notation(pos, mv) == t
        pos.make_move(mv)


def test_red_double_rooks_same_file():
    pos = Position.from_fen("3k5/9/9/9/9/4R4/9/4R4/9/5K3 w - - 0 1")
    assert parse_notation(pos, "前车进一") == (sq(5, 4), sq(4, 4))
    assert to_notation(pos, (sq(7, 4), sq(7, 0))) == "后车平九"
    with pytest.raises(ValueError):
        parse_notation(pos, "车五进一")


def test_black_double_cannons_same_file():
    # 黑方的“前”是更靠近红方（row 更大）的那个
    pos = Position.from_fen("3k5/9/4c4/9/4c4/9/9/9/9/5K3 b - - 0 1")
    assert parse_notation(pos, "前炮进2") == (sq(4, 4), sq(6, 4))
    assert to_notation(pos, (sq(2, 4), sq(2, 2))) == "后炮平3"


def test_triple_pawns_same_file():
    pos = Position.from_fen("3k5/9/4P4/9/4P4/9/4P4/9/9/5K3 w - - 0 1")
    assert parse_notation(pos, "中兵进一") == (sq(4, 4), sq(3, 4))
    assert to_notation(pos, (sq(2, 4), sq(2, 3))) == "前兵平六"
    assert to_notation(pos, (sq(6, 4), sq(5, 4))) == "后兵进一"


def test_stacked_pawns_on_two_files_use_file_marker():
    # 两路都有叠兵时，“前兵进一”有歧义，退化为 标记+路数
    pos = Position.from_fen("3k5/9/9/9/2P3P2/9/2P3P2/9/9/5K3 w - - 0 1")
    assert parse_notation(pos, "前七进一") == (sq(4, 2), sq(3, 2))
    assert to_notation(pos, (sq(6, 6), sq(5, 6))) == "后三进一"
    with pytest.raises(ValueError):
        parse_notation(pos, "前兵进一")


@pytest.mark.parametrize("bad", ["马二进二", "车二进一", "车十平九", "瞎写", ""])
def test_parse_rejects_invalid(bad):
    pos = Position.from_fen(START_FEN)
    with pytest.raises(ValueError):
        parse_notation(pos, bad)


def test_to_notation_rejects_illegal_move():
    pos = Position.from_fen(START_FEN)
    with pytest.raises(ValueError):
        to_notation(pos, (sq(9, 4), sq(0, 4)))
