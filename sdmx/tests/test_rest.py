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


R = Resource
PARAMS = (
    (R.actualconstraint, {}, "actualconstraint/ID0", "actualconstraint/ID0"),
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
    (R.codelist, {}, "codelist/A0/ID0/latest", "structure/codelist/A0/ID0/+"),
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
    (R.data, {}, "data/ID0", "data/ID0"),
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
    (R.metadata, {}, "metadata/A0/ID0/latest", "structure/metadata/A0/ID0/+"),
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
    (R.schema, {}, "schema/A0/ID0/latest", "structure/schema/A0/ID0/+"),
    (R.structure, {}, "structure/A0/ID0/latest", "structure/structure/A0/ID0/+"),
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


class TestURLv21(TestURL):
    """Construction of SDMX REST API 2.1 URLs."""

    @pytest.mark.parametrize("resource_type, kw, expected, _", PARAMS)
    def test_join(self, source, resource_type, kw, expected, _) -> None:
        from sdmx.rest.v21 import URL

        # Instance can be created
        u = URL(source, resource_type, resource_id="ID0", **kw)

        # Constructed URL is as expected
        assert f"https://example.com/{expected}" == u.join()


class TestURLv30(TestURL):
    """Construction of SDMX REST API 3.0.0 URLs."""

    @pytest.mark.parametrize("resource_type, kw, _, expected", PARAMS)
    def test_join(self, source, resource_type, kw, _, expected) -> None:
        from sdmx.rest.v30 import URL

        # Instance can be created
        u = URL(source, resource_type, resource_id="ID0", **kw)

        # Constructed URL is as expected
        assert f"https://example.com/{expected}" == u.join()
