# v2 upgrade
Replace in your repo: scrape.py, config.json, docs/index.html, .github/workflows/scrape.yml. New: apps-script/Code.gs.
Reset old data: replace docs/data/opportunities.json with {"updated":"never","log":[],"items":[]} (v2 ignores v1 items anyway).

## Test locally first (VS Code terminal)
    python scrape.py
Read the log lines and open docs/data/opportunities.json: are the items real, open calls? Then:
    git add . && git commit -m "v2" && git push

## Google Sheet (team assigns leads here)
1. New Google Sheet > Extensions > Apps Script > paste apps-script/Code.gs > Save.
2. Project Settings > Script properties: add TOKEN (any long random string) and DIGEST_TO (team emails, comma separated).
3. Run `setup` once and approve permissions. A "Leads" tab appears with a Status dropdown.
4. Deploy > New deployment > Web app > Execute as: Me > Who has access: Anyone > copy the URL.
5. GitHub repo > Settings > Secrets and variables > Actions > New repository secret: SHEET_WEBHOOK (the URL) and SHEET_TOKEN (same string as TOKEN).
6. Apps Script > Triggers > add `weeklyDigest`, time-driven, weekly, Monday morning.
Share the Sheet with your team. They fill Owner, Status and Next action.
