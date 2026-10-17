// Prints the QR matrices for the JSON list of texts given as the first argument.
const fs = require('fs'), vm = require('vm'), path = require('path');
const ctx = { TextEncoder, Array, Math };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../src/qr.js'), 'utf8') + ';this.Q = TallyQR;', ctx);
const texts = JSON.parse(process.argv[2]);
console.log(JSON.stringify(texts.map(t => ctx.Q.matrix(t).map(row => row.map(v => (v ? 1 : 0))))));
