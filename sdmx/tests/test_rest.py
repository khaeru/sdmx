import re
from typing import Any, Dict, Optional, Tuple

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


_S = "?startPeriod=2024-02-12"

R = Resource
PARAMS: Tuple[Tuple[Resource, Dict[str, Any], str, Optional[str]], ...] = (
    # (R.actualconstraint, {}, "actualconstraint/ID0", "actualconstraint/ID0"),
    (
        R.agencyscheme,
        {},
        "agencyscheme/A0/ID0/latest",
        "structure/agencyscheme/A0/ID0/+",
    ),
    (
        R.allowedconstraint,
        {},
        "allowedconstraint/A0/ID0/latest",
        "structure/allowedconstraint/A0/ID0/+",
    ),
    (
        R.attachementconstraint,
        {},
        "attachementconstraint/A0/ID0/latest",
        "structure/attachementconstraint/A0/ID0/+",
    ),
    (
        R.availableconstraint,
        dict(key="111+134.PCPIHA_IX.*"),
        "availableconstraint/ID0/111+134.PCPIHA_IX.*",
        # "availability/dataflow/ID0/111+134.PCPIHA_IX.*",
        None,
    ),
    (
        R.categorisation,
        {},
        "categorisation/A0/ID0/latest",
        "structure/categorisation/A0/ID0/+",
    ),
    (
        R.categoryscheme,
        {},
        "categoryscheme/A0/ID0/latest",
        "structure/categoryscheme/A0/ID0/+",
    ),
    # All other parameters explicit
    (R.codelist, {}, "codelist/A0/ID0/latest", "structure/codelist/A0/ID0/+"),
    # Providing explicit version
    (
        R.codelist,
        {"version": "1.0"},
        "codelist/A0/ID0/1.0",
        "structure/codelist/A0/ID0/1.0",
    ),
    (
        R.codelist,
        {"version": "1.0"},
        "codelist/A0/ID0/1.0",
        "structure/codelist/A0/ID0/1.0",
    ),
    (
        R.conceptscheme,
        {},
        "conceptscheme/A0/ID0/latest",
        "structure/conceptscheme/A0/ID0/+",
    ),
    (
        R.contentconstraint,
        {},
        "contentconstraint/A0/ID0/latest",
        "structure/contentconstraint/A0/ID0/+",
    ),
    (
        R.customtypescheme,
        {},
        "customtypescheme/A0/ID0/latest",
        "structure/customtypescheme/A0/ID0/+",
    ),
    # No extra parameters
    (R.data, {}, "data/ID0", "data/ID0"),
    # Different ways of expressing the same query
    (R.data, dict(start_period="2024-02-12"), f"data/ID0{_S}", None),
    (R.data, dict(startPeriod="2024-02-12"), f"data/ID0{_S}", None),
    (R.data, dict(params=dict(start_period="2024-02-12")), f"data/ID0{_S}", None),
    (R.data, dict(params=dict(startPeriod="2024-02-12")), f"data/ID0{_S}", None),
    (
        R.dataconsumerscheme,
        {},
        "dataconsumerscheme/A0/ID0/latest",
        "structure/dataconsumerscheme/A0/ID0/+",
    ),
    (R.dataflow, {}, "dataflow/A0/ID0/latest", "structure/dataflow/A0/ID0/+"),
    (
        R.dataproviderscheme,
        {},
        "dataproviderscheme/A0/ID0/latest",
        "structure/dataproviderscheme/A0/ID0/+",
    ),
    (
        R.datastructure,
        {},
        "datastructure/A0/ID0/latest",
        "structure/datastructure/A0/ID0/+",
    ),
    (
        R.hierarchicalcodelist,
        {},
        "hierarchicalcodelist/A0/ID0/latest",
        "structure/hierarchicalcodelist/A0/ID0/+",
    ),
    (R.metadata, {}, "metadata/ID0", "metadata/ID0"),
    (
        R.metadataflow,
        {},
        "metadataflow/A0/ID0/latest",
        "structure/metadataflow/A0/ID0/+",
    ),
    (
        R.metadatastructure,
        {},
        "metadatastructure/A0/ID0/latest",
        "structure/metadatastructure/A0/ID0/+",
    ),
    (
        R.namepersonalisationscheme,
        {},
        "namepersonalisationscheme/A0/ID0/latest",
        "structure/namepersonalisationscheme/A0/ID0/+",
    ),
    (
        R.organisationscheme,
        {},
        "organisationscheme/A0/ID0/latest",
        "structure/organisationscheme/A0/ID0/+",
    ),
    (
        R.organisationunitscheme,
        {},
        "organisationunitscheme/A0/ID0/latest",
        "structure/organisationunitscheme/A0/ID0/+",
    ),
    (R.process, {}, "process/A0/ID0/latest", "structure/process/A0/ID0/+"),
    (
        R.provisionagreement,
        {},
        "provisionagreement/A0/ID0/latest",
        "structure/provisionagreement/A0/ID0/+",
    ),
    (
        R.reportingtaxonomy,
        {},
        "reportingtaxonomy/A0/ID0/latest",
        "structure/reportingtaxonomy/A0/ID0/+",
    ),
    (
        R.rulesetscheme,
        {},
        "rulesetscheme/A0/ID0/latest",
        "structure/rulesetscheme/A0/ID0/+",
    ),
    (
        R.schema,
        dict(context="provisionagreement"),
        "schema/provisionagreement/A0/ID0/latest",
        "schema/provisionagreement/A0/ID0/+",
    ),
    # (R.structure, {}, "structure/A0/ID0/latest", None),
    (
        R.structureset,
        {},
        "structureset/A0/ID0/latest",
        "structure/structureset/A0/ID0/+",
    ),
    (
        R.transformationscheme,
        {},
        "transformationscheme/A0/ID0/latest",
        "structure/transformationscheme/A0/ID0/+",
    ),
    (
        R.userdefinedoperatorscheme,
        {},
        "userdefinedoperatorscheme/A0/ID0/latest",
        "structure/userdefinedoperatorscheme/A0/ID0/+",
    ),
    (
        R.vtlmappingscheme,
        {},
        "vtlmappingscheme/A0/ID0/latest",
        "structure/vtlmappingscheme/A0/ID0/+",
    ),
)

