// Prints the PDF templates listed in a jobs file: [{src: page.html, out: file.pdf}]
const { chromium } = require('playwright');
const jobs = require(require('path').resolve(process.argv[2]));
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  for (const job of jobs) {
    await page.goto('file://' + job.src);
    await page.pdf({ path: job.out, preferCSSPageSize: true, printBackground: true });
  }
  await browser.close();
})();
