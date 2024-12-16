import pytest

from sdmx.format import Flag, MediaType
from sdmx.model import v21
from sdmx.reader.base import BaseReader
from sdmx.reader.xml.v21 import Reader as XMLv21Reader


class TestBaseReader:
    @pytest.fixture
    def MinimalReader(self):
        """A reader that implements the minimum abstract methods."""

        class cls(BaseReader):
            media_types = [
                MediaType("", "xml", "2.1", Flag.data, full="application/foo"),
            ]

            def convert(self, source, dsd=None):
                pass  # pragma: no cover

        return cls

    def test_deprecated_kwarg(self):
        r = XMLv21Reader()

        dsd0 = v21.DataStructureDefinition(id="FOO")
        dsd1 = v21.DataStructureDefinition(id="BAR")
        with (
            pytest.warns(
                DeprecationWarning, match="dsd=.* keyword argument; use structure="
            ),
            pytest.raises(ValueError, match="Mismatched structure=FOO, dsd=BAR"),
        ):
            r.convert(None, structure=dsd0, dsd=dsd1)

    def test_detect(self, MinimalReader):
        with pytest.warns(DeprecationWarning, match="use Converter.handles"):
            assert False is MinimalReader.detect(b"foo")

    def test_handles_media_type(self, caplog, MinimalReader):
        """:meth:`.handles_media_type` matches even when params differ, but logs."""
        with pytest.warns(DeprecationWarning, match="use Converter.handles"):
            assert True is MinimalReader.handles_media_type("application/foo; bar=qux")
        assert (
            "Match application/foo with params {'bar': 'qux'}; "
            "expected {'version': '2.1'}" in caplog.messages
        )
