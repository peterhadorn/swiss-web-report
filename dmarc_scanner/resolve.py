"""Real DNS resolution — public resolvers only, never the domain's own servers.

One `dns.resolver.Resolver` per thread (thread-local): dnspython Resolver
objects are not safe to share a cache across threads under this concurrency
model, so each worker thread lazily builds and reuses its own.
"""

import threading

import dns.exception
import dns.resolver

PUBLIC_NAMESERVERS = ["1.1.1.1", "8.8.8.8", "9.9.9.9", "1.0.0.1", "8.8.4.4"]
QUERY_TIMEOUT = 4.0   # per-nameserver-attempt timeout, seconds
QUERY_LIFETIME = 6.0  # total budget across nameserver retries, seconds

_thread_local = threading.local()


def _make_resolver() -> "dns.resolver.Resolver":
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = list(PUBLIC_NAMESERVERS)
    # Spread queries across all 5 resolvers instead of hammering the first
    # one in the list — dnspython defaults to trying nameservers in a fixed
    # order otherwise.
    resolver.rotate = True
    resolver.timeout = QUERY_TIMEOUT
    resolver.lifetime = QUERY_LIFETIME
    resolver.cache = None
    return resolver


def _get_thread_resolver():
    resolver = getattr(_thread_local, "resolver", None)
    if resolver is None:
        resolver = _make_resolver()
        _thread_local.resolver = resolver
    return resolver


def _txt_to_text(rdata) -> str:
    return b"".join(rdata.strings).decode("utf-8", errors="replace")


def query(name: str, rdtype: str) -> tuple:
    """Run one DNS query. Returns (status, answers).

    status: "ok" | "nxdomain" | "noanswer" | "error"
    answers: list of plain strings (TXT segments already joined), [] unless "ok"
    """
    resolver = _get_thread_resolver()
    try:
        answer = resolver.resolve(name, rdtype, raise_on_no_answer=True)
    except dns.resolver.NXDOMAIN:
        return "nxdomain", []
    except dns.resolver.NoAnswer:
        return "noanswer", []
    except Exception:
        return "error", []

    if rdtype == "TXT":
        return "ok", [_txt_to_text(r) for r in answer]
    return "ok", [str(r) for r in answer]
