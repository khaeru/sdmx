import pytest

from sdmx import Client, Resource
from sdmx.model import v21 as model
from sdmx.source import Source, add_source, get_source, list_sources, sources


def test_get_source(caplog):
    s1 = get_source("WB")
    assert 0 == len(caplog.messages)

    s2 = get_source("wb")
    assert "'WB' as a case-insensitive match for id 'wb'" in caplog.messages[-1]

    assert s1 == s2


def test_list_sources():
    source_ids = list_sources()
    # Correct number of sources, excluding those created for testing
    assert 35 == len(set(source_ids) - {"MOCK", "TEST"})

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


@pytest.mark.parametrize("source_id", ["ABS", "ABS_JSON"])
def test_abs_url(source_id):
    assert sources[source_id].url == "https://data.api.abs.gov.au/rest"


def test_abs_support():
    source = sources["ABS"]

    assert all(
        source.supports[resource]
        for resource in (
            Resource.actualconstraint,
            Resource.categoryscheme,
            Resource.contentconstraint,
        )
    )


def test_abs_metadata_accept_header():
    client = Client("ABS")

    request = client.datastructure(
        "DS_LABOUR_ACCT_Q", params={"references": "none"}, dry_run=True
    )

    assert request.url == (
        "https://data.api.abs.gov.au/rest/datastructure/ABS/"
        "DS_LABOUR_ACCT_Q/latest?references=none"
    )
    assert request.headers["Accept"] == "application/xml"

    request = client.datastructure(
        "DS_LABOUR_ACCT_Q",
        params={"references": "none"},
        headers={"X-Test": "value"},
        dry_run=True,
    )

    assert request.headers["Accept"] == "application/xml"
    assert request.headers["X-Test"] == "value"

    # An explicit content type supplied by the caller takes precedence.
    request = client.datastructure(
        "DS_LABOUR_ACCT_Q",
        params={"references": "none"},
        headers={"accept": "application/vnd.sdmx.structure+json"},
        dry_run=True,
    )

    assert request.headers["Accept"] == "application/vnd.sdmx.structure+json"

    request = client.data(
        "LABOUR_ACCT_Q",
        key="M28...10.Q",
        dsd=model.DataStructureDefinition(),
        dry_run=True,
    )

    assert (
        request.headers["Accept"]
        == "application/vnd.sdmx.structurespecificdata+xml;version=2.1"
    )


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
