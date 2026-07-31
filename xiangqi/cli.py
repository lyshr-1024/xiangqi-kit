"""xq — 象棋 CLI。棋局存于 $XIANGQI_HOME/games/<name>.json（默认 ~/.xiangqi）。"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from xiangqi.board import RED
from xiangqi.game import Game
from xiangqi.notation import to_notation
from xiangqi.render import render

_RESULT_TEXT = {"red": "红方胜", "black": "黑方胜", "draw": "和棋"}
_REASON_TEXT = {"checkmate": "将死", "stalemate": "困毙", "repetition": "三次重复局面"}


def _game_path(name: str) -> Path:
    home = Path(os.environ.get("XIANGQI_HOME") or Path.home() / ".xiangqi")
    return home / "games" / f"{name}.json"


def _load(name: str) -> Game:
    path = _game_path(name)
    if not path.exists():
        raise ValueError(f"棋局 {name!r} 不存在，先用 xq new 开局")
    return Game.load(path)


def _print_state(game: Game) -> None:
    print(render(game.position, color=sys.stdout.isatty()))
    result = game.result
    if result:
        winner, reason = result
        print(f"棋局结束：{_RESULT_TEXT[winner]}（{_REASON_TEXT[reason]}）")
    else:
        side = "红方" if game.position.side_to_move == RED else "黑方"
        check = "（将军！）" if game.position.in_check() else ""
        print(f"轮到{side}{check}")


def _cmd_new(args: argparse.Namespace) -> int:
    path = _game_path(args.name)
    if path.exists() and not args.force:
        raise ValueError(f"棋局 {args.name!r} 已存在，用 --force 覆盖")
    game = Game(start_fen=args.fen, name=args.name)
    game.save(path)
    _print_state(game)
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    _print_state(_load(args.name))
    return 0


def _cmd_move(args: argparse.Namespace) -> int:
    game = _load(args.name)
    canonical = game.move(args.notation)
    game.save(_game_path(args.name))
    print(f"已走：{canonical}")
    _print_state(game)
    return 0


def _cmd_undo(args: argparse.Namespace) -> int:
    game = _load(args.name)
    undone = game.undo()
    game.save(_game_path(args.name))
    print(f"已撤销：{undone}")
    _print_state(game)
    return 0


def _cmd_legal(args: argparse.Namespace) -> int:
    game = _load(args.name)
    for mv in sorted(to_notation(game.position, m) for m in game.position.legal_moves()):
        print(mv)
    return 0


def _cmd_fen(args: argparse.Namespace) -> int:
    print(_load(args.name).position.to_fen())
    return 0


def _cmd_history(args: argparse.Namespace) -> int:
    notations = [m["notation"] for m in _load(args.name).moves]
    for i in range(0, len(notations), 2):
        pair = "  ".join(notations[i : i + 2])
        print(f"{i // 2 + 1}. {pair}")
    return 0


def _cmd_ai(args: argparse.Namespace) -> int:
    from xiangqi.search import search

    game = _load(args.name)
    if game.result is not None:
        raise ValueError("棋局已结束")
    result = search(game.position, time_limit=args.time)
    notation = to_notation(game.position, result.move)
    game.move(notation)
    game.save(_game_path(args.name))
    print(f"AI 走：{notation}（深度 {result.depth}，评分 {result.score:+d}，{result.nodes} 节点）")
    _print_state(game)
    return 0


def main(argv: list[str] | None = None) -> int:
    from xiangqi.board import START_FEN

    parser = argparse.ArgumentParser(prog="xq", description="中国象棋 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, func, help: str) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help)
        p.add_argument("-n", "--name", default="default", help="棋局名（默认 default）")
        p.set_defaults(func=func)
        return p

    p_new = add("new", _cmd_new, "开新棋局")
    p_new.add_argument("--fen", default=START_FEN, help="起始 FEN（默认标准开局）")
    p_new.add_argument("--force", action="store_true", help="覆盖已存在的棋局")
    add("show", _cmd_show, "显示棋盘")
    p_move = add("move", _cmd_move, "按中文记谱走一步")
    p_move.add_argument("notation", help="如 炮二平五 / 马8进7 / 前车进三")
    p_ai = add("ai", _cmd_ai, "让 AI 走一步")
    p_ai.add_argument("--time", type=float, default=2.0, help="单步限时秒数（默认 2）")
    add("undo", _cmd_undo, "悔一步棋")
    add("legal", _cmd_legal, "列出所有合法着法")
    add("fen", _cmd_fen, "输出当前 FEN")
    add("history", _cmd_history, "显示棋谱")

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