PARAMS_INVALID = (
    # Providing an invalid parameter
    (R.codelist, {"foo": "bar"}, ValueError, "Unexpected/unhandled parameters"),
    # Providing duplicate path and query parameters
    (
        R.codelist,
        {"foo": "bar", "params": {"foo": "baz"}},
        ValueError,
        "Duplicate values for",
    ),
    # Positive integer parameter must be positive integer
    (
        R.data,
        {"first_n_observations": -1},
        ValueError,
        "must be positive integer; got -1",
    ),
)


class URLTests:
    """Common fixtures for testing URL classes."""

    expected_index: int

    @pytest.fixture
    def source(self):
        from sdmx.source import Source

        return Source(id="A0", url="https://example.com", name="Test source")

    @pytest.mark.parametrize("resource_type, kw, expected0, expected1", PARAMS)
    def test_join(self, URL, source, resource_type, kw, expected0, expected1) -> None:
        expected = [expected0, expected1][self.expected_index]
        if expected is None:
            return

        # Instance can be created
        u = URL(source, resource_type, resource_id="ID0", **kw)

        # Constructed URL is as expected
        assert f"https://example.com/{expected}" == u.join()

    @pytest.mark.parametrize("resource_type, kw, exc_type, exc_re", PARAMS_INVALID)
    def test_join_invalid(self, URL, source, resource_type, kw, exc_type, exc_re):
        with pytest.raises(exc_type, match=exc_re):
            URL(source, resource_type, resource_id="ID0", **kw)


class TestURLv21(URLTests):
    """Construction of SDMX REST API 2.1 URLs."""

    expected_index = 0

    @pytest.fixture
    def URL(self):
        import sdmx.rest.v21

        return sdmx.rest.v21.URL


class TestURLv30(URLTests):
    """Construction of SDMX REST API 3.0.0 URLs."""

    expected_index = 1

    @pytest.fixture
    def URL(self):
        import sdmx.rest.v30

        return sdmx.rest.v30.URL
