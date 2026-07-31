"""SVG 棋盘快照，几何与配色和 Web 版一致，供 skill 在对话中可视化。"""
from __future__ import annotations

from xiangqi.board import Move, Position
from xiangqi.render import _BLACK_CHARS, _RED_CHARS

_CELL = 60
_MARGIN = 50
_R = 26
_HAN = "一二三四五六七八九"

_WOOD = "#d0ac79"
_FRAME = "#7d5633"
_LINE = "#6b4a26"
_IVORY = "#f8f0dd"
_RED = "#a63a2a"
_INK = "#2b2620"
_KAI = "Kaiti SC, STKaiti, KaiTi, serif"
_SONG = "Songti SC, STSong, SimSun, serif"


def _x(c: int) -> int:
    return _MARGIN + c * _CELL


def _y(r: int) -> int:
    return _MARGIN + r * _CELL


def render_svg(pos: Position, last_move: Move | None = None) -> str:
    """渲染当前局面为自包含 SVG 字符串。"""
    out: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 580 640" '
        'width="580" height="640">',
        f'<rect x="0" y="0" width="580" height="640" rx="10" fill="{_WOOD}" '
        f'stroke="{_FRAME}" stroke-width="3"/>',
        f'<g stroke="{_LINE}" stroke-width="1.2" stroke-linecap="round" fill="none">',
        f'<rect x="{_x(0) - 5}" y="{_y(0) - 5}" width="{8 * _CELL + 10}" '
        f'height="{9 * _CELL + 10}" stroke-width="2.2"/>',
    ]
    for r in range(10):
        out.append(f'<line x1="{_x(0)}" y1="{_y(r)}" x2="{_x(8)}" y2="{_y(r)}"/>')
    for c in range(9):
        if c in (0, 8):
            out.append(f'<line x1="{_x(c)}" y1="{_y(0)}" x2="{_x(c)}" y2="{_y(9)}"/>')
        else:
            out.append(f'<line x1="{_x(c)}" y1="{_y(0)}" x2="{_x(c)}" y2="{_y(4)}"/>')
            out.append(f'<line x1="{_x(c)}" y1="{_y(5)}" x2="{_x(c)}" y2="{_y(9)}"/>')
    for r1, c1, r2, c2 in ((0, 3, 2, 5), (0, 5, 2, 3), (7, 3, 9, 5), (7, 5, 9, 3)):
        out.append(f'<line x1="{_x(c1)}" y1="{_y(r1)}" x2="{_x(c2)}" y2="{_y(r2)}"/>')
    # 炮/兵位刻点
    ticks = [(2, 1), (2, 7), (7, 1), (7, 7)] + [(r, c) for r in (3, 6) for c in (0, 2, 4, 6, 8)]
    for r, c in ticks:
        px, py = _x(c), _y(r)
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            if (c == 0 and sx < 0) or (c == 8 and sx > 0):
                continue
            out.append(
                f'<path d="M {px + sx * 4} {py + sy * 11} V {py + sy * 4} '
                f'H {px + sx * 11}" stroke-width="1.1"/>'
            )
    out.append("</g>")

    river_y = _y(4) + _CELL // 2
    for text, c in (("楚 河", 2), ("漢 界", 6)):
        out.append(
            f'<text x="{_x(c)}" y="{river_y}" font-family="{_KAI}" font-size="30" '
            f'fill="rgba(90,62,28,0.38)" text-anchor="middle" '
            f'dominant-baseline="central" letter-spacing="0.5em">{text}</text>'
        )
    for cc in range(9):
        top, bottom = str(cc + 1), _HAN[8 - cc]
        for text, y in ((top, _MARGIN - 28), (bottom, _MARGIN + 9 * _CELL + 36)):
            out.append(
                f'<text x="{_x(cc)}" y="{y}" font-family="{_SONG}" font-size="15" '
                f'fill="rgba(80,55,25,0.75)" text-anchor="middle">{text}</text>'
            )

    if last_move is not None:
        for s in last_move:
            px, py = _x(s % 9), _y(s // 9)
            out.append(
                f'<rect x="{px - 30}" y="{py - 30}" width="60" height="60" rx="8" '
                f'fill="none" stroke="rgba(166,58,42,0.55)" stroke-width="2" '
                'class="lastmove"/>'
            )

    for s, pc in enumerate(pos.board):
        if pc == ".":
            continue
        red = pc.isupper()
        px, py = _x(s % 9), _y(s // 9)
        color = _RED if red else _INK
        char = (_RED_CHARS if red else _BLACK_CHARS)[pc]
        out.append(
            f'<circle cx="{px}" cy="{py}" r="{_R}" fill="{_IVORY}" '
            f'stroke="#b89968" stroke-width="1.5"/>'
            f'<circle cx="{px}" cy="{py}" r="{_R - 4.5}" fill="none" '
            f'stroke="{color}" stroke-width="1.2"/>'
            f'<text x="{px}" y="{py + 1}" font-family="{_KAI}" font-size="30" '
            f'font-weight="700" fill="{color}" text-anchor="middle" '
            f'dominant-baseline="central">{char}</text>'
        )
    out.append("</svg>")
    return "\n".join(out)
