import pytest

from sdmx.model import v21 as model
from sdmx.source import Source, add_source, list_sources, sources


def test_list_sources():
    source_ids = list_sources()
    # Correct number of sources, excluding those created for testing
    assert 29 == len(set(source_ids) - {"MOCK", "TEST"})

    # Listed alphabetically
    assert "ABS" == source_ids[0]
    assert "WB_WDI" == source_ids[-1]


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

    def test_get_url_class(self):
        """get_url_class() returns :class:`.v30.URL` as appropriate."""
        from sdmx.rest import v30

        assert issubclass(sources["ESTAT3"].get_url_class(), v30.URL)

    def test_modify_request_args(self, s):
        kwargs = dict(dsd=model.DataStructureDefinition())

        s.modify_request_args(kwargs)
        assert "structurespecificdata" in kwargs["headers"]["Accept"]
