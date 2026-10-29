// 用 macOS 自带的 JXA（osascript -l JavaScript）画棋盘与圆形棋子 PNG，供 xq play 的 Kitty 图形模式使用。
// 棋盘透明、线条与棋子半透明，让终端自己的背景透出来。
// 参数为一个 JSON：{cw, ch, px, py, mx, my, out, top, bottom, pieces: {name: [字, "red"|"black"]}}
// px/py 为交叉点列距/行距（字符格），mx/my 为棋盘图从最外侧交叉点向外留出的列数/行数
ObjC.import('AppKit');

const INK = { red: '#B58C8E', black: '#B8BCC4' };
const RING = { normal: null, last: '#CDB48A', selected: '#88AFCF', target: '#9DB88A' };
const LINE = '#FFFFFF';
const DISC = '#16161C';

function rgb(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return $.NSColor.colorWithSRGBRedGreenBlueAlpha(((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255, a === undefined ? 1 : a);
}

function font(size) {
  for (const name of ['STKaitiSC-Bold', 'STKaiti', 'STSongti-SC-Black', 'STSongti-SC-Bold', 'PingFangSC-Semibold']) {
    const f = $.NSFont.fontWithNameSize(name, size);
    if (!f.isNil()) return f;
  }
  return $.NSFont.boldSystemFontOfSize(size);
}

// Cocoa 原点在左下角；以下绘图函数都接收左上角原点的坐标，内部用 H - y 翻转
function render(w, h, path, draw) {
  const rep = $.NSBitmapImageRep.alloc.initWithBitmapDataPlanesPixelsWidePixelsHighBitsPerSampleSamplesPerPixelHasAlphaIsPlanarColorSpaceNameBytesPerRowBitsPerPixel(
    null, w, h, 8, 4, true, false, $.NSDeviceRGBColorSpace, 0, 0);
  $.NSGraphicsContext.saveGraphicsState;
  $.NSGraphicsContext.setCurrentContext($.NSGraphicsContext.graphicsContextWithBitmapImageRep(rep));
  draw(h);
  $.NSGraphicsContext.restoreGraphicsState;
  rep.representationUsingTypeProperties($.NSBitmapImageFileTypePNG, $({})).writeToFileAtomically(path, true);
}

function text(s, cx, cy, size, color, h, alpha) {
  const str = $.NSString.alloc.initWithUTF8String(s);
  // 数组须显式 $() 包成 NSArray，否则 ObjC 对象会被桥接成字典；键用 NSFontAttributeName 等常量的字符串值
  const attrs = $.NSDictionary.dictionaryWithObjectsForKeys($([font(size), rgb(color, alpha)]), $(['NSFont', 'NSColor']));
  const sz = str.sizeWithAttributes(attrs);
  str.drawAtPointWithAttributes($.NSMakePoint(cx - sz.width / 2, h - cy - sz.height / 2), attrs);
}

function oval(cx, cy, r, h) {
  return $.NSBezierPath.bezierPathWithOvalInRect($.NSMakeRect(cx - r, h - cy - r, 2 * r, 2 * r));
}

function polyline(points, width, h) {
  const p = $.NSBezierPath.bezierPath;
  points.forEach(([x, y], i) => {
    if (i) p.lineToPoint($.NSMakePoint(x, h - y));
    else p.moveToPoint($.NSMakePoint(x, h - y));
  });
  p.setLineWidth(width);
  p.setLineCapStyle($.NSLineCapStyleSquare);
  p.stroke;
}

function board(cfg, path) {
  const { cw, ch, px, py, mx, my } = cfg;
  const W = (px * 8 + 2 * mx) * cw, H = (py * 9 + 2 * my) * ch;
  const X = (c) => (mx + px * c) * cw, Y = (r) => (my + py * r) * ch;
  const pitch = Math.min(px * cw, py * ch);
  const lw = Math.max(1, Math.round(ch / 14));
  render(W, H, path, (h) => {
    rgb(LINE, 0.18).setStroke;
    for (let r = 0; r < 10; r++) polyline([[X(0), Y(r)], [X(8), Y(r)]], lw, h);
    for (let c = 0; c < 9; c++) {
      if (c === 0 || c === 8) polyline([[X(c), Y(0)], [X(c), Y(9)]], lw, h);
      else {
        polyline([[X(c), Y(0)], [X(c), Y(4)]], lw, h);
        polyline([[X(c), Y(5)], [X(c), Y(9)]], lw, h);
      }
    }
    for (const r of [0, 7]) {
      polyline([[X(3), Y(r)], [X(5), Y(r + 2)]], lw, h);
      polyline([[X(5), Y(r)], [X(3), Y(r + 2)]], lw, h);
    }
    // 炮位、兵位的角标
    const g = pitch * 0.07, L = pitch * 0.16;
    const marks = [[2, 1], [2, 7], [7, 1], [7, 7]];
    for (const r of [3, 6]) for (const c of [0, 2, 4, 6, 8]) marks.push([r, c]);
    for (const [r, c] of marks) {
      for (const sx of [-1, 1]) {
        if ((c === 0 && sx < 0) || (c === 8 && sx > 0)) continue;
        for (const sy of [-1, 1]) {
          const x = X(c) + sx * g, y = Y(r) + sy * g;
          polyline([[x, y + sy * L], [x, y], [x + sx * L, y]], lw, h);
        }
      }
    }
    const off = pitch * 0.62;
    rgb(LINE, 0.24).setStroke;
    polyline([[X(0) - off, Y(0) - off], [X(8) + off, Y(0) - off], [X(8) + off, Y(9) + off],
      [X(0) - off, Y(9) + off], [X(0) - off, Y(0) - off]], lw * 2.5, h);
    const riverY = (Y(4) + Y(5)) / 2;
    text('楚  河', X(2), riverY, pitch * 0.5, LINE, h, 0.28);
    text('漢  界', X(6), riverY, pitch * 0.5, LINE, h, 0.28);
    [...cfg.top].forEach((s, c) => text(s, X(c), (Y(0) - off) / 2, ch * 0.8, LINE, h, 0.32));
    [...cfg.bottom].forEach((s, c) => text(s, X(c), (Y(9) + off + H) / 2, ch * 0.8, LINE, h, 0.32));
  });
}

function piece(w, h, glyph, ink, ring, path) {
  render(w, h, path, (H) => {
    const d = Math.min(w, h) * 0.84, cx = w / 2, cy = h / 2;
    rgb(DISC, 0.65).setFill;
    oval(cx, cy, d / 2, H).fill;
    // 外圈平时用棋子本色淡描边，选中/可吃/上一步时换成对应状态色并加粗
    const edge = oval(cx, cy, d / 2 - d * 0.03, H);
    edge.setLineWidth(Math.max(1, d * (ring ? 0.06 : 0.03)));
    rgb(ring || ink, ring ? 0.75 : 0.35).setStroke;
    edge.stroke;
    const inner = oval(cx, cy, d / 2 - d * 0.12, H);
    inner.setLineWidth(Math.max(1, d * 0.02));
    rgb(ink, 0.2).setStroke;
    inner.stroke;
    text(glyph, cx, cy, d * 0.52, ink, H, 0.85);
  });
}

function marker(w, h, kind, path) {
  render(w, h, path, (H) => {
    const d = Math.min(w, h) * 0.84;
    if (kind === 'dot') {
      rgb(RING.target, 0.55).setFill;
      oval(w / 2, h / 2, d * 0.13, H).fill;
    } else {
      const p = oval(w / 2, h / 2, d * 0.2, H);
      p.setLineWidth(Math.max(1, d * 0.05));
      rgb(RING.last, 0.55).setStroke;
      p.stroke;
    }
  });
}

function run(argv) {
  const cfg = JSON.parse(argv[0]);
  const w = cfg.px * cfg.cw, h = cfg.py * cfg.ch;
  board(cfg, `${cfg.out}/board.png`);
  for (const [name, [glyph, side]] of Object.entries(cfg.pieces)) {
    for (const state of Object.keys(RING)) piece(w, h, glyph, INK[side], RING[state], `${cfg.out}/${name}-${state}.png`);
  }
  marker(w, h, 'dot', `${cfg.out}/dot.png`);
  marker(w, h, 'from', `${cfg.out}/from.png`);
}
