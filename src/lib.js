/* Tallystick core, format version 1.
   Shared by the creator and by every vault file. Plain JavaScript, no dependencies.
   Uses only the Web Crypto API (crypto.getRandomValues, crypto.subtle). */
var Tally = (function () {
  'use strict';

  /* ---------- GF(256) arithmetic, AES field polynomial x^8+x^4+x^3+x+1 (0x11B), generator 3 ---------- */
  var EXP = new Uint8Array(512), LOG = new Uint8Array(256);
  (function () {
    var x = 1;
    for (var i = 0; i < 255; i++) {
      EXP[i] = x; LOG[x] = i;
      var x2 = (x << 1) ^ ((x & 0x80) ? 0x11B : 0); // x * 2
      x = (x2 ^ x) & 0xFF;                            // x * 3
    }
    for (var j = 255; j < 512; j++) EXP[j] = EXP[j - 255];
  })();
  function gmul(a, b) { return (a === 0 || b === 0) ? 0 : EXP[LOG[a] + LOG[b]]; }
  function gdiv(a, b) {
    if (b === 0) throw new Error('division by zero');
    return a === 0 ? 0 : EXP[(LOG[a] + 255 - LOG[b]) % 255];
  }

  /* Browsers only offer Web Crypto on secure pages (https, localhost or a local file). */
  var INSECURE = 'This page isn\'t secure, so your browser has switched off the encryption Tallystick needs. ' +
    'Open it from an https:// address, or save the file and open it from your device.';
  function cryptoAvailable() {
    var c = typeof crypto !== 'undefined' ? crypto : null;
    return !!(c && c.subtle && typeof c.getRandomValues === 'function');
  }
  function subtle() { if (!cryptoAvailable()) throw new Error(INSECURE); return crypto.subtle; }

  function randomBytes(n) { subtle(); var b = new Uint8Array(n); crypto.getRandomValues(b); return b; }

  /* ---------- Shamir secret sharing, byte by byte ---------- */
  // Returns n shares; share i has x = i (1..n) and y = one byte per secret byte.
  function split(secret, k, n) {
    if (!(k >= 1 && n >= k && n <= 255)) throw new Error('Need 1 <= k <= n <= 255');
    var shares = [];
    for (var s = 1; s <= n; s++) shares.push({ x: s, y: new Uint8Array(secret.length) });
    var coeffs = new Uint8Array(k);
    for (var b = 0; b < secret.length; b++) {
      coeffs[0] = secret[b];
      if (k > 1) coeffs.set(randomBytes(k - 1), 1);
      for (var i = 0; i < n; i++) {
        var x = shares[i].x, acc = 0;
        for (var c = k - 1; c >= 0; c--) acc = gmul(acc, x) ^ coeffs[c]; // Horner
        shares[i].y[b] = acc;
      }
    }
    return shares;
  }

  // Lagrange interpolation at x = 0. Needs at least k distinct shares.
  function combine(shares) {
    var len = shares[0].y.length, out = new Uint8Array(len);
    for (var i = 0; i < shares.length; i++) {
      var li = 1;
      for (var j = 0; j < shares.length; j++) {
        if (i === j) continue;
        li = gmul(li, gdiv(shares[j].x, shares[j].x ^ shares[i].x));
      }
      for (var b = 0; b < len; b++) out[b] ^= gmul(shares[i].y[b], li);
    }
    return out;
  }

  /* ---------- encodings ---------- */
  function toHex(u8) { var s = ''; for (var i = 0; i < u8.length; i++) s += (u8[i] < 16 ? '0' : '') + u8[i].toString(16); return s.toUpperCase(); }
  function fromHex(h) {
    if (h.length % 2) throw new Error('odd hex');
    var out = new Uint8Array(h.length / 2);
    for (var i = 0; i < out.length; i++) {
      var v = parseInt(h.substr(i * 2, 2), 16);
      if (isNaN(v)) throw new Error('bad hex');
      out[i] = v;
    }
    return out;
  }
  function toB64(u8) {
    var s = '', CH = 0x8000;
    for (var i = 0; i < u8.length; i += CH) s += String.fromCharCode.apply(null, u8.subarray(i, i + CH));
    return btoa(s);
  }
  function fromB64(b) {
    var s = atob(b.replace(/\s+/g, '')), out = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
    return out;
  }
  var enc = new TextEncoder(), dec = new TextDecoder();

  async function sha256(u8) { return new Uint8Array(await subtle().digest('SHA-256', u8)); }

  /* ---------- card codes ----------
     Bytes: [version=1][vault id, 8][k][n][x][key share, 32][checksum, 4 = first 4 bytes of SHA-256 of the rest]
     Written as "TALLY1-" followed by uppercase hex, grouped in fours for typing. */
  var PREFIX = 'TALLY1';
  async function encodeShare(vaultIdHex, k, n, share) {
    var body = new Uint8Array(1 + 8 + 3 + share.y.length);
    body[0] = 1;
    body.set(fromHex(vaultIdHex), 1);
    body[9] = k; body[10] = n; body[11] = share.x;
    body.set(share.y, 12);
    var sum = (await sha256(body)).subarray(0, 4);
    var all = new Uint8Array(body.length + 4); all.set(body); all.set(sum, body.length);
    return PREFIX + '-' + toHex(all).replace(/(.{4})/g, '$1 ').trim().replace(/ /g, '-');
  }
  async function decodeShare(code) {
    var clean = String(code).toUpperCase().replace(/[^0-9A-Z]/g, '');
    if (clean.indexOf(PREFIX) !== 0) throw new Error('This is not a Tallystick card code.');
    var hex = clean.slice(PREFIX.length);
    if (!/^[0-9A-F]+$/.test(hex) || hex.length !== 96) throw new Error('This card code is the wrong length. Check for missing characters.');
    var all = fromHex(hex), body = all.subarray(0, 44), sum = all.subarray(44);
    var want = (await sha256(body)).subarray(0, 4);
    for (var i = 0; i < 4; i++) if (want[i] !== sum[i]) throw new Error('This card code has a typo somewhere. Check it against the card.');
    if (body[0] !== 1) throw new Error('This card is from a newer version of Tallystick.');
    return { vaultId: toHex(body.subarray(1, 9)), k: body[9], n: body[10], x: body[11], y: body.slice(12, 44) };
  }

  /* ---------- bundle: [4-byte big-endian manifest length][manifest JSON, UTF-8][file bytes, in manifest order] ---------- */
  function pack(manifest, fileBytes) {
    var m = Object.assign({}, manifest, { files: (manifest.files || []).map(function (f, i) {
      return { name: f.name, type: f.type || 'application/octet-stream', size: fileBytes[i].length };
    }) });
    var mb = enc.encode(JSON.stringify(m)), total = 4 + mb.length;
    fileBytes.forEach(function (b) { total += b.length; });
    var out = new Uint8Array(total), dv = new DataView(out.buffer);
    dv.setUint32(0, mb.length); out.set(mb, 4);
    var off = 4 + mb.length;
    fileBytes.forEach(function (b) { out.set(b, off); off += b.length; });
    return out;
  }
  function unpack(u8) {
    var len = new DataView(u8.buffer, u8.byteOffset, u8.byteLength).getUint32(0);
    var manifest = JSON.parse(dec.decode(u8.subarray(4, 4 + len)));
    var off = 4 + len, files = [];
    (manifest.files || []).forEach(function (f) { files.push(u8.slice(off, off + f.size)); off += f.size; });
    return { manifest: manifest, files: files };
  }

  /* ---------- AES-256-GCM. Ciphertext = [12-byte IV][ciphertext+tag]. AAD = "tallystick-v1:" + vault id ---------- */
  async function importKey(raw) { return subtle().importKey('raw', raw, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']); }
  async function encrypt(key32, vaultIdHex, plain) {
    var iv = randomBytes(12), key = await importKey(key32);
    var ct = new Uint8Array(await subtle().encrypt({ name: 'AES-GCM', iv: iv, additionalData: enc.encode('tallystick-v1:' + vaultIdHex) }, key, plain));
    var out = new Uint8Array(12 + ct.length); out.set(iv); out.set(ct, 12);
    return out;
  }
  async function decrypt(key32, vaultIdHex, blob) {
    var key = await importKey(key32);
    return new Uint8Array(await subtle().decrypt({ name: 'AES-GCM', iv: blob.subarray(0, 12), additionalData: enc.encode('tallystick-v1:' + vaultIdHex) }, key, blob.subarray(12)));
  }

  /* ---------- high level ---------- */
  // Creates one vault: returns { id, k, n, ciphertextB64, codes: [code per trustee, in order] }
  async function makeVault(manifest, fileBytes, k, n) {
    var id = toHex(randomBytes(8)), key = randomBytes(32);
    var ct = await encrypt(key, id, pack(manifest, fileBytes));
    var shares = split(key, k, n), codes = [];
    for (var i = 0; i < shares.length; i++) codes.push(await encodeShare(id, k, n, shares[i]));
    key.fill(0);
    return { id: id, k: k, n: n, ciphertextB64: toB64(ct), codes: codes };
  }

  // Opens a vault from card codes. Throws a readable Error on any problem.
  async function openVault(vaultIdHex, k, ciphertextB64, codeList) {
    return unpack(await openRaw(vaultIdHex, k, ciphertextB64, codeList));
  }

  // Same as openVault but returns the decrypted bundle bytes (used by the self-test).
  async function openRaw(vaultIdHex, k, ciphertextB64, codeList) {
    var seen = {}, shares = [];
    for (var i = 0; i < codeList.length; i++) {
      var s = await decodeShare(codeList[i]);
      if (s.vaultId !== vaultIdHex) throw new Error('Card ' + (i + 1) + ' belongs to a different envelope.');
      if (seen[s.x]) continue;
      seen[s.x] = true; shares.push(s);
    }
    if (shares.length < k) throw new Error('This envelope needs ' + k + ' different cards. You have entered ' + shares.length + '.');
    var key = combine(shares.slice(0, k));
    var plain;
    try { plain = await decrypt(key, vaultIdHex, fromB64(ciphertextB64)); }
    catch (e) { throw new Error('The cards did not open this envelope. The envelope file may be damaged, or a card may be wrong.'); }
    finally { key.fill(0); }
    return plain;
  }

  /* ---------- rich text: rebuilt from an allowlist, no attributes kept (browser only) ---------- */
  var KEEP = { B: 'strong', STRONG: 'strong', I: 'em', EM: 'em', U: 'u', UL: 'ul', OL: 'ol', LI: 'li', P: 'p', DIV: 'p', BR: 'br', H3: 'h3', H4: 'h3' };
  function cleanHTML(html) {
    var src = new DOMParser().parseFromString('<body>' + (html || ''), 'text/html').body;
    var out = document.createElement('div');
    (function walk(from, to) {
      Array.prototype.forEach.call(from.childNodes, function (n) {
        if (n.nodeType === 3) { to.appendChild(document.createTextNode(n.textContent)); return; }
        if (n.nodeType !== 1 || /^(SCRIPT|STYLE|TEMPLATE|IFRAME|OBJECT|SVG|MATH)$/.test(n.tagName)) return;
        var tag = KEEP[n.tagName];
        if (!tag) { walk(n, to); return; }
        var e = document.createElement(tag); to.appendChild(e);
        if (tag !== 'br') walk(n, e);
      });
    })(src, out);
    return out.innerHTML;
  }
  function isBlankHTML(html) { return !String(html || '').replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').trim(); }

  return { cryptoAvailable: cryptoAvailable, cleanHTML: cleanHTML, isBlankHTML: isBlankHTML, split: split, combine: combine, encodeShare: encodeShare, decodeShare: decodeShare,
           pack: pack, unpack: unpack, encrypt: encrypt, decrypt: decrypt,
           makeVault: makeVault, openVault: openVault, openRaw: openRaw, sha256: sha256, toHex: toHex, fromHex: fromHex,
           toB64: toB64, fromB64: fromB64, randomBytes: randomBytes, gmul: gmul, gdiv: gdiv };
})();
