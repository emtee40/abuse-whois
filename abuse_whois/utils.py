import pathlib
from collections.abc import Callable
from functools import lru_cache
from typing import cast
from urllib.parse import urlparse

import tldextract
import validators
import yaml
from starlette.datastructures import CommaSeparatedStrings

from abuse_whois import settings


def _is_x(v: str, *, validator: Callable[[str], bool]) -> bool:
    res = validator(v)

    if isinstance(res, validators.ValidationFailure):
        return False

    return res


def is_ip_address(v: str) -> bool:
    return _is_x(v, validator=validators.ipv4) or _is_x(v, validator=validators.ipv6)  # type: ignore


def is_domain(v: str) -> bool:
    if len(v.split(".")) == 1:
        return False

    if "@" in v:
        return False

    return _is_x(v, validator=validators.domain)  # type: ignore


def is_url(v: str) -> bool:
    if not v.startswith(("http://", "https://")):
        return False

    return _is_x(v, validator=validators.url)  # type: ignore


def is_email(v: str) -> bool:
    return _is_x(v, validator=validators.email)  # type: ignore


def is_supported_address(v: str) -> bool:
    if is_domain(v) or is_ip_address(v) or is_email(v) or is_url(v):
        return True

    return False


@lru_cache(maxsize=settings.WHOIS_LOOKUP_CACHE_SIZE)
def get_registered_domain(v: str) -> str | None:
    parsed = tldextract.extract(v)

    if parsed.registered_domain == "":
        return None

    return parsed.registered_domain


def get_hostname(value: str) -> str:
    if is_ip_address(value) or is_domain(value):
        return value

    if is_email(value):
        value = f"http://{value}"

    parsed = urlparse(value)
    return parsed.hostname or value


def load_yaml(path: str | pathlib.Path) -> dict:
    with open(path) as f:
        return cast(dict, yaml.safe_load(f))


def glob_rules(
    base_directory: str | pathlib.Path,
    *,
    additional_directories: list[str] | list[pathlib.Path] | CommaSeparatedStrings,
    rule_extensions=settings.RULE_EXTENSIONS,
) -> list[pathlib.Path]:
    directories = [base_directory]
    directories.extend(additional_directories)

    directories = [pathlib.Path(d) for d in directories]

    paths: set[str] = set()
    for directory in directories:
        for extension in rule_extensions:
            paths.update([str(p) for p in directory.glob(f"*.{extension}")])

    return [pathlib.Path(p) for p in paths]
