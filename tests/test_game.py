"""Game：棋谱管理、持久化、终局判定（含三次重复判和的简化规则）。"""
import pytest

from xiangqi import START_FEN, sq
from xiangqi.game import Game


def test_new_game_starts_at_startpos():
    game = Game()
    assert game.position.to_fen() == START_FEN
    assert game.moves == []
    assert game.result is None


def test_move_by_notation_appends_history():
    game = Game()
    assert game.move("炮2平5") == "炮二平五"
    assert game.move("马8进7") == "马8进7"
    assert [m["notation"] for m in game.moves] == ["炮二平五", "马8进7"]
    assert game.position.board[sq(7, 4)] == "C"


def test_undo_restores_previous_position():
    game = Game()
    game.move("炮二平五")
    fen_after_first = game.position.to_fen()
    game.move("马8进7")
    assert game.undo() == "马8进7"
    assert game.position.to_fen() == fen_after_first
    assert len(game.moves) == 1


def test_undo_empty_raises():
    with pytest.raises(ValueError):
        Game().undo()


def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "g.json"
    game = Game(name="test")
    game.move("炮二平五")
    game.move("马8进7")
    game.save(path)
    loaded = Game.load(path)
    assert loaded.name == "test"
    assert loaded.position.to_fen() == game.position.to_fen()
    assert [m["notation"] for m in loaded.moves] == ["炮二平五", "马8进7"]
    loaded.move("马二进三")  # 载入后可以继续走


def test_checkmate_result():
    game = Game(start_fen="4k4/R7R/9/9/9/9/9/9/9/3K5 w - - 0 1")
    game.move("车一进一")
    assert game.result == ("red", "checkmate")
    with pytest.raises(ValueError):
        game.move("车九平八")


def test_stalemate_result():
    game = Game(start_fen="4k4/3R2R2/9/9/9/9/9/9/9/3K5 w - - 0 1")
    game.move("车三平四")
    assert game.result == ("red", "stalemate")


def test_threefold_repetition_draw():
    game = Game(start_fen="3k5/r8/9/9/9/9/9/4R4/9/5K3 w - - 0 1")
    cycle = ["车五平四", "车1平2", "车四平五", "车2平1"]
    for text in cycle + cycle[:-1]:
        game.move(text)
        assert game.result is None
    game.move(cycle[-1])  # 初始局面第三次出现
    assert game.result == ("draw", "repetition")


def test_repetition_survives_save_load(tmp_path):
    game = Game(start_fen="3k5/r8/9/9/9/9/9/4R4/9/5K3 w - - 0 1")
    for text in ["车五平四", "车1平2", "车四平五", "车2平1"] * 2:
        game.move(text)
    path = tmp_path / "g.json"
    game.save(path)
    assert Game.load(path).result == ("draw", "repetition")
