"""外部 UCI 象棋引擎（Pikafish）：查找、安装、对弈。找不到时调用方退回内置搜索。"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from xiangqi.board import Move
from xiangqi.game import Game

_RELEASES = "https://api.github.com/repos/official-pikafish/Pikafish/releases/latest"
_BINARIES = {"darwin": "Pikafish-MacOS-universal", "linux": "Pikafish-Linux-x86-64-universal"}


def to_uci(move: Move) -> str:
    """格子编号走法转 UCI 坐标：列 a-i 自红方左起，行 0-9 自红方底线起（如炮二平五 = h2e2）。"""
    return "".join(f"{'abcdefghi'[s % 9]}{9 - s // 9}" for s in move)


def from_uci(text: str) -> Move:
    frm, to = ((9 - int(text[i + 1])) * 9 + "abcdefghi".index(text[i]) for i in (0, 2))
    return frm, to


def find_engine(home: Path) -> Path | None:
    """依次找 $XIANGQI_ENGINE、$XIANGQI_HOME/engines/pikafish/pikafish、PATH 里的 pikafish。"""
    for candidate in (os.environ.get("XIANGQI_ENGINE"), home / "engines" / "pikafish" / "pikafish", shutil.which("pikafish")):
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def install(home: Path) -> Path:
    """下载 Pikafish 最新发布包，把本平台程序与 NNUE 权重解到 $XIANGQI_HOME/engines/pikafish/。"""
    binary = _BINARIES.get(sys.platform)
    if binary is None:
        raise ValueError(f"暂不支持在 {sys.platform} 上自动安装 Pikafish")
    release = json.loads(subprocess.run(["curl", "-fsSL", _RELEASES], capture_output=True, text=True, check=True).stdout)
    asset = next(a for a in release["assets"] if a["name"].endswith(".7z"))
    dest = home / "engines" / "pikafish"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / asset["name"]
        print(f"下载 {release['tag_name']}（{asset['size'] // 2**20} MB）…", flush=True)
        subprocess.run(["curl", "-fL#", "-o", str(archive), asset["browser_download_url"]], check=True)
        # bsdtar（libarchive）能直接解 7z，macOS 自带
        subprocess.run(["bsdtar", "-xf", str(archive), "-C", tmp, binary, "pikafish.nnue"], check=True)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.move(str(Path(tmp) / binary), dest / "pikafish")
        shutil.move(str(Path(tmp) / "pikafish.nnue"), dest / "pikafish.nnue")
    (dest / "pikafish").chmod(0o755)
    return dest / "pikafish"


class Engine:
    """一个常驻的 UCI 引擎进程；工作目录设为程序所在目录，好让它找到同目录的 pikafish.nnue。"""

    def __init__(self, path: Path, threads: int = max(1, (os.cpu_count() or 2) // 2)) -> None:
        self.name = path.stem.capitalize()
        self.proc = subprocess.Popen(
            [str(path)], cwd=path.parent, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
        self._send("uci")
        self._wait("uciok")
        self._send(f"setoption name Threads value {threads}")
        self._send("setoption name Hash value 128")
        self._send("isready")
        self._wait("readyok")

    def best_move(self, game: Game, time_limit: float) -> Move:
        """按整盘棋谱（引擎据此判断重复局面）思考 time_limit 秒，返回最佳走法。"""
        moves = " ".join(to_uci((m["from"], m["to"])) for m in game.moves)
        self._send(f"position fen {game.start_fen}" + (f" moves {moves}" if moves else ""))
        self._send(f"go movetime {int(time_limit * 1000)}")
        return from_uci(self._wait("bestmove").split()[1])

    def close(self) -> None:
        self._send("quit")
        self.proc.wait(timeout=5)

    def _send(self, line: str) -> None:
        self.proc.stdin.write(line + "\n")

    def _wait(self, prefix: str) -> str:
        for line in self.proc.stdout:
            if line.startswith(prefix):
                return line
        raise RuntimeError(f"引擎意外退出（等待 {prefix} 时）")
