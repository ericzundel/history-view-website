from datetime import UTC, datetime, timedelta, timezone
from ipaddress import ip_address

import pytest
from lib.utils import (
    coerce_str,
    ensure_list,
    ensure_mapping,
    extract_domain,
    is_ip_or_local,
    is_private_ip,
    merge_lists,
    normalize_domain,
    normalize_epoch,
    normalize_tag,
    normalize_timestamp,
    parse_datetime,
)


def test_normalize_domain() -> None:
    assert normalize_domain("example.com") == "example.com"
    assert normalize_domain("sub.example.com") == "sub.example.com"
    assert normalize_domain("http://WWW.EXAMPLE.COM/foo?bar") == "www.example.com"
    assert normalize_domain(None) is None


def test_normalize_epoch_thresholds() -> None:
    assert normalize_epoch(1_700_000_000.0) == 1_700_000_000.0
    assert normalize_epoch(1_700_000_000_000.0) == 1_700_000_000.0
    assert normalize_epoch(1_700_000_000_000_000.0) == 1_700_000_000.0


def test_parse_datetime_accepts_datetime() -> None:
    original = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    assert parse_datetime(original) is original


def test_parse_datetime_parses_numeric_and_string() -> None:
    parsed_epoch = parse_datetime(1_717_245_296)
    assert parsed_epoch == datetime(2024, 6, 1, 12, 34, 56, tzinfo=UTC)

    parsed_millis = parse_datetime("1717245296000")
    assert parsed_millis == datetime(2024, 6, 1, 12, 34, 56, tzinfo=UTC)

    parsed_iso = parse_datetime("2024-06-01T12:34:56Z")
    assert parsed_iso == datetime(2024, 6, 1, 12, 34, 56, tzinfo=UTC)


def test_parse_datetime_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="Unable to parse timestamp"):
        parse_datetime("not-a-date")

    with pytest.raises(ValueError, match="Unsupported timestamp value"):
        parse_datetime(object())


def test_is_private_ip_flags_private_loopback_link_local() -> None:
    assert is_private_ip(ip_address("10.0.0.1"))
    assert is_private_ip(ip_address("127.0.0.1"))
    assert is_private_ip(ip_address("169.254.1.1"))
    assert not is_private_ip(ip_address("8.8.8.8"))


def test_is_ip_or_local_detects_ip_and_sentinel() -> None:
    assert is_ip_or_local("local_development")
    assert is_ip_or_local("10.0.0.1")
    assert is_ip_or_local("2001:db8::1")
    assert not is_ip_or_local("example.com")


def test_extract_domain_handles_ports_and_credentials() -> None:
    assert extract_domain("https://user:pass@www.example.com:8443/path") == "example.com"
    assert extract_domain("example.com/path") == "example.com"
    assert extract_domain("http://192.168.1.5/page") == "local_development"


def test_extract_domain_rejects_empty() -> None:
    with pytest.raises(ValueError, match="Could not extract domain"):
        extract_domain("   ")


def test_normalize_timestamp_handles_naive_and_offset() -> None:
    naive = datetime(2024, 6, 1, 12, 34, 56)
    assert normalize_timestamp(naive) == "2024-06-01 12:34:56"

    offset = datetime(2024, 6, 1, 7, 34, 56, tzinfo=timezone(timedelta(hours=-5)))
    assert normalize_timestamp(offset) == "2024-06-01 12:34:56"


def test_normalize_tag_strips_hash_and_whitespace() -> None:
    assert normalize_tag(None) is None
    assert normalize_tag("") is None
    assert normalize_tag("  #News ") == "news"
    assert normalize_tag("Tech") == "tech"


def test_ensure_mapping_and_list_validate_types() -> None:
    assert ensure_mapping({"a": 1}, context="mapping") == {"a": 1}
    assert ensure_list([1, 2], context="list") == [1, 2]
    with pytest.raises(ValueError, match="Expected mapping"):
        ensure_mapping(["nope"], context="mapping")
    with pytest.raises(ValueError, match="Expected list"):
        ensure_list({"nope": 1}, context="list")


def test_coerce_str_handles_none_and_whitespace() -> None:
    assert coerce_str(None) is None
    assert coerce_str("   ") is None
    assert coerce_str(" ok ") == "ok"
    assert coerce_str(123) == "123"


def test_merge_lists_dedupes_and_sorts() -> None:
    assert merge_lists(["b", "a"], ["b", "c"]) == ["a", "b", "c"]
    assert merge_lists([], ["z", "y"]) == ["y", "z"]
