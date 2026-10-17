// Crypto core tests. Run with: node --test test/
const { describe, it, before } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs'), path = require('path'), vm = require('vm');

function loadTally() {
  const ctx = { crypto: globalThis.crypto, TextEncoder, TextDecoder, btoa, atob, Uint8Array, DataView, console };
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../src/lib.js'), 'utf8') + ';this.Tally = Tally;', ctx);
  return ctx.Tally;
}
const T = loadTally();
const bytes = (u8) => Buffer.from(u8);

function combinations(list, k) {
  if (k === 0) return [[]];
  if (list.length < k) return [];
  const [first, ...rest] = list;
  return [...combinations(rest, k - 1).map((c) => [first, ...c]), ...combinations(rest, k)];
}

describe('GF(256) arithmetic', () => {
  it('division undoes multiplication for every non-zero byte', () => {
    for (let a = 1; a < 256; a++) assert.equal(T.gmul(T.gdiv(a, 7), 7), a);
  });
});

describe('Shamir secret sharing', () => {
  const secret = T.randomBytes(32);

  for (const [k, n] of [[1, 1], [1, 3], [2, 3], [3, 5], [4, 7], [5, 5]]) {
    it(`any ${k} of ${n} shares rebuild the secret`, () => {
      const shares = T.split(secret, k, n);
      for (const subset of combinations(shares, k)) assert.deepEqual(bytes(T.combine(subset)), bytes(secret));
    });
    if (k > 1) {
      it(`${k - 1} of ${n} shares do not`, () => {
        assert.notDeepEqual(bytes(T.combine(T.split(secret, k, n).slice(0, k - 1))), bytes(secret));
      });
    }
  }

  it('works at the largest size, 255 shares', () => {
    assert.deepEqual(bytes(T.combine(T.split(secret, 10, 255).slice(200, 210))), bytes(secret));
  });

  it('rejects impossible thresholds', () => {
    assert.throws(() => T.split(secret, 4, 3));
    assert.throws(() => T.split(secret, 1, 256));
  });
});

describe('Sealed envelopes', () => {
  const files = [new TextEncoder().encode('hello'), Uint8Array.from([0, 255, 1, 2])];
  const manifest = { title: 'Affairs', notes: 'Bank: [x]', files: [{ name: 'a.txt', type: 'text/plain' }, { name: 'b.bin' }] };
  let vault, other;

  before(async () => {
    vault = await T.makeVault(manifest, files, 3, 5);
    other = await T.makeVault({ files: [] }, [], 2, 3);
  });

  const open = (codes, sealed = vault.ciphertextB64) => T.openVault(vault.id, 3, sealed, codes);

  it('opens with any three cards and returns notes and files intact', async () => {
    const out = await open([vault.codes[4], vault.codes[0], vault.codes[2]]);
    assert.equal(out.manifest.notes, 'Bank: [x]');
    assert.equal(new TextDecoder().decode(out.files[0]), 'hello');
    assert.deepEqual([...out.files[1]], [0, 255, 1, 2]);
  });

  it('accepts codes typed in lowercase with spaces', async () => {
    await open(vault.codes.slice(1, 4).map((c) => c.toLowerCase().replace(/-/g, ' ')));
  });

  it('refuses too few cards', async () => {
    await assert.rejects(open(vault.codes.slice(0, 2)), /needs 3 different cards/);
  });

  it('does not count the same card twice', async () => {
    await assert.rejects(open([vault.codes[0], vault.codes[0], vault.codes[1]]), /needs 3/);
  });

  it('catches a mistyped code', async () => {
    const c = vault.codes[0];
    const typo = c.slice(0, 20) + (c[20] === 'A' ? 'B' : 'A') + c.slice(21);
    await assert.rejects(open([typo, vault.codes[1], vault.codes[2]]), /typo/);
  });

  it('refuses a card from another envelope', async () => {
    await assert.rejects(open([other.codes[0], vault.codes[1], vault.codes[2]]), /different envelope/);
  });

  it('detects a damaged envelope', async () => {
    const damaged = T.fromB64(vault.ciphertextB64);
    damaged[40] ^= 1;
    await assert.rejects(open(vault.codes.slice(0, 3), T.toB64(damaged)), /did not open/);
  });

  it('writes card codes as TALLY1 plus 24 groups of four', () => {
    assert.match(vault.codes[0], /^TALLY1(-[0-9A-F]{4}){24}$/);
  });
});
