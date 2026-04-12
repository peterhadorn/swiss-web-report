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

## VPS Deployment (MANDATORY — read before deploying)

**VPS:** root@82.21.4.94 (same VPS as leadgen backend)

### First-time setup
```bash
# Create directory on VPS
ssh root@82.21.4.94 "mkdir -p /var/www/swiss-web-report/data"

# Deploy code
scp -r scanner/ scan.py analyze.py requirements.txt root@82.21.4.94:/var/www/swiss-web-report/

# Copy zonefile (strip trailing dots first)
sed 's/\.$//' /Users/peterhadorn/chzone/ch_uniq.txt > /tmp/ch_domains.txt
scp /tmp/ch_domains.txt root@82.21.4.94:/var/www/swiss-web-report/data/ch_domains.txt

# Install dependencies on VPS
ssh root@82.21.4.94 "cd /var/www/swiss-web-report && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"

# Clean logs first (frees ~900MB)
ssh root@82.21.4.94 "journalctl --vacuum-size=100M"

# Increase file descriptor limit for async connections
ssh root@82.21.4.94 "echo '* soft nofile 65535' >> /etc/security/limits.conf"
```

### Run the scan
```bash
# SSH into VPS, use tmux so it survives disconnection
ssh root@82.21.4.94
tmux new -s webscan
cd /var/www/swiss-web-report

# Start at concurrency 200, monitor for 10 min
.venv/bin/python3 scan.py --input data/ch_domains.txt --output data/results.db --concurrency 200

# Ctrl+B, D to detach from tmux
# tmux attach -t webscan to reconnect
```

### Monitor progress
```bash
# Check how many domains scanned so far
ssh root@82.21.4.94 "sqlite3 /var/www/swiss-web-report/data/results.db 'SELECT COUNT(*) FROM scan_results'"

# Check active count
ssh root@82.21.4.94 "sqlite3 /var/www/swiss-web-report/data/results.db 'SELECT COUNT(*) FROM scan_results WHERE is_active=1'"

# Check system resources
ssh root@82.21.4.94 "htop" or "top -bn1 | head -5"

# Check disk space
ssh root@82.21.4.94 "df -h /"
```

### After scan completes
```bash
# Download results to local machine
scp root@82.21.4.94:/var/www/swiss-web-report/data/results.db ./data/results.db

# Run analysis
python3 analyze.py data/results.db
```

### Resume after interruption
The scanner auto-resumes — just run the same command again. It skips already-scanned domains.

### Disk space
- VPS has ~5.6 GB free (after journal cleanup)
- Expected results.db size: ~800MB - 1.2GB
- Plenty of room

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
