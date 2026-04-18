# Changelog

## v0.14.1 — 2026-04-18

### Fix selectolax None attribute crash
- selectolax `.attributes.get("content", "")` returns `None` (not `""`) for malformed HTML attributes
- Caused 49K domains to fail with `'NoneType' object has no attribute 'strip'`
- Fix: use `or ""` fallback in `parse_homepage()` and `_detect_cms()`
- Deleted affected rows from DB so scanner rescans them with the fix

## v0.14.0 — 2026-04-18

### Detect auto-generated llms.txt
- New `llms_txt_auto` field distinguishes Wix boilerplate from organic llms.txt
- Wix auto-deploys identical 873-byte template on all sites (MCP endpoint docs, zero business-specific content)
- Detection checks for "powered by Wix" + "/_api/mcp" signatures in actual content
- Real organic llms.txt adoption: 8.5% of active Swiss sites, not 12.5%

## v0.13.0 — 2026-04-17

### Fix DNS death spiral + batch skip bug
- **Root cause found**: aiohttp's default DNS uses a ~5-thread `getaddrinfo` threadpool — saturates after ~1 hour of mass scanning, causing 0% active rate (all DNS lookups queue behind stale ones)
- Added `aiodns` (c-ares) for fully async DNS resolution — no threadpool bottleneck
- Use 5 DNS resolvers: Cloudflare (1.1.1.1, 1.0.0.1), Google (8.8.8.8, 8.8.4.4), Quad9 (9.9.9.9)
- Session recycling every 15 min to prevent stale connection pools
- **Fixed**: duplicate `i += BATCH_SIZE` was skipping every other batch (~50% of domains never scanned)
- **Fixed**: circuit breaker rewind used already-reset `zero_batches` (always rewound only 1 batch)
- Legal pages: try homepage-discovered links first (higher hit rate), hardcoded paths second
- Capped legal page attempts at 5 per type (was up to 16 for non-compliant domains)
- Default concurrency changed to 50
- Division-by-zero guard on final summary log
- Scan runs as systemd service again (auto-restart, survives reboot)

## v0.12.0 — 2026-04-16

### Circuit breaker for network failures
- Scanner pauses when 2 consecutive batches have 0% active rate
- Tests connectivity against google.com, sbb.ch, admin.ch before resuming
- Deletes unreliable results from zero-active batches automatically
- Recreates aiohttp session (fixes corrupted TCP connector pool)
- Waits 30s between connectivity retries until network returns
- Fixed bug: circuit breaker check moved inside reporting block (counters were reset before outer loop could check them)
- **Root cause**: VPS provider's single DNS server (82.21.4.1) overwhelmed by 50 concurrent lookups → switched to Cloudflare/Google DNS (1.1.1.1, 8.8.8.8)
- Incident: DNS failures corrupted ~470K results across two episodes; deleted and re-scanned from 77K

## v0.11.0 — 2026-04-15

### Production scan setup
- Timeout reduced from 15s to 8s (dead domains clear faster)
- Removed trailing-slash duplicate paths (12→6 impressum, 14→10 datenschutz)
- Added `--shuffle` flag (seed=42, reproducible) to distribute active/dead domains evenly
- Health monitoring: writes `results_health.json` every 1000 domains with rate, active %, ETA
- Per-batch active rate logged to detect network saturation
- Systemd service (`swiss-web-scan`) with auto-restart on crash
- Hourly Slack notifications to leadgen-pipeline channel
- Swap flush cron (every 30min, only if >200MB swap and >1GB RAM free)
- Benchmarked concurrency: 50 is optimal (73% active, no choking)
- Rolling 1-hour active rate window in health file and Slack notifications

## v0.10.0 — 2026-04-14

### Sixth review fixes
- **Schema validation**: fail fast on resume if DB columns don't match current schema
- **Legal link resolution**: resolve discovered links against `final_url` (not origin) via `urljoin`, fixing detection on path-based multilingual sites (e.g. `/de/impressum`)
- **Relative links**: `href="impressum"` and `href="de/datenschutz"` now handled (was only absolute/root-relative)
- **Request budget**: deduplicate and cap discovered legal links at 5 per page type
- **Robots Allow**: only `Allow: /` (exact root) cancels `Disallow: /`, not `Allow: /assets/`
- **Sitemap comments**: `# Sitemap:` lines no longer falsely set `has_sitemap`
- Move inline `import re` to top of `scanner/scan.py`

