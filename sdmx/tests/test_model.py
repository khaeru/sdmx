# TODO test str() and repr() implementations
import logging

import pytest
from pytest import raises

from sdmx import Resource
from sdmx.model import v21 as model
from sdmx.model.v21 import (
    ConstraintRole,
    ConstraintRoleType,
    ContentConstraint,
    CubeRegion,
    DataflowDefinition,
    DataSet,
    Dimension,
    DimensionDescriptor,
    Item,
    Key,
)


class TestAnnotation:
    def test_text(self) -> None:
        """`text` can be :class:`str`."""
        a = model.Annotation(text="Foo")

        assert a.text.localizations["en"] == "Foo"


class TestAnnotableArtefact:
    def test_get_annotation(self):
        aa = model.AnnotableArtefact(
            annotations=[
                model.Annotation(id="foo", text="bar"),
                model.Annotation(id="baz", title="baz_title", text="baz_text"),
            ]
        )

        with pytest.raises(KeyError):
            aa.get_annotation(id="bar")

        # Retrieve with 1 key
        assert "bar" == str(aa.get_annotation(id="foo").text)

        # Retrieve with 2 keys
        assert "baz_text" == str(aa.get_annotation(id="baz", title="baz_title").text)

        # Annotations are not removed
        assert 2 == len(aa.annotations)

    def test_pop_annotation(self):
        aa = model.AnnotableArtefact()
        anno = model.Annotation(id="foo", text="bar")

        assert 0 == len(aa.annotations)
        aa.annotations.append(anno)
        assert 1 == len(aa.annotations)

        with pytest.raises(KeyError):
            aa.pop_annotation(id="baz")

        assert anno == aa.pop_annotation(id="foo")
        assert 0 == len(aa.annotations)


class TestConstraint:
    def test_contains(self):
        c = model.Constraint(
            role=model.ConstraintRole(role=ConstraintRoleType["allowable"])
        )
        d = model.Dimension(id="FOO")
        kv = model.KeyValue(value_for=d, id="FOO", value=1)
        key = model.Key([kv])

        with pytest.raises(
            NotImplementedError, match="Constraint does not contain a DataKeySet"
        ):
            key in c

        # Add an empty DKS
        c.data_content_keys = model.DataKeySet(included=True)

        # Empty DKS does not contain `key`
        assert (key in c) is False

        # Add a matching DataKey to the DKS
        c.data_content_keys.keys.append(
            model.DataKey(
                included=True, key_value={d: model.ComponentValue(value_for=d, value=1)}
            )
        )

        # __contains__() returns True
        assert (key in c) is True


class TestMemberValue:
    def test_repr(self):
        mv = model.MemberValue(value="foo")
        assert "'foo'" == repr(mv)
        mv.cascade_values = True
        assert "'foo' + children" == repr(mv)


class TestMemberSelection:
    def test_repr(self):
        ms = model.MemberSelection(
            values_for=model.Component(id="FOO"),
            values=[
                model.MemberValue(value="foo0", cascade_values=True),
                model.MemberValue(value="foo1"),
            ],
        )
        assert "<MemberSelection FOO in {'foo0' + children, 'foo1'}>" == repr(ms)
        ms.included = False
        ms.values.pop(0)
        assert "<MemberSelection FOO not in {'foo1'}>" == repr(ms)


