from datetime import UTC, datetime
from ipaddress import IPv4Address, IPv6Address, ip_address
from typing import Any, cast
from urllib.parse import urlparse

import dateutil

LOCAL_DEVELOPMENT = "local_development"


def as_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def normalize_domain(raw: object) -> str | None:
    url = as_str(raw)
    if url is None:
        return None
    name = urlparse(url).hostname
    if name is None:
        name = url
    return name.strip().lower()


def normalize_epoch(value: float) -> float:
    if value > 1e14:
        return value / 1_000_000
    if value > 1e12:
        return value / 1000
    return value


def parse_datetime(raw: object) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, (int, float)):
        seconds = normalize_epoch(float(raw))
        return datetime.fromtimestamp(seconds, tz=UTC)
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.isdigit():
            seconds = normalize_epoch(float(int(stripped)))
            return datetime.fromtimestamp(seconds, tz=UTC)
        try:
            parsed: Any = dateutil.parser.parse(stripped)
            return cast(datetime, parsed)
        except dateutil.parser.ParserError as exc:
            raise ValueError(f"Unable to parse timestamp: {raw!r}") from exc
    raise ValueError(f"Unsupported timestamp value: {raw!r}")


def is_private_ip(ip_obj: IPv4Address | IPv6Address) -> bool:
    return ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local


def is_ip_or_local(domain: str) -> bool:
    if domain == LOCAL_DEVELOPMENT:
        return True
    try:
        ip_address(domain)
        return True
    except ValueError:
        return False


def extract_domain(url: str) -> str:
    candidate = url.strip()
    if "://" not in candidate:
        candidate = f"http://{candidate}"
    parsed = urlparse(candidate)
    netloc = parsed.netloc or parsed.path.split("/")[0]
    host = netloc.split("@")[-1].split(":")[0].lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        raise ValueError(f"Could not extract domain from URL: {url!r}")
    try:
        ip_obj = ip_address(host)
        if is_private_ip(ip_obj):
            return LOCAL_DEVELOPMENT
    except ValueError:
        return host
    return host


def normalize_timestamp(raw: object) -> str:
    dt = parse_datetime(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
