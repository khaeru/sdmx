import pytest

from sdmx.format import Flag, MediaType
from sdmx.reader.base import BaseReader


class TestBaseReader:
    @pytest.fixture
    def MinimalReader(self):
        """A reader that implements the minimum abstract methods."""

        class cls(BaseReader):
            media_types = [
                MediaType("", "xml", "2.1", Flag.data, full="application/foo"),
            ]

            def read_message(self, source, dsd=None):
                pass  # pragma: no cover

        return cls

    def test_detect(self, MinimalReader):
        assert False is MinimalReader.detect(b"foo")

    def test_handles_media_type(self, caplog, MinimalReader):
        """:meth:`.handles_media_type` matches even when params differ, but logs."""
        assert True is MinimalReader.handles_media_type("application/foo; bar=qux")
        assert (
            "Match application/foo with params {'bar': 'qux'}; "
            "expected {'version': '2.1'}" in caplog.messages
        )
