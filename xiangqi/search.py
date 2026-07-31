"""Alpha-beta 搜索 + 迭代加深 + 置换表，子力与位置估值。

目标业余中低水平。困毙与将死同为负（象棋无逼和），统一按被杀计分。
搜索路径或对局历史中出现过的局面一律按和棋（0 分）剪掉，避免无意义
往返与长将循环。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Mapping

from xiangqi.board import Move, Position, RED

MATE = 100_000

_VALUES = {"R": 900, "N": 400, "C": 450, "P": 100, "A": 200, "B": 200, "K": 0}

# 各兵种按行的位置分（红方视角，row 0 = 黑方底线），列上叠加中心奖励。
# 幅度取兵值的 1/4 左右，让"发展一步"与"空着"拉开差距。
_ROW_BONUS = {
    "N": (4, 12, 18, 16, 14, 10, 6, 4, 2, 0),
    "R": (14, 18, 12, 10, 12, 12, 6, 4, 4, 6),
    "C": (6, 4, 10, 8, 10, 8, 4, 2, 2, 0),
}


def _build_pst() -> dict[str, list[int]]:
    pst: dict[str, list[int]] = {}
    for kind in _VALUES:
        table = []
        for s in range(90):
            r, c = divmod(s, 9)
            center = 4 - abs(c - 4)
            if kind == "N":
                v = _ROW_BONUS["N"][r] + center * 5
            elif kind == "R":
                v = _ROW_BONUS["R"][r] + center * 2
            elif kind == "C":
                v = _ROW_BONUS["C"][r] + (12 if c == 4 else center * 2)
            elif kind == "P":
                if r == 0:
                    v = 15  # 老兵
                elif r <= 4:
                    v = 25 + (4 - r) * 12 + center * 5
                else:
                    v = 8 if r == 5 else 0
            elif kind == "K":
                v = 10 if r == 9 else (2 if r == 8 else -8)
            else:
                v = 0
            table.append(v)
        pst[kind] = table
    return pst


_PST = _build_pst()
_MIRROR = [(9 - s // 9) * 9 + s % 9 for s in range(90)]


def evaluate(pos: Position) -> int:
    """红方视角的静态估值。"""
    score = 0
    for s, pc in enumerate(pos.board):
        if pc == ".":
            continue
        kind = pc.upper()
        if pc.isupper():
            score += _VALUES[kind] + _PST[kind][s]
        else:
            score -= _VALUES[kind] + _PST[kind][_MIRROR[s]]
    return score


@dataclass
class SearchResult:
    move: Move
    score: int
    depth: int
    nodes: int


class _Timeout(Exception):
    pass


def _key(pos: Position) -> str:
    return "".join(pos.board) + pos.side_to_move


class _Searcher:
    def __init__(self, pos: Position, deadline: float, history: Mapping[str, int]) -> None:
        self.pos = pos
        self.deadline = deadline
        self.history = history
        self.path: dict[str, bool] = {}
        self.tt: dict = {}
        self.killers: dict[int, list] = {}
        self.hist_score: dict[Move, int] = {}
        self.nodes = 0

    def _tick(self) -> None:
        self.nodes += 1
        if self.nodes % 2048 == 0 and time.monotonic() >= self.deadline:
            raise _Timeout

    def _eval_stm(self) -> int:
        score = evaluate(self.pos)
        return score if self.pos.side_to_move == RED else -score

    def _ordered(self, moves: list[Move], tt_move: Move | None, ply: int) -> list[Move]:
        board = self.pos.board
        killers = self.killers.get(ply, ())

        def order_key(mv: Move) -> int:
            if mv == tt_move:
                return -(10**9)
            captured = board[mv[1]]
            if captured != ".":
                return -(10**6 + _VALUES[captured.upper()] * 10 - _VALUES[board[mv[0]].upper()])
            if mv in killers:
                return -(10**5)
            return -self.hist_score.get(mv, 0)

        return sorted(moves, key=order_key)

    def _record_quiet_cutoff(self, mv: Move, depth: int, ply: int) -> None:
        killers = self.killers.setdefault(ply, [None, None])
        if killers[0] != mv:
            killers[1] = killers[0]
            killers[0] = mv
        self.hist_score[mv] = self.hist_score.get(mv, 0) + depth * depth

    def _qsearch(self, alpha: int, beta: int) -> int:
        self._tick()
        stand = self._eval_stm()
        if stand >= beta:
            return stand
        alpha = max(alpha, stand)
        board = self.pos.board
        us = self.pos.side_to_move
        captures = [mv for mv in self.pos._pseudo_moves() if board[mv[1]] != "."]
        for mv in self._ordered(captures, None, -1):
            undo = self.pos.make_move(mv)
            if self.pos.in_check(us):
                self.pos.unmake_move(undo)
                continue
            try:
                score = -self._qsearch(-beta, -alpha)
            finally:
                self.pos.unmake_move(undo)
            if score >= beta:
                return score
            alpha = max(alpha, score)
        return alpha

    def _negamax(self, depth: int, alpha: int, beta: int, ply: int) -> int:
        self._tick()
        key = _key(self.pos)
        if ply > 0 and (key in self.path or key in self.history):
            return 0  # 重复局面按和棋

        entry = self.tt.get(key)
        tt_move = entry[3] if entry else None
        if entry and entry[0] >= depth:
            _, score, flag, _ = entry
            if flag == 0:
                return score
            if flag == 1 and score >= beta:
                return score
            if flag == 2 and score <= alpha:
                return score

        if depth <= 0:
            return self._qsearch(alpha, beta)

        us = self.pos.side_to_move
        best = -MATE * 2
        best_move = None
        original_alpha = alpha
        found_legal = False
        self.path[key] = True
        try:
            for mv in self._ordered(self.pos._pseudo_moves(), tt_move, ply):
                undo = self.pos.make_move(mv)
                if self.pos.in_check(us):
                    self.pos.unmake_move(undo)
                    continue
                found_legal = True
                try:
                    ext = 1 if ply < 32 and self.pos.in_check() else 0  # 将军延伸
                    score = -self._negamax(depth - 1 + ext, -beta, -alpha, ply + 1)
                finally:
                    self.pos.unmake_move(undo)
                if score > best:
                    best = score
                    best_move = mv
                alpha = max(alpha, score)
                if alpha >= beta:
                    if self.pos.board[mv[1]] == ".":
                        self._record_quiet_cutoff(mv, depth, ply)
                    break
        finally:
            del self.path[key]

        if not found_legal:
            return -(MATE - ply)  # 将死与困毙同为负

        flag = 1 if best >= beta else (2 if best <= original_alpha else 0)
        self.tt[key] = (depth, best, flag, best_move)
        return best

    def root(self, depth: int) -> tuple[int, Move]:
        key = _key(self.pos)
        entry = self.tt.get(key)
        tt_move = entry[3] if entry else None
        us = self.pos.side_to_move
        best = -MATE * 2
        best_move = None
        alpha, beta = -MATE * 2, MATE * 2
        self.path[key] = True
        try:
            for mv in self._ordered(self.pos._pseudo_moves(), tt_move, 0):
                undo = self.pos.make_move(mv)
                if self.pos.in_check(us):
                    self.pos.unmake_move(undo)
                    continue
                try:
                    score = -self._negamax(depth - 1, -beta, -alpha, 1)
                finally:
                    self.pos.unmake_move(undo)
                if score > best:
                    best = score
                    best_move = mv
                alpha = max(alpha, score)
        finally:
            del self.path[key]
        self.tt[key] = (depth, best, 0, best_move)
        return best, best_move


def search(
    pos: Position,
    time_limit: float = 2.0,
    max_depth: int = 32,
    history: Mapping[str, int] | None = None,
) -> SearchResult | None:
    """迭代加深搜索，返回限时内最深完成层的最佳走法；无棋可走返回 None。

    history 传对局中出现过的局面计数（键 = 棋盘串+走子方），
    搜索会把走向这些局面视为和棋，用于避免长打循环。
    """
    fallback = pos.legal_moves()
    if not fallback:
        return None
    searcher = _Searcher(pos, time.monotonic() + time_limit, history or {})
    result: SearchResult | None = None
    for depth in range(1, max_depth + 1):
        try:
            score, move = searcher.root(depth)
        except _Timeout:
            break
        if move is not None:
            result = SearchResult(move, score, depth, searcher.nodes)
        if score > MATE - 1000:
            break
    if result is None:
        result = SearchResult(fallback[0], 0, 0, searcher.nodes)
    return result
