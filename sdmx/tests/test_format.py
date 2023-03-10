import pytest

from sdmx.format import Flag, MediaType, list_media_types


class TestMediaType:
    @pytest.fixture
    def mt(self):
        yield MediaType("foo", "xml", "3.0.0", Flag.meta | Flag.ts)

    def test_match(self, mt):
        other = "application/vnd.sdmx.foo+xml; version=3.0.1, bar=baz"
        assert mt.match(other) is True
        assert mt.match(other, strict=True) is False

    def test_flags(self, mt):
        assert mt.is_data is False
        assert mt.is_meta is True
        assert mt.is_structure_specific is False
        assert mt.is_time_series is True

    def test_repr(self, mt):
        assert "application/vnd.sdmx.foo+xml; version=3.0.0" == repr(mt)


@pytest.mark.parametrize("base, N", [("csv", 2), ("json", 8), ("xml", 14)])
def test_list_media_types(base, N):
    assert N == len(list_media_types(base=base))
