import pytest

from sdmx.model.common import ConstraintRole, ConstraintRoleType
from sdmx.model.v30 import (
    DataConstraint,
    GeoCodelistType,
    GeoFeatureSetCode,
    GeographicCodelist,
    GeoGridCode,
    GeoGridCodelist,
    HierarchicalCode,
    Hierarchy,
    HierarchyAssociation,
    Level,
    MetadataConstraint,
    MetadataProvider,
    MetadataProviderScheme,
)

# §4.3: Codelist


class TestGeoGridCode:
    def test_init(self):
        GeoGridCode(geo_cell="foo")


class TestGeoFeatureSetCode:
    def test_init(self):
        GeoFeatureSetCode(value="foo")


class TestGeographicCodelist:
    def test_init(self):
        cl = GeographicCodelist()

        assert GeoCodelistType.geographic == cl.geo_type


class TestGeoGridCodelist:
    def test_init(self):
        cl = GeoGridCodelist()

        assert GeoCodelistType.geogrid == cl.geo_type


# §4.7: OrganisationScheme


class TestMetadataProvider:
    def test_init(self):
        MetadataProvider()


class TestMetadataProviderScheme:
    def test_init(self):
        MetadataProviderScheme()


# §8: Hierarchy


class TestLevel:
    def test_init(self):
        Level()


class TestHierarchicalCode:
    def test_init(self):
        HierarchicalCode()


class TestHierarchy:
    def test_init(self):
        Hierarchy()


class TestHierarchyAssociation:
    def test_init(self):
        HierarchyAssociation()


# §12.3: Constraints


_ROLE_PARAMS = [
    ConstraintRole(role=ConstraintRoleType.actual),
    ConstraintRole(role=ConstraintRoleType.allowable),
    ConstraintRoleType.actual,
    ConstraintRoleType.allowable,
    "actual",
    "allowable",
    pytest.param("foo", marks=pytest.mark.xfail(raises=KeyError)),
]


class TestDataConstraint:
    @pytest.mark.parametrize("role", _ROLE_PARAMS)
    def test_init(self, role):
        DataConstraint(role=role)


class TestMetadataConstraint:
    @pytest.mark.parametrize("role", _ROLE_PARAMS)
    def test_init(self, role):
        MetadataConstraint(role=role)
