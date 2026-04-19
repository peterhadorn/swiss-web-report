# Next Version — Planned Improvements

Changes to implement before the next full scan.

## Schema Detection: Split by Format

Currently `has_schema` is a single boolean merging JSON-LD, Microdata, and RDFa. Split into separate fields:

- `has_jsonld` — `application/ld+json` detected
- `has_microdata` — `itemtype` + schema.org detected
- `has_rdfa` — `vocab` + schema.org detected

Keep `has_schema` as a convenience field (`has_jsonld OR has_microdata OR has_rdfa`).

This enables reporting the breakdown by format (e.g. "X% use JSON-LD, Y% use Microdata").
