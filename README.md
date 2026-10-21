# Impact Radar
Free funding-opportunity radar and pipeline for Bridge Talent's impact work.

## Setup (about 15 minutes)
1. Create a free GitHub account, then a **new private repository** (e.g. `impact-radar`). Private repos still get free Actions minutes; GitHub Pages on private repos needs a paid plan, so if you want the dashboard online either make the repo **public** (it holds only public opportunity links, never put contacts or notes in it) or open `docs/index.html` locally.
2. Upload every file in this folder (keep the folder structure, including `.github/workflows`).
3. Settings > Pages > Source: "Deploy from a branch", branch `main`, folder `/docs`. Your dashboard URL appears there.
4. Actions tab > "Scrape opportunities" > **Run workflow**. Check the log lines: each source shows OK or FAILED.
5. Settings > Actions > General > Workflow permissions: set to "Read and write".

## Add Google Alerts (the most reliable source)
alerts: google.com/alerts > create e.g. `"youth employment" Kenya "call for proposals"` > Show options > Deliver to: **RSS feed** > copy the feed link into `config.json` (replace `PASTE_GOOGLE_ALERT_RSS_URL`, set `"enabled": true`).

## Tuning
Edit `config.json`: theme keywords and weights, `min_score` (raise it if too noisy), and sources. Types: `rss`, `page` (collects links from any page), `wb` (World Bank). Only scrape sites whose terms allow it.

## Privacy
Your pipeline (stages, contacts, notes) is saved only in your browser. Use Export/Import in the dashboard to back up or move it.
