import re

import pytest

from sdmx import to_sdmx
from sdmx.reader import (
    detect_content_reader,
    get_reader_for_media_type,
    get_reader_for_path,
    json,
)
from sdmx.reader.base import BaseReader, Converter


class TestConverter:
    def test_handles(self) -> None:
        assert False is Converter.handles({}, {})

    def test_convert(self) -> None:
        with pytest.raises(NotImplementedError):
            Converter().convert({})


class TestBaseReader:
    def test_deprecated_read_message(self) -> None:
        with (
            pytest.raises(NotImplementedError),
            pytest.warns(DeprecationWarning, match="use Converter.convert"),
        ):
            BaseReader().read_message({})


def test_deprecated_detect_content_reader() -> None:
    with pytest.warns(DeprecationWarning, match=r"use get_reader\(\) instead"):
        assert json.Reader is detect_content_reader(b"{")


@pytest.mark.parametrize(
    "value",
    [
        "application/x-pdf",
    ],
)
def test_deprecated_get_reader_for_media_type0(value):
    with (
        pytest.raises(
            ValueError, match=re.escape(f"Media type {value!r} not supported by any of")
        ),
        pytest.warns(DeprecationWarning, match=r"use get_reader\(requests.Response"),
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
def test_deprecated_get_reader_for_media_type1(value):
    with pytest.warns(DeprecationWarning, match=r"use get_reader\(requests.Response"):
        # Does not raise
        get_reader_for_media_type(value)


@pytest.mark.parametrize(
    "path",
    (
        "example.json",
        pytest.param("example.badsuffix", marks=pytest.mark.xfail(raises=ValueError)),
    ),
)
def test_deprecated_get_reader_for_path(path):
    with pytest.warns(DeprecationWarning, match=r"use get_reader\(\) instead"):
        assert json.Reader is get_reader_for_path(path)


def test_to_sdmx():
    with pytest.raises(NotImplementedError, match="Convert <class 'dict"):
        to_sdmx(dict())
