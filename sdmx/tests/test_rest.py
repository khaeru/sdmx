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
    (R.actualconstraint, "ID0", "actualconstraint/ID0", "actualconstraint/ID0"),
    (
        R.agencyscheme,
        "ID0",
        "agencyscheme/A0/ID0/latest",
        "structure/agencyscheme/A0/ID0/+",
    ),
    (
        R.allowedconstraint,
        "ID0",
        "allowedconstraint/A0/ID0/latest",
        "structure/allowedconstraint/A0/ID0/+",
    ),
    (
        R.attachementconstraint,
        "ID0",
        "attachementconstraint/A0/ID0/latest",
        "structure/attachementconstraint/A0/ID0/+",
    ),
    (
        R.categorisation,
        "ID0",
        "categorisation/A0/ID0/latest",
        "structure/categorisation/A0/ID0/+",
    ),
    (
        R.categoryscheme,
        "ID0",
        "categoryscheme/A0/ID0/latest",
        "structure/categoryscheme/A0/ID0/+",
    ),
    (R.codelist, "CL0", "codelist/A0/CL0/latest", "structure/codelist/A0/CL0/+"),
    (
        R.conceptscheme,
        "ID0",
        "conceptscheme/A0/ID0/latest",
        "structure/conceptscheme/A0/ID0/+",
    ),
    (
        R.contentconstraint,
        "ID0",
        "contentconstraint/A0/ID0/latest",
        "structure/contentconstraint/A0/ID0/+",
    ),
    (
        R.customtypescheme,
        "ID0",
        "customtypescheme/A0/ID0/latest",
        "structure/customtypescheme/A0/ID0/+",
    ),
    (R.data, "ID0", "data/ID0", "data/ID0"),
    (
        R.dataconsumerscheme,
        "ID0",
        "dataconsumerscheme/A0/ID0/latest",
        "structure/dataconsumerscheme/A0/ID0/+",
    ),
    (R.dataflow, "DF0", "dataflow/A0/DF0/latest", "structure/dataflow/A0/DF0/+"),
    (R.dataflow, "ID0", "dataflow/A0/ID0/latest", "structure/dataflow/A0/ID0/+"),
    (
        R.dataproviderscheme,
        "ID0",
        "dataproviderscheme/A0/ID0/latest",
        "structure/dataproviderscheme/A0/ID0/+",
    ),
    (
        R.datastructure,
        "ID0",
        "datastructure/A0/ID0/latest",
        "structure/datastructure/A0/ID0/+",
    ),
    (
        R.hierarchicalcodelist,
        "ID0",
        "hierarchicalcodelist/A0/ID0/latest",
        "structure/hierarchicalcodelist/A0/ID0/+",
    ),
    (R.metadata, "ID0", "metadata/A0/ID0/latest", "structure/metadata/A0/ID0/+"),
    (
        R.metadataflow,
        "ID0",
        "metadataflow/A0/ID0/latest",
        "structure/metadataflow/A0/ID0/+",
    ),
    (
        R.metadatastructure,
        "ID0",
        "metadatastructure/A0/ID0/latest",
        "structure/metadatastructure/A0/ID0/+",
    ),
    (
        R.namepersonalisationscheme,
        "ID0",
        "namepersonalisationscheme/A0/ID0/latest",
        "structure/namepersonalisationscheme/A0/ID0/+",
    ),
    (
        R.organisationscheme,
        "ID0",
        "organisationscheme/A0/ID0/latest",
        "structure/organisationscheme/A0/ID0/+",
    ),
    (
        R.organisationunitscheme,
        "ID0",
        "organisationunitscheme/A0/ID0/latest",
        "structure/organisationunitscheme/A0/ID0/+",
    ),
    (R.process, "ID0", "process/A0/ID0/latest", "structure/process/A0/ID0/+"),
    (
        R.provisionagreement,
        "ID0",
        "provisionagreement/A0/ID0/latest",
        "structure/provisionagreement/A0/ID0/+",
    ),
    (
        R.reportingtaxonomy,
        "ID0",
        "reportingtaxonomy/A0/ID0/latest",
        "structure/reportingtaxonomy/A0/ID0/+",
    ),
    (
        R.rulesetscheme,
        "ID0",
        "rulesetscheme/A0/ID0/latest",
        "structure/rulesetscheme/A0/ID0/+",
    ),
    (R.schema, "ID0", "schema/A0/ID0/latest", "structure/schema/A0/ID0/+"),
    (R.structure, "ID0", "structure/A0/ID0/latest", "structure/structure/A0/ID0/+"),
    (
        R.structureset,
        "ID0",
        "structureset/A0/ID0/latest",
        "structure/structureset/A0/ID0/+",
    ),
    (
        R.transformationscheme,
        "ID0",
        "transformationscheme/A0/ID0/latest",
        "structure/transformationscheme/A0/ID0/+",
    ),
    (
        R.userdefinedoperatorscheme,
        "ID0",
        "userdefinedoperatorscheme/A0/ID0/latest",
        "structure/userdefinedoperatorscheme/A0/ID0/+",
    ),
    (
        R.vtlmappingscheme,
        "ID0",
        "vtlmappingscheme/A0/ID0/latest",
        "structure/vtlmappingscheme/A0/ID0/+",
    ),
)


class TestURLv21(TestURL):
    """Construction of SDMX REST API 2.1 URLs."""

    @pytest.mark.parametrize("resource_type, resource_id, expected, _", PARAMS)
    def test_join(self, source, resource_type, resource_id, expected, _) -> None:
        from sdmx.rest.v21 import URL

        # Instance can be created
        u = URL(source, resource_type, resource_id)

        # Constructed URL is as expected
        assert f"https://example.com/{expected}" == u.join()


class TestURLv30(TestURL):
    """Construction of SDMX REST API 3.0.0 URLs."""

    @pytest.mark.parametrize("resource_type, resource_id, _, expected", PARAMS)
    def test_join(self, source, resource_type, resource_id, _, expected) -> None:
        from sdmx.rest.v30 import URL

        # Instance can be created
        u = URL(source, resource_type, resource_id)

        # Constructed URL is as expected
        assert f"https://example.com/{expected}" == u.join()
