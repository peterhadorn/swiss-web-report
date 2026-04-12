"""Data models for scan results."""

from dataclasses import dataclass, field


@dataclass
class ScanResult:
    domain: str

    # Infrastructure
    is_active: bool = False
    status_code: int = 0
    has_ssl: bool = False
    http_version: str = ""
    response_time_ms: int = 0
    server: str = ""
    redirects_www: bool = False
    final_url: str = ""

    # CMS & Tech
    cms: str = ""
    cms_version: str = ""
    ecommerce: str = ""

    # SEO Structure
    has_title: bool = False
    title_len: int = 0
    has_meta_desc: bool = False
    meta_desc_len: int = 0
    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    has_canonical: bool = False
    has_viewport: bool = False
    has_hreflang: bool = False
    language: str = ""
    has_og: bool = False

    # AI Readiness
    has_schema: bool = False
    schema_types: list = field(default_factory=list)
    has_llms_txt: bool = False
    llms_txt_score: int = 0
    has_robots: bool = False
    has_sitemap: bool = False
    blocks_ai_bots: list = field(default_factory=list)

    # Legal Compliance
    has_impressum: bool = False
    impressum_has_email: bool = False
    impressum_has_address: bool = False
    has_datenschutz: bool = False
    has_cookie_banner: bool = False
    cookie_provider: str = ""

    # Error
    error: str = ""
