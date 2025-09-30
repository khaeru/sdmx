import pytest

from sdmx.format.csv.common import Labels
from sdmx.format.csv.v1 import FormatOptions


class TestFormatOptions:
    def test_post_init(self) -> None:
        with pytest.raises(ValueError):
            FormatOptions(labels=Labels.name)
