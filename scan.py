"""Swiss Web Report 2026 — Main scanner entry point.

Usage:
    python3 scan.py --input domains.txt --output results.db --concurrency 200
    python3 scan.py --input domains.txt --output results.db --limit 100  # test run
"""

import argparse
import asyncio
import json
import logging
import random
import sqlite3
import time

import aiohttp

from scanner.db import create_table, get_done_domains, insert_result
from scanner.scan import scan_domain, TIMEOUT, HEADERS

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000  # commit every N results
REPORT_EVERY = 1000  # log progress every N results


async def run(
    domains: list[str],
    db_path: str,
    concurrency: int = 100,
    resume: bool = True,
):
    """Scan all domains with concurrency limit, write to SQLite."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    create_table(conn)

    # Get overall counts from DB (survives restarts)
    db_total_scanned = conn.execute("SELECT COUNT(*) FROM scan_results").fetchone()[0]
    db_total_active = conn.execute("SELECT COUNT(*) FROM scan_results WHERE is_active=1").fetchone()[0]

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
    active = 0
    errors = 0
    batch_active = 0
    batch_scanned = 0
    hour_active = 0
    hour_scanned = 0
    hour_reset = time.monotonic()
    start_time = time.monotonic()
    health_path = db_path.replace(".db", "_health.json")

    connector = aiohttp.TCPConnector(
        limit=concurrency,
        ttl_dns_cache=300,
        enable_cleanup_closed=True,
    )

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=TIMEOUT,
        headers=HEADERS,
    ) as session:

        semaphore = asyncio.Semaphore(concurrency)

        async def scan_one(domain: str):
            nonlocal scanned, active, errors, batch_active, batch_scanned
            nonlocal hour_active, hour_scanned, hour_reset
            async with semaphore:
                try:
                    result = await scan_domain(session, domain)
                    insert_result(conn, result)
                    scanned += 1
                    batch_scanned += 1
                    hour_scanned += 1
                    if result.is_active:
                        active += 1
                        batch_active += 1
                        hour_active += 1
                except Exception as exc:
                    errors += 1
                    logger.warning(f"Failed {domain}: {exc}")
                    return

                if scanned % REPORT_EVERY == 0:
                    elapsed = time.monotonic() - start_time
                    rate = scanned / elapsed
                    eta_min = (total - scanned) / rate / 60 if rate > 0 else 0
                    batch_pct = 100 * batch_active / batch_scanned if batch_scanned else 0
                    total_scanned = db_total_scanned + scanned
                    total_active = db_total_active + active
                    overall_pct = 100 * total_active / total_scanned if total_scanned else 0
                    hour_pct = 100 * hour_active / hour_scanned if hour_scanned else 0
                    # Reset hourly counters every 60 min
                    now = time.monotonic()
                    if now - hour_reset >= 3600:
                        hour_active = 0
                        hour_scanned = 0
                        hour_reset = now
                    logger.info(
                        f"{scanned}/{total} ({scanned/total*100:.1f}%) "
                        f"active={active} "
                        f"rate={rate:.0f}/s "
                        f"ETA={eta_min:.0f}m "
                        f"batch_active={batch_pct:.0f}% "
                        f"hour_active={hour_pct:.0f}% "
                        f"overall_active={overall_pct:.0f}%"
                    )
                    # Write health file
                    with open(health_path, "w") as hf:
                        json.dump({
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "scanned": total_scanned,
                            "total": total + db_total_scanned,
                            "active": total_active,
                            "errors": errors,
                            "rate": round(rate, 1),
                            "eta_min": round(eta_min),
                            "batch_active_pct": round(batch_pct, 1),
                            "hour_active_pct": round(hour_pct, 1),
                            "overall_active_pct": round(overall_pct, 1),
                        }, hf)
                    batch_active = 0
                    batch_scanned = 0
                    conn.commit()

        # Process in batches to avoid creating millions of coroutines at once
        for i in range(0, total, BATCH_SIZE):
            batch = domains[i:i + BATCH_SIZE]
            tasks = [scan_one(d) for d in batch]
            await asyncio.gather(*tasks)
            conn.commit()

    conn.commit()
    conn.close()

    elapsed = time.monotonic() - start_time
    logger.info(
        f"Done: {scanned} domains in {elapsed/60:.1f}m. "
        f"Active: {active} ({active/scanned*100:.1f}%) "
        f"Errors: {errors}"
    )


def load_domains(path: str) -> list[str]:
    """Load domains from file, strip trailing dots."""
    domains = []
    with open(path) as f:
        for line in f:
            d = line.strip().rstrip(".")
            if d:
                domains.append(d)
    return domains


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(description="Swiss Web Report Scanner")
    parser.add_argument("--input", required=True, help="Domain list file")
    parser.add_argument("--output", default="results.db", help="SQLite output")
    parser.add_argument("--concurrency", type=int, default=100)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--shuffle", action="store_true", help="Randomize domain order (seed=42)")
    parser.add_argument("--limit", type=int, help="Limit domains (testing)")

    args = parser.parse_args()

    domains = load_domains(args.input)
    if args.shuffle:
        random.seed(42)  # reproducible shuffle
        random.shuffle(domains)
    if args.limit:
        domains = domains[:args.limit]

    logger.info(f"Loaded {len(domains)} domains, concurrency={args.concurrency}")

    asyncio.run(run(
        domains,
        args.output,
        concurrency=args.concurrency,
        resume=not args.no_resume,
    ))


if __name__ == "__main__":
    main()
