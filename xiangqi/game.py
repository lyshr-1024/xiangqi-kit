"""棋局：局面 + 完整棋谱 + JSON 持久化 + 终局判定。

长将/长捉按简化规则处理：同一局面（棋盘+走子方）第三次出现即判和，
与正式规则（长将、长捉一方判负）不同。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from xiangqi.board import BLACK, START_FEN, Position
from xiangqi.notation import parse_notation, to_notation


class Game:
    """一盘棋，走法用中文记谱驱动，可保存/载入 JSON。"""

    def __init__(self, start_fen: str = START_FEN, name: str = "default") -> None:
        self.name = name
        self.start_fen = start_fen
        self.position = Position.from_fen(start_fen)
        self.moves: list[dict] = []
        self._line: Counter = Counter([self._key()])

    def _key(self) -> tuple[str, str]:
        return ("".join(self.position.board), self.position.side_to_move)

    @property
    def result(self) -> tuple[str, str] | None:
        """终局返回 (胜方/'draw', 原因)，未终局返回 None。"""
        pos = self.position
        if not pos.legal_moves():
            winner = "red" if pos.side_to_move == BLACK else "black"
            return (winner, "checkmate" if pos.in_check() else "stalemate")
        if self._line[self._key()] >= 3:
            return ("draw", "repetition")
        return None

    def move(self, text: str) -> str:
        """按中文记谱走一步，返回规范记谱。"""
        if self.result is not None:
            raise ValueError("棋局已结束")
        mv = parse_notation(self.position, text)
        canonical = to_notation(self.position, mv)
        self.position.make_move(mv)
        self.moves.append({"from": mv[0], "to": mv[1], "notation": canonical})
        self._line[self._key()] += 1
        return canonical

    def undo(self) -> str:
        """悔一步棋，返回被撤销的记谱。"""
        if not self.moves:
            raise ValueError("没有可悔的棋")
        moves = self.moves[:-1]
        undone = self.moves[-1]["notation"]
        self._reset(moves)
        return undone

    def _reset(self, moves: list[dict]) -> None:
        self.position = Position.from_fen(self.start_fen)
        self.moves = []
        self._line = Counter([self._key()])
        for m in moves:
            self.position.make_move((m["from"], m["to"]))
            self.moves.append(m)
            self._line[self._key()] += 1

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_fen": self.start_fen,
            "moves": self.moves,
            "fen": self.position.to_fen(),  # 仅供人读，载入时以 moves 重放为准
        }

    def save(self, path: Path) -> None:
        """保存为 JSON。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> "Game":
        """从 JSON 载入并重放棋谱。"""
        data = json.loads(Path(path).read_text())
        game = cls(start_fen=data["start_fen"], name=data.get("name", "default"))
        game._reset([
            {"from": m["from"], "to": m["to"], "notation": m["notation"]}
            for m in data["moves"]
        ])
        return game
