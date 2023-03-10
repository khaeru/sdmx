import re

import pytest

from sdmx.model import v21 as m
from sdmx.urn import make, match


def test_make():
    """:func:`.make` can look up and use information about the parent ItemScheme."""
    c = m.Code(id="BAR")

    with pytest.raises(
        ValueError, match="Neither <Code BAR> nor None are maintainable"
    ):
        make(c)

    cl = m.Codelist(id="FOO")
    cl.append(c)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Cannot construct URN for <Codelist FOO (1 items)> without maintainer"
        ),
    ):
        make(c)

    cl.maintainer = m.Agency(id="BAZ")

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Cannot construct URN for <Codelist BAZ:FOO (1 items)> without version"
        ),
    ):
        make(c, strict=True)

    cl.version = "1.2.3"

    assert "urn:sdmx:org.sdmx.infomodel.codelist.Code=BAZ:FOO(1.2.3).BAR" == make(c)
    assert "urn:sdmx:org.sdmx.infomodel.codelist.Codelist=BAZ:FOO(1.2.3)" == make(cl)


def test_match():
    # Value containing a "." in the ID
    urn = (
        "urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=LSD:"
        "TSTT1201R001_MIT1938_1_1._1(1.0)"
    )
    assert "TSTT1201R001_MIT1938_1_1._1" == match(urn)["id"]

    # Invalid value (only the "package" component, no "class")
    urn = "urn:sdmx:org.sdmx.infomodel.codelist=BBK:CLA_BBK_COLLECTION(1.0)"
    with pytest.raises(ValueError, match=re.escape(f"not a valid SDMX URN: {urn}")):
        match(urn)
