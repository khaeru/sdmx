import logging
import typing
from collections.abc import Iterator
from dataclasses import Field, fields
from functools import lru_cache
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Tuple,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

import requests

try:
    import requests_cache
except ImportError:  # pragma: no cover
    HAS_REQUESTS_CACHE = False
else:
    HAS_REQUESTS_CACHE = True


KT = TypeVar("KT")
VT = TypeVar("VT")

log = logging.getLogger(__name__)

__all__ = [
    "DictLike",
    "compare",
    "only",
    "summarize_dictlike",
]


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


class DictLike(dict, typing.MutableMapping[KT, VT]):
    """Container with features of :class:`dict`, attribute access, and validation."""

    __slots__ = ("__dict__", "_types")

    def __init__(self, *args, **kwargs):
        # (key type, value type) for items
        self._types = (object, object)

        super().__init__(*args, **kwargs)

        # Ensures attribute access to dict items
        self.__dict__ = self

    @classmethod
    def with_types(cls, key_type, value_type):
        """Construct a new DictLike with the given `key_type` and `value_type`."""
        result = cls()
        result._types = (key_type, value_type)
        return result

    def __getitem__(self, key: Union[KT, int]) -> VT:
        """:meth:`dict.__getitem__` with integer access."""
        try:
            return super().__getitem__(key)
        except KeyError:
            if isinstance(key, int):
                # int() index access
                return list(self.values())[key]
            else:
                raise

    def __setitem__(self, key: KT, value: VT) -> None:
        """:meth:`dict.__setitem` with validation."""
        super().__setitem__(*self._validate_entry((key, value)))

    def __copy__(self):
        # Construct explicitly to avoid returning the parent class, dict()
        return DictLike(**self)

    def copy(self):
        """Return a copy of the DictLike."""
        return self.__copy__()

    def update(self, other):
        """Update the DictLike with elements from `other`, validating entries."""
        try:
            it = other.items()
        except AttributeError:
            it = iter(other)
        super().update(map(self._validate_entry, it))

    # Satisfy dataclass(), which otherwise complains when InternationalStringDescriptor
    # is used
    @classmethod
    def __hash__(cls):
        pass

    def _validate_entry(self, kv: Tuple):
        """Validate one `key`/`value` pair."""
        key, value = kv
        try:
            kt, vt = self._types
        except AttributeError:
            pass
        else:
            if not isinstance(key, kt):
                raise TypeError(
                    f"Expected key type {kt.__name__}; got {type(key).__name__}"
                )
            elif not isinstance(value, vt):
                raise TypeError(
                    f"Expected value type {vt.__name__}; got {type(value).__name__}"
                )

        return key, value

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two DictLike instances are identical if they contain the same set of keys, and
        corresponding values compare equal.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`compare` for the values.
        """
        if set(self.keys()) != set(other.keys()):
            log.info(f"Not identical: {sorted(self.keys())} / {sorted(other.keys())}")
            return False

        for key, value in self.items():
            if not value.compare(other[key], strict):
                return False

        return True


# Utility methods for DictLike
#
# These are defined in separate functions to avoid collisions with keys and the
# attribute access namespace, e.g. if the DictLike contains keys "summarize" or
# "validate".


def summarize_dictlike(dl, maxwidth=72):
    """Return a string summary of the DictLike contents."""
    value_cls = dl[0].__class__.__name__
    count = len(dl)
    keys = " ".join(dl.keys())
    result = f"{value_cls} ({count}): {keys}"

    if len(result) > maxwidth:
        # Truncate the list of keys
        result = result[: maxwidth - 3] + "..."

    return result


class DictLikeDescriptor(Generic[KT, VT]):
    """Descriptor for :class:`DictLike` attributes on dataclasses."""

    def __set_name__(self, owner, name):
        self._name = "_" + name
        self._field = None
        self._types = (object, object)

    def _get_field_types(self, obj):
        """Record the types of the described field."""
        if self._field:
            return  # Already done

        # Identify the field on `obj` that matches self._name
        self._field = next(filter(lambda f: f.name == self._name[1:], fields(obj)))
        # The type is DictLike[KeyType, ValueType]; retrieve those arguments
        kt, vt = get_args(self._field.type)
        # Store. If ValueType is a generic, e.g. List[int], store only List.
        self._types = (kt, get_origin(vt) or vt)

    def __get__(self, obj, type) -> DictLike[KT, VT]:
        if obj is None:
            return None  # type: ignore [return-value]

        try:
            return obj.__dict__[self._name]
        except KeyError:
            # Construct new DictLike with specified types
            default = DictLike.with_types(*self._types)
            return obj.__dict__.setdefault(self._name, default)

    def __set__(self, obj, value):
        self._get_field_types(obj)

        if not isinstance(value, DictLike):
            # Construct new DictLike with specified types
            _value = DictLike.with_types(*self._types)
            # Update with validation
            _value.update(value or {})
            value = _value

        setattr(obj, self._name, value)


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
