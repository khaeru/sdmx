# TODO test str() and repr() implementations
import logging

import pydantic
import pytest
from pytest import raises

from sdmx import model
from sdmx.model import (
    DEFAULT_LOCALE,
    AttributeDescriptor,
    AttributeValue,
    ConstraintRole,
    ConstraintRoleType,
    ContentConstraint,
    CubeRegion,
    DataAttribute,
    DataflowDefinition,
    DataSet,
    DataStructureDefinition,
    Dimension,
    DimensionDescriptor,
    GroupKey,
    IdentifiableArtefact,
    Item,
    ItemScheme,
    Key,
    Observation,
)


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


class TestCubeRegion:
    def test_contains(self):
        cr = model.CubeRegion()
        d = model.Dimension(id="FOO")
        cr.member[d] = model.MemberSelection(
            values_for=d, values=[model.MemberValue(value="1")]
        )

        # KeyValue, but no value_for to associate with a particular Dimension
        kv = model.KeyValue(id="FOO", value="1")
        # __contains__() returns False
        assert (kv in cr) is False

        # Containment works with value_for
        kv.value_for = d
        assert (kv in cr) is True


def test_contentconstraint():
    crole = ConstraintRole(role=ConstraintRoleType["allowable"])
    cr = ContentConstraint(role=crole)
    cr.content = {DataflowDefinition()}
    cr.data_content_region = CubeRegion(included=True, member={})


def test_dataset():
    # Enumeration values can be used to initialize
    from sdmx.model import ActionType

    DataSet(action=ActionType["information"])


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
        assert all(isinstance(k, model.Key) for k in keys0)
        assert 2 ** 3 == len(keys0)

        # Iterate over only some dimensions
        keys1 = list(dsd.iter_keys(dims=["foo"]))
        assert 2 == len(keys1)
        assert "<Key: foo=1, bar=(bar), baz=(baz)>" == repr(keys1[0])

        # Create a ContentConstraint (containing a single CubeRegion(included=True))
        cc0 = dsd.make_constraint(dict(foo="1", bar="2+5", baz="3+6"))

        # Resulting Keys have only "1" for the "foo" dimension
        keys2 = list(dsd.iter_keys(constraint=cc0))
        assert 1 * 2 ** 2 == len(keys2)

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


def test_dimension():
    # Constructor
    Dimension(id="CURRENCY", order=0)


def test_dimensiondescriptor():
    # from_key()
    key1 = Key(foo=1, bar=2, baz=3)
    dd = DimensionDescriptor.from_key(key1)

    # Key in reverse order
    key2 = Key(baz=3, bar=2, foo=1)
    assert list(key1.values.keys()) == list(reversed(list(key2.values.keys())))
    key3 = dd.order_key(key2)
    assert list(key1.values.keys()) == list(key3.values.keys())


class TestIdentifiableArtefact:
    def test_general(self):
        urn = (
            "urn:sdmx:org.sdmx.infomodel.conceptscheme.ConceptScheme=IT1:VARIAB_ALL"
            "(9.6)"
        )
        urn_pat = urn.replace("(", r"\(").replace(")", r"\)")

        with pytest.raises(
            ValueError, match=f"ID BAD_URN does not match URN {urn_pat}"
        ):
            model.IdentifiableArtefact(id="BAD_URN", urn=urn)

        # IdentifiableArtefact is hashable
        ia = IdentifiableArtefact()
        assert hash(ia) == id(ia)

        ia = IdentifiableArtefact(id="foo")
        assert hash(ia) == hash("foo")

        # Subclass is hashable
        ad = AttributeDescriptor()
        assert hash(ad) == id(ad)

    def test_sort(self):
        """Test IdentifiableArtefact.__lt__."""
        # Items of the same class can be sorted
        items = [Item(id="b"), Item(id="a")]
        assert list(reversed(items)) == sorted(items)

        with pytest.raises(
            TypeError,
            match=(
                "'<' not supported between instances of 'Item' and "
                "'DataStructureDefinition'"
            ),
        ):
            sorted([DataStructureDefinition(id="c")] + items)


def test_nameable(caplog):
    na1 = model.NameableArtefact(
        name=dict(en="Name"), description=dict(en="Description")
    )
    na2 = model.NameableArtefact()

    assert not na1.compare(na2)
    assert caplog.messages[-1] == "Not identical: name <en: Name> != <>"

    na2.name["en"] = "Name"

    assert not na1.compare(na2)
    assert caplog.messages[-1] == "Not identical: description <en: Description> != <>"

    na2.description["en"] = "Description"

    assert na1.compare(na2)


def test_maintainable():
    urn = "urn:sdmx:org.sdmx.infomodel.conceptscheme.ConceptScheme=IT1:VARIAB_ALL(9.6)"
    ma = model.MaintainableArtefact(id="VARIAB_ALL", urn=urn)

    # Version is parsed from URN
    assert ma.version == "9.6"

    # Mismatch raises an exception
    with pytest.raises(ValueError, match="Version 9.7 does not match URN"):
        model.MaintainableArtefact(version="9.7", urn=urn)

    # Maintainer is parsed from URN
    assert ma.maintainer == model.Agency(id="IT1")

    # Mismatch raises an exception
    with pytest.raises(ValueError, match="Maintainer FOO does not match URN"):
        model.MaintainableArtefact(maintainer=model.Agency(id="FOO"), urn=urn)


