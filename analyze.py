"""Analyze Swiss Web Report scan results.

Usage:
    python3 analyze.py results.db
"""

import sqlite3
import sys


def analyze(db_path: str):
    conn = sqlite3.connect(db_path)

    total = _c(conn, "1=1")
    active = _c(conn, "is_active = 1")
    scannable = _c(conn, "status_category = 'scannable'")

    if total == 0:
        print("No domains found.")
        conn.close()
        return

    print(f"{'='*60}")
    print("SWISS WEB REPORT 2026")
    print(f"{'='*60}")
    print(f"\nTotal .ch domains scanned: {total:,}")
    print(f"Active (any response): {active:,} ({active/total*100:.1f}%)")
    print(f"Scannable (HTTP 200): {scannable:,} ({scannable/total*100:.1f}%)")
    print(f"Inactive/dead: {total - active:,} ({(total-active)/total*100:.1f}%)")

    # Status category breakdown
    _section("DOMAIN STATUS")
    for row in conn.execute(
        "SELECT status_category, COUNT(*) c FROM scan_results "
        "GROUP BY status_category ORDER BY c DESC"
    ).fetchall():
        pct = row[1] / total * 100
        print(f"  {row[0]}: {row[1]:,} ({pct:.1f}%)")

    if scannable == 0:
        print("\nNo scannable domains found.")
        conn.close()
        return

    # All content metrics use scannable (status 200) as denominator
    _section("INFRASTRUCTURE")
    _stat(conn, scannable, "has_ssl = 1", "HTTPS")
    for v in ["2.0", "1.1"]:
        _stat(conn, scannable, f"http_version = '{v}'", f"HTTP/{v}")
    _stat(conn, scannable, "has_viewport = 1", "Mobile-ready (viewport)")
    avg = conn.execute(
        "SELECT AVG(response_time_ms) FROM scan_results "
        "WHERE status_category = 'scannable' AND response_time_ms > 0"
    ).fetchone()[0]
    if avg is not None:
        print(f"  Avg response time: {avg:.0f}ms")

    _section("CMS MARKET SHARE")
    no_cms = scannable - _c(conn, "cms != '' AND status_category = 'scannable'")
    print(f"  No CMS detected: {no_cms:,} ({no_cms/scannable*100:.1f}%)")
    rows = conn.execute(
        "SELECT cms, COUNT(*) c FROM scan_results "
        "WHERE status_category = 'scannable' AND cms != '' "
        "GROUP BY cms ORDER BY c DESC LIMIT 15"
    ).fetchall()
    for cms, cnt in rows:
        print(f"  {cms}: {cnt:,} ({cnt/scannable*100:.1f}%)")

    _section("SEO STRUCTURE")
    _stat(conn, scannable, "has_title = 1", "Title tag")
    _stat(conn, scannable, "has_meta_desc = 1", "Meta description")
    _stat(conn, scannable, "has_canonical = 1", "Canonical URL")
    _stat(conn, scannable, "has_og = 1", "Open Graph tags")
    _stat(conn, scannable, "has_hreflang = 1", "Hreflang (multilingual)")
    _stat(conn, scannable, "h1_count = 1", "Exactly 1 H1 (correct)")
    _stat(conn, scannable, "h1_count = 0", "No H1 tag")
    _stat(conn, scannable, "h1_count > 1", "Multiple H1 tags")

    _section("AI READINESS")
    _stat(conn, scannable, "has_llms_txt = 1", "Has llms.txt")
    _stat(conn, scannable, "has_schema = 1", "Has structured data")
    _stat(conn, scannable, "has_robots = 1", "Has robots.txt")
    _stat(conn, scannable, "has_sitemap = 1", "Has sitemap")
    _stat(conn, scannable, "blocks_ai_bots != '[]' AND blocks_ai_bots != ''",
          "Blocks AI bots (specific)")
    _stat(conn, scannable, "blocks_all_bots = 1", "Blocks ALL bots")

    # robots.txt/llms.txt for all active (not just scannable)
    _section("ROBOTS & LLMS (all active domains)")
    _stat(conn, active, "has_robots = 1", "Has robots.txt")
    _stat(conn, active, "has_llms_txt = 1", "Has llms.txt")

    _section("LEGAL COMPLIANCE")
    _stat(conn, scannable, "has_impressum = 1", "Has Impressum page")
    imp = _c(conn, "has_impressum = 1 AND status_category = 'scannable'")
    if imp > 0:
        imp_email = _c(conn, "impressum_has_email = 1 AND status_category = 'scannable'")
        imp_addr = _c(conn, "impressum_has_address = 1 AND status_category = 'scannable'")
        print(f"    ...with email: {imp_email:,} ({imp_email/imp*100:.1f}% of impressum pages)")
        print(f"    ...with address: {imp_addr:,} ({imp_addr/imp*100:.1f}% of impressum pages)")
    _stat(conn, scannable, "has_datenschutz = 1", "Has Datenschutzerklärung")
    _stat(conn, scannable, "has_cookie_banner = 1", "Has cookie banner")

    cookie_rows = conn.execute(
        "SELECT cookie_provider, COUNT(*) c FROM scan_results "
        "WHERE status_category = 'scannable' AND cookie_provider != '' "
        "GROUP BY cookie_provider ORDER BY c DESC LIMIT 10"
    ).fetchall()
    if cookie_rows:
        for provider, cnt in cookie_rows:
            print(f"    {provider}: {cnt:,}")

    _section("LANGUAGE")
    lang_rows = conn.execute(
        "SELECT language, COUNT(*) c FROM scan_results "
        "WHERE status_category = 'scannable' AND language != '' "
        "GROUP BY language ORDER BY c DESC LIMIT 10"
    ).fetchall()
    for lang, cnt in lang_rows:
        print(f"  {lang}: {cnt:,} ({cnt/scannable*100:.1f}%)")

    conn.close()


def _section(title: str):
    print(f"\n{'─'*60}")
    print(title)
    print(f"{'─'*60}")


def _stat(conn, denom: int, where: str, label: str):
    n = _c(conn, where)
    print(f"  {label}: {n:,} ({n/denom*100:.1f}%)")


def _c(conn, where: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM scan_results WHERE {where}").fetchone()[0]


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "results.db"
    analyze(db_path)
