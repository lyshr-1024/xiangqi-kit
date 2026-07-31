// 从 web/index.html 提取引擎脚本块，对共享 perft 数据做一致性校验。
// 用法: node scripts/perft_js.mjs [--max-depth N]
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const maxDepth = (() => {
  const i = process.argv.indexOf("--max-depth");
  return i === -1 ? 4 : Number(process.argv[i + 1]);
})();

const html = readFileSync(join(root, "web", "index.html"), "utf8");
const match = html.match(/<script id="engine">([\s\S]*?)<\/script>/);
if (!match) {
  console.error("web/index.html 中找不到 <script id=\"engine\"> 块");
  process.exit(1);
}
const XQ = new Function(`${match[1]}; return XQ;`)();

const data = JSON.parse(
  readFileSync(join(root, "tests", "data", "perft.json"), "utf8"),
);

let failed = 0;
for (const { name, fen, depths } of data.positions) {
  for (const [depth, expected] of Object.entries(depths)) {
    if (Number(depth) > maxDepth) continue;
    const start = Date.now();
    const actual = XQ.perft(XQ.Position.fromFen(fen), Number(depth));
    const ms = Date.now() - start;
    const ok = actual === expected;
    if (!ok) failed += 1;
    console.log(
      `${ok ? "✓" : "✗"} ${name} depth ${depth}: ${actual}` +
        (ok ? "" : ` (期望 ${expected})`) +
        ` [${ms}ms]`,
    );
  }
}
if (failed) {
  console.log(`${failed} 项不一致`);
  process.exit(1);
}
console.log("全部通过");
