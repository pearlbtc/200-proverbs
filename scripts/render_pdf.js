/*
 * 把 build_book.py 生成的 book.html 渲染为 PDF（印刷级）。
 * 用 Chromium headless 的打印能力，@page 尺寸/边距由 book.html 内 CSS 控制。
 *
 * 用法:
 *   node render_pdf.js <book.html> <out.pdf> [chromePath]
 * 示例:
 *   node render_pdf.js "D:/WorkBuddy-CQ/book.html" "D:/WorkBuddy-CQ/300首唐诗.pdf"
 *
 * 依赖:
 *   - puppeteer-core（npm i -D puppeteer-core）
 *   - 一个 Chrome/Chromium 可执行文件（本机路径见 CHROME 默认，或传第 3 个参数覆盖）
 *   本机 Chrome 多版本，先用 glob 找到 chrome.exe 再传参最稳：
 *     node render_pdf.js book.html out.pdf "C:/Users/brain/.cache/puppeteer/chrome/win64-<ver>/chrome-win64/chrome.exe"
 *
 * 注意:
 *   - book.html 里图片若为 base64 内联，无需额外资源；若引用外部图片，需与 html 同目录。
 *   - printBackground:true 才能保留水墨底色；preferCSSPageSize:true 才尊重 @page size。
 */
const puppeteer = require("puppeteer-core");
const path = require("path");

const SRC = process.argv[2] || "D:/WorkBuddy-CQ/book.html";
const OUT = process.argv[3] || "D:/WorkBuddy-CQ/out.pdf";
const CHROME = process.argv[4] ||
  "C:/Users/brain/.cache/puppeteer/chrome/win64-149.0.7827.22/chrome-win64/chrome.exe";

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      "--font-render-hinting=none",
    ],
  });
  const page = await browser.newPage();
  await page.goto("file:///" + path.resolve(SRC), { waitUntil: "load", timeout: 120000 });
  await new Promise((r) => setTimeout(r, 2000)); // 等字体与图片渲染稳定

  await page.pdf({
    path: OUT,
    printBackground: true,
    preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: "<div></div>",
    footerTemplate:
      '<div style="width:100%;text-align:center;font-size:9px;color:#5c5346;font-family:\'Songti SC\',\'STSong\',\'SimSun\',serif;letter-spacing:2px;">第 <span class="pageNumber"></span> 页 / 共 <span class="totalPages"></span> 页</div>',
    format: "A4",
  });

  await browser.close();
  const fs = require("fs");
  console.log("DONE size=", (fs.statSync(OUT).size / 1024 / 1024).toFixed(2), "MB ->", OUT);
})().catch((e) => {
  console.error("ERROR", e);
  process.exit(1);
});
