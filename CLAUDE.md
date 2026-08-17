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

Companion passive DNS email-security scanner (separate DB, separate CLI):

```
dmarc_scan.py           # CLI entry point — passive DNS-only scanner
dmarc_scanner/           # Core package
│   ├── models.py        # DmarcScanResult dataclass
│   ├── parsers.py        # SPF/DMARC/BIMI/MTA-STS/TLS-RPT/DKIM record parsing
│   ├── providers.py      # MX/DKIM provider fingerprinting
│   ├── resolve.py        # dnspython DNS resolution (thread-local resolver)
│   └── scan.py            # per-domain orchestration
analyze_dmarc.py         # Aggregate stats + cold-outreach lead-list query
data/dmarc_scan_results.db  # Gitignored — sibling DB, not a table in results.db
```

Run with:
```bash
python3 dmarc_scan.py --input data/ch_domains.txt --output data/dmarc_scan_results.db --concurrency 300
python3 analyze_dmarc.py data/dmarc_scan_results.db
```

DNS-only: MX, SPF, DKIM (provider-aware selector guess), DMARC, DNSSEC,
BIMI, MTA-STS, TLS-RPT, CAA. SPF/DKIM/DMARC/BIMI/MTA-STS/TLS-RPT/CAA are only
checked for domains with MX; DNSSEC is checked for all domains. Never
connects to the domain's own mail/web servers — public resolvers only.
Domains that error on a query are retried on the next run rather than
recorded as permanently done.

## How to Run

```bash
# Test on 100 domains
python3 scan.py --input data/ch_domains.txt --output results.db --limit 100

# Full scan on VPS
python3 scan.py --input data/ch_domains.txt --output results.db --concurrency 50

# Analyze results
python3 analyze.py results.db
```

## Key Design Decisions

- **SQLite, not Postgres** — portable, single-file, no server dependency. 2.5M rows is fine for SQLite.
- **No waterfall crawler** — plain aiohttp, 3-30 requests per domain (homepage + sub-pages), no JS rendering. Speed over depth.
- **200KB HTML limit** — bounded reads at network level. Homepage only for content parsing.
- **Resume support** — scanner skips already-scanned domains. Safe to restart.
- **Legal compliance** — tries multilingual hardcoded paths first (/impressum, /mentions-legales, /note-legali, etc.), then follows homepage-discovered links with content validation.

## Data Points Per Domain

**Infrastructure:** is_active, status_code, status_category, has_ssl, http_version, response_time_ms, server, final_host_is_www, final_url
**CMS:** cms, cms_version, ecommerce
**SEO Structure:** has_title, title_len, has_meta_desc, meta_desc_len, h1/h2/h3_count, has_canonical, has_viewport, has_hreflang, language, has_og
**AI Readiness:** has_schema, schema_types, has_llms_txt, llms_txt_score, has_robots, has_sitemap, blocks_ai_bots, blocks_all_bots
**Legal Compliance:** has_impressum, impressum_has_email, impressum_has_address, has_datenschutz, has_cookie_banner, cookie_provider

## Deployment

For full scans, run on a server with stable network and ample file descriptors. Use `tmux` so the scan survives disconnection. Concurrency 50 is the sweet spot — higher values cause DNS/network exhaustion after ~1 hour.

The scanner auto-resumes — re-running the same command skips already-scanned domains.

Expected `results.db` size: ~800MB – 1.2GB for the full 2.46M domain set.

## Ethics

- No domain names published in results
- No login attempts or form submissions
- Only homepage + specific paths (robots.txt, llms.txt, sitemap.xml, impressum/datenschutz variants)
- Browser User-Agent (standard Chrome UA)
- Reads robots.txt for data collection (AI bot blocking stats), does not honor Disallow for scanning
- The companion passive DNS email-security scan (`dmarc_scan.py`) additionally
  powers a cold-outreach lead list and a public aggregate stat. Per-domain
  rows stay in the gitignored `data/` directory (same as `results.db`) and
  are never committed or individually published. It reads only DNS
  TXT/MX/DS/CAA records the domain's own DNS operator already publishes —
  no HTTP/TCP connection to the domain itself.

## Related

- Full plan: `leadgen/plans/2026-04-12-SWISS-WEB-LANDSCAPE-STUDY.md`
- Results published at: webevolve.ch/studie/
- Risikomonitor complementary study: risikomonitor.com/news/cybersecurity-studie-schweiz-2026
- Email-security product exploration: `leadgen/plans/explorations/2026-08-15-swiss-domain-security-product.md`
