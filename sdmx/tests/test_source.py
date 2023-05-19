import pytest

from sdmx.model import v21 as model
from sdmx.source import Source, add_source, list_sources, sources


def test_list_sources():
    source_ids = list_sources()
    assert len(source_ids) == 27

    # Listed alphabetically
    assert source_ids[0] == "ABS"
    assert source_ids[-1] == "WB_WDI"


def test_source_support():
    # Implicitly supported endpoint
    assert sources["ILO"].supports["categoryscheme"] is True

    # Specifically unsupported endpoint
    assert sources["ESTAT"].supports["contentconstraint"] is False

    # Explicitly supported structure-specific data
    assert sources["INEGI"].supports["structure-specific data"] is True


def test_add_source():
    profile = """{
        "id": "FOO",
        "name": "Demo source",
        "url": "https://example.org/sdmx"
        }"""
    add_source(profile)

    # JSON sources do not support metadata endpoints, by default
    profile2 = """{
        "id": "BAR",
        "data_content_type": "JSON",
        "name": "Demo source",
        "url": "https://example.org/sdmx"
        }"""
    add_source(profile2)
    assert not sources["BAR"].supports["datastructure"]

    with pytest.raises(
        ValueError, match="Data source 'ECB' already defined; use override=True"
    ):
        add_source(dict(id="ECB", name="Demo source", url="https://example.com/sdmx"))


class TestSource:
    @pytest.fixture
    def s(self):
        """An instance of the class."""
        yield Source(id="FOO", name="Test source", url="https://example.com")

    def test_modify_request_args(self, s):
        kwargs = dict(dsd=model.DataStructureDefinition())

        s.modify_request_args(kwargs)
        assert "structurespecificdata" in kwargs["headers"]["Accept"]
