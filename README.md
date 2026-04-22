# Schweizer Web-Studie

**Frühling 2026: KI-Bereitschaft, CMS, SEO & mehr**

Scanner für die Schweizer Web-Studie 2026: eine technische Feldstudie von 2'459'124 `.ch`-Domains zu KI-Bereitschaft, SEO-Struktur, CMS-Erkennung, Infrastruktur und Legal-Page-Signalen.

Publizierte Ergebnisse: [ki-barometer.ch/schweizer-web-studie](https://ki-barometer.ch/schweizer-web-studie/)

## Methodik

Grundlage ist das öffentliche SWITCH-Zonefile vom 12. April 2026 mit allen registrierten `.ch`-Domains. Der Scanner prüft jede Domain per HTTP-Request und erfasst pro Website 35+ Datenpunkte:

- **KI-Bereitschaft:** `llms.txt`, Wix-generiertes `llms.txt`-Boilerplate, strukturierte Daten (JSON-LD, Microdata, RDFa), KI-Bot-Blockierung via `robots.txt`
- **CMS-Erkennung:** WordPress, TYPO3, Wix, Jimdo, Squarespace, Joomla, Drupal, Contao, Webflow, Shopify u.a.
- **Page Builder und E-Commerce:** Elementor, Divi, WooCommerce, Shopify, Magento, PrestaShop
- **SEO-Struktur:** Title-Tag, Meta Description, H1/H2/H3, Canonical URL, Viewport, Hreflang, Open Graph
- **Infrastruktur:** HTTPS, HTTP-Version, Antwortzeit, Server-Header
- **Legal-Page-Signale:** Impressum, E-Mail- und Adresssignale, Datenschutzseite, Cookie-Banner-Anbieter

Der Scan erfolgt mit `aiohttp` und `aiodns`, ohne JavaScript-Rendering. Pro HTML-Seite werden maximal 200 KB gelesen. Die Reihenfolge kann randomisiert werden, um DNS-Last gleichmässig zu verteilen.

Legal-Page-Signale sind technische Indikatoren, keine Rechtsberatung und kein vollständiger Compliance-Audit.

## Umfang

- **2'459'124** `.ch`-Domains gescannt
- **1'742'537** aktiv
- **1'463'577** analysierbare Websites mit HTTP 200 und nutzbarem HTML
- **35+** Datenpunkte pro Domain

Alle publizierten Prozentwerte beziehen sich auf die 1'463'577 analysierbaren Websites.

## Nutzung

```bash
git clone https://github.com/peterhadorn/swiss-web-report.git
cd swiss-web-report
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Domainliste: eine Domain pro Zeile, ohne Protokoll
python3 scan.py --input domains.txt --output results.db --limit 100
python3 scan.py --input domains.txt --output results.db --concurrency 50 --shuffle
python3 analyze.py results.db
```

## Scanner-Design

- Async DNS via `aiodns` / c-ares
- Fünf öffentliche DNS-Resolver: Cloudflare, Google, Quad9
- Session-Recycling alle 15 Minuten
- Circuit Breaker bei aufeinanderfolgenden Zero-Active-Batches
- Connectivity Checks vor dem Fortsetzen nach Ausfällen
- Resume standardmässig aktiv
- `--no-resume` löscht die bestehende Tabelle `scan_results` und startet neu
- Begrenzte HTML-Reads: 200 KB pro Seite
- Deterministisches Shuffle mit Seed `42`

## CLI

```text
python3 scan.py --input FILE [--output DB] [options]

--input         Domainliste, eine Domain pro Zeile
--output        SQLite-Ausgabepfad, Standard: results.db
--concurrency   Parallele Verbindungen, Standard: 50
--limit         Nur die ersten N Domains scannen
--shuffle       Domainreihenfolge mit Seed 42 randomisieren
--no-resume     Bestehende Ergebnisse löschen und neu scannen
```

```text
python3 analyze.py [DB]

DB              SQLite-Ergebnisdatenbank, Standard: results.db
```

## Ergebnisse

Die aggregierten Ergebnisse sind unter [ki-barometer.ch/schweizer-web-studie](https://ki-barometer.ch/schweizer-web-studie/) publiziert.

Domain-Level-Rohdaten werden nicht veröffentlicht.

## Zitation

```bibtex
@misc{hadorn2026schweizerwebstudie,
  author = {Peter Hadorn},
  title = {Schweizer Web-Studie (Fruehling 2026): KI-Bereitschaft und technische Bestandsaufnahme von 2'459'124 .ch-Domains},
  year = {2026},
  url = {https://ki-barometer.ch/schweizer-web-studie/},
  publisher = {KI-Barometer.ch}
}
```

## Autor

Peter Hadorn - [WebEvolve.ch](https://webevolve.ch) | [LinkedIn](https://linkedin.com/in/peterhadorn)

## Lizenz

MIT. Siehe [LICENSE](LICENSE).
