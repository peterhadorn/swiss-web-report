"""Swiss email-security scanner — passive DNS-only entry point.

Usage:
    python3 dmarc_scan.py --input data/ch_domains.txt --output data/dmarc_scan_results.db --limit 100
    python3 dmarc_scan.py --input data/ch_domains.txt --output data/dmarc_scan_results.db --concurrency 300
"""

import argparse
import concurrent.futures
import json
import logging
import random
import sqlite3
import time
from pathlib import Path

from dmarc_scanner.db import create_table, get_done_domains, insert_result
from dmarc_scanner.resolve import query as real_query
from dmarc_scanner.scan import scan_domain

logger = logging.getLogger(__name__)

BATCH_SIZE = 2000
REPORT_EVERY = 2000


def _health_path_for(db_path: str) -> str:
    path = Path(db_path)
    return str(path.with_name(f"{path.stem}_health.json"))


def run(
    domains: list,
    db_path: str,
    concurrency: int = 300,
    resume: bool = True,
    query_fn=None,
):
    """Scan all domains with a thread-pool concurrency limit, write to SQLite."""
    query_fn = query_fn or real_query

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    if not resume:
        conn.execute("DROP TABLE IF EXISTS dmarc_scan_results")
        conn.commit()
        logger.info("Starting fresh: cleared existing dmarc_scan_results table")
    create_table(conn)

    db_total_scanned = conn.execute("SELECT COUNT(*) FROM dmarc_scan_results").fetchone()[0]

    if resume:
        done = get_done_domains(conn)
        before = len(domains)
        domains = [d for d in domains if d not in done]
        logger.info(f"Resume: {len(done)} done, {len(domains)} remaining (of {before})")

    total = len(domains)
    if total == 0:
        logger.info("Nothing to scan.")
        conn.close()
        return

    scanned = 0
    mx_found = 0
    errors = 0
    start_time = time.monotonic()
    health_path = _health_path_for(db_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        i = 0
        while i < total:
            batch = domains[i:i + BATCH_SIZE]
            futures = {pool.submit(scan_domain, d, query_fn): d for d in batch}

            for future in concurrent.futures.as_completed(futures):
                domain = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    errors += 1
                    logger.warning(f"Failed {domain}: {exc}")
                    continue

                insert_result(conn, result)
                scanned += 1
                if result.has_mx:
                    mx_found += 1
                if result.error:
                    errors += 1

                if scanned % REPORT_EVERY == 0:
                    elapsed = time.monotonic() - start_time
                    rate = scanned / elapsed if elapsed > 0 else 0
                    eta_min = (total - scanned) / rate / 60 if rate > 0 else 0
                    total_scanned = db_total_scanned + scanned
                    logger.info(
                        f"{scanned}/{total} ({scanned/total*100:.1f}%) "
                        f"mx_found={mx_found} rate={rate:.0f}/s ETA={eta_min:.0f}m errors={errors}"
                    )
                    with open(health_path, "w") as hf:
                        json.dump({
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "scanned": total_scanned,
                            "total": total + db_total_scanned,
                            "mx_found": mx_found,
                            "errors": errors,
                            "rate": round(rate, 1),
                            "eta_min": round(eta_min),
                        }, hf)
                    conn.commit()

            conn.commit()
            i += BATCH_SIZE

    conn.commit()
    conn.close()

    elapsed = time.monotonic() - start_time
    logger.info(
        f"Done: {scanned} domains in {elapsed/60:.1f}m. "
        f"MX found: {mx_found} ({mx_found/max(scanned,1)*100:.1f}%) Errors: {errors}"
    )


def load_domains(path: str) -> list:
    """Load domains from file, strip trailing dots and blank lines."""
    domains = []
    with open(path) as f:
        for line in f:
            d = line.strip().rstrip(".")
            if d:
                domains.append(d)
    return domains


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Swiss Email Security Scanner (passive DNS-only)")
    parser.add_argument("--input", required=True, help="Domain list file")
    parser.add_argument("--output", default="data/dmarc_scan_results.db", help="SQLite output")
    parser.add_argument("--concurrency", type=int, default=300)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--shuffle", action="store_true", help="Randomize domain order (seed=42)")
    parser.add_argument("--limit", type=int, help="Limit domains (testing)")

    args = parser.parse_args()

    domains = load_domains(args.input)
    if args.shuffle:
        random.seed(42)
        random.shuffle(domains)
    if args.limit:
        domains = domains[:args.limit]

    logger.info(f"Loaded {len(domains)} domains, concurrency={args.concurrency}")

    run(
        domains,
        args.output,
        concurrency=args.concurrency,
        resume=not args.no_resume,
    )


if __name__ == "__main__":
    main()
