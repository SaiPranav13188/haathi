// Export every icon size from the master SVG (haathi.md §8). Run: npm run icons
import sharp from "sharp";
import { readFile, writeFile } from "node:fs/promises";

const dir = new URL("../public/icons/", import.meta.url);
const master = await readFile(new URL("icon.svg", dir));
const png = (size, svg = master, opts = {}) => sharp(svg, { density: 384 }).resize(size, size).png(opts).toBuffer();

await writeFile(new URL("icon-192.png", dir), await png(192));
await writeFile(new URL("icon-512.png", dir), await png(512));

// maskable: logo inside the central 80% safe zone on a full-bleed background
const inner = await png(400);
await writeFile(new URL("icon-maskable-512.png", dir),
  await sharp({ create: { width: 512, height: 512, channels: 4, background: "#0b6e84" } })
    .composite([{ input: inner, top: 56, left: 56 }]).png().toBuffer());

// apple-touch-icon: 180×180, no transparency
await writeFile(new URL("apple-touch-icon.png", dir),
  await sharp(await png(180)).flatten({ background: "#0b6e84" }).png().toBuffer());

// favicon.ico with 16 + 32 px PNG images
const sizes = [16, 32];
const imgs = await Promise.all(sizes.map((s) => png(s)));
const header = Buffer.alloc(6 + 16 * imgs.length);
header.writeUInt16LE(0, 0); header.writeUInt16LE(1, 2); header.writeUInt16LE(imgs.length, 4);
let offset = header.length;
imgs.forEach((buf, i) => {
  const e = 6 + 16 * i;
  header.writeUInt8(sizes[i], e); header.writeUInt8(sizes[i], e + 1); header.writeUInt8(0, e + 2); header.writeUInt8(0, e + 3);
  header.writeUInt16LE(1, e + 4); header.writeUInt16LE(32, e + 6); header.writeUInt32LE(buf.length, e + 8); header.writeUInt32LE(offset, e + 12);
  offset += buf.length;
});
await writeFile(new URL("favicon.ico", dir), Buffer.concat([header, ...imgs]));

// og-image 1200×630 for WhatsApp / LinkedIn / X previews
const og = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f7f0e4"/><stop offset="1" stop-color="#efe3cf"/></linearGradient></defs>
  <rect width="1200" height="630" fill="url(#g)"/>
  <circle cx="1040" cy="560" r="180" fill="#f4a51c" opacity=".18"/><circle cx="120" cy="60" r="140" fill="#0b6e84" opacity=".10"/>
  <text x="440" y="270" font-family="Helvetica, Arial, sans-serif" font-size="112" font-weight="800" fill="#0b6e84">Haathi</text>
  <text x="444" y="340" font-family="Helvetica, Arial, sans-serif" font-size="38" font-weight="600" fill="#1b2a30">Find government schemes you're eligible for</text>
  <text x="444" y="398" font-family="Helvetica, Arial, sans-serif" font-size="30" fill="#4a5a60">Telugu · Hindi · English — with proof from official rules</text>
  <rect x="444" y="440" width="300" height="56" rx="28" fill="#0b6e84"/>
  <text x="594" y="477" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="26" font-weight="700" fill="#fff">Telangana first</text>
</svg>`;
const ogIcon = await png(300);
await writeFile(new URL("og-image.png", dir),
  await sharp(Buffer.from(og)).composite([{ input: ogIcon, top: 165, left: 90 }]).png().toBuffer());
console.log("icons written to public/icons/");