class TestCubeRegion:
    def test_contains(self):
        FOO = model.Dimension(id="FOO")

        cr = model.CubeRegion()
        cr.member[FOO] = model.MemberSelection(
            values_for=FOO, values=[model.MemberValue(value="1")]
        )

        # KeyValue, but no value_for to associate with a particular Dimension
        kv = model.KeyValue(id="FOO", value="1")
        # __contains__() returns False
        assert (kv in cr) is False

        # Containment works with value_for
        kv.value_for = FOO
        assert (kv in cr) is True

    def test_contains_excluded(self):
        # Two dimensions
        FOO = model.Dimension(id="FOO")
        BAR = model.Dimension(id="BAR")

        # A CubeRegion that *excludes* only FOO=1, BAR=A
        cr = model.CubeRegion(included=False)
        cr.member[FOO] = model.MemberSelection(
            values_for=FOO, values=[model.MemberValue(value="1")]
        )
        cr.member[BAR] = model.MemberSelection(
            values_for=BAR, values=[model.MemberValue(value="A")]
        )

        # Targeted key(s) are excluded
        assert (model.Key(FOO="1", BAR="A") in cr) is False

        # Key with more dimensions but fully within this reason
        assert (model.Key(FOO="1", BAR="A", BAZ=3) in cr) is False

        # Other key(s) that intersect only partly with the region are not excluded
        assert (model.Key(FOO="1", BAR="B") in cr) is True
        assert (model.Key(FOO="2", BAR="A", BAZ=3) in cr) is True

        # KeyValues for a subset of the dimensions cannot be excluded, because it
        # cannot be determined if they are fully within the region
        assert (model.KeyValue(value_for=FOO, id="FOO", value="1") in cr) is True

        # KeyValues not associated with a dimension cannot be excluded
        assert (model.KeyValue(value_for=None, id="BAR", value="A") in cr) is True

        # New MemberSelections with included=False. This is a CubeRegion that excludes
        # all values where FOO is other than "1" *and* BAR is other than "A".
        cr.member[FOO] = model.MemberSelection(
            included=False, values_for=FOO, values=[model.MemberValue(value="1")]
        )
        cr.member[BAR] = model.MemberSelection(
            included=False, values_for=BAR, values=[model.MemberValue(value="A")]
        )

        # FOO is other than 1, BAR is other than A → excluded
        assert (model.Key(FOO="2", BAR="B") in cr) is False

        # Other combinations → not excluded
        assert (model.Key(FOO="1", BAR="A") in cr) is True
        assert (model.Key(FOO="1", BAR="B") in cr) is True
        assert (model.Key(FOO="2", BAR="A") in cr) is True

    def test_repr(self):
        FOO = model.Dimension(id="FOO")

        cr = model.CubeRegion()
        cr.member[FOO] = model.MemberSelection(
            values_for=FOO, values=[model.MemberValue(value="1")]
        )

        assert "<CubeRegion include <MemberSelection FOO in {'1'}>>" == repr(cr)
        cr.included = False
        assert "<CubeRegion exclude <MemberSelection FOO in {'1'}>>" == repr(cr)


def test_contentconstraint():
    crole = ConstraintRole(role=ConstraintRoleType["allowable"])
    cr = ContentConstraint(role=crole)
    cr.content = {DataflowDefinition()}
    cr.data_content_region = CubeRegion(included=True, member={})


def test_dataset():
    # Enumeration values can be used to initialize
    from sdmx.model.v21 import ActionType

    DataSet(action=ActionType["information"])


class TestDimension:
    def test_init(self):
        # Constructor
        Dimension(id="CURRENCY", order=0)

    def test_hash(self):
        d = Dimension(id="CURRENCY")
        assert hash("CURRENCY") == hash(d)


class TestDimensionDescriptor:
    def test_from_key(self):
        # from_key()
        key1 = Key(foo=1, bar=2, baz=3)
        dd = DimensionDescriptor.from_key(key1)

        # Key in reverse order
        key2 = Key(baz=3, bar=2, foo=1)
        assert list(key1.values.keys()) == list(reversed(list(key2.values.keys())))
        key3 = dd.order_key(key2)
        assert list(key1.values.keys()) == list(key3.values.keys())


