// 抓四种循环 UI 的大截屏。用法（见 web/shoot.sh）：
//   node capture.js <baseURL>
// 每种循环产出：整页大图 / 主区 / 代码卡近景，全部 2x 高清。
const puppeteer = require('puppeteer');

const BASE = process.argv[2] || 'http://127.0.0.1:8099';
const KEYS = ['dialog', 'goal', 'scheduled', 'pipeline'];
const OUT = require('path').join(__dirname, 'shots');

(async () => {
  const browser = await puppeteer.launch({
    headless: 'shell',
    args: ['--no-sandbox', '--disable-gpu', '--force-device-scale-factor=2'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1480, height: 1000, deviceScaleFactor: 2 });
  await page.goto(BASE, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 500));

  for (let i = 0; i < KEYS.length; i++) {
    await page.evaluate((idx) => window.select(idx), i);
    await new Promise(r => setTimeout(r, 450));
    const k = KEYS[i];
    // 整页大图（含左栏语境）
    await page.screenshot({ path: `${OUT}/ui-${k}-full.png`, fullPage: true });
    // 主区
    const main = await page.$('#main');
    if (main) await main.screenshot({ path: `${OUT}/ui-${k}-main.png` });
    // 代码卡近景（代码要清晰）
    const code = await page.$('.codecard');
    if (code) await code.screenshot({ path: `${OUT}/ui-${k}-code.png` });
    console.log('captured', k);
  }
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('CAPERR', e.message); process.exit(1); });
