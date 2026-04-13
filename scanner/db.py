"""SQLite storage for scan results."""

import json
import sqlite3
from dataclasses import asdict

from scanner.models import ScanResult

COLUMNS = [
    "domain TEXT PRIMARY KEY",
    "is_active INTEGER", "status_code INTEGER", "has_ssl INTEGER",
    "http_version TEXT", "response_time_ms INTEGER", "server TEXT",
    "final_host_is_www INTEGER", "final_url TEXT",
    "cms TEXT", "cms_version TEXT", "ecommerce TEXT",
    "has_title INTEGER", "title_len INTEGER",
    "has_meta_desc INTEGER", "meta_desc_len INTEGER",
    "h1_count INTEGER", "h2_count INTEGER", "h3_count INTEGER",
    "has_canonical INTEGER", "has_viewport INTEGER",
    "has_hreflang INTEGER", "language TEXT", "has_og INTEGER",
    "has_schema INTEGER", "schema_types TEXT",
    "has_llms_txt INTEGER", "llms_txt_score INTEGER",
    "has_robots INTEGER", "has_sitemap INTEGER", "blocks_ai_bots TEXT",
    "blocks_all_bots INTEGER",
    "status_category TEXT",
    "has_impressum INTEGER", "impressum_has_email INTEGER",
    "impressum_has_address INTEGER", "has_datenschutz INTEGER",
    "has_cookie_banner INTEGER", "cookie_provider TEXT",
    "error TEXT",
    "scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
]

JSON_FIELDS = {"schema_types", "blocks_ai_bots"}


def create_table(conn: sqlite3.Connection):
    """Create results table if not exists."""
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS scan_results ({', '.join(COLUMNS)})"
    )
    conn.commit()


def get_done_domains(conn: sqlite3.Connection) -> set[str]:
    """Get set of already-scanned domains for resume support."""
    cursor = conn.execute("SELECT domain FROM scan_results")
    return {row[0] for row in cursor}


def insert_result(conn: sqlite3.Connection, result: ScanResult):
    """Insert or replace a scan result."""
    d = asdict(result)
    # Remove private/temporary fields
    d = {k: v for k, v in d.items() if not k.startswith("_")}
    for key in JSON_FIELDS:
        if isinstance(d[key], (list, dict)):
            d[key] = json.dumps(d[key])
    columns = ", ".join(d.keys())
    placeholders = ", ".join(["?"] * len(d))
    conn.execute(
        f"INSERT OR REPLACE INTO scan_results ({columns}) VALUES ({placeholders})",
        list(d.values()),
    )
