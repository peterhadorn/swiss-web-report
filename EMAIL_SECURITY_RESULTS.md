# Swiss Email Security Barometer — Results

Full-scan results from the passive DNS-only email-security scanner (`dmarc_scan.py`, `dmarc_scanner/`), run against the complete SWITCH `.ch` zonefile.

- **Scanned:** 2,459,127 `.ch` domains
- **Analyzable:** 2,324,088 (135,039 domains, 5.5%, returned persistent DNS errors — primarily SERVFAIL from broken/unresponsive authoritative nameservers, confirmed via direct `dig` verification, not a scanner artifact)
- **Method:** passive DNS only — MX, DS, NS, TXT/SPF, legacy SPF RR-type-99, DMARC, DKIM (provider-aware selector guess), BIMI, MTA-STS (TXT presence only), TLS-RPT, CAA, TLSA/DANE, and per-MX-host resolvability. No HTTP/TCP connections to any domain's own servers — only queries to 5 public resolvers (1.1.1.1, 8.8.8.8, 9.9.9.9, 1.0.0.1, 8.8.4.4). No domain names published in aggregate results.

All percentages below are of the 2,324,088 analyzable domains unless noted otherwise.

## Infrastructure

| Metric | Count | % |
|---|---|---|
| Domains with MX (set up for email) | 1,708,618 | 73.5% |
| DNSSEC signed | 1,252,199 | 53.9% |
| Real NS record present | 2,241,187 | 96.4% |

### MX provider breakdown (of domains with MX)

| Provider | Count | % |
|---|---|---|
| Self-hosted | 433,207 | 25.4% |
| Other / unrecognized | 410,893 | 24.0% |
| Hostpoint | 348,745 | 20.4% |
| Infomaniak | 179,364 | 10.5% |
| Microsoft 365 | 160,321 | 9.4% |
| Google Workspace | 59,756 | 3.5% |
| Hosttech | 47,008 | 2.8% |
| Swizzonic | 22,442 | 1.3% |
| Tophost | 18,539 | 1.1% |
| ProtonMail | 9,565 | 0.6% |
| VTX | 5,459 | 0.3% |
| NetZone | 4,512 | 0.3% |
| iWay | 4,098 | 0.2% |
| Cyon | 1,120 | 0.1% |
| Barracuda | 1,034 | 0.1% |
| Proofpoint | 914 | 0.1% |
| Mailbox.org | 634 | 0.0% |
| Mimecast | 478 | 0.0% |
| Metanet | 411 | 0.0% |
| GMX | 69 | 0.0% |
| Swisscom | 29 | 0.0% |
| Init7 | 17 | 0.0% |
| green.ch | 3 | 0.0% |

## SPF (of domains with MX)

| Metric | Count | % |
|---|---|---|
| Has SPF | 1,482,058 | 86.7% |
| — all=hardfail (`-all`) | 574,101 | 33.6% |
| — all=softfail (`~all`) | 490,742 | 28.7% |
| — all=neutral (`?all`) | 87,889 | 5.1% |
| — all=pass (`+all`) | 359 | 0.0% |
| — all=none (no `all` mechanism) | 328,967 | 19.3% |
| Lookup mechanisms ≥ 8 (rough, top-level count — not recursive) | 1,238 | 0.1% |
| Legacy SPF RR-type-99 still in use (deprecated by RFC 7208) | 9,954 | 0.43% of all analyzable |

No-MX domains that still publish SPF anyway (self-protection against spoofing despite sending no mail): **180,313 of 615,470 no-MX domains (29.3%)**

## DKIM (provider-aware selector guess only — not exhaustive)

| Metric | Count | % |
|---|---|---|
| Selector found | 342,876 | 20.1% of MX domains |
| Weak key (≤1024-bit, length heuristic) | 108,768 | 31.72% of domains with DKIM found |
| Testing mode (`t=y`) | 25,430 | 7.42% of domains with DKIM found |

## DMARC (of domains with MX)

| Metric | Count | % |
|---|---|---|
| Has DMARC record | 731,804 | 42.8% |
| — policy=reject | 227,927 | 13.3% |
| — policy=quarantine | 283,399 | 16.6% |
| — policy=none (monitoring only) | 219,990 | 12.9% |
| — policy=absent | 977,122 | 57.2% |
| **Unprotected (absent or monitoring-only)** | **1,197,112** | **70.1%** |
| Partial enforcement (`pct` < 100) | 4,435 | 0.49% of domains with DMARC |
| Strict alignment (`adkim=s` or `aspf=s`) | 109,255 | 12.05% of domains with DMARC |

Of the 57.2% "absent": 977,122 domains never configured DMARC at all; only 308 domains have a DMARC record present but missing its policy tag (a rare misconfiguration, not the norm).

No-MX domains that still publish DMARC anyway: **174,646 of 615,470 no-MX domains (28.4%)**

## Emerging standards (of domains with MX)

| Metric | Count | % |
|---|---|---|
| BIMI | 1,324 | 0.1% |
| MTA-STS (TXT record presence only — enforcement mode requires an HTTPS-fetched policy file, out of scope for a passive-DNS-only scanner) | 2,537 | 0.1% |
| TLS-RPT | 2,728 | 0.2% |
| CAA (certificate authority authorization — general domain/TLS security, not email-specific) | 26,279 | 1.5% |
| TLSA/DANE for SMTP | 654,920 | 38.33% |

TLSA's 38.33% figure is not broadly-based adoption — it's concentrated among a small number of dominant Swiss shared-hosting providers who have evidently enabled DANE platform-wide for their customers, not a signal of widespread deliberate configuration.

## Dangling MX (per-host, unresolvable A/AAAA)

| Metric | Count | % |
|---|---|---|
| Domains with at least one unresolvable MX host | 38,351 | 2.24% of MX domains |

A host is flagged only on confirmed non-existence (NXDOMAIN) or a clean absence of both A and AAAA records — a transient DNS error never counts as a false-positive "dangling" finding.

## Notes on methodology

- SPF's lookup-mechanism count is a rough, top-level count only — it does not recursively resolve `include:`/`redirect=` chains, so a domain can genuinely exceed RFC 7208's 10-lookup limit while `spf_near_limit` stays unset. Full recursive evaluation is deliberately out of scope for this scanner.
- DKIM detection is a provider-aware selector guess (Microsoft 365, Google Workspace get their standardized selectors; everything else is checked against 12 commonly-observed selector names) — not exhaustive, so `has_dkim` numbers are a lower bound.
- The 5.5% error rate is DNS-side (predominantly SERVFAIL from broken authoritative nameservers on the domain operator's side), not a scanner or infrastructure issue — verified directly via manual `dig` queries against a sample of erroring domains.
- No individual domain names are published in these results — everything above is aggregate only.
