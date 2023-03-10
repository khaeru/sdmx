import pytest

from sdmx.reader.csv import Reader


class TestReader:
    @pytest.mark.parametrize(
        "mt, expected",
        [
            ("foo", False),
            ("application/vnd.sdmx.data+csv; version=1.0.0", True),
            ("application/vnd.sdmx.metadata+csv; version=2.0.0", True),
        ],
    )
    def test_handles_media_type(self, mt, expected) -> None:
        assert expected is Reader.handles_media_type(mt)

    @pytest.mark.parametrize("value, expected", [(".csv", True), (".xlsx", False)])
    def test_supports_suffix(self, value, expected) -> None:
        assert expected is Reader.supports_suffix(value)
