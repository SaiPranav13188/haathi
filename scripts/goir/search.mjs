import { chromium } from "playwright";
import { writeFileSync } from "fs";
// dept, keyword (searched in G.O. subjects), no year filter
const Q = [
  ["AGLC", "Rythu Bharosa"], ["AGLC", "Rythu Bima"], ["AGLC", "Investment Support"],
  ["PR", "Aasara"], ["PR", "Cheyutha"], ["PR", "Atmiya Bharosa"], ["PR", "landless"],
  ["ENY", "Gruha Jyothi"], ["ENY", "200 units"],
  ["TRB", "Mahalakshmi"], ["TRB", "free travel"],
  ["FCS", "Mahalakshmi"], ["FCS", "LPG"],
  ["HOU", "Indiramma"], ["HMF", "Aarogyasri"], ["HMF", "Arogyasri"],
  ["BCW", "Kalyana Lakshmi"], ["SW", "Kalyana Lakshmi"], ["MW", "Shaadi Mubarak"], ["TW", "Kalyana Lakshmi"],
  ["SW", "Post Matric"], ["BCW", "Post Matric"], ["BCW", "fee reimbursement"], ["MW", "Post Matric"],
  ["WCDW", "Mahalakshmi"],
];
const b = await chromium.launch();
const out = [];
for (const [dept, kw] of Q) {
  const p = await b.newPage({ userAgent: "Mozilla/5.0 (Macintosh) HaathiBot/0.1 (educational)" });
  try {
    await p.goto("https://goir.telangana.gov.in/", { waitUntil: "domcontentloaded", timeout: 60000 });
    await p.selectOption('select[name="DDLDeptname"]', dept);
    await p.waitForLoadState("domcontentloaded"); await p.waitForTimeout(2000);
    await p.fill('input[name="txtSearchText"]', kw);
    await Promise.all([p.waitForLoadState("domcontentloaded"), p.click('input[name="BtnSearch"]')]);
    await p.waitForTimeout(3000);
    const rows = await p.$$eval("table tr", (trs) => trs.map((tr) => [...tr.querySelectorAll("td")].map((td) => td.innerText.trim().replace(/\s+/g, " ")))
      .filter((c) => c.length >= 8 && c.length <= 14 && /\d{2}\/\d{2}\/\d{4}/.test(c[5] || "")));
    console.log(`${dept} "${kw}": ${rows.length}`);
    for (const r of rows) out.push({ dept, kw, idx: Number(r[0]) - 1, section: r[2], type: r[3], no: r[4], date: r[5], cat: r[6], subject: r[7] });
  } catch (e) { console.log(`${dept} "${kw}": ERROR ${e.message.slice(0, 80)}`); }
  await p.close();
  await new Promise((r) => setTimeout(r, 2500));
}
writeFileSync(new URL("./goir_hits.json", import.meta.url), JSON.stringify(out, null, 1));
await b.close();
