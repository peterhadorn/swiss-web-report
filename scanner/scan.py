"""Async domain scanner — core scanning logic."""

import logging
import time
from urllib.parse import urlparse

import aiohttp

from scanner.models import ScanResult
from scanner.parsers import (
    parse_homepage, parse_impressum, parse_robots_txt, find_legal_links,
)

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-CH,de;q=0.9,en;q=0.8",
}
MAX_HTML_BYTES = 200_000  # 200KB max per page

IMPRESSUM_PATHS = [
    # German
    "/impressum", "/impressum/",
    # French
    "/mentions-legales", "/mentions-legales/",
    "/informations-legales",
    # Italian
    "/note-legali", "/note-legali/",
    # English
    "/legal-notice", "/legal-notice/",
    "/imprint", "/imprint/",
]
DATENSCHUTZ_PATHS = [
    # German
    "/datenschutz", "/datenschutz/",
    "/datenschutzerklaerung", "/datenschutzerklaerung/",
    # French
    "/politique-de-confidentialite",
    "/protection-des-donnees",
    "/confidentialite",
    # Italian
    "/protezione-dati",
    "/informativa-privacy",
    # English
    "/privacy", "/privacy/",
    "/privacy-policy", "/privacy-policy/",
    "/data-protection",
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
                result.redirects_www = resp.url.host.startswith("www.")
                base_url = f"{resp.url.scheme}://{resp.url.host}"

                if resp.status == 200:
                    raw = await resp.content.read(MAX_HTML_BYTES)
                    charset = resp.charset or "utf-8"
                    try:
                        html = raw.decode(charset, errors="replace")
                    except (UnicodeDecodeError, LookupError):
                        html = raw.decode("utf-8", errors="replace")
                    page_data = parse_homepage(html)
                    for key, value in page_data.items():
                        setattr(result, key, value)
                    # Extract legal page links from homepage for fallback
                    result._homepage_legal_links = find_legal_links(html)
                break  # success, don't try http fallback
        except Exception as exc:
            if scheme == "http":
                result.error = str(exc)[:200]
            continue

    if not result.is_active:
        result.status_category = "inactive"
        return result

    # Classify based on status code
    code = result.status_code
    if code == 200:
        result.status_category = "scannable"
    elif code in (403, 401, 429, 407):
        result.status_category = "blocked"
    elif code == 404:
        result.status_category = "parked"
    elif code == 499 or code == 408:
        result.status_category = "timeout"
    elif code >= 500:
        result.status_category = "error"
    elif code >= 300:
        result.status_category = "redirect"
    else:
        result.status_category = "other"

    # Always check robots.txt and llms.txt regardless of status code
    if base_url:
        await _fetch_robots(session, base_url, result)
        await _fetch_llms_txt(session, base_url, result)

    if result.status_code != 200:
        return result

    # --- 4. Sitemap (direct check) ---
    await _fetch_sitemap(session, base_url, result)

    # --- 5. Impressum ---
    homepage_links = getattr(result, "_homepage_legal_links", {})
    await _fetch_legal_page(
        session, base_url, IMPRESSUM_PATHS,
        homepage_links.get("impressum", []),
        "impressum", result,
    )

    # --- 6. Datenschutz ---
    await _fetch_legal_page(
        session, base_url, DATENSCHUTZ_PATHS,
        homepage_links.get("datenschutz", []),
        "datenschutz", result,
    )

    return result


async def _fetch_robots(
    session: aiohttp.ClientSession, base_url: str, result: ScanResult
):
    """Fetch and parse robots.txt."""
    try:
        async with session.get(f"{base_url}/robots.txt") as resp:
            if resp.status == 200:
                raw = await resp.content.read(100_000)
                text = raw.decode("utf-8", errors="replace")
                if text.strip() and not text.strip().startswith("<!"):
                    result.has_robots = True
                    data = parse_robots_txt(text)
                    result.has_sitemap = data["has_sitemap"]
                    result.blocks_ai_bots = data["blocks_ai_bots"]
                    result.blocks_all_bots = data["blocks_all_bots"]
    except Exception:
        pass


async def _fetch_llms_txt(
    session: aiohttp.ClientSession, base_url: str, result: ScanResult
):
    """Fetch and score llms.txt."""
    try:
        async with session.get(f"{base_url}/llms.txt") as resp:
            if resp.status == 200:
                raw = await resp.content.read(100_000)
                text = raw.decode("utf-8", errors="replace")
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


async def _fetch_sitemap(
    session: aiohttp.ClientSession, base_url: str, result: ScanResult
):
    """Directly check /sitemap.xml if not already found via robots.txt."""
    if result.has_sitemap:
        return
    try:
        async with session.get(f"{base_url}/sitemap.xml") as resp:
            if resp.status == 200:
                raw = await resp.content.read(10_000)
                text = raw.decode("utf-8", errors="replace")
                # Must look like XML, not a 404 HTML page
                if "<?xml" in text[:200] or "<urlset" in text[:500] or "<sitemapindex" in text[:500]:
                    result.has_sitemap = True
    except Exception:
        pass


async def _fetch_legal_page(
    session: aiohttp.ClientSession,
    base_url: str,
    paths: list[str],
    homepage_discovered: list[str],
    page_type: str,
    result: ScanResult,
):
    """Try hardcoded paths, then homepage-discovered links for legal pages."""
    # Phase 1: Try hardcoded paths (light content validation to filter catch-all 200s)
    for path in paths:
        try:
            async with session.get(f"{base_url}{path}") as resp:
                if resp.status == 200:
                    raw = await resp.content.read(MAX_HTML_BYTES)
                    html = raw.decode("utf-8", errors="replace")
                    html_lower = html.lower()
                    if page_type == "impressum":
                        if not _looks_like_impressum(html_lower):
                            continue
                        result.has_impressum = True
                        data = parse_impressum(html)
                        result.impressum_has_email = data["impressum_has_email"]
                        result.impressum_has_address = data["impressum_has_address"]
                    else:
                        if not _looks_like_datenschutz(html_lower):
                            continue
                        result.has_datenschutz = True
                    return  # found it
        except Exception:
            continue

    # Phase 2: Try homepage-discovered links (same host only, need content validation)
    base_host = urlparse(base_url).hostname
    for link in homepage_discovered:
        if link.startswith("http"):
            link_host = urlparse(link).hostname
            if link_host and link_host != base_host and not link_host.endswith(f".{base_host}"):
                continue  # skip external links (e.g. policies.google.com)
            url = link
        elif link.startswith("/"):
            url = f"{base_url}{link}"
        else:
            continue
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    raw = await resp.content.read(MAX_HTML_BYTES)
                    html = raw.decode("utf-8", errors="replace")
                    html_lower = html.lower()
                    if page_type == "impressum":
                        if not _looks_like_impressum(html_lower):
                            continue
                        result.has_impressum = True
                        data = parse_impressum(html)
                        result.impressum_has_email = data["impressum_has_email"]
                        result.impressum_has_address = data["impressum_has_address"]
                    else:
                        if not _looks_like_datenschutz(html_lower):
                            continue
                        result.has_datenschutz = True
                    return  # found it
        except Exception:
            continue


def _looks_like_impressum(html_lower: str) -> bool:
    """Check if page content actually looks like an impressum."""
    keywords = [
        "impressum", "imprint", "legal notice", "mentions légales",
        "note legali", "handelsregister", "uid", "mwst", "ust-id",
        "firmensitz", "geschäftsführ",
    ]
    return any(kw in html_lower for kw in keywords)


def _looks_like_datenschutz(html_lower: str) -> bool:
    """Check if page content actually looks like a privacy page."""
    # Require at least 2 keywords to avoid false positives from catch-all 200s
    keywords = [
        "datenschutz", "privacy policy", "privacy statement",
        "protection des données", "protezione dei dati",
        "personendaten", "personenbezogen", "datenbearbeitung",
        "données personnelles", "data protection", "confidentialité",
        "datenerhebung", "personenbezogene daten",
    ]
    matches = sum(1 for kw in keywords if kw in html_lower)
    return matches >= 2
