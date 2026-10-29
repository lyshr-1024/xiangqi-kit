"""xq play — curses 全屏棋盘：鼠标点选走子，AI 本地应手，存档与其他 xq 命令共用。

支持 Kitty 图形协议的终端（Ghostty 等）贴图片画木纹棋盘和圆形棋子，其余终端用字符画。
"""
from __future__ import annotations

import curses
import locale
import math
from pathlib import Path

from xiangqi import kitty
from xiangqi.board import BLACK, RED, Position
from xiangqi.game import Game
from xiangqi.notation import to_notation
from xiangqi.render import _BLACK_CHARS, _RED_CHARS
from xiangqi.uci import Engine

_TOP, _LEFT = 3, 2  # 左上交叉点的屏幕坐标
_PX, _PY = 4, 2  # 交叉点列距/行距，约为正方格（终端字符高≈宽×2）
# 交叉点的视觉中心在 (x+1 列边界, y 行正中)；棋盘图四周从中心线外扩 _MX 列、_MY 行，容纳半个棋子+边框+路数
_MX, _MY = 3, 2.5
_ART_TOP, _ART_LEFT = int(_TOP + 0.5 - _MY), _LEFT + 1 - _MX
_ART_ROWS, _ART_COLS = int(_PY * 9 + 2 * _MY), _PX * 8 + 2 * _MX
_PANEL, _PANEL_W = _LEFT + _PX * 8 + 8, 40
_MIN_LINES, _MIN_COLS = _ART_TOP + _ART_ROWS, _ART_LEFT + _ART_COLS
_BLACK_FILES = "１２３４５６７８９"
_RED_FILES = "九八七六五四三二一"
_RESULT_TEXT = {"red": "红方胜", "black": "黑方胜", "draw": "和棋"}
_REASON_TEXT = {"checkmate": "将死", "stalemate": "困毙", "repetition": "三次重复局面"}


def to_screen(square: int, flipped: bool) -> tuple[int, int]:
    r, c = divmod(square, 9)
    if flipped:
        r, c = 9 - r, 8 - c
    return _TOP + _PY * r, _LEFT + _PX * c


