import { chromium } from "playwright";
import { createHash } from "crypto";
import { readFileSync, writeFileSync, existsSync } from "fs";
const RAW = "/Users/saipranav/Desktop/haathi/data/raw/";
const T = [
  ["ts_mahalakshmi_bus", "TRB", "free travel", "47", "08/12/2023"],
  ["ts_mahalakshmi_lpg", "FCS", "LPG", "2", "27/02/2024"],
  ["ts_kalyana_lakshmi", "BCW", "Kalyana Lakshmi", "14", "06/07/2017"],
  ["ts_kalyana_lakshmi_amount", "BCW", "Kalyana Lakshmi", "8", "03/04/2018"],
  ["ts_aasara_pension", "PR", "Aasara", "34", "28/05/2019"],
  ["ts_epass_post_matric", "SW", "Post Matric", "18", "29/09/2022"],
];
const statePath = RAW + "goir_state.json";
const state = existsSync(statePath) ? JSON.parse(readFileSync(statePath)) : {};
const b = await chromium.launch();
const ctx = await b.newContext({ acceptDownloads: true, userAgent: "Mozilla/5.0 (Macintosh) HaathiBot/0.1 (educational)" });
for (const [sid, dept, kw, no, date] of T) {
  const p = await ctx.newPage();
  try {
    await p.goto("https://goir.telangana.gov.in/", { waitUntil: "domcontentloaded", timeout: 60000 });
    await p.selectOption('select[name="DDLDeptname"]', dept);
    await p.waitForLoadState("domcontentloaded"); await p.waitForTimeout(2000);
    await p.fill('input[name="txtSearchText"]', kw);
    await Promise.all([p.waitForLoadState("domcontentloaded"), p.click('input[name="BtnSearch"]')]);
    await p.waitForTimeout(3000);
    const rows = p.locator("table tr").filter({ hasText: date });
    let row = null;
    for (let i = 0; i < await rows.count(); i++) {
      const cells = await rows.nth(i).locator("td").allInnerTexts();
      if (cells.length >= 8 && cells[3].trim() === "MS" && cells[4].trim() === no && cells[5].includes(date)) { row = rows.nth(i); break; }
    }
    if (!row) { console.log(sid, "row not found"); continue; }
    const subject = (await row.locator("td").nth(7).innerText()).trim();
    const [dl] = await Promise.all([p.waitForEvent("download", { timeout: 60000 }), row.getByText("Download", { exact: true }).click()]);
    const file = `${sid}.pdf`;
    await dl.saveAs(RAW + file);
    const buf = readFileSync(RAW + file);
    state[sid] = { source: "goir.telangana.gov.in", dept, go: `G.O.Ms.No.${no}`, date, subject, file, bytes: buf.length,
                   sha256: createHash("sha256").update(buf).digest("hex"), pdf: buf.subarray(0, 5).toString() === "%PDF-",
                   downloaded_at: new Date().toISOString() };
    console.log(sid, "OK", buf.length, "bytes", state[sid].pdf ? "PDF" : "NOT-PDF");
  } catch (e) { console.log(sid, "ERROR", e.message.slice(0, 100)); }
  await p.close();
  await new Promise((r) => setTimeout(r, 3000));
}
writeFileSync(statePath, JSON.stringify(state, null, 1));
await b.close();
