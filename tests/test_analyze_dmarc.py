import sqlite3

from analyze_dmarc import analyze
from dmarc_scanner.db import create_table, insert_result
from dmarc_scanner.models import DmarcScanResult


def _seed(db_path):
    conn = sqlite3.connect(db_path)
    create_table(conn)
    rows = [
        DmarcScanResult(domain="nomail.ch", has_mx=False, dnssec_signed=False),
        # An errored row must not distort the stats below (excluded from
        # the "analyzable" denominator; it never sets has_mx/dnssec_signed).
        DmarcScanResult(domain="broken.ch", error="mx_query_error"),
        DmarcScanResult(
            domain="unprotected.ch", has_mx=True, mx_provider="hostpoint",
            has_spf=True, spf_all_mechanism="softfail",
            has_dmarc=False, dmarc_policy="absent",
        ),
        DmarcScanResult(
            domain="monitoring.ch", has_mx=True, mx_provider="microsoft365",
            has_spf=True, spf_all_mechanism="hardfail",
            has_dmarc=True, dmarc_policy="none", dmarc_rua=True,
        ),
        DmarcScanResult(
            domain="protected.ch", has_mx=True, mx_provider="google_workspace",
            has_spf=True, spf_all_mechanism="hardfail", spf_lookup_count=9,
            spf_near_limit=True, has_dkim=True,
            has_dmarc=True, dmarc_policy="reject", dmarc_rua=True, dmarc_ruf=True,
            dnssec_signed=True, has_bimi=True, has_mta_sts=True, has_tlsrpt=True,
        ),
    ]
    for row in rows:
        insert_result(conn, row)
    conn.commit()
    conn.close()


def test_analyze_reports_mx_and_dmarc_breakdown(tmp_path, capsys):
    db_path = str(tmp_path / "dmarc.db")
    _seed(db_path)

    analyze(db_path)

    out = capsys.readouterr().out
    assert "Total rows in DB: 5" in out
    assert "Analyzable domains: 4" in out
    assert "reject" in out
    assert "hostpoint" in out


def test_analyze_raises_on_missing_db(tmp_path):
    missing = str(tmp_path / "does-not-exist.db")
    try:
        analyze(missing)
        assert False, "expected SystemExit"
    except SystemExit:
        pass
