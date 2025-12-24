import operator

import pytest
from packaging.version import InvalidVersion
from packaging.version import Version as PVVersion

from sdmx.model.version import Version, increment, parse

_NIE = pytest.mark.xfail(raises=NotImplementedError)


class TestVersion:
    @pytest.mark.parametrize("value, exp_kind", (("1.2.0+dev1", "py"),))
    def test_init(self, value: str, exp_kind: str) -> None:
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
    def test_binop_str(self, op, value: str, exp: bool) -> None:
        assert exp is op(Version("1.0.0"), value)

    @pytest.mark.parametrize(
        "base, kwargs, expected",
        (
            ("1.0.0", dict(), PVVersion("1.1.0+dev1")),
            ("1.0.0", dict(), "1.1.0+dev1"),
            ("1.0.0", dict(), "1.1.0-dev1"),
            ("1.0.0", dict(major=True), "2.0.0"),
            ("1.0.0", dict(major=1), "2.0.0"),
            ("1.0.0", dict(minor=True), "1.1.0"),
            ("1.0.0", dict(minor=1), "1.1.0"),
            ("1.0.0", dict(patch=True), "1.0.1"),
            ("1.0.0", dict(patch=1), "1.0.1"),
            ("1.0.0", dict(ext=1), "1.0.0+dev1"),
            # Aliases, boolean arguments
            ("1.0.0", dict(micro=True), "1.0.1"),
            ("1.0.0", dict(local=True), "1.0.0+dev1"),
            # Invalid kwargs
            pytest.param(
                "1.0.0", dict(foo=True), None, marks=pytest.mark.xfail(raises=TypeError)
            ),
            # Increment the 'extension' version part
            ("1.0.0", dict(ext=1), "1.0.0+dev1"),
            ("1.0.0-dev1", dict(ext=1), "1.0.0+dev2"),
            ("1.0.0-dev1", dict(ext=2), "1.0.0+dev3"),
            ("1.0.0-foodev1", dict(ext=1), "1.0.0+foodev2"),
            pytest.param("1.0.0-draft", dict(ext=1), "", marks=_NIE),
            # Increment of any release component resets the inferior components and
            # the ext/local segment
            ("1.2.3-dev1", dict(patch=1), "1.2.4"),
            ("1.2.3-dev1", dict(minor=1), "1.3.0"),
            ("1.2.3-dev1", dict(major=1), "2.0.0"),
            # Same as above, but preserving the smaller parts
            ("1.2.3-dev1", dict(patch=1, ext=0), "1.2.4-dev1"),
            ("1.2.3-dev1", dict(minor=1, patch=0, ext=0), "1.3.3-dev1"),
            ("1.2.3-dev1", dict(major=1, minor=0, patch=0, ext=0), "2.2.3-dev1"),
        ),
    )
    def test_increment(
        self, base: str, kwargs: dict, expected: str | PVVersion
    ) -> None:
        # Version.increment() method
        assert expected == Version(base).increment(**kwargs)

        # increment() function
        assert expected == increment(base, **kwargs)


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
        (
            "1!2.3.4rc5.post6.dev7+abc8.xyz.9",
            PVVersion("1!2.3.4rc5.post6.dev7+abc8.xyz.9"),
        ),
        # Invalid
        pytest.param("foo", None, marks=pytest.mark.xfail(raises=InvalidVersion)),
    ),
)
def test_parse(value: str, expected: PVVersion) -> None:
    v = parse(value)

    assert expected == v

    # Value round-trips
    assert value == str(v)

    # Attributes can be accessed and have the expected types
    assert isinstance(v.major, int)
    assert isinstance(v.minor, int)
    assert isinstance(v.patch, int)
    assert isinstance(v.local, tuple)
    assert isinstance(v.ext, (type(None), str))

    # Object's increment() method can be called
    assert v < v.increment(patch=1) < v.increment(minor=1) < v.increment(major=1)