def from_screen(y: int, x: int, flipped: bool) -> int | None:
    """屏幕坐标转格子编号，交叉点周围半格内都算命中；落在棋盘外返回 None。"""
    r, c = (y - _TOP + _PY // 2) // _PY, (x - _LEFT + _PX // 2 - 1) // _PX
    if not (0 <= r <= 9 and 0 <= c <= 8):
        return None
    if flipped:
        r, c = 9 - r, 8 - c
    return r * 9 + c


def undo_turn(game: Game, side: str) -> None:
    """悔到上一次轮到玩家时：通常撤 AI+玩家两步，玩家走完即终局时只撤一步。"""
    n = 2 if game.position.side_to_move == side else 1
    if len(game.moves) < n:
        raise ValueError("没有可悔的棋")
    for _ in range(n):
        game.undo()


def _piece_image(pc: str) -> str:
    return ("w" if pc.isupper() else "b") + pc.lower()  # macOS 文件名不分大小写，不能直接用 R/r


def _cross(r: int, c: int) -> str:
    edge = c in (0, 8)  # 两侧边线贯穿河界，中间竖线在河界断开
    top = r == 0 if edge else r in (0, 5)
    bottom = r == 9 if edge else r in (4, 9)
    v = 0 if top else 2 if bottom else 1
    h = 0 if c == 0 else 2 if c == 8 else 1
    return "┌┬┐├┼┤└┴┘"[v * 3 + h]


class _App:
    def __init__(self, game: Game, path: Path, side: str, time_limit: float, graphics: bool, engine: Engine | None) -> None:
        self.game = game
        self.engine = engine
        self.path = path
        self.side = side
        self.time_limit = time_limit
        self.flipped = side == BLACK
        self.selected: int | None = None
        self.msg = ""
        self.confirm_new = False
        self.images = kitty.Images() if graphics else None
        self.cell: tuple[int, int] | None = None
        self.oy = self.ox = 0  # 棋盘+面板整体居中时的偏移，所有绘制与点击坐标都要加/减它

    def run(self, scr: curses.window) -> None:
        self.scr = scr
        curses.curs_set(0)
        curses.mousemask(curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED)
        curses.mouseinterval(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        self.pairs: dict[tuple[int, int], int] = {}
        if curses.COLORS >= 256:  # 字符模式的木色棋子；selected/target/last 为对应状态的底色
            self.disc = {"normal": 180, "last": 222, "selected": 117, "target": 114}
            self.ink = {RED: 124, BLACK: 16}
        else:
            self.disc = {"normal": curses.COLOR_YELLOW, "last": curses.COLOR_WHITE,
                         "selected": curses.COLOR_CYAN, "target": curses.COLOR_GREEN}
            self.ink = {RED: curses.COLOR_RED, BLACK: curses.COLOR_BLACK}
        scr.refresh()  # 先让 curses 完成首次清屏，再传图片
        self._load_images()
        try:
            while True:
                if self.game.result is None and self.game.position.side_to_move != self.side:
                    self._ai_move()
                    continue
                self._draw()
                key = scr.getch()
                if key == ord("q"):
                    return
                self._handle(key)
        finally:
            if self.images:
                self.images.clear()

    def _load_images(self) -> None:
        """按当前字符格像素尺寸渲染并传输图片，失败则退回字符模式。

        Ghostty 清屏（ED 2）会连图片数据一起清掉，所以必须在 curses 清屏之后调用。
        """
        if not self.images:
            return
        cell = self.cell = kitty.cell_size()
        if cell is None:
            self.images, self.msg = None, "终端未报告像素尺寸，改用字符棋盘"
            return
        top, bottom = (_RED_FILES, _BLACK_FILES) if self.flipped else (_BLACK_FILES, _RED_FILES)
        pieces = {
            _piece_image(pc): [ch, "red" if pc.isupper() else "black"]
            for pc, ch in {**_RED_CHARS, **_BLACK_CHARS}.items()
        }
        try:
            self.images.load({"cw": cell[0], "ch": cell[1], "px": _PX, "py": _PY, "mx": _MX, "my": _MY,
                              "top": top, "bottom": bottom, "pieces": pieces})
        except (OSError, RuntimeError) as exc:
            self.images, self.msg = None, f"图形渲染失败，改用字符棋盘：{exc}"

    def _handle(self, key: int) -> None:
        confirm_new, self.confirm_new = self.confirm_new, False
        if key == curses.KEY_RESIZE:
            # 尺寸变化后 curses 会整屏清掉重画，图片随之丢失；字号变化还会改变像素尺寸，故先刷新再重传
            self.scr.refresh()
            self._load_images()
        elif key == curses.KEY_MOUSE:
            try:
                _, x, y, _, bstate = curses.getmouse()
            except curses.error:
                return
            if bstate & (curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED):
                square = from_screen(y - self.oy, x - self.ox, self.flipped)
                if square is not None:
                    self._click(square)
        elif key == ord("u"):
            self.selected = None
            try:
                undo_turn(self.game, self.side)
                self._save()
                self.msg = "已悔棋"
            except ValueError as exc:
                self.msg = str(exc)
        elif key == ord("n"):
            if confirm_new:
                self.game = Game(name=self.game.name)
                self.selected = None
                self._save()
                self.msg = "已开新局"
            else:
                self.confirm_new = True
                self.msg = "再按 n 确认开新局"

    def _click(self, square: int) -> None:
        if self.game.result is not None:
            return
        pos = self.game.position
        pc = pos.board[square]
        if pc != "." and pc.isupper() == (self.side == RED):
            self.selected = None if square == self.selected else square
        elif self.selected is not None and (self.selected, square) in pos.legal_moves():
            notation = self.game.move(to_notation(pos, (self.selected, square)))
            self.selected = None
            self._save()
            self.msg = f"你走：{notation}"
        else:
            self.selected = None

    def _ai_move(self) -> None:
        from xiangqi.search import search

        self._draw(thinking=True)
        if self.engine:
            move = self.engine.best_move(self.game, self.time_limit)
        else:
            move = search(self.game.position, time_limit=self.time_limit, history=self.game.seen_positions).move
        notation = self.game.move(to_notation(self.game.position, move))
        self._save()
        self.msg = f"AI 走：{notation}"
        curses.flushinp()

    def _save(self) -> None:
        self.game.save(self.path)

    def _color(self, fg: int, bg: int) -> int:
        if (fg, bg) not in self.pairs:
            n = len(self.pairs) + 4  # 1-3 已被固定颜色占用
            curses.init_pair(n, fg, bg)
            self.pairs[(fg, bg)] = curses.color_pair(n)
        return self.pairs[(fg, bg)]

    def _put(self, y: int, x: int, text: str, attr: int = 0) -> None:
        try:
            self.scr.addstr(y + self.oy, x + self.ox, text, attr)
        except curses.error:
            pass  # 终端太小时越界写入会抛错，截断即可

    def _state(self, square: int, targets: set[int], last_squares: set[int]) -> str:
        if square == self.selected:
            return "selected"
        if square in targets:
            return "target"
        if square in last_squares:
            return "last"
        return "normal"

    def _draw(self, thinking: bool = False) -> None:
        scr = self.scr
        scr.erase()
        lines, cols = scr.getmaxyx()
        self.oy = max(0, (lines - _MIN_LINES) // 2)
        # 优先让棋盘本身水平居中；右侧放不下面板时，退而让棋盘+面板整体居中
        self.ox = (cols - _ART_COLS) // 2 - _ART_LEFT
        if self.ox + _PANEL + _PANEL_W > cols:
            self.ox = max(0, (cols - _PANEL - _PANEL_W) // 2)
        if lines < _MIN_LINES or cols < _MIN_COLS:
            self.oy = self.ox = 0
            self._put(0, 0, f"终端太小，请放大到至少 {_MIN_LINES} 行 × {_MIN_COLS} 列（q 退出）")
            scr.refresh()
            if self.images:
                self.images.show([])
            return
        pos = self.game.position
        last = self.game.moves[-1] if self.game.moves else None
        last_squares = {last["from"], last["to"]} if last else set()
        targets = {to for frm, to in pos.legal_moves() if frm == self.selected}

        if self.images:
            # 棋盘区内没有文字，图片直接叠在文字层之上（z>0）
            placements = [("board", _ART_TOP + self.oy, _ART_LEFT + self.ox, _ART_COLS, _ART_ROWS, 0, 1)]
            # 棋子图以交叉点中心 (y+0.5, x+1) 为中心、占 _PX×_PY 格；_PY 为偶数时上沿落在半行，用像素偏移补齐
            top = 0.5 - _PY / 2
            row_off, y_px = math.floor(top), round((top - math.floor(top)) * self.cell[1])
            for square, pc in enumerate(pos.board):
                y, x = to_screen(square, self.flipped)
                at = (y + row_off + self.oy, x + 1 - _PX // 2 + self.ox, _PX, _PY, y_px)
                if pc != ".":
                    placements.append((f"{_piece_image(pc)}-{self._state(square, targets, last_squares)}", *at, 3))
                elif square in targets:
                    placements.append(("dot", *at, 2))
                elif square in last_squares:
                    placements.append(("from", *at, 2))
            self._draw_panel(thinking)
            scr.refresh()
            self.images.show(placements)
            return

        self._draw_text_board(pos, targets, last_squares)
        self._draw_panel(thinking)
        scr.refresh()

    def _draw_text_board(self, pos: Position, targets: set[int], last_squares: set[int]) -> None:
        top_files, bottom_files = (_RED_FILES, _BLACK_FILES) if self.flipped else (_BLACK_FILES, _RED_FILES)
        for dc in range(9):
            c = 8 - dc if self.flipped else dc
            self._put(_TOP - 2, _LEFT + _PX * dc, top_files[c])
            self._put(_TOP + _PY * 9 + 2, _LEFT + _PX * dc, bottom_files[c])

        for dr in range(9):
            y0 = _TOP + _PY * dr
            for i in range(1, _PY):
                for dc in range(9):
                    if dr != 4 or dc in (0, 8):
                        self._put(y0 + i, _LEFT + _PX * dc, "│")
            if dr == 4:
                self._put(y0 + _PY // 2, _LEFT + _PX * 2 - 3, "楚    河", curses.A_BOLD)
                self._put(y0 + _PY // 2, _LEFT + _PX * 6 - 3, "汉    界", curses.A_BOLD)
            elif dr in (0, 1, 7, 8):  # 九宫斜线：按 i/_PY 插值，左右以棋子中心（x+1）镜像对称
                x3, x4 = _LEFT + _PX * 3, _LEFT + _PX * 4
                for i in range(1, _PY):
                    dx = _PX * i // _PY
                    if dr in (0, 7):
                        self._put(y0 + i, x3 + dx, "╲")
                        self._put(y0 + i, x4 + _PX + 1 - dx, "╱")
                    else:
                        self._put(y0 + i, x4 + 1 - dx, "╱")
                        self._put(y0 + i, x4 + dx, "╲")

        for square, pc in enumerate(pos.board):
            y, x = to_screen(square, self.flipped)
            r, c = (y - _TOP) // _PY, (x - _LEFT) // _PX
            if c < 8:
                self._put(y, x + 2, "─" * (_PX - 2))
            if pc == ".":
                if square in targets:
                    self._put(y, x, "ｏ", curses.color_pair(2) | curses.A_BOLD)
                else:
                    attr = curses.color_pair(3) | curses.A_BOLD if square in last_squares else 0
                    self._put(y, x, _cross(r, c) + ("─" if c < 8 else ""), attr)
                continue
            red = pc.isupper()
            disc = self.disc[self._state(square, targets, last_squares)]
            attr = self._color(self.ink[RED if red else BLACK], disc) | curses.A_BOLD
            self._put(y, x, (_RED_CHARS if red else _BLACK_CHARS)[pc], attr)

    def _draw_panel(self, thinking: bool) -> None:
        game, x = self.game, _PANEL
        side_text = "红" if self.side == RED else "黑"
        self._put(_TOP - 2, x, f"棋局 {game.name} · 你执{side_text} · {self.engine.name if self.engine else '内置 AI'} {self.time_limit:g}s", curses.A_BOLD)
        result = game.result
        if result:
            winner, reason = result
            status, attr = f"棋局结束：{_RESULT_TEXT[winner]}（{_REASON_TEXT[reason]}）", curses.color_pair(3) | curses.A_BOLD
        elif thinking:
            status, attr = "AI 思考中…", curses.color_pair(3)
        else:
            status = "轮到你" + ("（被将军！）" if game.position.in_check() else "")
            attr = curses.color_pair(1) | curses.A_BOLD if game.position.in_check() else curses.A_BOLD
        self._put(_TOP, x, status, attr)
        self._put(_TOP + 1, x, self.msg)

        notations = [m["notation"] for m in game.moves]
        rounds = [
            f"{i // 2 + 1:>3}. " + "  ".join(notations[i : i + 2]) for i in range(0, len(notations), 2)
        ]
        for i, line in enumerate(rounds[-(_PY * 9 - 2):]):
            self._put(_TOP + 3 + i, x, line)

        self._put(_TOP + _PY * 9 + 2, x, "点选棋子→点落点   u 悔棋  n 新局  q 退出", curses.A_DIM)


def play(path: Path, name: str, side: str, time_limit: float, graphics: bool = True, engine: Engine | None = None) -> None:
    """进入全屏对弈；存档存在则续棋，否则新开一局。graphics=False 强制字符棋盘；engine 为 None 时用内置搜索。"""
    game = Game.load(path) if path.exists() else Game(name=name)
    if not path.exists():
        game.save(path)
    locale.setlocale(locale.LC_ALL, "")
    curses.wrapper(_App(game, path, side, time_limit, graphics and kitty.supported(), engine).run)
