# Next Version — Planned Improvements

Changes to implement before the next full scan.

## Schema Detection: Split by Format

Currently `has_schema` is a single boolean merging JSON-LD, Microdata, and RDFa. Split into separate fields:

- `has_jsonld` — `application/ld+json` detected
- `has_microdata` — `itemtype` + schema.org detected
- `has_rdfa` — `vocab` + schema.org detected

Keep `has_schema` as a convenience field (`has_jsonld OR has_microdata OR has_rdfa`).

This enables reporting the breakdown by format (e.g. "X% use JSON-LD, Y% use Microdata").

## Known Limitations of Current Scan (April 2026)

### HTTP/2 — Disregard

aiohttp negotiates HTTP/1.1 only. The `http_version` field always shows `HTTP/1.1` regardless of server capability. **HTTP/2 stats are meaningless** — do not publish them.

Fix for next scan: use a probe that negotiates ALPN (e.g. `httpx` with HTTP/2 support, or a dedicated h2 check).

### Legal Compliance — Likely Undercounted

Impressum/Datenschutz detection relies on hardcoded paths (`/impressum`, `/datenschutz`, `/mentions-legales`, etc.) plus homepage link discovery. Sites that use non-standard paths, embed legal info in footers without dedicated pages, or use JavaScript-rendered legal sections will be missed.

The 24.5% Impressum and 19.8% Datenschutz rates are **lower bounds**, not ground truth. Do not claim "75% of Swiss sites lack an Impressum" — the real gap is smaller.
