"""HTML parsing and signal extraction."""

import re

from selectolax.parser import HTMLParser


def parse_homepage(html: str) -> dict:
    """Extract all data points from homepage HTML."""
    tree = HTMLParser(html)
    r: dict = {}
    html_lower = html.lower()

    # --- Language ---
    html_tag = tree.css_first("html")
    r["language"] = html_tag.attributes.get("lang", "") if html_tag else ""

    # --- CMS ---
    r["cms"], r["cms_version"] = _detect_cms(html_lower, tree)

    # --- E-commerce ---
    r["ecommerce"] = _detect_ecommerce(html_lower)

    # --- SEO Structure ---
    title = tree.css_first("title")
    if title:
        t = title.text(strip=True)
        r["has_title"] = bool(t)
        r["title_len"] = len(t)
    else:
        r["has_title"] = False
        r["title_len"] = 0

    meta_desc = tree.css_first('meta[name="description"]')
    if meta_desc:
        content = meta_desc.attributes.get("content", "")
        r["has_meta_desc"] = bool(content.strip())
        r["meta_desc_len"] = len(content)
    else:
        r["has_meta_desc"] = False
        r["meta_desc_len"] = 0

    r["h1_count"] = len(tree.css("h1"))
    r["h2_count"] = len(tree.css("h2"))
    r["h3_count"] = len(tree.css("h3"))
    r["has_canonical"] = 'rel="canonical"' in html_lower
    r["has_viewport"] = 'name="viewport"' in html_lower
    r["has_hreflang"] = "hreflang" in html_lower
    r["has_og"] = 'property="og:' in html_lower or "property='og:" in html_lower

    # --- AI Readiness (from HTML) ---
    r["has_schema"] = "application/ld+json" in html_lower
    if r["has_schema"]:
        types = re.findall(r'"@type"\s*:\s*"([^"]+)"', html)
        r["schema_types"] = list(set(types))
    else:
        r["schema_types"] = []

    # --- Cookie Banner ---
    r["has_cookie_banner"] = False
    r["cookie_provider"] = ""
    cookie_patterns = {
        "cookiebot": "cookiebot",
        "onetrust": "onetrust",
        "cookieconsent": "cookieconsent",
        "complianz": "complianz",
        "borlabs": "borlabs",
        "real_cookie_banner": "real-cookie-banner",
        "usercentrics": "usercentrics",
        "consentmanager": "consentmanager",
        "klaro": "klaro",
        "cookie_notice": "cookie-notice",
    }
    for provider, pattern in cookie_patterns.items():
        if pattern in html_lower:
            r["has_cookie_banner"] = True
            r["cookie_provider"] = provider
            break

    return r


def parse_impressum(html: str) -> dict:
    """Check impressum page for required legal elements."""
    html_lower = html.lower()

    has_email = "mailto:" in html_lower
    # Swiss postal codes: 4 digits, typically 1000-9999
    has_address = bool(re.search(r'\b[1-9]\d{3}\b', html))

    return {
        "impressum_has_email": has_email,
        "impressum_has_address": has_address,
    }


def parse_robots_txt(text: str) -> dict:
    """Extract signals from robots.txt."""
    text_lower = text.lower()

    has_sitemap = "sitemap:" in text_lower

    ai_bots_blocked = []
    ai_bots = [
        "gptbot", "claudebot", "ccbot", "google-extended",
        "anthropic", "bytespider", "chatgpt-user",
    ]
    for bot in ai_bots:
        if bot in text_lower:
            # Check if actually disallowed
            bot_section = re.search(
                rf"user-agent:\s*{bot}.*?(?=user-agent:|\Z)",
                text_lower, re.DOTALL,
            )
            if bot_section and "disallow" in bot_section.group():
                ai_bots_blocked.append(bot)

    return {
        "has_sitemap": has_sitemap,
        "blocks_ai_bots": ai_bots_blocked,
    }


def _detect_cms(html_lower: str, tree) -> tuple[str, str]:
    """Detect CMS and version from HTML."""
    generator = tree.css_first('meta[name="generator"]')
    gen = generator.attributes.get("content", "") if generator else ""
    gen_lower = gen.lower()

    if "wordpress" in gen_lower or "wp-content" in html_lower:
        v = re.search(r"wordpress\s*([\d.]+)", gen_lower)
        # Detect page builders
        if "elementor" in html_lower:
            return "wordpress_elementor", v.group(1) if v else ""
        if "divi" in html_lower:
            return "wordpress_divi", v.group(1) if v else ""
        return "wordpress", v.group(1) if v else ""
    if "typo3" in gen_lower or "typo3" in html_lower:
        return "typo3", ""
    if "joomla" in gen_lower:
        return "joomla", ""
    if "drupal" in gen_lower or "data-drupal" in html_lower:
        return "drupal", ""
    if "wix.com" in html_lower:
        return "wix", ""
    if "squarespace" in html_lower:
        return "squarespace", ""
    if "jimdo" in html_lower:
        return "jimdo", ""
    if "webflow" in html_lower:
        return "webflow", ""
    if "shopify" in html_lower:
        return "shopify", ""
    if "weebly" in html_lower:
        return "weebly", ""
    if "contao" in html_lower:
        return "contao", ""
    if "craft" in gen_lower:
        return "craft", ""
    if "ghost" in gen_lower:
        return "ghost", ""

    return "", ""


def _detect_ecommerce(html_lower: str) -> str:
    """Detect e-commerce platform."""
    if "woocommerce" in html_lower or "wc-block" in html_lower:
        return "woocommerce"
    if "shopify" in html_lower:
        return "shopify"
    if "magento" in html_lower:
        return "magento"
    if "prestashop" in html_lower:
        return "prestashop"
    return ""