def test_internationalstring():
    # Constructor; the .name attribute is an InternationalString
    i = Item(id="ECB")

    # Set and get using the attribute directly
    i.name.localizations["DE"] = "Europäische Zentralbank"
    assert i.name.localizations["DE"] == "Europäische Zentralbank"

    # Set and get using item convenience
    i.name["FR"] = "Banque centrale européenne"
    assert len(i.name.localizations) == 2
    assert i.name["FR"] == "Banque centrale européenne"

    # repr() gives all localizations
    assert repr(i.name) == "\n".join(
        sorted(["DE: Europäische Zentralbank", "FR: Banque centrale européenne"])
    )

    # Setting with a string directly sets the value in the default locale
    i.name = "European Central Bank"
    assert len(i.name.localizations) == 1
    assert i.name.localizations[DEFAULT_LOCALE] == "European Central Bank"

    # Setting with a (locale, text) tuple
    i.name = ("FI", "Euroopan keskuspankki")
    assert len(i.name.localizations) == 1

    # Setting with a dict()
    i.name = {"IT": "Banca centrale europea"}
    assert len(i.name.localizations) == 1

    # Using some other type is an error
    with raises(pydantic.ValidationError):
        i.name = 123

    # Same, but in the constructor
    i2 = Item(id="ECB", name="European Central Bank")

    # str() uses the default locale
    assert str(i2.name) == "European Central Bank"

    # Creating with name=None raises an exception…
    with raises(pydantic.ValidationError, match="none is not an allowed value"):
        Item(id="ECB", name=None)

    # …giving empty dict is equivalent to giving nothing
    i3 = Item(id="ECB", name={})
    assert i3.name.localizations == Item(id="ECB").name.localizations

    # Create with iterable of 2-tuples
    i4 = Item(
        id="ECB",
        name=[("DE", "Europäische Zentralbank"), ("FR", "Banque centrale européenne")],
    )
    assert i4.name["FR"] == "Banque centrale européenne"

    # Compares equal with same contents
    is1 = model.InternationalString(en="Foo", fr="Le foo")
    is2 = model.InternationalString(en="Foo", fr="Le foo")
    assert is1 == is2


class TestItem:
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


def test_itemscheme():
    is0 = ItemScheme(id="is0")
    foo0 = Item(id="foo0")

    # With a single Item

    # append()
    is0.append(foo0)

    # __getattr__
    assert is0.foo0 is foo0

    # __getitem__
    assert is0["foo0"] is foo0

    # __contains__
    assert "foo0" in is0
    assert foo0 in is0

    # __len__
    assert len(is0) == 1

    # __repr__
    assert repr(is0) == "<ItemScheme is0 (1 items)>"

    # __iter__
    assert all(i is foo0 for i in is0)

    # With multiple Items

    foo1 = Item(id="foo1")
    foo2 = Item(id="foo2")
    items_list = [foo0, foo1, foo2]
    items_dict = {"foo0": foo0, "foo1": foo1, "foo2": foo2}

    # set with a non-dict
    is0.items = items_list
    assert is0.items == items_dict

    # set with a dict
    is0.items = items_dict
    assert is0.items == items_dict

    # extend()
    is0.items = [foo0]
    is0.extend(items_list[1:])
    assert is0.items == items_dict

    # setdefault()
    bar0 = is0.setdefault(id="bar")
    assert bar0.id == "bar"

    with raises(ValueError):
        is0.setdefault(foo0, id="bar")

    is0.setdefault(id="bar1", parent="foo0")
    bar1 = is0.setdefault(id="bar1", parent=foo0)

    # get_hierarchical()
    assert is0.get_hierarchical("foo0.bar1") == bar1


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


def test_observation():
    obs = Observation()

    # Set by item name
    obs.attached_attribute["TIME_PERIOD"] = 3
    # NB the following does not work; see Observation.attrib()
    # obs.attrib['TIME_PERIOD'] = 3

    obs.attached_attribute["CURRENCY"] = "USD"

    # Access by attribute name
    assert obs.attrib.TIME_PERIOD == 3
    assert obs.attrib.CURRENCY == "USD"

    # Access by item index
    assert obs.attrib[1] == "USD"

    # Add attributes
    obs.attached_attribute["FOO"] = "1"
    obs.attached_attribute["BAR"] = "2"
    assert obs.attrib.FOO == "1" and obs.attrib["BAR"] == "2"

    # Using classes
    da = DataAttribute(id="FOO")
    av = AttributeValue(value_for=da, value="baz")
    obs.attached_attribute[da.id] = av
    assert obs.attrib[da.id] == "baz"


class TestDataKeySet:
    @pytest.fixture
    def dks(self):
        return model.DataKeySet(included=True)

    def test_len(self, dks):
        """__len__() works."""
        assert 0 == len(dks)


def test_get_class():
    with pytest.raises(ValueError, match="Package 'codelist' invalid for Category"):
        model.get_class(name="Category", package="codelist")
