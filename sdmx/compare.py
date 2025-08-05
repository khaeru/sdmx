"""Compare SDMX artefacts."""

import datetime
import enum
import logging
import textwrap
from collections import defaultdict
from collections.abc import Iterable
from copy import copy
from dataclasses import dataclass, fields, is_dataclass
from functools import singledispatch
from typing import Any, TypeVar, Union

import lxml.etree

from .model import internationalstring

log = logging.getLogger(__name__)


IGNORE_CONTEXT = {"Categorisation.artefact"}
VISITED: dict[tuple[int, int], set[int]] = defaultdict(set)


class Comparable:
    """Mix-in class for objects with a :meth:`.compare` method."""

    def compare(self, other, strict: bool = True) -> bool:
        """Return :any:`True` if `self` is the same as `other`.

        Parameters
        ----------
        strict :
            If :any:`True` (the default), then attributes and associated objects must
            compare exactly equal. If :any:`False`, then :any:`None` values on either
            side are permitted.
        """
        return compare(self, other, Options(self, strict=strict))


@dataclass
class Options:
    """Options for a comparison."""

    base: Any
    strict: bool = True
    verbose: bool = False

    _memo_key: tuple[int, int] = (0, 0)

    def __post_init__(self):
        # Create a key for memoization
        self._memo_key = (id(self.base), id(self))
        VISITED[self._memo_key].clear()

    def log(self, message: str, level: int = logging.INFO) -> None:
        """Log `message` on `level`.

        If :attr:`verbose` is :any:`False`, `level` must be at least
        :data:`logging.DEBUG`.
        """
        if self.verbose or level > logging.DEBUG:
            log.log(level, message)

    def visited(self, obj) -> bool:
        """Return :any:`True` if `obj` has already be compared."""
        if type(obj).__module__ == "builtins":
            return False

        entry = id(obj)

        if entry in VISITED[self._memo_key]:
            return True
        else:
            VISITED[self._memo_key].add(entry)
            return False


T = TypeVar("T", bound=object)


@singledispatch
def compare(left: object, right, opts: Options, context: str = "") -> bool:
    """Compare `left` to `right`."""
    if is_dataclass(left):
        return compare_dataclass(left, right, opts, context)

    raise NotImplementedError(f"Compare {type(left)} {left!r} in {context}")


def compare_dataclass(left, right, opts: Options, context: str) -> bool:
    c = context or type(left).__name__

    result = right is not None
    for f in fields(left) if result else []:
        l_val, r_val = getattr(left, f.name), getattr(right, f.name)

        if opts.visited(l_val):
            continue  # Already compared to its counterpart

        c_sub = f"{c}.{f.name}"

        result_f = (
            l_val is r_val
            or compare(l_val, r_val, opts, c_sub)
            or c_sub in IGNORE_CONTEXT
        )

        result &= result_f

        if result_f is False:
            opts.log(f"Not identical: {c_sub}={shorten(l_val)} != {shorten(r_val)}")
            if not opts.verbose:
                break
        elif opts.verbose:
            opts.log(f"{c_sub}={shorten(l_val)} == {shorten(r_val)}", logging.DEBUG)

    return result


# Built-in types


@compare.register
def _eq(left: Union[str, datetime.date], right, opts, context=""):
    """Built-in types that must compare equal."""
    return left == right or (not opts.strict and right is None)


@compare.register
def _is(left: Union[None, bool, float, int, type, enum.Enum], right, opts, context):
    """Built-in types that must compare identical."""
    return left is right or (not opts.strict and right is None)


@compare.register
def _(left: dict, right, opts, context=""):
    """Return :obj:`True` if `self` is the same as `other`.

    Two DictLike instances are identical if they contain the same set of keys, and
    corresponding values compare equal.
    """
    result = True

    l_keys = set(left.keys())
    r_keys = set(right.keys()) if hasattr(right, "keys") else set()
    if l_keys != r_keys:
        opts.log(
            f"Mismatched {type(left).__name__} keys: {shorten(sorted(l_keys))} "
            f"!= {shorten(sorted(r_keys))}"
        )
        result = False

    # Compare items pairwise
    for key in sorted(l_keys) if (result or opts.verbose and right is not None) else ():
        result &= compare(left[key], right.get(key, None), opts)
        if result is False and not opts.verbose:
            break

    return result


@compare.register
def _(left: Union[list, set], right, opts, context=""):
    if len(left) != len(right):
        opts.log(f"Mismatched length: {len(left)} != {len(right)}")
        return False

    try:
        l_values: Iterable = sorted(left)
        r_values: Iterable = sorted(right)
    except TypeError:
        l_values, r_values = left, right

    return all(
        compare(a, b, opts, f"{context}[{i}]")
        for i, (a, b) in enumerate(zip(l_values, r_values))
    )


# Types from upstream packages


@compare.register
def _(left: lxml.etree._Element, right, opts, context=""):
    try:
        r_val = copy(right)
        lxml.etree.cleanup_namespaces(r_val)
    except TypeError:
        return not opts.strict
    else:
        l_val = copy(left)
        lxml.etree.cleanup_namespaces(l_val)
        return lxml.etree.tostring(l_val) == lxml.etree.tostring(r_val)


# SDMX types


@compare.register
def _(left: internationalstring.InternationalString, right, opts, context=""):
    return compare(
        left.localizations, right.localizations, opts, f"{context}.localizations"
    )


def shorten(value: Any) -> str:
    """Return a shortened :func:`repr` of `value` for logging."""
    return textwrap.shorten(repr(value), 30, placeholder="…")
