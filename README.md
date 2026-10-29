# xiangqi-kit

A Xiangqi (Chinese chess) engine with a Claude Code skill and a zero-dependency web board. Full rule validation, Chinese notation, and a built-in AI opponent.

中国象棋工具集：一套规则逻辑，三个交付物——Python 引擎、Claude Code skill（CLI）、单文件 Web 版。完整合法走法校验（蹩马腿、塞象眼、将帅照面、过河兵等）、中文记谱法双向转换、alpha-beta AI。

## 为什么

LLM 纯靠文字记棋盘，走到二三十步就会记错子的位置、走出不合法的棋。解决办法是让模型调用真正的引擎：棋局状态存文件，每步走法由代码校验。这个仓库就是那个引擎，加上让它在 Claude Code 和浏览器里用起来的胶水层。

## CLI（`xq`）

零第三方依赖，系统 python3（3.9+）即可运行：

```sh
./skill/xq new                # 开新棋局
./skill/xq move 炮二平五       # 按中文记谱走子（红汉字、黑阿拉伯：马8进7）
./skill/xq ai --time 2        # 让 AI 走一步（默认限时 2 秒）
./skill/xq show               # 显示棋盘
./skill/xq legal              # 列出所有合法着法
./skill/xq undo               # 悔棋
./skill/xq history            # 棋谱
./skill/xq fen                # 当前局面 FEN
./skill/xq play               # 全屏棋盘：鼠标点选走子，AI 自动应手（--side black 执黑，--time 调 AI 限时）
                              # macOS 上的 Ghostty/kitty/WezTerm 用图片画棋盘与圆形棋子（Kitty 图形协议），其余终端或 --text 用字符画
./skill/xq engine install      # 下载 Pikafish 引擎到 ~/.xiangqi/engines/；装了以后 ai/play 自动用它（--engine builtin 换回内置）
```

棋局存在 `~/.xiangqi/games/<name>.json`（`-n <名字>` 管理多盘棋，`XIANGQI_HOME` 可改存档目录），跨会话自动续棋。非法走法会报错并返回非零退出码。

记谱要点：路数从各自右手数起；车炮兵帅进退记步数，马象士记到达路数；同线双子用前/后（前车进三），三兵同线用前/中/后。解析对繁体、异体字（仕/士、相/象、兵/卒）和红方用阿拉伯数字都宽容。

## Claude Code Skill

```sh
skill/install.sh              # 安装到 ~/.claude/skills/xiangqi（含 vendored 引擎，自包含）
```

安装后对 Claude 说"陪我下盘象棋"即可。SKILL.md 强制要求 Claude 通过 CLI 操作棋局、以引擎输出为准，杜绝凭记忆走棋。

## Web 版

打开 `web/index.html` 就能玩——单文件、零依赖、无构建、可离线。

通过 HTTP 访问（如 GitHub Pages，推送 `web/` 后由 `.github/workflows/pages.yml` 自动部署）时，AI 会换成 `web/engine/` 里的 Fairy-Stockfish（WASM + Pikafish 团队训练的象棋 NNUE，GPL-3.0），难度可选到"大师"。多线程 WASM 需要跨源隔离，静态托管设不了响应头，由 `coi-serviceworker.js` 补上；浏览器不支持或直接打开本地文件时自动用内置 JS 引擎。

- 点击选子、高亮合法落点，走子动画，将军提示
- AI 在 Web Worker 里搜索不卡 UI，难度三档（入门/普通/较强）
- 右侧中文棋谱，点击任意一手回退复盘，从历史续走自动分支
- 执黑时棋盘自动翻转；三次重复局面判和

## Python API

```python
from xiangqi import Position, START_FEN, parse_notation, to_notation, render
from xiangqi.game import Game
from xiangqi.search import search

game = Game()
game.move("炮二平五")
result = search(game.position, time_limit=2.0)
print(to_notation(game.position, result.move))
print(render(game.position))
```

## 开发与测试

引擎正确性靠 perft（走法数统计）证明，Python 与 JS 两份实现跑同一份 `tests/data/perft.json`：

| depth | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| startpos 节点数 | 44 | 1,920 | 79,666 | 3,290,240 | 133,312,995 |

```sh
uv run pytest                          # 全部测试（需要 Python 3.10+）
uv run pytest -m slow                  # startpos depth 4
node scripts/perft_js.mjs              # JS 引擎跨实现校验（从 index.html 提取引擎块）
```

规则说明：长将/长捉按简化规则处理——同一局面第三次出现判和，与正式规则（长打一方判负）不同。

## License

MIT
