// 把 web/_term/*.html 的终端卡片截成 shots/*.png（2x 高清）。
const puppeteer = require('puppeteer');
const fs = require('fs'), path = require('path');
const TERM = path.join(__dirname, '_term');
const OUT = path.join(__dirname, 'shots');

(async () => {
  const files = fs.readdirSync(TERM).filter(f => f.endsWith('.html'));
  const browser = await puppeteer.launch({ headless: 'shell', args: ['--no-sandbox', '--disable-gpu', '--force-device-scale-factor=2'] });
  const page = await browser.newPage();
  await page.setViewport({ width: 1000, height: 800, deviceScaleFactor: 2 });
  for (const f of files) {
    await page.goto('file://' + path.join(TERM, f), { waitUntil: 'networkidle0' });
    const el = await page.$('.term');
    const name = f.replace('.html', '');
    await el.screenshot({ path: path.join(OUT, name + '.png') });
    console.log('shot', name);
  }
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
