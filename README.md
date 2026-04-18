# Swiss Web Report 2026

**The first comprehensive field study of Switzerland's 2.46 million .ch domains — analyzing AI readiness, legal compliance, CMS landscape, and SEO structure.**

## What This Study Measures

We scan every registered .ch domain and collect 35+ data points per website:

### AI Readiness
- **llms.txt** — Does the site provide an AI-readable description? ([llmstxt.org](https://llmstxt.org))
- **Schema.org / JSON-LD** — Is structured data present for AI extraction?
- **AI bot blocking** — Does robots.txt block GPTBot, ClaudeBot, or other AI crawlers?

### Legal Compliance (Swiss Law)
- **Impressum** — Required by [UWG Art. 3 Abs. 1 lit. s](https://www.fedlex.admin.ch/eli/cc/1988/223_223_223/de) for e-commerce sites
- **Email in Impressum** — Legally required contact method
- **Postal address in Impressum** — Must be a real address, not a PO box
- **Datenschutzerklärung** — Required by [DSG Art. 19](https://www.fedlex.admin.ch/eli/cc/2022/491/de) since September 2023
- **Cookie banner** — NOT required by Swiss law (tracked for comparison)

### CMS & Technology
- Content Management System detection (WordPress, Typo3, Wix, Jimdo, Squarespace, Joomla, Drupal, Contao, Webflow, Shopify, and more)
- E-commerce platform detection (WooCommerce, Shopify, Magento, PrestaShop)

### Infrastructure
- HTTPS adoption, HTTP version, response time, server software

### SEO Structure
- Title tag, meta description, heading hierarchy (H1/H2/H3), canonical URL, viewport meta, hreflang, Open Graph tags

## Quick Start

```bash
git clone https://github.com/peterhadorn/swiss-web-report.git
cd swiss-web-report
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Prepare a domain list (one domain per line, no protocol)
# e.g. example.com, example.org — works with any TLD or zonefile

# Test on 100 domains
python3 scan.py --input domains.txt --output results.db --limit 100

# Full scan
python3 scan.py --input domains.txt --output results.db --concurrency 50

# Analyze results
python3 analyze.py results.db
```

## Built for Scale

The scanner is designed to handle millions of domains reliably:

- **Async DNS (aiodns/c-ares)** — no threadpool bottleneck; rotates across 5 public DNS servers (Cloudflare, Google, Quad9)
- **Session recycling** — recreates HTTP sessions every 15 minutes to prevent stale connection pools and DNS cache poisoning
- **Circuit breaker** — automatically pauses when network connectivity drops (detects consecutive zero-active batches), deletes unreliable results, waits for recovery, then resumes
- **Connectivity health checks** — tests against known-good domains before resuming after an outage
- **Resume support** — skips already-scanned domains; safe to restart at any time
- **Bounded reads** — 200KB max per page, prevents memory exhaustion on large sites
- **Shuffled scanning** — randomizes domain order to spread DNS load evenly across nameservers

## CLI Options

```
python3 scan.py --input FILE --output DB [options]

--input         Domain list (one per line, required)
--output        SQLite output path (required)
--concurrency   Parallel connections (default: 50)
--limit         Scan only first N domains (for testing)
--shuffle       Randomize domain order
--no-resume     Start fresh, ignore existing results
```

## Results

Results are published as aggregated statistics at **[ki-barometer.ch](https://ki-barometer.ch)**.

No individual domain names are exposed in the published results.

## Citation

```bibtex
@misc{hadorn2026swissweb,
  author = {Peter Hadorn},
  title = {Swiss Web Report 2026: AI Readiness, Legal Compliance, and CMS Landscape Across 2.46 Million .ch Domains},
  year = {2026},
  url = {https://ki-barometer.ch},
  publisher = {WebEvolve}
}
```

## License

MIT — see [LICENSE](LICENSE).

## Author

**Peter Hadorn** — [WebEvolve.ch](https://webevolve.ch) | [LinkedIn](https://linkedin.com/in/peterhadorn)
