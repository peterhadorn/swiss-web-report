# Changelog

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
