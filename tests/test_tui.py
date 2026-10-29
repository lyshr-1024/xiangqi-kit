import json
import subprocess
import sys
from pathlib import Path

import pytest

from xiangqi import kitty
from xiangqi.board import BLACK, RED
from xiangqi.game import Game
from xiangqi.tui import from_screen, to_screen, undo_turn


@pytest.mark.parametrize("flipped", [False, True])
def test_screen_mapping_round_trips_with_tolerance(flipped):
    for square in range(90):
        y, x = to_screen(square, flipped)
        for dy, dx in [(0, -1), (0, 0), (0, 1), (0, 2), (-1, 0)]:
            assert from_screen(y + dy, x + dx, flipped) == square


def test_flipped_puts_red_rook_top_right():
    assert to_screen(81, False) > to_screen(0, False)
    assert to_screen(81, True) == to_screen(8, False)


def test_click_outside_board_is_none():
    y, x = to_screen(89, False)
    assert from_screen(y + 3, x, False) is None
    assert from_screen(y, x + 5, False) is None


def test_undo_turn_reverts_ai_and_player_moves():
    game = Game()
    game.move("炮二平五")
    game.move("马8进7")
    undo_turn(game, RED)
    assert game.moves == []


def test_undo_turn_refuses_when_only_ai_has_moved():
    game = Game()
    game.move("炮二平五")
    with pytest.raises(ValueError):
        undo_turn(game, BLACK)
    assert len(game.moves) == 1


@pytest.mark.skipif(sys.platform != "darwin", reason="棋盘图片用 macOS 的 JXA 渲染")
def test_board_art_renders_board_and_all_piece_states(tmp_path):
    cfg = {"cw": 8, "ch": 16, "px": 4, "py": 2, "mx": 3, "my": 2.5, "out": str(tmp_path), "top": "１２３４５６７８９",
           "bottom": "九八七六五四三二一", "pieces": {"wc": ["炮", "red"], "bk": ["將", "black"]}}
    script = Path(kitty.__file__).with_name("board_art.js")
    subprocess.run(["osascript", "-l", "JavaScript", str(script), json.dumps(cfg)], check=True)
    names = {p.stem for p in tmp_path.glob("*.png")}
    states = ["normal", "last", "selected", "target"]
    assert names == {"board", "dot", "from"} | {f"{n}-{s}" for n in ("wc", "bk") for s in states}
