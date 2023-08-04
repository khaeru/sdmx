import logging
from collections.abc import Iterator
from dataclasses import Field, fields
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Tuple

import requests

try:
    import requests_cache
except ImportError:  # pragma: no cover
    HAS_REQUESTS_CACHE = False
else:
    HAS_REQUESTS_CACHE = True


log = logging.getLogger(__name__)


class MaybeCachedSession(type):
    """Metaclass to inherit from :class:`requests_cache.CachedSession`, if available.

    If :mod:`requests_cache` is not installed, returns :class:`requests.Session` as a
    base class.
    """

    def __new__(cls, name, bases, dct):
        base = (
            requests.Session if not HAS_REQUESTS_CACHE else requests_cache.CachedSession
        )
        return super().__new__(cls, name, (base,), dct)


def compare(attr, a, b, strict: bool) -> bool:
    """Return :obj:`True` if ``a.attr`` == ``b.attr``.

    If strict is :obj:`False`, :obj:`None` is permissible as `a` or `b`; otherwise,
    """
    return getattr(a, attr) == getattr(b, attr) or (
        not strict and None in (getattr(a, attr), getattr(b, attr))
    )
    # if not result:
    #     log.info(f"Not identical: {attr}={getattr(a, attr)} / {getattr(b, attr)}")
    # return result


def only(iterator: Iterator) -> Any:
    """Return the only element of `iterator`, or :obj:`None`."""
    try:
        result = next(iterator)
        flag = object()
        assert flag is next(iterator, flag)
    except (StopIteration, AssertionError):
        return None  # 0 or ≥2 matches
    else:
        return result


@lru_cache()
def parse_content_type(value: str) -> Tuple[str, Dict[str, Any]]:
    """Return content type and parameters from `value`.

    Modified from :mod:`requests.util`.
    """
    tokens = value.split(";")
    content_type, params_raw = tokens[0].strip(), tokens[1:]
    params = {}
    to_strip = "\"' "

    for param in params_raw:
        k, *v = param.strip().split("=")

        if not k and not v:
            continue

        params[k.strip(to_strip).lower()] = v[0].strip(to_strip) if len(v) else True

    return content_type, params


_FIELDS_CACHE: Dict[str, List[Field]] = dict()


def direct_fields(cls) -> Iterable[Field]:
    """Return the data class fields defined on `cls` or its class.

    This is like the ``__fields__`` attribute, but excludes the fields defined on any
    parent class(es).
    """
    # Key for `_FIELDS_CACHE`: the fully qualified name
    cls_name = f"{cls.__module__}.{cls.__name__}"

    try:
        return _FIELDS_CACHE[cls_name]
    except KeyError:
        parent_fields = set(fields(cls.mro()[1]))
        result = list(filter(lambda f: f not in parent_fields, fields(cls)))
        return _FIELDS_CACHE.setdefault(cls_name, result)
