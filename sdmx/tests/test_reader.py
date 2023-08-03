import re

import pytest

from sdmx.reader import get_reader_for_media_type


@pytest.mark.parametrize(
    "value",
    [
        "application/x-pdf",
    ],
)
def test_get_reader_for_media_type0(value):
    with pytest.raises(
        ValueError, match=re.escape(f"Media type {value!r} not supported by any of")
    ):
        get_reader_for_media_type(value)


@pytest.mark.parametrize(
    "value",
    [
        "application/vnd.sdmx.data+xml; version=3.0.0",
        "application/xml;charset=UTF-8",
        "draft-sdmx-json;charset=UTF-8",
    ],
)
def test_get_reader_for_media_type1(value):
    # Does not raise
    get_reader_for_media_type(value)
