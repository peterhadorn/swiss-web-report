"""Per-domain orchestration: combine DNS lookups into one DmarcScanResult.

`query` is injected — this module never touches the network directly.
Production wiring (dmarc_scan.py) passes dmarc_scanner.resolve.query; tests
pass a fake. SPF/DKIM/DMARC/BIMI/MTA-STS/TLS-RPT/CAA are only checked for
domains that have MX records; DNSSEC is checked for every domain that exists
in DNS, since it isn't mail-specific.
"""

from dmarc_scanner.models import DmarcScanResult
from dmarc_scanner.parsers import (
    find_first, is_bimi_record, is_dkim_record, is_dmarc_record,
    is_mta_sts_record, is_spf_record, is_tlsrpt_record,
    parse_dmarc, parse_mx_answer, parse_spf,
)
from dmarc_scanner.providers import dkim_selectors_for_provider, fingerprint_mx_provider


def scan_domain(domain: str, query) -> DmarcScanResult:
    result = DmarcScanResult(domain=domain)

    mx_status, mx_answers = query(domain, "MX")
    if mx_status == "nxdomain":
        result.domain_exists = False
        return result
    if mx_status == "error":
        result.error = "mx_query_error"
        return result

    result.domain_exists = True

    if mx_status == "ok" and mx_answers:
        # Filter out RFC 7505 null MX ("0 .", parses to an empty host) — it
        # means the domain explicitly accepts no mail, not that it has one.
        hosts = [host for _, host in
                 (parse_mx_answer(raw) for raw in mx_answers) if host]
        if hosts:
            result.has_mx = True
            result.mx_hosts = hosts
            result.mx_provider = fingerprint_mx_provider(hosts, domain)

    ds_status, ds_answers = query(domain, "DS")
    result.dnssec_signed = ds_status == "ok" and bool(ds_answers)

    if not result.has_mx:
        return result

    txt_status, txt_answers = query(domain, "TXT")
    if txt_status == "ok":
        spf_raw = find_first(txt_answers, is_spf_record)
        if spf_raw:
            result.has_spf = True
            result.spf_record = spf_raw
            spf = parse_spf(spf_raw)
            result.spf_all_mechanism = spf["all_mechanism"]
            result.spf_lookup_count = spf["lookup_count"]
            result.spf_near_limit = spf["near_limit"]

    selectors = dkim_selectors_for_provider(result.mx_provider)
    result.dkim_selectors_checked = selectors
    found_selectors = []
    for selector in selectors:
        dkim_status, dkim_answers = query(f"{selector}._domainkey.{domain}", "TXT")
        if dkim_status == "ok" and find_first(dkim_answers, is_dkim_record):
            found_selectors.append(selector)
    result.dkim_selectors_found = found_selectors
    result.has_dkim = bool(found_selectors)

    dmarc_status, dmarc_answers = query(f"_dmarc.{domain}", "TXT")
    dmarc_raw = find_first(dmarc_answers, is_dmarc_record) if dmarc_status == "ok" else None
    if dmarc_raw:
        result.has_dmarc = True
        result.dmarc_record = dmarc_raw
        dmarc = parse_dmarc(dmarc_raw)
        result.dmarc_policy = dmarc["policy"]
        result.dmarc_rua = dmarc["has_rua"]
        result.dmarc_ruf = dmarc["has_ruf"]
    else:
        # No DMARC record found at all — same "not protected" bucket as a
        # record present but missing its p= tag (parse_dmarc's "absent").
        result.dmarc_policy = "absent"

    bimi_status, bimi_answers = query(f"default._bimi.{domain}", "TXT")
    if bimi_status == "ok":
        bimi_raw = find_first(bimi_answers, is_bimi_record)
        if bimi_raw:
            result.has_bimi = True
            result.bimi_record = bimi_raw

    mta_status, mta_answers = query(f"_mta-sts.{domain}", "TXT")
    if mta_status == "ok":
        mta_raw = find_first(mta_answers, is_mta_sts_record)
        if mta_raw:
            result.has_mta_sts = True
            result.mta_sts_record = mta_raw

    tlsrpt_status, tlsrpt_answers = query(f"_smtp._tls.{domain}", "TXT")
    if tlsrpt_status == "ok":
        tlsrpt_raw = find_first(tlsrpt_answers, is_tlsrpt_record)
        if tlsrpt_raw:
            result.has_tlsrpt = True
            result.tlsrpt_record = tlsrpt_raw

    caa_status, caa_answers = query(domain, "CAA")
    if caa_status == "ok" and caa_answers:
        result.has_caa = True
        result.caa_records = caa_answers

    return result
