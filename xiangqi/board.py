"""局面表示、FEN 序列化、合法走法生成与 perft。

坐标：row 0 = 黑方底线，row 9 = 红方底线，col 0 = FEN 每段首格。
格子编号 square = row * 9 + col。红方大写（RNBAKCP），黑方小写。
"""
from __future__ import annotations

Move = tuple[int, int]

RED = "w"
BLACK = "b"

START_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

_PIECES = set("rnbakcpRNBAKCP")
_ORTHO = ((-1, 0), (1, 0), (0, -1), (0, 1))
_DIAG = ((-1, -1), (-1, 1), (1, -1), (1, 1))
_HORSE = ((-2, -1), (-2, 1), (2, -1), (2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2))
_ELEPHANT = ((-2, -2), (-2, 2), (2, -2), (2, 2))


def sq(row: int, col: int) -> int:
    """(row, col) 转格子编号。"""
    return row * 9 + col


def _in_palace(r: int, c: int, red: bool) -> bool:
    return 3 <= c <= 5 and (7 <= r <= 9 if red else 0 <= r <= 2)


class Position:
    """一个可变的象棋局面，走法通过 make/unmake 原地更新。"""

    __slots__ = ("board", "side_to_move", "halfmove_clock", "fullmove_number")

    def __init__(
        self,
        board: list[str],
        side_to_move: str = RED,
        halfmove_clock: int = 0,
        fullmove_number: int = 1,
    ) -> None:
        self.board = board
        self.side_to_move = side_to_move
        self.halfmove_clock = halfmove_clock
        self.fullmove_number = fullmove_number

    @classmethod
    def from_fen(cls, fen: str) -> "Position":
        """解析 FEN（象棋变体，UCCI 风格）。"""
        fields = fen.split()
        if len(fields) < 2:
            raise ValueError(f"FEN 字段不足: {fen!r}")
        rows = fields[0].split("/")
        if len(rows) != 10:
            raise ValueError(f"FEN 应有 10 行, 实际 {len(rows)}: {fen!r}")
        board: list[str] = []
        for row in rows:
            cols: list[str] = []
            for ch in row:
                if ch.isdigit():
                    cols.extend("." * int(ch))
                elif ch in _PIECES:
                    cols.append(ch)
                else:
                    raise ValueError(f"FEN 含非法字符 {ch!r}: {fen!r}")
            if len(cols) != 9:
                raise ValueError(f"FEN 行宽应为 9, 实际 {len(cols)}: {row!r}")
            board.extend(cols)
        side = fields[1]
        if side not in (RED, BLACK):
            raise ValueError(f"走子方应为 w/b, 实际 {side!r}")
        halfmove = int(fields[4]) if len(fields) > 4 else 0
        fullmove = int(fields[5]) if len(fields) > 5 else 1
        return cls(board, side, halfmove, fullmove)

    def to_fen(self) -> str:
        """序列化为 FEN。"""
        rows: list[str] = []
        for r in range(10):
            row = ""
            empty = 0
            for c in range(9):
                pc = self.board[r * 9 + c]
                if pc == ".":
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += pc
            if empty:
                row += str(empty)
            rows.append(row)
        return (
            f"{'/'.join(rows)} {self.side_to_move} - - "
            f"{self.halfmove_clock} {self.fullmove_number}"
        )

    def make_move(self, move: Move) -> tuple:
        """执行走法，返回 unmake_move 所需的 undo 信息。"""
        frm, to = move
        piece = self.board[frm]
        captured = self.board[to]
        undo = (frm, to, piece, captured, self.halfmove_clock)
        self.board[to] = piece
        self.board[frm] = "."
        self.halfmove_clock = 0 if captured != "." else self.halfmove_clock + 1
        if self.side_to_move == BLACK:
            self.fullmove_number += 1
        self.side_to_move = BLACK if self.side_to_move == RED else RED
        return undo

    def unmake_move(self, undo: tuple) -> None:
        """撤销 make_move。"""
        frm, to, piece, captured, halfmove = undo
        self.board[frm] = piece
        self.board[to] = captured
        self.halfmove_clock = halfmove
        self.side_to_move = BLACK if self.side_to_move == RED else RED
        if self.side_to_move == BLACK:
            self.fullmove_number -= 1

    def in_check(self, side: str | None = None) -> bool:
        """side（默认走子方）的将/帅是否被攻击（含将帅照面）。"""
        side = side or self.side_to_move
        board = self.board
        red = side == RED
        ks = board.index("K" if red else "k")
        kr, kc = divmod(ks, 9)
        enemy_rook = "r" if red else "R"
        enemy_cannon = "c" if red else "C"
        enemy_king = "k" if red else "K"
        enemy_horse = "n" if red else "N"
        enemy_pawn = "p" if red else "P"

        # 车 / 炮 / 照面：沿四条直线扫，第一个子看车与对方将帅，第二个子看炮。
        # 仕相困于己方区域，永远够不到对方九宫，无需检查。
        for dr, dc in _ORTHO:
            r, c = kr + dr, kc + dc
            behind_screen = False
            while 0 <= r < 10 and 0 <= c < 9:
                pc = board[r * 9 + c]
                if pc != ".":
                    if not behind_screen:
                        if pc == enemy_rook or pc == enemy_king:
                            return True
                        behind_screen = True
                    else:
                        if pc == enemy_cannon:
                            return True
                        break
                r += dr
                c += dc

        # 马：马腿在马与王之间的斜邻格
        for dr, dc in _HORSE:
            r, c = kr + dr, kc + dc
            if 0 <= r < 10 and 0 <= c < 9 and board[r * 9 + c] == enemy_horse:
                lr = kr + (1 if dr > 0 else -1)
                lc = kc + (1 if dc > 0 else -1)
                if board[lr * 9 + lc] == ".":
                    return True

        # 兵：正面一格；过河兵可从两侧攻击
        enemy_fwd = 1 if red else -1
        pr = kr - enemy_fwd
        if 0 <= pr < 10 and board[pr * 9 + kc] == enemy_pawn:
            return True
        enemy_crossed = kr >= 5 if red else kr <= 4
        if enemy_crossed:
            for dc in (-1, 1):
                c = kc + dc
                if 0 <= c < 9 and board[kr * 9 + c] == enemy_pawn:
                    return True
        return False

    def _pseudo_moves(self) -> list[Move]:
        board = self.board
        red = self.side_to_move == RED
        moves: list[Move] = []
        for s, pc in enumerate(board):
            if pc == "." or pc.isupper() != red:
                continue
            r, c = divmod(s, 9)
            kind = pc.upper()
            if kind == "R":
                for dr, dc in _ORTHO:
                    nr, nc = r + dr, c + dc
                    while 0 <= nr < 10 and 0 <= nc < 9:
                        target = board[nr * 9 + nc]
                        if target == ".":
                            moves.append((s, nr * 9 + nc))
                        else:
                            if target.isupper() != red:
                                moves.append((s, nr * 9 + nc))
                            break
                        nr += dr
                        nc += dc
            elif kind == "C":
                for dr, dc in _ORTHO:
                    nr, nc = r + dr, c + dc
                    while 0 <= nr < 10 and 0 <= nc < 9:
                        if board[nr * 9 + nc] == ".":
                            moves.append((s, nr * 9 + nc))
                        else:
                            break
                        nr += dr
                        nc += dc
                    # 越过炮架找第一个子，是敌子则可吃
                    nr += dr
                    nc += dc
                    while 0 <= nr < 10 and 0 <= nc < 9:
                        target = board[nr * 9 + nc]
                        if target != ".":
                            if target.isupper() != red:
                                moves.append((s, nr * 9 + nc))
                            break
                        nr += dr
                        nc += dc
            elif kind == "N":
                for dr, dc in _HORSE:
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < 10 and 0 <= nc < 9):
                        continue
                    lr = r + (dr // 2 if abs(dr) == 2 else 0)
                    lc = c + (dc // 2 if abs(dc) == 2 else 0)
                    if board[lr * 9 + lc] != ".":
                        continue
                    target = board[nr * 9 + nc]
                    if target == "." or target.isupper() != red:
                        moves.append((s, nr * 9 + nc))
            elif kind == "B":
                for dr, dc in _ELEPHANT:
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < 10 and 0 <= nc < 9):
                        continue
                    if red and nr < 5 or not red and nr > 4:
                        continue
                    if board[(r + dr // 2) * 9 + (c + dc // 2)] != ".":
                        continue
                    target = board[nr * 9 + nc]
                    if target == "." or target.isupper() != red:
                        moves.append((s, nr * 9 + nc))
            elif kind == "A":
                for dr, dc in _DIAG:
                    nr, nc = r + dr, c + dc
                    if not _in_palace(nr, nc, red):
                        continue
                    target = board[nr * 9 + nc]
                    if target == "." or target.isupper() != red:
                        moves.append((s, nr * 9 + nc))
            elif kind == "K":
                for dr, dc in _ORTHO:
                    nr, nc = r + dr, c + dc
                    if not _in_palace(nr, nc, red):
                        continue
                    target = board[nr * 9 + nc]
                    if target == "." or target.isupper() != red:
                        moves.append((s, nr * 9 + nc))
            elif kind == "P":
                fwd = -1 if red else 1
                nr = r + fwd
                if 0 <= nr < 10:
                    target = board[nr * 9 + c]
                    if target == "." or target.isupper() != red:
                        moves.append((s, nr * 9 + c))
                crossed = r <= 4 if red else r >= 5
                if crossed:
                    for dc in (-1, 1):
                        nc = c + dc
                        if 0 <= nc < 9:
                            target = board[r * 9 + nc]
                            if target == "." or target.isupper() != red:
                                moves.append((s, r * 9 + nc))
        return moves

    def legal_moves(self) -> list[Move]:
        """所有合法走法（排除送将与将帅照面）。"""
        us = self.side_to_move
        moves: list[Move] = []
        for mv in self._pseudo_moves():
            undo = self.make_move(mv)
            if not self.in_check(us):
                moves.append(mv)
            self.unmake_move(undo)
        return moves

    def is_checkmate(self) -> bool:
        """将死：被将军且无合法走法。"""
        return self.in_check() and not self.legal_moves()

    def is_stalemate(self) -> bool:
        """困毙：未被将军但无合法走法（象棋规则判负）。"""
        return not self.in_check() and not self.legal_moves()

    def perft(self, depth: int) -> int:
        """走法树叶节点计数，用于校验走法生成。"""
        if depth == 0:
            return 1
        moves = self.legal_moves()
        if depth == 1:
            return len(moves)
        total = 0
        for mv in moves:
            undo = self.make_move(mv)
            total += self.perft(depth - 1)
            self.unmake_move(undo)
        return total
