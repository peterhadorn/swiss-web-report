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

    if active == 0:
        print("No active domains found.")
        conn.close()
        return

    print(f"{'='*60}")
    print("SWISS WEB REPORT 2026")
    print(f"{'='*60}")
    print(f"\nTotal .ch domains scanned: {total:,}")
    print(f"Active websites: {active:,} ({active/total*100:.1f}%)")
    print(f"Inactive/dead: {total - active:,} ({(total-active)/total*100:.1f}%)")

    _section("INFRASTRUCTURE")
    _stat(conn, active, "has_ssl = 1", "HTTPS")
    for v in ["2.0", "1.1"]:
        _stat(conn, active, f"http_version = '{v}'", f"HTTP/{v}")
    _stat(conn, active, "has_viewport = 1", "Mobile-ready (viewport)")
    avg = conn.execute(
        "SELECT AVG(response_time_ms) FROM scan_results "
        "WHERE is_active = 1 AND response_time_ms > 0"
    ).fetchone()[0]
    print(f"  Avg response time: {avg:.0f}ms")

    _section("CMS MARKET SHARE")
    no_cms = active - _c(conn, "cms != '' AND is_active = 1")
    print(f"  No CMS detected: {no_cms:,} ({no_cms/active*100:.1f}%)")
    rows = conn.execute(
        "SELECT cms, COUNT(*) c FROM scan_results "
        "WHERE is_active = 1 AND cms != '' "
        "GROUP BY cms ORDER BY c DESC LIMIT 15"
    ).fetchall()
    for cms, cnt in rows:
        print(f"  {cms}: {cnt:,} ({cnt/active*100:.1f}%)")

    _section("SEO STRUCTURE")
    _stat(conn, active, "has_title = 1", "Title tag")
    _stat(conn, active, "has_meta_desc = 1", "Meta description")
    _stat(conn, active, "has_canonical = 1", "Canonical URL")
    _stat(conn, active, "has_og = 1", "Open Graph tags")
    _stat(conn, active, "has_hreflang = 1", "Hreflang (multilingual)")
    _stat(conn, active, "h1_count = 1", "Exactly 1 H1 (correct)")
    _stat(conn, active, "h1_count = 0", "No H1 tag")
    _stat(conn, active, "h1_count > 1", "Multiple H1 tags")

    _section("AI READINESS")
    _stat(conn, active, "has_llms_txt = 1", "Has llms.txt")
    _stat(conn, active, "has_schema = 1", "Has structured data (JSON-LD)")
    _stat(conn, active, "has_robots = 1", "Has robots.txt")
    _stat(conn, active, "has_sitemap = 1", "Has sitemap (in robots.txt)")
    _stat(conn, active, "blocks_ai_bots != '[]' AND blocks_ai_bots != ''",
          "Blocks AI bots")

    _section("LEGAL COMPLIANCE")
    _stat(conn, active, "has_impressum = 1", "Has Impressum page")
    imp = _c(conn, "has_impressum = 1 AND is_active = 1")
    if imp > 0:
        imp_email = _c(conn, "impressum_has_email = 1 AND is_active = 1")
        imp_addr = _c(conn, "impressum_has_address = 1 AND is_active = 1")
        print(f"    ...with email: {imp_email:,} ({imp_email/imp*100:.1f}% of impressum pages)")
        print(f"    ...with address: {imp_addr:,} ({imp_addr/imp*100:.1f}% of impressum pages)")
    _stat(conn, active, "has_datenschutz = 1", "Has Datenschutzerklärung")
    _stat(conn, active, "has_cookie_banner = 1", "Has cookie banner")

    cookie_rows = conn.execute(
        "SELECT cookie_provider, COUNT(*) c FROM scan_results "
        "WHERE is_active = 1 AND cookie_provider != '' "
        "GROUP BY cookie_provider ORDER BY c DESC LIMIT 10"
    ).fetchall()
    if cookie_rows:
        for provider, cnt in cookie_rows:
            print(f"    {provider}: {cnt:,}")

    _section("LANGUAGE")
    lang_rows = conn.execute(
        "SELECT language, COUNT(*) c FROM scan_results "
        "WHERE is_active = 1 AND language != '' "
        "GROUP BY language ORDER BY c DESC LIMIT 10"
    ).fetchall()
    for lang, cnt in lang_rows:
        print(f"  {lang}: {cnt:,} ({cnt/active*100:.1f}%)")

    conn.close()


def _section(title: str):
    print(f"\n{'─'*60}")
    print(title)
    print(f"{'─'*60}")


def _stat(conn, active: int, where: str, label: str):
    n = _c(conn, f"{where} AND is_active = 1")
    print(f"  {label}: {n:,} ({n/active*100:.1f}%)")


def _c(conn, where: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM scan_results WHERE {where}").fetchone()[0]


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "results.db"
    analyze(db_path)
