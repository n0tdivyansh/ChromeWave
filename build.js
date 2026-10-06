// Bundles the game into one self-contained HTML file: node build.js [output]
const fs = require('fs');
const path = require('path');
const src = __dirname;
const out = process.argv[2] || path.join(src, '..', 'Chromewave.html');
let html = fs.readFileSync(path.join(src, 'index.html'), 'utf8');
html = html.replace(/<link rel="stylesheet" href="([^"]+)">/g, (m, href) => {
  const css = fs.readFileSync(path.join(src, href), 'utf8');
  return '<style>\n' + css + '\n</style>';
});
html = html.replace(/<script src="(?!https?:)([^"]+)"><\/script>/g, (m, file) => {   // local scripts only (the portal SDK stays external)
  const js = fs.readFileSync(path.join(src, file), 'utf8');
  if (/<\/script/i.test(js)) throw new Error('Sequence </script> not allowed in ' + file);
  return '<script>\n' + js + '\n</script>';
});
fs.writeFileSync(out, html);
console.log('OK ' + out + ' (' + Math.round(fs.statSync(out).size / 1024) + ' KB)');
