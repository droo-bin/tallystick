/* Minimal QR code encoder: alphanumeric or byte mode, error correction level M, versions 1-6.
   Enough for Tallystick card codes (126 alphanumeric characters fit version 6-M). No dependencies. */
var TallyQR = (function () {
  'use strict';
  // [total codewords, ec codewords per block, number of blocks] for level M, versions 1..6 (all blocks equal size)
  var TABLE = [null, [26, 10, 1], [44, 16, 1], [70, 26, 1], [100, 18, 2], [134, 24, 2], [172, 16, 4]];
  var ALNUM = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:';

  function rsMul(x, y) { var z = 0; for (var i = 7; i >= 0; i--) { z = (z << 1) ^ ((z >>> 7) * 0x11D); z ^= ((y >>> i) & 1) * x; } return z & 0xFF; }
  function rsDivisor(deg) {
    var r = []; for (var i = 0; i < deg - 1; i++) r.push(0); r.push(1);
    var root = 1;
    for (var i2 = 0; i2 < deg; i2++) {
      for (var j = 0; j < r.length; j++) { r[j] = rsMul(r[j], root); if (j + 1 < r.length) r[j] ^= r[j + 1]; }
      root = rsMul(root, 2);
    }
    return r;
  }
  function rsRemainder(data, div) {
    var r = div.map(function () { return 0; });
    data.forEach(function (b) {
      var f = b ^ r.shift(); r.push(0);
      div.forEach(function (c, i) { r[i] ^= rsMul(c, f); });
    });
    return r;
  }

  function encodeBits(text) {
    var alnum = /^[0-9A-Z $%*+\-./:]*$/.test(text), bits = [];
    function put(v, n) { for (var i = n - 1; i >= 0; i--) bits.push((v >>> i) & 1); }
    var bytes = alnum ? null : Array.from(new TextEncoder().encode(text));
    for (var ver = 1; ver <= 6; ver++) {
      bits = [];
      var t = TABLE[ver], dataCw = t[0] - t[1] * t[2], cap = dataCw * 8;
      if (alnum) {
        put(2, 4); put(text.length, 9);
        for (var i = 0; i + 1 < text.length; i += 2) put(ALNUM.indexOf(text[i]) * 45 + ALNUM.indexOf(text[i + 1]), 11);
        if (text.length % 2) put(ALNUM.indexOf(text[text.length - 1]), 6);
      } else {
        put(4, 4); put(bytes.length, 8); bytes.forEach(function (b) { put(b, 8); });
      }
      if (bits.length <= cap) {
        put(0, Math.min(4, cap - bits.length));
        put(0, (8 - bits.length % 8) % 8);
        for (var pad = 0xEC; bits.length < cap; pad ^= 0xEC ^ 0x11) put(pad, 8);
        var cw = []; for (var k = 0; k < bits.length; k += 8) { var v = 0; for (var m = 0; m < 8; m++) v = (v << 1) | bits[k + m]; cw.push(v); }
        return { version: ver, data: cw };
      }
    }
    throw new Error('Text too long for this QR encoder');
  }

  function interleave(ver, data) {
    var t = TABLE[ver], nb = t[2], ecLen = t[1], per = data.length / nb, div = rsDivisor(ecLen), blocks = [], ecs = [], out = [];
    for (var b = 0; b < nb; b++) { var blk = data.slice(b * per, (b + 1) * per); blocks.push(blk); ecs.push(rsRemainder(blk, div)); }
    for (var i = 0; i < per; i++) for (var b2 = 0; b2 < nb; b2++) out.push(blocks[b2][i]);
    for (var j = 0; j < ecLen; j++) for (var b3 = 0; b3 < nb; b3++) out.push(ecs[b3][j]);
    return out;
  }

  function build(ver, cw, mask) {
    var size = ver * 4 + 17, mod = [], fn = [];
    for (var y = 0; y < size; y++) { mod.push(new Array(size).fill(false)); fn.push(new Array(size).fill(false)); }
    function set(x, y, d) { mod[y][x] = d; fn[y][x] = true; }
    for (var i = 0; i < size; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); }
    [[3, 3], [size - 4, 3], [3, size - 4]].forEach(function (c) {
      for (var dy = -4; dy <= 4; dy++) for (var dx = -4; dx <= 4; dx++) {
        var d = Math.max(Math.abs(dx), Math.abs(dy)), xx = c[0] + dx, yy = c[1] + dy;
        if (xx >= 0 && xx < size && yy >= 0 && yy < size) set(xx, yy, d !== 2 && d !== 4);
      }
    });
    if (ver >= 2) {
      var a = size - 7;
      for (var dy2 = -2; dy2 <= 2; dy2++) for (var dx2 = -2; dx2 <= 2; dx2++) set(a + dx2, a + dy2, Math.max(Math.abs(dx2), Math.abs(dy2)) !== 1);
    }
    function format(m) {
      var data = (0 << 3) | m, rem = data; // level M = 0b00
      for (var k = 0; k < 10; k++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
      var bits = ((data << 10) | rem) ^ 0x5412, bit = function (n) { return ((bits >>> n) & 1) !== 0; };
      for (var q = 0; q <= 5; q++) set(8, q, bit(q));
      set(8, 7, bit(6)); set(8, 8, bit(7)); set(7, 8, bit(8));
      for (var r = 9; r < 15; r++) set(14 - r, 8, bit(r));
      for (var s = 0; s < 8; s++) set(size - 1 - s, 8, bit(s));
      for (var u = 8; u < 15; u++) set(8, size - 15 + u, bit(u));
      set(8, size - 8, true);
    }
    format(mask);
    var idx = 0, total = cw.length * 8;
    for (var right = size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (var vert = 0; vert < size; vert++) for (var j = 0; j < 2; j++) {
        var x = right - j, up = ((right + 1) & 2) === 0, yy2 = up ? size - 1 - vert : vert;
        if (!fn[yy2][x] && idx < total) { mod[yy2][x] = ((cw[idx >>> 3] >>> (7 - (idx & 7))) & 1) !== 0; idx++; }
      }
    }
    for (var y3 = 0; y3 < size; y3++) for (var x3 = 0; x3 < size; x3++) {
      if (fn[y3][x3]) continue;
      var inv;
      switch (mask) {
        case 0: inv = (x3 + y3) % 2 === 0; break;
        case 1: inv = y3 % 2 === 0; break;
        case 2: inv = x3 % 3 === 0; break;
        case 3: inv = (x3 + y3) % 3 === 0; break;
        case 4: inv = (Math.floor(x3 / 3) + Math.floor(y3 / 2)) % 2 === 0; break;
        case 5: inv = (x3 * y3) % 2 + (x3 * y3) % 3 === 0; break;
        case 6: inv = ((x3 * y3) % 2 + (x3 * y3) % 3) % 2 === 0; break;
        default: inv = ((x3 + y3) % 2 + (x3 * y3) % 3) % 2 === 0;
      }
      if (inv) mod[y3][x3] = !mod[y3][x3];
    }
    return mod;
  }

  function penalty(m) {
    var n = m.length, p = 0, dark = 0;
    function lines(get) {
      for (var a = 0; a < n; a++) {
        var run = 1, line = [];
        for (var b = 0; b < n; b++) line.push(get(a, b));
        for (var c = 1; c < n; c++) {
          if (line[c] === line[c - 1]) { run++; if (run === 5) p += 3; else if (run > 5) p++; } else run = 1;
        }
        for (var d = 0; d + 7 <= n; d++) {
          var pat = line[d] && !line[d + 1] && line[d + 2] && line[d + 3] && line[d + 4] && !line[d + 5] && line[d + 6];
          if (!pat) continue;
          var before = true, after = true;
          for (var e = 1; e <= 4; e++) { if (d - e >= 0 && line[d - e]) before = false; if (d + 6 + e < n && line[d + 6 + e]) after = false; }
          if (before || after) p += 40;
        }
      }
    }
    lines(function (y, x) { return m[y][x]; });
    lines(function (x, y) { return m[y][x]; });
    for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) {
      if (m[y][x]) dark++;
      if (x + 1 < n && y + 1 < n && m[y][x] === m[y][x + 1] && m[y][x] === m[y + 1][x] && m[y][x] === m[y + 1][x + 1]) p += 3;
    }
    p += Math.floor(Math.abs(dark * 20 - n * n * 10) / (n * n)) * 10;
    return p;
  }

  function matrix(text) {
    var enc = encodeBits(text), cw = interleave(enc.version, enc.data), best = null, bestP = Infinity;
    for (var mask = 0; mask < 8; mask++) { var m = build(enc.version, cw, mask), p = penalty(m); if (p < bestP) { bestP = p; best = m; } }
    return best;
  }

  // Returns an SVG string with a 4-module quiet zone.
  function svg(text, label) {
    var m = matrix(text), n = m.length, q = 4, d = '';
    for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) if (m[y][x]) d += 'M' + (x + q) + ',' + (y + q) + 'h1v1h-1z';
    var s = n + q * 2;
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + s + ' ' + s + '" shape-rendering="crispEdges" role="img" aria-label="' + (label || 'QR code') + '">' +
      '<rect width="' + s + '" height="' + s + '" fill="#fff"/><path fill="#000" d="' + d + '"/></svg>';
  }

  return { matrix: matrix, svg: svg };
})();
