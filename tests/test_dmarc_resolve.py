import dns.exception
import dns.resolver
import pytest

import dmarc_scanner.resolve as resolve_module
from dmarc_scanner.resolve import query


class FakeTxtRdata:
    """Mimics dnspython TXT rdata: `.strings` is a tuple of byte segments."""

    def __init__(self, *segments):
        self.strings = tuple(s.encode() for s in segments)


class FakeRdata:
    """Mimics any other rdtype: str()'s to the record's text form."""

    def __init__(self, text):
        self._text = text

    def __str__(self):
        return self._text


class FakeResolver:
    def __init__(self, effect):
        self._effect = effect

    def resolve(self, name, rdtype, raise_on_no_answer=True):
        return self._effect(name, rdtype)


def _patch_resolver(monkeypatch, effect):
    monkeypatch.setattr(resolve_module, "_get_thread_resolver", lambda: FakeResolver(effect))


def test_query_ok_txt_joins_multi_segment_strings(monkeypatch):
    _patch_resolver(monkeypatch, lambda name, rdtype: [FakeTxtRdata("v=spf1 ", "~all")])
    status, answers = query("example.ch", "TXT")
    assert status == "ok"
    assert answers == ["v=spf1 ~all"]


def test_query_ok_mx_returns_string_form(monkeypatch):
    _patch_resolver(monkeypatch, lambda name, rdtype: [FakeRdata("10 mail.example.ch.")])
    status, answers = query("example.ch", "MX")
    assert status == "ok"
    assert answers == ["10 mail.example.ch."]


def test_query_nxdomain(monkeypatch):
    def effect(name, rdtype):
        raise dns.resolver.NXDOMAIN()
    _patch_resolver(monkeypatch, effect)
    status, answers = query("does-not-exist.ch", "MX")
    assert status == "nxdomain"
    assert answers == []


def test_query_noanswer(monkeypatch):
    def effect(name, rdtype):
        raise dns.resolver.NoAnswer()
    _patch_resolver(monkeypatch, effect)
    status, answers = query("example.ch", "MX")
    assert status == "noanswer"
    assert answers == []


def test_query_timeout_is_error(monkeypatch):
    def effect(name, rdtype):
        raise dns.exception.Timeout()
    _patch_resolver(monkeypatch, effect)
    status, answers = query("example.ch", "MX")
    assert status == "error"
    assert answers == []


def test_query_unexpected_exception_degrades_to_error(monkeypatch):
    def effect(name, rdtype):
        raise RuntimeError("boom")
    _patch_resolver(monkeypatch, effect)
    status, answers = query("example.ch", "MX")
    assert status == "error"
    assert answers == []


def test_make_resolver_enables_rotation_across_nameservers():
    # Without rotate=True, dnspython always tries nameservers[0] first, so
    # ~all traffic hits one public resolver (1.1.1.1) instead of spreading
    # across the configured list — a self-inflicted rate-limit risk at
    # 250-400 concurrent threads.
    resolver = resolve_module._make_resolver()
    assert resolver.rotate is True
