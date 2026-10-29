from pathlib import Path

import pytest

from xiangqi.board import sq
from xiangqi.game import Game
from xiangqi.notation import to_notation
from xiangqi.uci import Engine, find_engine, from_uci, to_uci

INSTALLED = find_engine(Path.home() / ".xiangqi")


def test_uci_coordinates_match_red_view():
    assert to_uci((sq(7, 7), sq(7, 4))) == "h2e2"  # 炮二平五
    assert to_uci((sq(0, 1), sq(2, 2))) == "b9c7"  # 马8进7
    for move in [(0, 89), (sq(9, 4), sq(8, 4)), (sq(3, 0), sq(4, 0))]:
        assert from_uci(to_uci(move)) == move


def test_find_engine_prefers_env_then_home(tmp_path, monkeypatch):
    monkeypatch.delenv("XIANGQI_ENGINE", raising=False)
    monkeypatch.setenv("PATH", "")
    assert find_engine(tmp_path) is None
    installed = tmp_path / "engines" / "pikafish" / "pikafish"
    installed.parent.mkdir(parents=True)
    installed.touch()
    assert find_engine(tmp_path) == installed
    custom = tmp_path / "my-engine"
    custom.touch()
    monkeypatch.setenv("XIANGQI_ENGINE", str(custom))
    assert find_engine(tmp_path) == custom


@pytest.mark.skipif(INSTALLED is None, reason="本机未安装 Pikafish")
def test_pikafish_plays_legal_moves_with_history():
    engine = Engine(INSTALLED)
    try:
        game = Game()
        for _ in range(4):
            move = engine.best_move(game, 0.2)
            assert move in game.position.legal_moves()
            game.move(to_notation(game.position, move))
    finally:
        engine.close()
