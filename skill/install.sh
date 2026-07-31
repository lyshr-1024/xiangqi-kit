#!/bin/sh
# 把 skill（含 vendored 引擎）安装到 Claude Code skills 目录
set -e
dest="${1:-$HOME/.claude/skills/xiangqi}"
src="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$dest"
cp "$src/SKILL.md" "$src/xq" "$dest/"
rm -rf "$dest/xiangqi"
cp -R "$src/../xiangqi" "$dest/xiangqi"
find "$dest/xiangqi" -name __pycache__ -type d -prune -exec rm -rf {} +
chmod +x "$dest/xq"
echo "已安装到 $dest"
