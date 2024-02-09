import re

import pytest

from sdmx import Resource


class TestResource:
    @pytest.mark.parametrize(
        "value, expected",
        [
            # Some values are mapped to different class names
            (Resource.dataflow, "DataflowDefinition"),
            (Resource.datastructure, "DataStructureDefinition"),
            # Other values pass through
            (Resource.agencyscheme, Resource.agencyscheme.value),
        ],
    )
    def test_class_name(self, value, expected):
        assert expected == Resource.class_name(value)

    def test_describe(self):
        assert re.fullmatch(
            "{actualconstraint .* vtlmappingscheme}", Resource.describe()
        )


class TestURL:
    """Common fixtures for testing URL classes."""

    @pytest.fixture
    def source(self):
        from sdmx.source import Source

        return Source(id="A0", url="https://example.com", name="Test source")


class TestURLv21(TestURL):
    """Construction of SDMX REST API 2.1 URLs."""

    def test_join(self, source) -> None:
        from sdmx.rest.v21 import URL

        u = URL(source, resource_type=Resource.dataflow, resource_id="DF0")
        assert "https://example.com/dataflow/A0/DF0/latest" == u.join()


class TestURLv30(TestURL):
    """Construction of SDMX REST API 3.0.0 URLs."""

    def test_join(self, source) -> None:
        from sdmx.rest.v21 import URL

        u = URL(source, resource_type=Resource.dataflow, resource_id="DF0")
        assert "https://example.com/dataflow/A0/DF0/latest" == u.join()
