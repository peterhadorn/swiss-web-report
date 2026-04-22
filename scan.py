"""Swiss Web Report 2026 — Main scanner entry point.

Usage:
    python3 scan.py --input domains.txt --output results.db --concurrency 50
    python3 scan.py --input domains.txt --output results.db --limit 100  # test run
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
import random
import sqlite3
import time

import aiohttp
from aiohttp.resolver import AsyncResolver

from scanner.db import create_table, get_done_domains, insert_result
from scanner.scan import scan_domain, TIMEOUT, HEADERS

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000  # commit every N results
REPORT_EVERY = 1000  # log progress every N results
CIRCUIT_BREAKER_THRESHOLD = 2  # consecutive 0% batches before pausing
HEALTH_CHECK_DOMAINS = ["google.com", "sbb.ch", "admin.ch"]
PAUSE_SECONDS = 30  # how long to wait before retrying after network failure
SESSION_RECYCLE_SECS = 900  # recreate session every 15 min to prevent stale connections
DNS_SERVERS = ["1.1.1.1", "8.8.8.8", "9.9.9.9", "1.0.0.1", "8.8.4.4"]


def _health_path_for(db_path: str) -> str:
    """Return a sidecar health-file path without risking DB overwrite."""
    path = Path(db_path)
    return str(path.with_name(f"{path.stem}_health.json"))


async def _check_connectivity(timeout: aiohttp.ClientTimeout, headers: dict) -> bool:
    """Test if we can reach known-good domains. Creates a fresh session with own resolver."""
    try:
        resolver = AsyncResolver(nameservers=list(DNS_SERVERS))
        conn = aiohttp.TCPConnector(limit=5, ttl_dns_cache=0, resolver=resolver)
        async with aiohttp.ClientSession(
            connector=conn, timeout=timeout, headers=headers,
        ) as test_session:
            for domain in HEALTH_CHECK_DOMAINS:
                try:
                    async with test_session.get(f"https://{domain}") as resp:
                        if resp.status > 0:
                            return True
                except Exception:
                    continue
    except Exception:
        pass
    return False


def _create_connector(concurrency: int) -> aiohttp.TCPConnector:
    """Create a fresh TCP connector with async DNS resolver."""
    resolver = AsyncResolver(nameservers=list(DNS_SERVERS))
    return aiohttp.TCPConnector(
        limit=concurrency,
        ttl_dns_cache=300,
        enable_cleanup_closed=True,
        resolver=resolver,
    )


async def run(
    domains: list[str],
    db_path: str,
    concurrency: int = 50,
    resume: bool = True,
):
    """Scan all domains with concurrency limit, write to SQLite."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    if not resume:
        conn.execute("DROP TABLE IF EXISTS scan_results")
        conn.commit()
        logger.info("Starting fresh: cleared existing scan_results table")
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
    health_path = _health_path_for(db_path)
    zero_batches = 0  # consecutive batches with 0% active

    session = None
    current_connector = None
    session_created_at = time.monotonic()

    async def create_session():
        nonlocal session, current_connector, session_created_at
        if session and not session.closed:
            await session.close()
        current_connector = _create_connector(concurrency)
        session = aiohttp.ClientSession(
            connector=current_connector,
            timeout=TIMEOUT,
            headers=HEADERS,
        )
        session_created_at = time.monotonic()
        return session

    await create_session()

    try:
        semaphore = asyncio.Semaphore(concurrency)

        # Circuit breaker state — set by scan_one, checked by outer loop
        circuit_break_needed = False

        async def scan_one(domain: str):
            nonlocal scanned, active, errors, batch_active, batch_scanned
            nonlocal hour_active, hour_scanned, hour_reset
            nonlocal zero_batches, circuit_break_needed
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

                    # Circuit breaker: check BEFORE resetting counters
                    if batch_active == 0 and batch_scanned >= REPORT_EVERY:
                        zero_batches += 1
                        logger.warning(
                            f"Zero active batch detected ({zero_batches}/{CIRCUIT_BREAKER_THRESHOLD})"
                        )
                        if zero_batches >= CIRCUIT_BREAKER_THRESHOLD:
                            circuit_break_needed = True
                    else:
                        zero_batches = 0

                    batch_active = 0
                    batch_scanned = 0
                    conn.commit()

        # Process in batches to avoid creating millions of coroutines at once
        i = 0
        while i < total:
            batch = domains[i:i + BATCH_SIZE]
            circuit_break_needed = False
            tasks = [scan_one(d) for d in batch]
            await asyncio.gather(*tasks)
            conn.commit()

            if circuit_break_needed:
                logger.warning(
                    f"CIRCUIT BREAKER TRIGGERED: {zero_batches} consecutive batches "
                    f"with 0% active. Pausing..."
                )
                # Collect domains from zero-active batches + current batch
                rewind_count = zero_batches + 1  # +1 for current batch
                bad_domains = []
                for j in range(rewind_count):
                    start_idx = i - j * BATCH_SIZE
                    if start_idx >= 0:
                        bad_domains.extend(domains[start_idx:start_idx + BATCH_SIZE])
                if bad_domains:
                    placeholders = ",".join("?" * len(bad_domains))
                    deleted = conn.execute(
                        f"DELETE FROM scan_results WHERE domain IN ({placeholders})",
                        bad_domains,
                    ).rowcount
                    conn.commit()
                    scanned -= deleted
                    logger.info(f"Deleted {deleted} unreliable results from {rewind_count} batches")

                # Wait for connectivity to return
                while True:
                    ok = await _check_connectivity(TIMEOUT, HEADERS)
                    if ok:
                        logger.info("Connectivity restored. Recreating session and resuming...")
                        await create_session()
                        # Rewind to re-scan deleted batches (before resetting zero_batches)
                        i = max(0, i - rewind_count * BATCH_SIZE)
                        zero_batches = 0
                        batch_active = 0
                        batch_scanned = 0
                        break
                    logger.warning(f"No connectivity. Waiting {PAUSE_SECONDS}s...")
                    await asyncio.sleep(PAUSE_SECONDS)
                continue  # restart loop from rewound position

            # Session recycling: refresh every 15 min to prevent stale connections/DNS
            if time.monotonic() - session_created_at > SESSION_RECYCLE_SECS:
                logger.info("Recycling session (periodic refresh to keep DNS healthy)")
                await create_session()

            i += BATCH_SIZE

    finally:
        if session and not session.closed:
            await session.close()

    conn.commit()
    conn.close()

    elapsed = time.monotonic() - start_time
    logger.info(
        f"Done: {scanned} domains in {elapsed/60:.1f}m. "
        f"Active: {active} ({active/max(scanned,1)*100:.1f}%) "
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
    parser.add_argument("--concurrency", type=int, default=50)
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
