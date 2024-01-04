import pytest

import sdmx
from sdmx.message import Message


@pytest.mark.parametrize_specimens("path", format="xml")
def test_read_xml(path):
    """XML specimens can be read."""
    if "esms_structured" in path.name:
        pytest.xfail("Not implemented")

    result = sdmx.read_sdmx(path)
    assert isinstance(result, Message)
