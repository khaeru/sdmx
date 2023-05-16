from operator import attrgetter
from typing import List

import pytest

from sdmx.model.common import ConstraintRoleType
from sdmx.model.v21 import (
    Code,
    ComponentList,
    ConstraintRole,
    ContentConstraint,
    CubeRegion,
    DataAttribute,
    DataflowDefinition,
    DataStructureDefinition,
    Dimension,
    DimensionDescriptor,
    GroupKey,
    Key,
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


class TestDataAttribute:
    def test_hash(self):
        cl = [DataAttribute(id="FOO"), DataAttribute(id="BAR")]
        print(cl[0].__eq__)
        print(f"{'FOO' == cl[0] = }")
        assert "FOO" in cl
        assert "BAZ" not in cl


class TestCode:
    @pytest.fixture
    def c(self) -> Code:
        yield Code(id="FOO", name=("en", "Foo"))

    def test_id(self) -> None:
        with pytest.raises(TypeError, match="got int"):
            Code(id=1)

    def test_hash(self, c):
        s = set([c])
        s.add(c)

        assert 1 == len(s)

    def test_name(self, c) -> None:
        assert "Foo" == c.name.localizations["en"]

    def test_str(self, c) -> None:
        assert "FOO" == str(c) == f"{c}"

    def test_repr(self, c) -> None:
        assert "<Code FOO: Foo>" == repr(c)


class TestDataStructureDefinition:
    def test_general(self):
        dsd = DataStructureDefinition()

        # Convenience methods
        da = dsd.attributes.getdefault(id="foo")
        assert isinstance(da, DataAttribute)

        d = dsd.dimensions.getdefault(id="baz", order=-1)
        assert isinstance(d, Dimension)

        # make_key(GroupKey, ..., extend=True, group_id=None)
        gk = dsd.make_key(GroupKey, dict(foo=1, bar=2), extend=True, group_id=None)

        # … does not create a GroupDimensionDescriptor (anonymous group)
        assert gk.described_by is None
        assert len(dsd.group_dimensions) == 0

        # But does create the 'bar' dimension
        assert "bar" in dsd.dimensions

        # make_key(..., group_id=...) creates a GroupDimensionDescriptor
        gk = dsd.make_key(GroupKey, dict(foo=1, baz2=4), extend=True, group_id="g1")
        assert gk.described_by is dsd.group_dimensions["g1"]
        assert len(dsd.group_dimensions) == 1

        # …also creates the "baz2" dimension and adds it to the GDD
        assert dsd.dimensions.get("baz2") is dsd.group_dimensions["g1"].get("baz2")

        # from_keys()
        key1 = Key(foo=1, bar=2, baz=3)
        key2 = Key(foo=4, bar=5, baz=6)
        DataStructureDefinition.from_keys([key1, key2])

    def test_iter_keys(self, caplog):
        dsd = DataStructureDefinition.from_keys(
            [Key(foo=1, bar=2, baz=3), Key(foo=4, bar=5, baz=6)]
        )

        keys0 = list(dsd.iter_keys())
        assert all(isinstance(k, Key) for k in keys0)
        assert 2**3 == len(keys0)

        # Iterate over only some dimensions
        keys1 = list(dsd.iter_keys(dims=["foo"]))
        assert 2 == len(keys1)
        assert "<Key: foo=1, bar=(bar), baz=(baz)>" == repr(keys1[0])

        # Create a ContentConstraint (containing a single CubeRegion(included=True))
        cc0 = dsd.make_constraint(dict(foo="1", bar="2+5", baz="3+6"))

        # Resulting Keys have only "1" for the "foo" dimension
        keys2 = list(dsd.iter_keys(constraint=cc0))
        assert 1 * 2**2 == len(keys2)

        # Use make_constraint() to create & modify a different CubeRegion
        cc1 = dsd.make_constraint(dict(baz="6"))
        cr = cc1.data_content_region[0]
        # Exclude this region
        cr.included = False

        # Add to `cc0` so that there are two CubeRegions
        cc0.data_content_region.append(cr)

        # Resulting keys have only "1" for the "foo" dimension, and not "6" for the
        # "baz" dimension
        keys3 = list(dsd.iter_keys(constraint=cc0))
        assert 1 * 2 * 1 == len(keys3)

        # Call ContentConstraint.iter_keys()

        # Message is logged
        assert 1 * 2 * 1 == len(list(cc0.iter_keys(dsd)))
        assert (
            "<DataStructureDefinition (missing id)> is not in "
            "<ContentConstraint (missing id)>.content" in caplog.messages
        )
        caplog.clear()

        # Add the DSD to the content referenced by the ContentConstraint
        cc0.content.add(dsd)
        assert 1 * 2 * 1 == len(list(cc0.iter_keys(dsd)))
        assert 0 == len(caplog.messages)

        # Call DataflowDefinition.iter_keys()
        dfd = DataflowDefinition(structure=dsd)
        keys4 = list(dfd.iter_keys(constraint=cc0))
        assert 1 * 2 * 1 == len(keys4)


class TestKeyValue:
    def test_sort(self) -> None:
        kv1 = KeyValue(id="DIM", value="3")
        assert kv1 < KeyValue(id="DIM", value="foo")
        assert kv1 < "foo"
