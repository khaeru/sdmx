import pytest

from sdmx import Resource
from sdmx.model import v21 as model


@pytest.mark.parametrize(
    "args,expected",
    [
        pytest.param(
            dict(name="Category", package="codelist"),
            None,
            marks=pytest.mark.xfail(
                raises=ValueError, reason="Package 'codelist' invalid for Category"
            ),
        ),
        # Resource types appearing in StructureMessage
        (dict(name=Resource.agencyscheme), model.AgencyScheme),
        (dict(name=Resource.categorisation), model.Categorisation),
        (dict(name=Resource.categoryscheme), model.CategoryScheme),
        (dict(name=Resource.codelist), model.Codelist),
        (dict(name=Resource.conceptscheme), model.ConceptScheme),
        (dict(name=Resource.contentconstraint), model.ContentConstraint),
        (dict(name=Resource.dataflow), model.DataflowDefinition),
        (dict(name=Resource.organisationscheme), model.OrganisationScheme),
        (dict(name=Resource.provisionagreement), model.ProvisionAgreement),
        pytest.param(
            dict(name=Resource.structure),
            model.DataStructureDefinition,
            marks=pytest.mark.skip(reason="Ambiguous value, not implemented"),
        ),
    ],
)
def test_get_class(args, expected):
    assert expected is model.get_class(**args)


def test_deprecated_import():
    """Deprecation warning when importing SDMX 2.1-specific class from :mod:`.model`."""
    with pytest.warns(
        DeprecationWarning, match=r"DataStructureDefinition from sdmx\.model"
    ):
        from sdmx.model import DataStructureDefinition  # noqa: F401

    with pytest.raises(ImportError):
        from sdmx.model import Foo  # noqa: F401
