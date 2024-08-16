import operator

import pytest
from packaging.version import InvalidVersion
from packaging.version import Version as PVVersion

from sdmx.model.version import Version, increment, parse


class TestVersion:
    @pytest.mark.parametrize("value, exp_kind", (("1.2.0+dev1", "py"),))
    def test_init(self, value, exp_kind) -> None:
        assert exp_kind == Version(value).kind

    @pytest.mark.parametrize(
        "op, value, exp",
        (
            (operator.eq, "1.0.0", True),
            (operator.ge, "1.0.0", True),
            (operator.gt, "1.0.0", False),
            (operator.le, "1.0.0", True),
            (operator.lt, "1.0.0", False),
            (operator.ne, "1.0.0", False),
            # Not implemented
            pytest.param(
                operator.gt, 1.0, None, marks=pytest.mark.xfail(raises=TypeError)
            ),
        ),
    )
    def test_binop_str(self, op, value, exp) -> None:
        assert exp is op(Version("1.0.0"), value)


@pytest.mark.parametrize(
    "value, expected",
    (
        # SDMX 2.1
        ("0.0", PVVersion("0.0")),
        ("1.0", PVVersion("1.0")),
        # SDMX 3.0
        ("0.0.0-dev1", PVVersion("0.0.0+dev1")),
        ("1.0.0-dev1", PVVersion("1.0.0+dev1")),
        # Python
        ("1!1.2.3+abc.dev1", PVVersion("1!1.2.3+abc.dev1")),
        # Invalid
        pytest.param("foo", None, marks=pytest.mark.xfail(raises=InvalidVersion)),
    ),
)
def test_parse(value, expected) -> None:
    v = parse(value)

    assert expected == v

    # Value round-trips
    assert value == str(v)

    # Attributes can be accessed
    v.major
    v.minor
    v.patch
    v.local
    v.ext

    # Object's increment() method can be called
    assert v < v.increment(patch=1) < v.increment(minor=1) < v.increment(major=1)


@pytest.mark.parametrize(
    "kwargs, expected",
    (
        (dict(), PVVersion("1.1.0+dev1")),
        (dict(major=True), PVVersion("2.0.0")),
        (dict(major=1), PVVersion("2.0.0")),
        (dict(minor=True), PVVersion("1.1.0")),
        (dict(minor=1), PVVersion("1.1.0")),
        (dict(patch=True), PVVersion("1.0.1")),
        (dict(patch=1), PVVersion("1.0.1")),
        (dict(micro=True), PVVersion("1.0.1")),
        (dict(ext=1), PVVersion("1.0.0+dev1")),
        pytest.param(dict(foo=True), None, marks=pytest.mark.xfail(raises=ValueError)),
    ),
)
def test_increment0(kwargs, expected):
    # PVVersion.increment() method
    assert expected == parse("1.0.0").increment(**kwargs)

    # increment() function
    assert expected == increment("1.0.0", **kwargs)


_NIE = pytest.mark.xfail(raises=NotImplementedError)


@pytest.mark.parametrize(
    "base, kwarg, expected",
    (
        ("1.0.0", dict(ext=1), PVVersion("1.0.0+dev1")),
        ("1.0.0-dev1", dict(ext=1), PVVersion("1.0.0+dev2")),
        ("1.0.0-dev1", dict(ext=2), PVVersion("1.0.0+dev3")),
        ("1.0.0-foodev1", dict(ext=1), PVVersion("1.0.0+foodev2")),
        pytest.param("1.0.0-draft", dict(ext=1), None, marks=_NIE),
    ),
)
def test_increment1(base, kwarg, expected):
    """Test incrementing the 'extension' version part."""
    assert expected == parse(base).increment(**kwarg)
