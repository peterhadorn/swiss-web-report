# Swiss Web Report 2026

**The first comprehensive field study of Switzerland's 2.46 million .ch domains — analyzing AI readiness, legal compliance, CMS landscape, and SEO structure.**

## What This Study Measures

We scan every registered .ch domain and collect 32 data points per active website:

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

## Methodology

| | |
|---|---|
| **Data source** | Official .ch zonefile from [SWITCH](https://www.switch.ch/open-data/) |
| **Domains** | 2,459,127 unique .ch domains |
| **Requests per domain** | 3-30 (homepage, robots.txt, llms.txt, sitemap.xml, up to 12 impressum paths, up to 15 datenschutz paths — stops at first match) |
| **Scanner** | Async Python (aiohttp), ~100 concurrent connections |
| **Runtime** | ~30-38 hours (single pass) |
| **Storage** | SQLite |
| **Ethics** | No domain names published. No login attempts. No crawling beyond homepage + legal pages. |

## Quick Start

```bash
# Clone
git clone https://github.com/peterhadorn/swiss-web-report.git
cd swiss-web-report

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Obtain the .ch zonefile (requires dig with TSIG key — see below)
# Place domain list in data/ch_domains.txt (one domain per line)

# Test on 100 domains
python3 scan.py --input data/ch_domains.txt --output results.db --limit 100

# Full scan
python3 scan.py --input data/ch_domains.txt --output results.db --concurrency 200

# Analyze results
python3 analyze.py results.db
```

## Obtaining the .ch Zonefile

The Swiss .ch zonefile is publicly available from SWITCH via DNS zone transfer:

```bash
dig -y hmac-sha512:tsig-zonedata-ch-public-21-01:stZwEGApYumtXkh73qMLPqfbIDozWKZLkqRvcjKSpRnsor6A6MxixRL6C2HeSVBQNfMW4wer+qjS0ZSfiWiJ3Q== \
    @zonedata.switch.ch +noall +answer +noidnout +onesoa AXFR ch. > ch_raw.txt

# Extract unique domains
awk '/\tIN\tNS\t/ { print $1 }' ch_raw.txt | sed 's/\.$//' | sort -u > data/ch_domains.txt
```

See [SWITCH Open Data](https://www.switch.ch/open-data/) for terms of use.

## Resume Support

The scanner automatically skips already-scanned domains. If the scan is interrupted, just restart it with the same command — it picks up where it left off.

## Results

Results are published as aggregated statistics at **[webevolve.ch/studie/](https://webevolve.ch/studie/)** (coming soon).

No individual domain names are exposed in the published results.

## Complementary Research

This study complements the [Swiss Digital Infrastructure Study 2026](https://risikomonitor.com/news/cybersecurity-studie-schweiz-2026) by RisikoMonitor, which analyzed security vulnerabilities across 3.3M .ch domains. Our study focuses on AI readiness, legal compliance, and CMS landscape — areas not covered by their security-focused analysis.

## Citation

```bibtex
@misc{hadorn2026swissweb,
  author = {Peter Hadorn},
  title = {Swiss Web Report 2026: AI Readiness, Legal Compliance, and CMS Landscape Across 2.46 Million .ch Domains},
  year = {2026},
  url = {https://webevolve.ch/studie/},
  publisher = {WebEvolve}
}
```

## License

MIT — see [LICENSE](LICENSE).

## Author

**Peter Hadorn** — [WebEvolve.ch](https://webevolve.ch) | [LinkedIn](https://linkedin.com/in/peterhadorn)
