# CLAUDE.md - Swiss Web Report

## What This Is

Open-source scanner that checks all 2.46 million Swiss .ch domains for AI readiness, legal compliance, CMS landscape, and SEO structure. Results published as aggregated statistics — no individual domain names exposed.

## Python Version

**Always use `python3`, never `python`.**

## Project Structure

```
swiss-web-report/
├── scan.py              # Main entry point — CLI scanner
├── scanner/             # Core scanner package
│   ├── models.py        # ScanResult dataclass (32 fields per domain)
│   ├── parsers.py       # HTML parsing: CMS detection, SEO, compliance
│   ├── scan.py          # Async scanning logic (aiohttp)
│   └── db.py            # SQLite storage layer
├── analyze.py           # Analysis script — aggregate stats from results.db
├── data/                # Gitignored — domain lists and results
│   └── ch_domains.txt   # 2.46M .ch domains from SWITCH zonefile
├── requirements.txt     # aiohttp, selectolax
└── README.md            # Public-facing documentation
```

## How to Run

```bash
# Test on 100 domains
python3 scan.py --input data/ch_domains.txt --output results.db --limit 100

# Full scan on VPS
python3 scan.py --input data/ch_domains.txt --output results.db --concurrency 200

# Analyze results
python3 analyze.py results.db
```

## Key Design Decisions

- **SQLite, not Postgres** — portable, single-file, no server dependency. 2.5M rows is fine for SQLite.
- **No waterfall crawler** — plain aiohttp, 5-8 requests per domain, no JS rendering. Speed over depth.
- **200KB HTML limit** — prevents memory issues on large pages. Homepage only.
- **Resume support** — scanner skips already-scanned domains. Safe to restart.
- **Option B compliance** — directly tries /impressum and /datenschutz URLs instead of parsing homepage links.

## Data Points Per Domain (32 fields)

**Infrastructure:** is_active, status_code, has_ssl, http_version, response_time_ms, server, redirects_www
**CMS:** cms, cms_version, ecommerce
**SEO Structure:** has_title, title_len, has_meta_desc, meta_desc_len, h1/h2/h3_count, has_canonical, has_viewport, has_hreflang, language, has_og
**AI Readiness:** has_schema, schema_types, has_llms_txt, llms_txt_score, has_robots, has_sitemap, blocks_ai_bots
**Legal Compliance:** has_impressum, impressum_has_email, impressum_has_address, has_datenschutz, has_cookie_banner, cookie_provider

## VPS Deployment

Scanner runs on VPS at 82.21.4.94. Deploy with:
```bash
scp -r scanner/ scan.py analyze.py requirements.txt root@82.21.4.94:/var/www/swiss-web-report/
```

## Ethics

- No domain names published in results
- No login attempts or form submissions
- Only homepage + 4 specific paths (robots.txt, llms.txt, impressum, datenschutz)
- User-Agent identifies the project: `SwissWebReport/1.0 (research; webevolve.ch/studie/)`
- Respects robots.txt (reads it, doesn't violate it)

## Related

- Full plan: `leadgen/plans/2026-04-12-SWISS-WEB-LANDSCAPE-STUDY.md`
- Results published at: webevolve.ch/studie/
- Risikomonitor complementary study: risikomonitor.com/news/cybersecurity-studie-schweiz-2026