## v0.9.0 — 2026-04-13

### Fifth review fixes
- `Allow: /` now cancels a `Disallow: /` block (was only matching `Allow: /path`)
- www vs apex host normalization for legal link comparison
- Canonical/viewport detection via selectolax CSS selectors (catches unquoted attributes)
- Deduplicate AI bot names from duplicate robots.txt groups

## v0.8.0 — 2026-04-13

### Naming and documentation fixes
- Renamed `redirects_www` → `final_host_is_www` (was not actually tracking redirects)
- Renamed status_category `parked` → `not_found` (404 is not parked)
- Updated CLAUDE.md: field count, requests per domain, compliance methodology
- Updated README.md: field count
- Updated status_category comment to include all values

## v0.7.0 — 2026-04-13

### Fourth review fixes
- Impressum: label + contact signal (email/address) is now sufficient (was rejecting valid minimal pages)
- robots.txt: strip inline comments before parsing (fixes missed blocks like `Disallow: / # no crawling`)
- AI bot blocking: apply allow-aware logic consistently (same as wildcard groups)
- base_url preserves explicit ports from redirected URLs

## v0.6.0 — 2026-04-13

### Third review fixes
- HTTPS non-200 now falls through to HTTP (was breaking on 403/500 HTTPS)
- Impressum validation requires 2+ keywords (was 1, caught catch-all pages)

## v0.5.0 — 2026-04-13

### Second review fixes
- analyze.py: `_stat()` now scopes numerator to match denominator (prevents >100% percentages)
- AI bot blocking: require `Disallow: /` (full block), not partial disallows
- `blocks_all_bots`: derived from parsed groups (handles stacked wildcard agents)

## v0.4.0 — 2026-04-13

### Code review fixes
- analyze.py: use `status_category = 'scannable'` as denominator for content metrics (was `is_active`)
- analyze.py: add status category breakdown, fix None crash on avg response time
- Legal links: restrict to same host (no more counting policies.google.com as target's privacy page)
- Datenschutz validation: require 2+ keywords (was 1, "cookies" alone caused false positives)
- robots.txt: proper group-based parsing for stacked User-agent lines
- README/CLAUDE.md: updated methodology (requests per domain, UA, robots.txt stance)

## v0.3.0 — 2026-04-13

### Scale & reliability fixes
- Batched processing: process 1000 domains at a time instead of creating 2.46M coroutines
- SQLite WAL mode: better write performance, commit every batch
- Bounded reads: `resp.content.read(N)` instead of unbounded `resp.text()` to prevent memory spikes
- Error logging: failed domains logged instead of silently swallowed
- Resume: iterate cursor instead of `fetchall()` for 2.46M rows
- CMS: fixed "divi" false positive matching "individual", "division" etc.
- robots.txt: `Disallow:` (empty = allow) no longer counted as blocking
- `redirects_www`: checks hostname only, not full URL

## v0.2.0 — 2026-04-13

### Scanner accuracy improvements
- Impressum/Datenschutz: multilingual paths (DE/FR/IT/EN) + homepage link discovery with content validation
- Schema: detect microdata and RDFa in addition to JSON-LD
- Sitemap: direct /sitemap.xml check, not just robots.txt reference
- Cookie banner: 17 providers (added CookieYes, Iubenda, Didomi, Quantcast, TrustArc, Axeptio, Tarteaucitron)
- CMS: added Neos, Sitecore, HubSpot, Strato detection
- AI bots: added Amazonbot, Cohere-AI, Meta-ExternalAgent; new `blocks_all_bots` field
- Email detection: plain text emails in addition to mailto: links
- Address detection: requires postal code + city name (no more false positives from years/prices)
- Status classification: `status_category` field (scannable/blocked/error/parked/timeout/inactive)
- Browser User-Agent to reduce false 403 blocks
- Timeout bumped to 15s
- robots.txt and llms.txt checked regardless of homepage status code

## v0.1.0 — 2026-04-12

- Initial scanner: 32 data points per domain
- Async scanning with aiohttp, SQLite storage
- Resume support, 200KB HTML limit
- CMS detection (13 platforms), cookie banner detection (10 providers)
- SEO structure, AI readiness, legal compliance checks
