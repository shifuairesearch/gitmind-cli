import os

from gmind.config import normalize_token, redact_token


def test_normalize_bearer_token_from_raw_v2():
    assert normalize_token("v2,123,343,abcdef") == "Bearer v2,123,343,abcdef"


def test_normalize_authorization_header():
    header = "Authorization:" + " " + "Bearer v2,123,343,abcdef"
    assert normalize_token(header) == "Bearer v2,123,343,abcdef"


def test_redact_token_keeps_prefix_and_tail_only():
    redacted = redact_token("Bearer " + "v2,123456,343,abcdefghijklmnopqrstuvwxyz")

    assert redacted.startswith("Bearer v2,123456")
    assert redacted.endswith("uvwxyz")
    assert "abcdefghijklmnopqrst" not in redacted
