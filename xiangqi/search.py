"""Alpha-beta 搜索 + 迭代加深 + 置换表，子力与位置估值。

目标业余中低水平。困毙与将死同为负（象棋无逼和），统一按被杀计分。
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from xiangqi.board import Move, Position, RED

MATE = 100_000

_VALUES = {"R": 900, "N": 400, "C": 450, "P": 100, "A": 200, "B": 200, "K": 0}


def _build_pst() -> dict[str, list[int]]:
    """按简单启发生成红方视角的位置估值表（列对称，黑方镜像行使用）。"""
    pst: dict[str, list[int]] = {}
    for kind in _VALUES:
        table = []
        for s in range(90):
            r, c = divmod(s, 9)
            center = 4 - abs(c - 4)
            advance = 9 - r
            if kind == "P":
                v = 20 + advance * 10 + center * 5 if r <= 4 else advance * 2
            elif kind == "N":
                v = center * 4 + (10 if r <= 4 else 0)
            elif kind == "C":
                v = center * 2
            elif kind == "R":
                v = center * 2 + (10 if r <= 4 else 0)
            elif kind == "K":
                v = 8 if r == 9 else 0
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


class _Searcher:
    def __init__(self, pos: Position, deadline: float) -> None:
        self.pos = pos
        self.deadline = deadline
        self.tt: dict = {}
        self.nodes = 0

    def _tick(self) -> None:
        self.nodes += 1
        if self.nodes % 2048 == 0 and time.monotonic() >= self.deadline:
            raise _Timeout

    def _eval_stm(self) -> int:
        score = evaluate(self.pos)
        return score if self.pos.side_to_move == RED else -score

    def _ordered(self, moves: list[Move], tt_move: Move | None) -> list[Move]:
        board = self.pos.board

        def key(mv: Move) -> int:
            if mv == tt_move:
                return -(10**9)
            captured = board[mv[1]]
            if captured != ".":
                return -(_VALUES[captured.upper()] * 10 - _VALUES[board[mv[0]].upper()])
            return 0

        return sorted(moves, key=key)

    def _qsearch(self, alpha: int, beta: int) -> int:
        self._tick()
        stand = self._eval_stm()
        if stand >= beta:
            return stand
        alpha = max(alpha, stand)
        board = self.pos.board
        captures = [mv for mv in self.pos.legal_moves() if board[mv[1]] != "."]
        for mv in self._ordered(captures, None):
            undo = self.pos.make_move(mv)
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
        key = ("".join(self.pos.board), self.pos.side_to_move)
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

        if depth == 0:
            return self._qsearch(alpha, beta)

        moves = self.pos.legal_moves()
        if not moves:
            return -(MATE - ply)  # 将死与困毙同为负

        best = -MATE * 2
        best_move = None
        original_alpha = alpha
        for mv in self._ordered(moves, tt_move):
            undo = self.pos.make_move(mv)
            try:
                score = -self._negamax(depth - 1, -beta, -alpha, ply + 1)
            finally:
                self.pos.unmake_move(undo)
            if score > best:
                best = score
                best_move = mv
            alpha = max(alpha, score)
            if alpha >= beta:
                break

        flag = 1 if best >= beta else (2 if best <= original_alpha else 0)
        self.tt[key] = (depth, best, flag, best_move)
        return best

    def root(self, depth: int) -> tuple[int, Move]:
        moves = self.pos.legal_moves()
        key = ("".join(self.pos.board), self.pos.side_to_move)
        entry = self.tt.get(key)
        tt_move = entry[3] if entry else None
        best = -MATE * 2
        best_move = moves[0]
        alpha, beta = -MATE * 2, MATE * 2
        for mv in self._ordered(moves, tt_move):
            undo = self.pos.make_move(mv)
            try:
                score = -self._negamax(depth - 1, -beta, -alpha, 1)
            finally:
                self.pos.unmake_move(undo)
            if score > best:
                best = score
                best_move = mv
            alpha = max(alpha, score)
        self.tt[key] = (depth, best, 0, best_move)
        return best, best_move


def search(pos: Position, time_limit: float = 2.0, max_depth: int = 32) -> SearchResult | None:
    """迭代加深搜索，返回限时内最深完成层的最佳走法；无棋可走返回 None。"""
    if not pos.legal_moves():
        return None
    searcher = _Searcher(pos, time.monotonic() + time_limit)
    result: SearchResult | None = None
    for depth in range(1, max_depth + 1):
        try:
            score, move = searcher.root(depth)
        except _Timeout:
            break
        result = SearchResult(move, score, depth, searcher.nodes)
        if score > MATE - 1000:  # 已找到杀棋，不必更深
            break
    if result is None:
        result = SearchResult(pos.legal_moves()[0], 0, 0, searcher.nodes)
    return result
