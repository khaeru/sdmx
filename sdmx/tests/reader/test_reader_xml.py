import pytest

import sdmx
from sdmx.message import Message


@pytest.mark.parametrize_specimens("path", format="xml")
def test_read_xml(path):
    """XML specimens can be read."""
    result = sdmx.read_sdmx(path)
    assert isinstance(result, Message)
