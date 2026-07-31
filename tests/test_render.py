"""文本棋盘渲染测试。红黑用繁/简变体区分（俥傌炮兵帥仕相 vs 車馬砲卒將士象）。"""
from xiangqi import Position, START_FEN
from xiangqi.render import render

START_RENDER = """\
１２３４５６７８９
車馬象士將士象馬車
・・・・・・・・・
・砲・・・・・砲・
卒・卒・卒・卒・卒
・・・・・・・・・
～楚河～～汉界～～
・・・・・・・・・
兵・兵・兵・兵・兵
・炮・・・・・炮・
・・・・・・・・・
俥傌相仕帥仕相傌俥
九八七六五四三二一"""


def test_render_start_position():
    assert render(Position.from_fen(START_FEN)) == START_RENDER


def test_render_color_marks_red_pieces():
    out = render(Position.from_fen(START_FEN), color=True)
    assert "\x1b[31m帥\x1b[0m" in out
    assert "\x1b[31m將" not in out


def test_render_after_move():
    pos = Position.from_fen(START_FEN)
    pos.make_move((7 * 9 + 7, 7 * 9 + 4))  # 炮二平五
    lines = render(pos).splitlines()
    assert lines[9] == "・炮・・炮・・・・"
