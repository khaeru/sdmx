import pytest

from sdmx.model import common, v30
from sdmx.model.common import ConstraintRole, ConstraintRoleType
from sdmx.model.v30 import (
    Annotation,
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
from sdmx.testing import CompareTests

# §3.2: Basic structures


class TestAnnotation:
    def test_value(self) -> None:
        a0 = Annotation()

        # Value defaults None
        assert None is a0.value

        # Value can be set
        a0.value = "foo"

        # Value can be retrieved
        assert "foo" == a0.value

        # Value can be set through constructor
        a1 = Annotation(value="bar")
        assert "bar" == a1.value


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


# §5.4: Data Set


class TestObservation(CompareTests):
    @pytest.fixture
    def obj(self) -> v30.Observation:
        return v30.Observation(
            attached_attribute={"FOO": common.AttributeValue(value="f1")},
            dimension=common.Key(BAR="b1"),
            group_keys={common.GroupKey(id="g1")},
            series_key=common.SeriesKey(),
            value=1.0,
            value_for=v30.Measure(id="m1"),
        )

    def test_compare(self, obj: v30.Observation, callback=None) -> None:
        """:py:`compare(…)` is :any:`False` when .value_for is changed.

        For other attributes, see test_common.TestBaseObservation.test_compare.
        """
        super().test_compare(
            obj, lambda obs: setattr(obs, "value_for", v30.Measure(id="m2"))
        )


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