class TestItem:
    def test_name(self) -> None:
        """`name` can be :class:`str`."""
        Item(name="Foo")

    def test_general(self):
        # Add a tree of 10 items
        items = []
        for i in range(10):
            items.append(Item(id="Foo {}".format(i)))

            if i > 0:
                items[-1].parent = items[-2]
                items[-2].child.append(items[-1])

        # __init__(parent=...)
        Item(id="Bar 1", parent=items[0])
        assert len(items[0].child) == 2

        # __init__(child=)
        bar2 = Item(id="Bar 2", child=[items[0]])

        # __contains__()
        assert items[0] in bar2
        assert items[-1] in items[0]

        # get_child()
        assert items[0].get_child("Foo 1") == items[1]

        with raises(ValueError):
            items[0].get_child("Foo 2")

        # Hierarchical IDs constructed automatically
        assert items[0].child[0].hierarchical_id == "Bar 2.Foo 0.Foo 1"


def test_itemscheme_compare(caplog):
    caplog.set_level(logging.DEBUG)

    is0 = model.ItemScheme()
    is1 = model.ItemScheme()

    is0.append(model.Item(id="foo", name="Foo"))
    is1.append(model.Item(id="foo", name="Bar"))

    assert not is0.compare(is1)

    # Log shows that items with same ID have different name
    assert caplog.messages[-2:] == [
        "Not identical: name <en: Foo> != <en: Bar>",
        "…for items with id='foo'",
    ]


class TestAttributeValue:
    def test_str(self):
        assert "FOO" == str(model.AttributeValue(value="FOO"))
        assert "FOO" == str(
            model.AttributeValue(value=model.Code(id="FOO", name="Foo"))
        )


class TestKey:
    @pytest.fixture
    def k1(self):
        # Construct with a dict
        yield Key({"foo": 1, "bar": 2})

    @pytest.fixture
    def k2(self):
        # Construct with kwargs
        yield Key(foo=1, bar=2)

    def test_init(self):
        # Construct with a dict and kwargs is an error
        with raises(ValueError):
            Key({"foo": 1}, bar=2)

        # Construct with a DimensionDescriptor
        d = model.Dimension(id="FOO")
        dd = model.DimensionDescriptor(components=[d])

        k = Key(FOO=1, described_by=dd)

        # KeyValue is associated with Dimension
        assert k["FOO"].value_for is d

    def test_general(self, k1, k2):
        # Results are __eq__ each other
        assert k1 == k2

        # __len__
        assert len(k1) == 2

        # __contains__: symmetrical if keys are identical
        assert k1 in k2
        assert k2 in k1
        assert Key(foo=1) in k1
        assert k1 not in Key(foo=1)

        # Set and get using item convenience
        k1["baz"] = 3  # bare value is converted to a KeyValue
        assert k1["foo"] == 1

        # __str__
        assert str(k1) == "(foo=1, bar=2, baz=3)"

        # copying: returns a new object equal to the old one
        k2 = k1.copy()
        assert id(k1) != id(k2) and k1 == k2
        # copy with changes
        k2 = Key(foo=1, bar=2).copy(baz=3)
        assert id(k1) != id(k2) and k1 == k2

        # __add__: Key with something else
        with raises(NotImplementedError):
            k1 + 4
        # Two Keys
        k2 = Key(foo=1) + Key(bar=2)
        assert k2 == k1

        # __radd__: adding a Key to None produces a Key
        assert None + k1 == k1
        # anything else is an error
        with raises(NotImplementedError):
            4 + k1

        # get_values(): preserve ordering
        assert k1.get_values() == (1, 2, 3)


class TestDataKeySet:
    @pytest.fixture
    def dks(self):
        return model.DataKeySet(included=True)

    def test_len(self, dks):
        """__len__() works."""
        assert 0 == len(dks)


class TestContact:
    def test_init(self) -> None:
        model.Contact(
            name="Jane Smith", org_unit="Statistics Office", responsibility="Director"
        )


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


def test_deprecated():
    """Deprecation warning when importing SDMX 2.1-specific class from :mod:`.model`."""
    with pytest.warns(
        DeprecationWarning, match=r"DataStructureDefinition from sdmx\.model"
    ):
        from sdmx.model import DataStructureDefinition  # noqa: F401
