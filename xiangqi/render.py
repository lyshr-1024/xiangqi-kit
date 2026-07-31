"""终端文本棋盘渲染。全角字符对齐；红黑用繁/简变体区分，可选 ANSI 着色。"""
from __future__ import annotations

from xiangqi.board import Position

_RED_CHARS = {"R": "俥", "N": "傌", "B": "相", "A": "仕", "K": "帥", "C": "炮", "P": "兵"}
_BLACK_CHARS = {"r": "車", "n": "馬", "b": "象", "a": "士", "k": "將", "c": "砲", "p": "卒"}
_EMPTY = "・"
_TOP = "１２３４５６７８９"
_BOTTOM = "九八七六五四三二一"
_RIVER = "～楚河～～汉界～～"


def render(pos: Position, color: bool = False) -> str:
    """渲染带列号的文本棋盘，黑方在上（列号 1-9），红方在下（九-一）。"""
    lines = [_TOP]
    for r in range(10):
        if r == 5:
            lines.append(_RIVER)
        row = ""
        for c in range(9):
            pc = pos.board[r * 9 + c]
            if pc == ".":
                row += _EMPTY
            elif pc.isupper():
                ch = _RED_CHARS[pc]
                row += f"\x1b[31m{ch}\x1b[0m" if color else ch
            else:
                row += _BLACK_CHARS[pc]
        lines.append(row)
    lines.append(_BOTTOM)
    return "\n".join(lines)
