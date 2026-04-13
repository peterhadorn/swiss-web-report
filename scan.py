"""Swiss Web Report 2026 — Main scanner entry point.

Usage:
    python3 scan.py --input domains.txt --output results.db --concurrency 200
    python3 scan.py --input domains.txt --output results.db --limit 100  # test run
"""

import argparse
import asyncio
import logging
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
    start_time = time.monotonic()

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
            nonlocal scanned, active, errors
            async with semaphore:
                try:
                    result = await scan_domain(session, domain)
                    insert_result(conn, result)
                    scanned += 1
                    if result.is_active:
                        active += 1
                except Exception as exc:
                    errors += 1
                    logger.warning(f"Failed {domain}: {exc}")
                    return

                if scanned % REPORT_EVERY == 0:
                    elapsed = time.monotonic() - start_time
                    rate = scanned / elapsed
                    eta_min = (total - scanned) / rate / 60 if rate > 0 else 0
                    logger.info(
                        f"{scanned}/{total} ({scanned/total*100:.1f}%) "
                        f"active={active} "
                        f"rate={rate:.0f}/s "
                        f"ETA={eta_min:.0f}m"
                    )
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
    parser.add_argument("--limit", type=int, help="Limit domains (testing)")

    args = parser.parse_args()

    domains = load_domains(args.input)
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
