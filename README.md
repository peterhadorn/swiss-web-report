# Schweizer Web-Studie 2026

Analyse der .ch-Zone auf KI-Bereitschaft, CMS-Verbreitung, SEO-Struktur und Infrastruktur.

## Methodik

Grundlage ist das öffentliche SWITCH-Zonefile mit allen registrierten .ch-Domains. Der Scanner prüft jede Domain per HTTP-Request und erfasst pro Website rund 35 Datenpunkte:

- **KI-Bereitschaft:** llms.txt-Datei vorhanden, Schema.org-Markup, KI-Bot-Blockierung via robots.txt
- **CMS-Erkennung:** WordPress, Wix, TYPO3, Joomla, Squarespace, Webflow, Contao, Drupal u.a.
- **E-Commerce:** WooCommerce, Shopify, PrestaShop, Magento
- **SEO-Struktur:** Title-Tag, Meta Description, H1-Hierarchie, Canonical URL, Hreflang, Open Graph
- **Infrastruktur:** HTTPS, Viewport-Meta-Tag (Mobile), Antwortzeit, Server-Software
- **Cookie-Banner:** Erkennung von 17 Anbietern (CookieConsent, Cookiebot, Complianz u.a.)

Der Scan erfolgt asynchron mit kontrollierter Parallelität. Pro Website werden maximal 200 KB gelesen. Die Reihenfolge wird randomisiert, um DNS-Last gleichmässig zu verteilen.

## Umfang

- **2'459'124** .ch-Domains gescannt
- **1'742'537** aktiv (70,9%)
- **1'463'577** vollständig analysiert — HTTP 200 (59,5%)

Alle publizierten Prozentwerte beziehen sich auf die 1'463'577 analysierbaren Websites.

## Ergebnisse

Die aggregierten Ergebnisse sind unter **[ki-barometer.ch/schweizer-web-studie](https://ki-barometer.ch/schweizer-web-studie/)** publiziert.

Es werden keine einzelnen Domainnamen veröffentlicht.

## Zitation

```
Hadorn, P. (2026). Schweizer Web-Studie 2026. KI-Barometer.ch.
https://ki-barometer.ch/schweizer-web-studie/
```

## Autor

**Peter Hadorn** — [WebEvolve.ch](https://webevolve.ch)

## Lizenz

MIT
