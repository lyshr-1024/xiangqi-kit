"""中文记谱法与走法的双向转换。

红方汉字数字、路数从右往左（col 8 = 一路）；黑方阿拉伯数字（col 0 = 1 路）。
同线双子用 前/后，三子用 前/中/后；多路叠兵产生歧义时退化为「前七进一」式。
解析对繁体、红黑异体字（仕/士、相/象、兵/卒）与数字写法宽容。
"""
from __future__ import annotations

from collections import Counter

from xiangqi.board import Move, Position

_HAN_DIGITS = "一二三四五六七八九"

_RED_NAMES = {"R": "车", "N": "马", "C": "炮", "P": "兵", "K": "帅", "A": "仕", "B": "相"}
_BLACK_NAMES = {"r": "车", "n": "马", "c": "炮", "p": "卒", "k": "将", "a": "士", "b": "象"}

_NORMALIZE = str.maketrans(
    "俥車傌馬砲包卒帥將将仕相進０１２３４５６７８９一二三四五六七八九",
    "车车马马炮炮兵帅帅帅士象进0123456789123456789",
)


def _normalize(text: str) -> str:
    return "".join(text.split()).translate(_NORMALIZE)


def _file_char(col: int, red: bool) -> str:
    return _HAN_DIGITS[8 - col] if red else str(col + 1)


def _num_char(n: int, red: bool) -> str:
    return _HAN_DIGITS[n - 1] if red else str(n)


def _markers(n: int) -> list[str]:
    if n == 2:
        return ["前", "后"]
    if n == 3:
        return ["前", "中", "后"]
    return ["前"] + [_HAN_DIGITS[i] for i in range(1, n - 1)] + ["后"]


def _notate(pos: Position, move: Move, file_marker: bool = False) -> str:
    board = pos.board
    frm, to = move
    pc = board[frm]
    red = pc.isupper()
    r, c = divmod(frm, 9)
    nr, nc = divmod(to, 9)
    name = (_RED_NAMES if red else _BLACK_NAMES)[pc]

    # 同型同线用位置标记；士象靠进/退天然无歧义，帅将唯一
    marker = ""
    if pc.upper() in "RNCP":
        rows = [r2 for r2 in range(10) if board[r2 * 9 + c] == pc]
        if len(rows) > 1:
            rows.sort(reverse=not red)  # 排头 = 靠近敌方
            marker = _markers(len(rows))[rows.index(r)]

    if marker:
        prefix = marker + (_file_char(c, red) if file_marker else name)
    else:
        prefix = name + _file_char(c, red)

    if nr == r:
        return prefix + "平" + _file_char(nc, red)
    forward = nr < r if red else nr > r
    verb = "进" if forward else "退"
    if pc.upper() in "RCKP":
        return prefix + verb + _num_char(abs(nr - r), red)
    return prefix + verb + _file_char(nc, red)


def _notation_map(pos: Position) -> dict[Move, str]:
    """当前局面所有合法走法的规范记谱，冲突的叠兵改用 标记+路数。"""
    result = {mv: _notate(pos, mv) for mv in pos.legal_moves()}
    counts = Counter(result.values())
    for mv, text in result.items():
        if counts[text] > 1:
            result[mv] = _notate(pos, mv, file_marker=True)
    return result


def to_notation(pos: Position, move: Move) -> str:
    """把合法走法转成中文记谱。"""
    try:
        return _notation_map(pos)[move]
    except KeyError:
        raise ValueError(f"不是当前局面的合法走法: {move!r}") from None


def parse_notation(pos: Position, text: str) -> Move:
    """把中文记谱解析成走法，无法唯一匹配合法走法时抛 ValueError。"""
    want = _normalize(text)
    for mv, canonical in _notation_map(pos).items():
        if _normalize(canonical) == want:
            return mv
    raise ValueError(f"无法识别或不是合法着法: {text!r}")
