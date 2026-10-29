"""Kitty 图形协议：把 board_art.js 画的棋盘/棋子 PNG 贴到终端指定的字符格区域。"""
from __future__ import annotations

import base64
import fcntl
import json
import os
import struct
import subprocess
import sys
import tempfile
import termios
from pathlib import Path

_SCRIPT = Path(__file__).with_name("board_art.js")


def supported() -> bool:
    """macOS 上的 Ghostty / kitty / WezTerm，且不在 tmux 里（tmux 不透传图形协议）。"""
    env = os.environ
    return (
        sys.platform == "darwin"
        and "TMUX" not in env
        and (env.get("TERM_PROGRAM") in ("ghostty", "WezTerm") or env.get("TERM") in ("xterm-ghostty", "xterm-kitty"))
    )


def cell_size() -> tuple[int, int] | None:
    """终端单个字符格的像素宽高；终端不报告像素尺寸时返回 None。"""
    rows, cols, xpix, ypix = struct.unpack("HHHH", fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, b"\0" * 8))
    if not (rows and cols and xpix and ypix):
        return None
    return xpix // cols, ypix // rows


def _apc(keys: str, payload: bytes = b"") -> bytes:
    return b"\x1b_G" + keys.encode() + (b";" + payload if payload else b"") + b"\x1b\\"


class Images:
    """一组已传给终端的图片（按名字索引），每帧整体重新摆放。"""

    def __init__(self) -> None:
        self.ids: dict[str, int] = {}

    def load(self, cfg: dict) -> None:
        """按 cfg 渲染全部 PNG 并传给终端；渲染失败抛 RuntimeError。"""
        with tempfile.TemporaryDirectory() as out:
            proc = subprocess.run(
                ["osascript", "-l", "JavaScript", str(_SCRIPT), json.dumps({**cfg, "out": out}, ensure_ascii=False)],
                capture_output=True, text=True,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip())
            data = bytearray(_apc("a=d,d=A,q=2"))
            self.ids = {}
            for i, png in enumerate(sorted(Path(out).glob("*.png")), start=1):
                self.ids[png.stem] = i
                b64 = base64.standard_b64encode(png.read_bytes())
                chunks = [b64[j : j + 4096] for j in range(0, len(b64), 4096)]
                for k, chunk in enumerate(chunks):
                    more = int(k < len(chunks) - 1)
                    keys = f"a=t,f=100,i={i},q=2,m={more}" if k == 0 else f"m={more}"
                    data += _apc(keys, chunk)
        _write(bytes(data))

    def show(self, placements: list[tuple[str, int, int, int, int, int, int]]) -> None:
        """清掉上一帧，按 (图名, 行, 列, 占列数, 占行数, 起始格内纵向像素偏移, z) 重新摆放；z 大的盖在上面。"""
        data = bytearray(_apc("a=d,d=a,q=2"))
        for name, row, col, cols, rows, y_px, z in placements:
            # 存/恢复光标，避免打乱 curses 记录的光标位置
            data += f"\x1b7\x1b[{row + 1};{col + 1}H".encode()
            data += _apc(f"a=p,i={self.ids[name]},c={cols},r={rows},Y={y_px},z={z},C=1,q=2") + b"\x1b8"
        _write(bytes(data))

    def clear(self) -> None:
        _write(_apc("a=d,d=A,q=2"))


def _write(data: bytes) -> None:
    fd = sys.stdout.fileno()
    while data:
        data = data[os.write(fd, data):]
