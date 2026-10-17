const fs = require('fs'), vm = require('vm');
const ctx = { TextEncoder, Array, Math };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(__dirname + '/../src/qr.js', 'utf8') + ';this.Q=TallyQR;', ctx);
const texts = JSON.parse(process.argv[2]);
console.log(JSON.stringify(texts.map(t => ctx.Q.matrix(t).map(r => r.map(v => v ? 1 : 0)))));
