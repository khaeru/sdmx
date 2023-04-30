from operator import attrgetter
from typing import List

import pytest

from sdmx.model.common import ConstraintRoleType
from sdmx.model.v21 import (
    ComponentList,
    ConstraintRole,
    ContentConstraint,
    CubeRegion,
    DataStructureDefinition,
    Dimension,
    DimensionDescriptor,
    KeyValue,
)


class TestContentConstraint:
    @pytest.fixture
    def dsd(self) -> DataStructureDefinition:
        return DataStructureDefinition()

    def test_to_query_string(self, caplog, dsd) -> None:
        cc = ContentConstraint(
            role=ConstraintRole(role=ConstraintRoleType["allowable"])
        )

        with pytest.raises(RuntimeError, match="does not contain"):
            cc.to_query_string(dsd)

        cc.data_content_region.extend([CubeRegion(), CubeRegion()])

        cc.to_query_string(dsd)

        assert "first of 2 CubeRegions" in caplog.messages[-1]


class TestComponentList:
    @pytest.fixture(scope="function")
    def cl(self):
        # Use concrete class to test abstract parent class ComponentList
        return DimensionDescriptor()

    @pytest.fixture(scope="function")
    def components(self):
        return [Dimension(id="C1"), Dimension(id="C2"), Dimension(id="C3")]

    def test_append(self, cl: ComponentList, components: List[Dimension]) -> None:
        # Components have no order
        assert (None, None, None) == tuple(map(attrgetter("order"), components))

        cl.append(components[2])
        cl.append(components[1])
        cl.append(components[0])

        # Order is assigned to components when they are added
        assert 1 == components[2].order
        assert 2 == components[1].order
        assert 3 == components[0].order

    def test_extend_no_order(
        self, cl: ComponentList, components: List[Dimension]
    ) -> None:
        cl.extend(components)

        # extend() also adds order
        assert (1, 2, 3) == tuple(map(attrgetter("order"), components))

    def test_extend_order(self, cl: ComponentList, components: List[Dimension]) -> None:
        components[2].order = 1
        components[1].order = 2
        components[0].order = 3

        cl.extend(components)

        # Order is not altered
        assert (3, 2, 1) == tuple(map(attrgetter("order"), components))


class TestKeyValue:
    def test_sort(self) -> None:
        kv1 = KeyValue(id="DIM", value="3")
        assert kv1 < KeyValue(id="DIM", value="foo")
        assert kv1 < "foo"
