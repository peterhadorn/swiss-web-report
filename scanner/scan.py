"""Async domain scanner — core scanning logic."""

import asyncio
import logging
import time

import aiohttp

from scanner.models import ScanResult
from scanner.parsers import parse_homepage, parse_impressum, parse_robots_txt

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=10, connect=5)
HEADERS = {"User-Agent": "SwissWebReport/1.0 (research; webevolve.ch/studie/)"}
MAX_HTML_BYTES = 200_000  # 200KB max per page

IMPRESSUM_PATHS = ["/impressum", "/impressum/", "/impressum.html"]
DATENSCHUTZ_PATHS = [
    "/datenschutz", "/datenschutz/",
    "/datenschutzerklaerung", "/datenschutzerklaerung/",
    "/privacy", "/privacy-policy",
]


async def scan_domain(session: aiohttp.ClientSession, domain: str) -> ScanResult:
    """Scan a single domain: homepage + robots.txt + llms.txt + legal pages."""
    result = ScanResult(domain=domain)
    base_url = ""

    # --- 1. Homepage ---
    for scheme in ["https", "http"]:
        url = f"{scheme}://{domain}"
        try:
            t0 = time.monotonic()
            async with session.get(url, allow_redirects=True) as resp:
                result.response_time_ms = int((time.monotonic() - t0) * 1000)
                result.is_active = True
                result.status_code = resp.status
                result.has_ssl = str(resp.url).startswith("https")
                result.http_version = f"{resp.version.major}.{resp.version.minor}"
                result.server = resp.headers.get("Server", "")[:100]
                result.final_url = str(resp.url)[:200]
                result.redirects_www = "www." in str(resp.url)
                base_url = f"{resp.url.scheme}://{resp.url.host}"

                if resp.status == 200:
                    html = await resp.text(
                        encoding=resp.charset or "utf-8",
                        errors="replace",
                    )
                    html = html[:MAX_HTML_BYTES]
                    page_data = parse_homepage(html)
                    for key, value in page_data.items():
                        setattr(result, key, value)
                break  # success, don't try http fallback
        except Exception as exc:
            if scheme == "http":
                result.error = str(exc)[:200]
            continue

    if not result.is_active:
        return result

    # --- 2. robots.txt ---
    await _fetch_robots(session, base_url, result)

    # --- 3. llms.txt ---
    await _fetch_llms_txt(session, base_url, result)

    # --- 4. Impressum ---
    await _fetch_legal_page(
        session, base_url, IMPRESSUM_PATHS, "impressum", result
    )

    # --- 5. Datenschutz ---
    await _fetch_legal_page(
        session, base_url, DATENSCHUTZ_PATHS, "datenschutz", result
    )

    return result


async def _fetch_robots(
    session: aiohttp.ClientSession, base_url: str, result: ScanResult
):
    """Fetch and parse robots.txt."""
    try:
        async with session.get(f"{base_url}/robots.txt") as resp:
            if resp.status == 200:
                text = await resp.text(errors="replace")
                if text.strip() and not text.strip().startswith("<!"):
                    result.has_robots = True
                    data = parse_robots_txt(text)
                    result.has_sitemap = data["has_sitemap"]
                    result.blocks_ai_bots = data["blocks_ai_bots"]
    except Exception:
        pass


async def _fetch_llms_txt(
    session: aiohttp.ClientSession, base_url: str, result: ScanResult
):
    """Fetch and score llms.txt."""
    try:
        async with session.get(f"{base_url}/llms.txt") as resp:
            if resp.status == 200:
                text = await resp.text(errors="replace")
                if text.strip() and not text.strip().startswith("<!"):
                    result.has_llms_txt = True
                    score = 5  # exists
                    if len(text.strip()) >= 50:
                        score += 2
                    tl = text.lower()
                    if any(s in tl for s in [
                        "is a", "we are", "provides", "offers",
                        "# about", "description:",
                    ]):
                        score += 4
                    if any(s in tl for s in [
                        "service", "product", "solution", "offering",
                    ]):
                        score += 4
                    result.llms_txt_score = score
    except Exception:
        pass


async def _fetch_legal_page(
    session: aiohttp.ClientSession,
    base_url: str,
    paths: list[str],
    page_type: str,
    result: ScanResult,
):
    """Try multiple URL paths for a legal page (impressum or datenschutz)."""
    for path in paths:
        try:
            async with session.get(f"{base_url}{path}") as resp:
                if resp.status == 200:
                    if page_type == "impressum":
                        result.has_impressum = True
                        html = await resp.text(errors="replace")
                        html = html[:MAX_HTML_BYTES]
                        data = parse_impressum(html)
                        result.impressum_has_email = data["impressum_has_email"]
                        result.impressum_has_address = data["impressum_has_address"]
                    else:
                        result.has_datenschutz = True
                    return  # found it, stop trying other paths
        except Exception:
            continue
