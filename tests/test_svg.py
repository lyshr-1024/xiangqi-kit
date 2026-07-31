"""SVG 棋盘渲染与 xq svg 子命令测试。"""
import json

import pytest

from xiangqi import Position, START_FEN, sq
from xiangqi.svg import render_svg


def test_render_svg_start_position():
    svg = render_svg(Position.from_fen(START_FEN))
    assert svg.startswith("<svg")
    assert 'viewBox="0 0 580 640"' in svg
    assert svg.count("<circle") >= 64  # 32 子 × 内外两圈
    for ch in "帥將俥車傌馬炮砲兵卒仕士相象":
        assert ch in svg
    assert "楚 河" in svg


def test_render_svg_marks_last_move():
    pos = Position.from_fen(START_FEN)
    mv = (sq(7, 7), sq(7, 4))
    pos.make_move(mv)
    svg = render_svg(pos, last_move=mv)
    assert svg.count('class="lastmove"') == 2
    assert render_svg(pos).count('class="lastmove"') == 0


def test_cli_svg_writes_file_and_prints_path(tmp_path, monkeypatch, capsys):
    from xiangqi.cli import main

    monkeypatch.setenv("XIANGQI_HOME", str(tmp_path))
    main(["new"])
    main(["move", "炮二平五"])
    capsys.readouterr()
    assert main(["svg"]) == 0
    path = capsys.readouterr().out.strip()
    assert path.endswith("default.svg")
    content = (tmp_path / "boards" / "default.svg").read_text()
    assert content.startswith("<svg")
    assert content.count('class="lastmove"') == 2


def test_cli_svg_custom_out(tmp_path, monkeypatch, capsys):
    from xiangqi.cli import main

    monkeypatch.setenv("XIANGQI_HOME", str(tmp_path))
    main(["new"])
    capsys.readouterr()
    out = tmp_path / "b.svg"
    assert main(["svg", "--out", str(out)]) == 0
    assert capsys.readouterr().out.strip() == str(out)
    assert out.read_text().startswith("<svg")
