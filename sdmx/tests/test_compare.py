from dataclasses import dataclass
from typing import Optional

import pytest
from lxml.etree import Element

from sdmx.compare import Options, compare


class Foo:
    """Dummy class for testing."""

    pass


def test_allow_implied_urn() -> None:
    """Test :py:`except ValueError` block in compare function for dataclasses."""

    @dataclass
    class Bar:
        urn: Optional[str] = None

    b1 = Bar(urn="")
    b2 = Bar()

    compare(b1, b2, Options(base=b1))
    compare(b2, b1, Options(base=b2))


def test_not_implemented() -> None:
    f1 = Foo()
    f2 = Foo()

    with pytest.raises(NotImplementedError):
        compare(f1, f2, Options(base=f1))


def test_element() -> None:
    """Test :py:`except TypeError` block in compare function for lxml.etree.Element."""
    e = Element("foo")
    assert False is compare(e, Foo(), Options(base=e))
