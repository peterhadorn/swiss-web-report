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
    r["has_canonical"] = 'rel="canonical"' in html_lower or "rel='canonical'" in html_lower
    r["has_viewport"] = 'name="viewport"' in html_lower
    r["has_hreflang"] = "hreflang" in html_lower
    r["has_og"] = 'property="og:' in html_lower or "property='og:" in html_lower

    # --- AI Readiness (from HTML) ---
    has_jsonld = "application/ld+json" in html_lower
    has_microdata = 'itemtype="http' in html_lower and "schema.org" in html_lower
    has_rdfa = 'vocab="' in html_lower and "schema.org" in html_lower
    r["has_schema"] = has_jsonld or has_microdata or has_rdfa
    if r["has_schema"]:
        types = set()
        # JSON-LD @type
        types.update(re.findall(r'"@type"\s*:\s*"([^"]+)"', html))
        # Microdata itemtype
        types.update(
            t.split("/")[-1]
            for t in re.findall(r'itemtype="https?://schema\.org/([^"]+)"', html)
        )
        r["schema_types"] = list(types)
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
        "cookieyes": "cookieyes",
        "iubenda": "iubenda",
        "didomi": "didomi",
        "quantcast": "quantcast",
        "trustarc": "trustarc",
        "axeptio": "axeptio",
        "tarteaucitron": "tarteaucitron",
    }
    for provider, pattern in cookie_patterns.items():
        if pattern in html_lower:
            r["has_cookie_banner"] = True
            r["cookie_provider"] = provider
            break

    return r


def find_legal_links(html: str) -> dict:
    """Scan homepage for links to impressum/datenschutz pages in all 4 languages."""
    tree = HTMLParser(html)
    result = {"impressum": [], "datenschutz": []}

    impressum_terms = [
        "impressum", "imprint", "legal notice", "legal-notice",
        "mentions légales", "mentions-legales", "mentions legales",
        "note legali", "note-legali",
    ]
    # Exclude false positives like "Impressionen" (photo galleries)
    impressum_exclude = ["impressionen", "impressions"]
    datenschutz_terms = [
        "datenschutz", "privacy", "data protection", "data-protection",
        "politique de confidentialité", "confidentialite",
        "protection des données", "protection-des-donnees",
        "protezione dati", "protezione-dati", "informativa-privacy",
    ]

    for a in tree.css("a[href]"):
        href = a.attributes.get("href", "").strip()
        if not href or href == "#":
            continue
        text = a.text(strip=True).lower()
        href_lower = href.lower()
        check = text + " " + href_lower

        if any(t in check for t in impressum_terms) and not any(ex in check for ex in impressum_exclude):
            result["impressum"].append(href)
        if any(t in check for t in datenschutz_terms):
            result["datenschutz"].append(href)

    return result


def parse_impressum(html: str) -> dict:
    """Check impressum page for required legal elements."""
    html_lower = html.lower()

    # Email: check mailto: links AND plain text emails
    has_email = bool(
        "mailto:" in html_lower
        or re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
    )

    # Address: Swiss postal code (4 digits) followed by a city name (word starting uppercase)
    # This avoids matching years (2024) or prices (3500 CHF)
    has_address = bool(
        re.search(r'\b(CH-)?\d{4}\s+[A-ZÄÖÜ][a-zäöüéèê]+', html)
    )

    return {
        "impressum_has_email": has_email,
        "impressum_has_address": has_address,
    }


def parse_robots_txt(text: str) -> dict:
    """Extract signals from robots.txt."""
    text_lower = text.lower()

    has_sitemap = "sitemap:" in text_lower

    # Check if site blocks ALL bots via User-agent: *
    blocks_all = False
    wildcard_section = re.search(
        r"user-agent:\s*\*.*?(?=user-agent:|\Z)",
        text_lower, re.DOTALL,
    )
    if wildcard_section:
        section = wildcard_section.group()
        # Blocks all if "Disallow: /" without any "Allow:" that opens things up
        if re.search(r"disallow:\s*/\s*$", section, re.MULTILINE):
            has_allow = bool(re.search(r"allow:\s*/\S", section))
            if not has_allow:
                blocks_all = True

    ai_bots_blocked = []
    ai_bots = [
        "gptbot", "claudebot", "ccbot", "google-extended",
        "anthropic", "bytespider", "chatgpt-user",
        "amazonbot", "cohere-ai", "meta-externalagent",
    ]
    for bot in ai_bots:
        if bot in text_lower:
            # Check if actually disallowed
            bot_section = re.search(
                rf"user-agent:\s*{bot}.*?(?=user-agent:|\Z)",
                text_lower, re.DOTALL,
            )
            if bot_section and re.search(r"disallow:\s*/", bot_section.group()):
                ai_bots_blocked.append(bot)

    return {
        "has_sitemap": has_sitemap,
        "blocks_ai_bots": ai_bots_blocked,
        "blocks_all_bots": blocks_all,
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
        if "et-divi" in html_lower or "divi-engine" in html_lower or "divi_theme" in html_lower or '"divi"' in html_lower:
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
    if "neos" in gen_lower or "neos-nodetypes" in html_lower:
        return "neos", ""
    if "sitecore" in html_lower:
        return "sitecore", ""
    if "hubspot" in html_lower and ("hs-script" in html_lower or "hubspot.com" in html_lower):
        return "hubspot", ""
    if "strato" in html_lower and "website-editor" in html_lower:
        return "strato", ""

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
