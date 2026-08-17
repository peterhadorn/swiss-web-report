import sqlite3

from dmarc_scan import load_domains, run
from dmarc_scanner.db import get_done_domains


def test_load_domains_strips_blank_lines_and_trailing_dots(tmp_path):
    domains_file = tmp_path / "domains.txt"
    domains_file.write_text("a.ch\n\nb.ch.\n  \nc.ch\n")

    assert load_domains(str(domains_file)) == ["a.ch", "b.ch", "c.ch"]


def _fake_query_factory():
    """Every domain: MX -> a self-hosted host, DS -> noanswer, everything
    else -> noanswer. Enough to exercise the full run() path without any
    real network access."""

    def query(name, rdtype):
        if rdtype == "MX":
            base = name
            return "ok", [f"10 mail.{base}."]
        return "noanswer", []

    return query


def test_run_writes_all_domains_to_db(tmp_path):
    db_path = str(tmp_path / "dmarc.db")
    run(["a.ch", "b.ch"], db_path, concurrency=2, query_fn=_fake_query_factory())

    conn = sqlite3.connect(db_path)
    assert get_done_domains(conn) == {"a.ch", "b.ch"}
    conn.close()


def test_run_resumes_and_skips_already_scanned_domains(tmp_path):
    db_path = str(tmp_path / "dmarc.db")

    calls = []

    def counting_query(name, rdtype):
        calls.append((name, rdtype))
        if rdtype == "MX":
            return "ok", [f"10 mail.{name}."]
        return "noanswer", []

    run(["a.ch", "b.ch"], db_path, concurrency=2, query_fn=counting_query)
    calls.clear()

    run(["a.ch", "b.ch", "c.ch"], db_path, concurrency=2, query_fn=counting_query)

    domains_queried_for_mx = {name for name, rdtype in calls if rdtype == "MX"}
    assert domains_queried_for_mx == {"c.ch"}

    conn = sqlite3.connect(db_path)
    assert get_done_domains(conn) == {"a.ch", "b.ch", "c.ch"}
    conn.close()


def test_run_retries_domains_that_previously_errored(tmp_path):
    # Regression test for the resumability fix: a domain that errored on one
    # run must be retried (not silently skipped) on the next.
    db_path = str(tmp_path / "dmarc.db")

    def failing_query(name, rdtype):
        return "error", []

    run(["flaky.ch"], db_path, concurrency=1, query_fn=failing_query)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT error, has_mx FROM dmarc_scan_results WHERE domain = 'flaky.ch'"
    ).fetchone()
    assert row[0] == "mx_query_error"
    conn.close()

    def succeeding_query(name, rdtype):
        if rdtype == "MX":
            return "ok", [f"10 mail.{name}."]
        return "noanswer", []

    run(["flaky.ch"], db_path, concurrency=1, query_fn=succeeding_query)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT error, has_mx FROM dmarc_scan_results WHERE domain = 'flaky.ch'"
    ).fetchone()
    assert row[0] == ""
    assert row[1] == 1
    conn.close()
