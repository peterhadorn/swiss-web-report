"""Analyze the passive DNS email-security scan results.

Usage:
    python3 analyze_dmarc.py data/dmarc_scan_results.db
"""

import argparse
from pathlib import Path
import sqlite3


def _c(conn, where: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM dmarc_scan_results WHERE {where}").fetchone()[0]


def _stat(conn, denom: int, where: str, label: str, base_where: str = "1=1"):
    n = _c(conn, f"({base_where}) AND ({where})")
    pct = (n / denom * 100) if denom else 0.0
    print(f"  {label}: {n:,} ({pct:.1f}%)")


def _section(title: str):
    print(f"\n--- {title} ---")


def analyze(db_path: str):
    if db_path != ":memory:" and not Path(db_path).exists():
        raise SystemExit(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "dmarc_scan_results" not in tables:
        conn.close()
        raise SystemExit(f"Database has no dmarc_scan_results table: {db_path}")

    raw_total = _c(conn, "1=1")
    if raw_total == 0:
        print("No domains found.")
        conn.close()
        return

    # Errored rows (DNS query failed) get retried on the next scan run — see
    # dmarc_scanner/db.py's get_done_domains. Excluding them here keeps
    # every percentage below scoped to domains we actually got an answer
    # for, instead of silently inflating "no MX" / "not signed" buckets.
    error_count = _c(conn, "error != ''")
    total = raw_total - error_count

    print("=" * 60)
    print("SWISS EMAIL SECURITY BAROMETER")
    print("=" * 60)
    print(f"\nTotal rows in DB: {raw_total:,}")
    if error_count:
        pct = error_count / raw_total * 100
        print(f"  Errored (excluded below, retried on next scan run): {error_count:,} ({pct:.1f}%)")
    print(f"Analyzable domains: {total:,}")

    if total == 0:
        print("\nNothing analyzable yet.")
        conn.close()
        return

    mx = _c(conn, "has_mx = 1")
    print(f"Domains with MX (set up for email): {mx:,} ({mx/total*100:.1f}%)")

    _section("DNSSEC (all analyzable domains)")
    _stat(conn, total, "dnssec_signed = 1", "DNSSEC signed")

    if mx == 0:
        print("\nNo domains with MX found.")
        conn.close()
        return

    _section("MX PROVIDER (of domains with MX)")
    for provider, count in conn.execute(
        "SELECT mx_provider, COUNT(*) c FROM dmarc_scan_results "
        "WHERE has_mx = 1 GROUP BY mx_provider ORDER BY c DESC"
    ).fetchall():
        pct = count / mx * 100
        print(f"  {provider or '(unknown)'}: {count:,} ({pct:.1f}%)")

    _section("SPF (of domains with MX)")
    _stat(conn, mx, "has_spf = 1", "Has SPF", base_where="has_mx = 1")
    for mechanism in ["hardfail", "softfail", "neutral", "pass", "none"]:
        _stat(conn, mx, f"spf_all_mechanism = '{mechanism}'", f"  all={mechanism}", base_where="has_mx = 1")
    _stat(conn, mx, "spf_near_limit = 1",
          "SPF lookup mechanisms >= 8 (rough, top-level count — not recursive)",
          base_where="has_mx = 1")

    _section("DKIM (of domains with MX, provider-aware guess only)")
    _stat(conn, mx, "has_dkim = 1", "DKIM selector found", base_where="has_mx = 1")

    _section("DMARC (of domains with MX)")
    _stat(conn, mx, "has_dmarc = 1", "Has DMARC record", base_where="has_mx = 1")
    for policy in ["reject", "quarantine", "none", "absent"]:
        _stat(conn, mx, f"dmarc_policy = '{policy}'", f"  policy={policy}", base_where="has_mx = 1")
    unprotected = _c(conn, "has_mx = 1 AND (dmarc_policy = 'absent' OR dmarc_policy = 'none')")
    print(f"  UNPROTECTED (absent or monitoring-only): {unprotected:,} ({unprotected/mx*100:.1f}%)")
    print(f"  -> cold-outreach / lead-list size: {unprotected:,}")

    _section("BIMI / MTA-STS / TLS-RPT / CAA (of domains with MX)")
    _stat(conn, mx, "has_bimi = 1", "BIMI", base_where="has_mx = 1")
    _stat(conn, mx, "has_mta_sts = 1", "MTA-STS", base_where="has_mx = 1")
    _stat(conn, mx, "has_tlsrpt = 1", "TLS-RPT", base_where="has_mx = 1")
    _stat(conn, mx, "has_caa = 1", "CAA", base_where="has_mx = 1")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Analyze dmarc_scan_results.db")
    parser.add_argument("db_path")
    args = parser.parse_args()
    analyze(args.db_path)


if __name__ == "__main__":
    main()
