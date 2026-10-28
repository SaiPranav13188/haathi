# Telangana G.O. fetcher

goir.telangana.gov.in is an ASP.NET form that only answers a real browser, so these scripts drive headless
Chromium (Playwright). The site's robots.txt allows all paths; requests are spaced 2.5–3 s apart.

```bash
cd scripts/goir && npm install && npx playwright install chromium
npm run search      # searches each department for each scheme name → goir_hits.json (G.O. no, date, subject)
npm run download    # downloads the chosen G.O.s (list at the top of download.mjs) into data/raw/ + goir_state.json
cd ../.. && make ingest && cd backend && uv run python -m ingestion.run --extract-only
uv run python -m ingestion.attach_official   # point seed rules at the official sentences (see MAP in that file)
```

To add a G.O.: find it with `search.mjs`, add a row to the list in `download.mjs`, then map the rules in
`backend/ingestion/attach_official.py`.
