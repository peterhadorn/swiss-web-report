from dmarc_scanner.providers import dkim_selectors_for_provider, fingerprint_mx_provider


def test_fingerprint_microsoft365():
    hosts = ["example-ch.mail.protection.outlook.com"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "microsoft365"


def test_fingerprint_google_workspace():
    hosts = ["aspmx.l.google.com", "alt1.aspmx.l.google.com"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "google_workspace"


def test_fingerprint_hostpoint():
    hosts = ["mx.hostpoint.ch"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "hostpoint"


def test_fingerprint_infomaniak():
    hosts = ["mail.infomaniak.com"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "infomaniak"


def test_fingerprint_cyon():
    hosts = ["mx1.cyon.ch"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "cyon"


def test_fingerprint_is_case_insensitive():
    hosts = ["EXAMPLE-CH.MAIL.PROTECTION.OUTLOOK.COM"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "microsoft365"


def test_fingerprint_self_hosted_when_mx_is_subdomain_of_own_domain():
    hosts = ["mail.example.ch"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "self_hosted"


def test_fingerprint_self_hosted_when_mx_equals_domain():
    hosts = ["example.ch"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "self_hosted"


def test_fingerprint_other_for_unrecognized_third_party():
    hosts = ["mx.somehost.example"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "other"


def test_fingerprint_uses_first_matching_host_in_list():
    hosts = ["mx.somehost.example", "aspmx.l.google.com"]
    assert fingerprint_mx_provider(hosts, "example.ch") == "google_workspace"


def test_fingerprint_does_not_false_positive_on_unrelated_substring_match():
    # "green.ch" must not match "evergreen.ch", "cyon.ch" must not match
    # "halcyon.ch" — matching requires an exact host or a dot-bounded suffix.
    assert fingerprint_mx_provider(["mail.evergreen.ch"], "example.ch") == "other"
    assert fingerprint_mx_provider(["mail.halcyon.ch"], "example.ch") == "other"


def test_dkim_selectors_microsoft365():
    assert dkim_selectors_for_provider("microsoft365") == ["selector1", "selector2"]


def test_dkim_selectors_google_workspace():
    assert dkim_selectors_for_provider("google_workspace") == ["google"]


def test_dkim_selectors_fallback_for_swiss_hosting_and_self_hosted_and_other():
    assert dkim_selectors_for_provider("hostpoint") == ["default"]
    assert dkim_selectors_for_provider("self_hosted") == ["default"]
    assert dkim_selectors_for_provider("other") == ["default"]
    assert dkim_selectors_for_provider("") == ["default"]
