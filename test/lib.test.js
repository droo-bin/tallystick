const fs = require('fs'), vm = require('vm'), assert = require('assert');
const src = fs.readFileSync(__dirname + '/../src/lib.js', 'utf8');
const ctx = { crypto: globalThis.crypto, TextEncoder, TextDecoder, btoa, atob, Uint8Array, DataView, console };
vm.createContext(ctx); vm.runInContext(src + ';this.Tally=Tally;', ctx);
const T = ctx.Tally;

(async () => {
  // field sanity
  for (let a = 1; a < 256; a++) assert.strictEqual(T.gmul(T.gdiv(a, 7), 7), a);
  // shamir all k-subsets for small cases
  const secret = T.randomBytes(32);
  for (const [k, n] of [[1, 1], [1, 3], [2, 3], [3, 5], [4, 7], [5, 5]]) {
    const sh = T.split(secret, k, n);
    const pick = (arr, k) => arr.length === k ? [arr] : arr.length < k ? [] : k === 0 ? [[]] :
      [...pick(arr.slice(1), k - 1).map(c => [arr[0], ...c]), ...pick(arr.slice(1), k)];
    for (const subset of pick(sh, k)) assert.deepStrictEqual(Buffer.from(T.combine(subset)), Buffer.from(secret));
    if (k > 1) assert.notDeepStrictEqual(Buffer.from(T.combine(sh.slice(0, k - 1))), Buffer.from(secret));
  }
  // big n
  const big = T.split(secret, 10, 255);
  assert.deepStrictEqual(Buffer.from(T.combine(big.slice(200, 210))), Buffer.from(secret));

  // full vault round trip
  const files = [new TextEncoder().encode('hello'), Uint8Array.from([0, 255, 1, 2])];
  const v = await T.makeVault({ title: 'Affairs', notes: 'Bank: [x]', files: [{ name: 'a.txt', type: 'text/plain' }, { name: 'b.bin' }] }, files, 3, 5);
  const out = await T.openVault(v.id, 3, v.ciphertextB64, [v.codes[4], v.codes[0], v.codes[2]]);
  assert.strictEqual(out.manifest.notes, 'Bank: [x]');
  assert.strictEqual(new TextDecoder().decode(out.files[0]), 'hello');
  assert.deepStrictEqual([...out.files[1]], [0, 255, 1, 2]);
  // typed with lowercase and spaces
  await T.openVault(v.id, 3, v.ciphertextB64, v.codes.slice(1, 4).map(c => c.toLowerCase().replace(/-/g, ' ')));

  const fails = async (p, re) => { try { await p; assert.fail('should fail'); } catch (e) { assert.match(e.message, re); } };
  await fails(T.openVault(v.id, 3, v.ciphertextB64, v.codes.slice(0, 2)), /needs 3 different cards/);
  await fails(T.openVault(v.id, 3, v.ciphertextB64, [v.codes[0], v.codes[0], v.codes[1]]), /needs 3/);
  const typo = v.codes[0].slice(0, 20) + (v.codes[0][20] === 'A' ? 'B' : 'A') + v.codes[0].slice(21);
  await fails(T.openVault(v.id, 3, v.ciphertextB64, [typo, v.codes[1], v.codes[2]]), /typo/);
  const other = await T.makeVault({ files: [] }, [], 2, 3);
  await fails(T.openVault(v.id, 3, v.ciphertextB64, [other.codes[0], v.codes[1], v.codes[2]]), /different envelope/);
  // tampered ciphertext
  const ct = T.fromB64(v.ciphertextB64); ct[40] ^= 1;
  await fails(T.openVault(v.id, 3, T.toB64(ct), v.codes.slice(0, 3)), /did not open/);
  console.log('all lib tests passed; code length', v.codes[0].length, v.codes[0]);
})().catch(e => { console.error(e); process.exit(1); });
