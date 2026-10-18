// Builds two things from src/:
//   dist/tallystick.html  one offline file; open it from disk. Blocks all network access.
//   dist/pwa/             an installable web app; host the folder anywhere static (GitHub Pages, Cloudflare Pages).
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const src = f => path.join(__dirname, 'src', f);
const r = f => fs.readFileSync(src(f), 'utf8');
const lib = r('lib.js'), qr = r('qr.js'), template = r('vault-template.html');
for (const [n, s] of [['lib', lib], ['qr', qr]]) if (/<\/script/i.test(s)) throw new Error(n + ' contains a closing script tag');
const tpl = JSON.stringify(template).replace(/<\//g, '<\\/');
const fill = (html, map) => Object.keys(map).reduce((h, k) => h.split('%%' + k + '%%').join(map[k]), html);

// Code placeholders first; the page placeholders (CSP etc.) are filled per build afterwards.
// Example screenshots for "How it works", embedded so the single file stays self-contained.
const ex = n => 'data:image/webp;base64,' + fs.readFileSync(src('examples/' + n + '.webp')).toString('base64');
const base = fill(r('creator.html'), { CSS: r('creator.css'), LIB: lib, QR: qr, TEMPLATE: tpl,
  EX_WRITE: ex('write'), EX_CARD: ex('card'), EX_ENVELOPE: ex('envelope') });

const STRICT = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src blob: data:; media-src blob:; form-action 'none'; base-uri 'none'";
const PWA = "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' blob: data:; media-src blob:; manifest-src 'self'; worker-src 'self'; connect-src 'self'; form-action 'none'; base-uri 'none'";

fs.mkdirSync(path.join(__dirname, 'dist/pwa/icons'), { recursive: true });
const single = fill(base, { CSP: STRICT, HEAD_EXTRA: '', PWA_SCRIPT: '' });
fs.writeFileSync(path.join(__dirname, 'dist/tallystick.html'), single);

const head = [
  '<link rel="manifest" href="manifest.webmanifest">',
  '<link rel="icon" type="image/png" sizes="32x32" href="icons/favicon-32.png">',
  '<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">',
  '<meta name="apple-mobile-web-app-capable" content="yes">',
  '<meta name="mobile-web-app-capable" content="yes">',
  '<meta name="apple-mobile-web-app-title" content="Tallystick">'
].join('\n');
const reg = "<script>if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(function(){});</script>";
const index = fill(base, { CSP: PWA, HEAD_EXTRA: head, PWA_SCRIPT: reg });
const version = crypto.createHash('sha256').update(index).digest('hex').slice(0, 12);
fs.writeFileSync(path.join(__dirname, 'dist/pwa/index.html'), index);
fs.writeFileSync(path.join(__dirname, 'dist/pwa/sw.js'), r('sw.js').split('%%VERSION%%').join(version));
fs.copyFileSync(src('manifest.webmanifest'), path.join(__dirname, 'dist/pwa/manifest.webmanifest'));
for (const f of fs.readdirSync(src('icons'))) fs.copyFileSync(path.join(src('icons'), f), path.join(__dirname, 'dist/pwa/icons', f));

for (const [n, s] of [['single', single], ['pwa', index]]) if (/%%(CSS|CSP|HEAD_EXTRA|PWA_SCRIPT|QR|TEMPLATE|EX_[A-Z]+)%%/.test(s)) throw new Error(n + ' has an unfilled placeholder');
console.log('built dist/tallystick.html', single.length, 'bytes; dist/pwa (version ' + version + ')');
