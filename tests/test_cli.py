"""CLI 子命令测试：进程内调用 main(argv)，用 XIANGQI_HOME 隔离存档目录。"""
import json

import pytest

from xiangqi.cli import main


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("XIANGQI_HOME", str(tmp_path))
    return tmp_path


def test_new_creates_game_and_shows_board(home, capsys):
    assert main(["new"]) == 0
    out = capsys.readouterr().out
    assert "楚河" in out
    assert "轮到红方" in out
    assert (home / "games" / "default.json").exists()


def test_new_refuses_overwrite_without_force(capsys):
    main(["new"])
    assert main(["new"]) == 1
    assert "已存在" in capsys.readouterr().err
    assert main(["new", "--force"]) == 0


def test_move_updates_and_persists(home, capsys):
    main(["new"])
    assert main(["move", "炮二平五"]) == 0
    out = capsys.readouterr().out
    assert "轮到黑方" in out
    data = json.loads((home / "games" / "default.json").read_text())
    assert data["moves"][0]["notation"] == "炮二平五"
    # 新的 CLI 调用（等于新会话）能续上
    assert main(["move", "马8进7"]) == 0
    assert main(["history"]) == 0
    out = capsys.readouterr().out
    assert "炮二平五" in out and "马8进7" in out


def test_move_illegal_reports_error(capsys):
    main(["new"])
    assert main(["move", "马二进二"]) == 1
    assert "马二进二" in capsys.readouterr().err


def test_move_without_game_hints_new(capsys):
    assert main(["move", "炮二平五"]) == 1
    assert "xq new" in capsys.readouterr().err


def test_legal_lists_44_moves_at_start(capsys):
    main(["new"])
    capsys.readouterr()
    assert main(["legal"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 44
    assert "炮二平五" in lines


def test_fen_outputs_current_fen(capsys):
    main(["new"])
    main(["move", "炮二平五"])
    capsys.readouterr()
    assert main(["fen"]) == 0
    fen = capsys.readouterr().out.strip()
    assert fen.endswith("b - - 1 1")
    assert "C" in fen


def test_undo_reverts_last_move(capsys):
    main(["new"])
    main(["move", "炮二平五"])
    assert main(["undo"]) == 0
    capsys.readouterr()
    main(["fen"])
    assert main(["legal"]) == 0
    out = capsys.readouterr().out
    assert "w - - 0 1" in out  # 回到起始局面


def test_named_games_are_independent(home, capsys):
    main(["new", "--name", "a"])
    main(["new", "--name", "b"])
    main(["move", "炮二平五", "--name", "a"])
    capsys.readouterr()
    main(["fen", "--name", "b"])
    assert "1C5C1" in capsys.readouterr().out
    assert (home / "games" / "a.json").exists()
    assert (home / "games" / "b.json").exists()


def test_show_reports_result_when_game_over(capsys):
    main(["new", "--fen", "4k4/R7R/9/9/9/9/9/9/9/3K5 w - - 0 1"])
    main(["move", "车一进一"])
    capsys.readouterr()
    assert main(["show"]) == 0
    out = capsys.readouterr().out
    assert "红方胜" in out and "将死" in out
