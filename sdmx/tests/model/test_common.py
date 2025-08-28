import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import date

import pytest

import sdmx.model as model
from sdmx.model import common, v21
from sdmx.model.common import (
    Agency,
    AnnotableArtefact,
    BaseAnnotation,
    Component,
    ComponentList,
    Contact,
    IdentifiableArtefact,
    Item,
    ItemScheme,
    NameableArtefact,
    Representation,
)
from sdmx.testing import CompareTests


class TestBaseAnnotation:
    def test_text(self) -> None:
        """`text` can be :class:`str`."""
        a = BaseAnnotation(text="Foo")

        assert a.text.localizations["en"] == "Foo"


class TestAnnotableArtefact:
    @pytest.fixture
    def aa(self) -> AnnotableArtefact:
        return AnnotableArtefact(
            annotations=[
                v21.Annotation(id="foo", text="bar"),
                v21.Annotation(id="baz", title="baz_title", text="baz_text"),
            ]
        )

    def test_compare(self, aa: AnnotableArtefact) -> None:
        aa_other = AnnotableArtefact()

        assert False is aa.compare(aa_other)

    def test_get_annotation(self, aa: AnnotableArtefact) -> None:
        with pytest.raises(KeyError):
            aa.get_annotation(id="bar")

        # Retrieve with 1 key
        assert "bar" == str(aa.get_annotation(id="foo").text)

        # Retrieve with 2 keys
        assert "baz_text" == str(aa.get_annotation(id="baz", title="baz_title").text)

        # Annotations are not removed
        assert 2 == len(aa.annotations)

    def test_pop_annotation(self):
        aa = AnnotableArtefact()
        anno = v21.Annotation(id="foo", text="bar")

        assert 0 == len(aa.annotations)
        aa.annotations.append(anno)
        assert 1 == len(aa.annotations)

        with pytest.raises(KeyError):
            aa.pop_annotation(id="baz")

        assert anno == aa.pop_annotation(id="foo")
        assert 0 == len(aa.annotations)

    def test_eval_annotation(self, caplog) -> None:
        aa = AnnotableArtefact()

        value = dict(foo=1.1, bar=2, baz=True)

        aa.annotations.append(v21.Annotation(id="test-anno0", text=repr(value)))
        aa.annotations.append(v21.Annotation(id="test-anno1", text="value['foo']"))

        # Returns None for a missing ID
        assert None is aa.eval_annotation(id="wrong-id")

        # Entire value is retrieved
        assert value == aa.eval_annotation(id="test-anno0")

        # Cannot handle a variable reference with no globals;
        assert "value['foo']" == aa.eval_annotation(id="test-anno1")
        assert "name 'value' is not defined" in caplog.messages[0]
        caplog.clear()

        # Globals can be used if passed
        assert value["foo"] == aa.eval_annotation(
            id="test-anno1", globals=dict(value=value)
        )


URN = "urn:sdmx:org.sdmx.infomodel.conceptscheme.ConceptScheme=IT1:VARIAB_ALL(9.6)"


class TestIdentifiableArtefact(CompareTests):
    @pytest.fixture
    def obj(self) -> common.IdentifiableArtefact:
        return common.IdentifiableArtefact(
            id="VARIAB_ALL",
            uri="https://example.com",
            urn=URN,
        )

    @pytest.mark.parametrize(
        "callback",
        (
            None,
            lambda obj: setattr(obj, "id", "VARIAB_ALL_"),
            lambda obj: setattr(obj, "uri", "https://example.com/foo"),
            lambda obj: setattr(obj, "urn", URN.replace("VARIAB_ALL", "X")),
        ),
    )
    def test_compare(self, obj: common.IdentifiableArtefact, callback) -> None:
        super().test_compare(obj, callback)

    def test_init_empty_id(self):
        """IdentifiableArtefact can be initialized with an empty :class:`str` as ID."""
        # No id= parameter → id attribute is MissingID
        ia0 = IdentifiableArtefact()
        assert common.MissingID == ia0.id
        assert common.MissingID is ia0.id

        # Empty string parameter → id attribute is empty string
        ia1 = IdentifiableArtefact(id="")
        assert "" == ia1.id

    def test_init_urn(self):
        """IdentifiableArtefact can be initialized with URN."""
        ia = IdentifiableArtefact(urn=URN)
        assert "VARIAB_ALL" == ia.id

    def test_general(self) -> None:
        urn_pat = URN.replace("(", r"\(").replace(")", r"\)")

        with pytest.raises(
            ValueError, match=f"ID BAD_URN does not match URN {urn_pat}"
        ):
            IdentifiableArtefact(id="BAD_URN", urn=URN)

        # IdentifiableArtefact is hashable
        ia = IdentifiableArtefact()
        assert hash(ia) == id(ia)

        ia = IdentifiableArtefact(id="foo")
        assert hash(ia) == hash("foo")

        # Subclass is hashable
        ad = model.AttributeDescriptor()
        assert hash(ad) == id(ad)

    def test_gt_lt(self):
        """Test IdentifiableArtefact.__gt__ and IdentifiableArtefact.__lt__."""
        # IdentifiableArtefact of the same class can be sorted
        items = [Item(id="b"), Item(id="a")]
        assert list(reversed(items)) == sorted(items)

        # Mixed IdentifiableArtefact and str can be sorted
        assert [Item(id="a"), "b", "c"] == sorted(["b", Item(id="a"), "c"])

    def test_hash_subclass(self):
        @dataclass
        class Foo(IdentifiableArtefact):
            __hash__ = IdentifiableArtefact.__hash__

        f = Foo(id="FOO")
        assert hash("FOO") == hash(f)


class TestNameableArtefact:
    def test_compare(self, caplog) -> None:
        na1 = NameableArtefact(name=dict(en="Name"), description=dict(en="Description"))
        na2 = NameableArtefact()

        assert not na1.compare(na2)
        assert "Not identical: NameableArtefact.name=en: Name != " in caplog.messages
        caplog.clear()

        na2.name["en"] = "Name"

        assert not na1.compare(na2)
        assert (
            "Not identical: NameableArtefact.description=en: Description != "
            in caplog.messages
        )

        na2.description["en"] = "Description"

        assert na1.compare(na2)

    def test_eq(self):
        na = NameableArtefact(id="FOO", name="Foo")
        assert na == "FOO"


class TestVersionableArtefact(CompareTests):
    @pytest.fixture
    def obj(self) -> common.VersionableArtefact:
        return common.VersionableArtefact(
            valid_from="0001-01-01",
            valid_to="9999-12-31",
            version="1.0.0",
        )

    @pytest.mark.parametrize(
        "callback",
        (
            None,
            lambda obj: setattr(obj, "valid_from", "0001-01-02"),
            lambda obj: setattr(obj, "valid_to", "9999-12-30"),
            lambda obj: setattr(obj, "version", "1.0.1"),
        ),
    )
    def test_compare(self, obj: common.VersionableArtefact, callback) -> None:
        super().test_compare(obj, callback)

    def test_urn(self) -> None:
        va = common.VersionableArtefact(id="VARIAB_ALL", urn=URN)

        # Version is parsed from URN
        assert va.version == "9.6"

        # Mismatch raises an exception
        with pytest.raises(ValueError, match="Version '9.7' does not match URN"):
            common.VersionableArtefact(version="9.7", urn=URN)

    def test_version_none(self) -> None:
        va = common.VersionableArtefact(version="None")
        assert va.version is None


class TestMaintainableArtefact(CompareTests):
    @pytest.fixture
    def obj(self) -> common.MaintainableArtefact:
        return common.MaintainableArtefact(
            is_external_reference=True,
            is_final=True,
            maintainer=common.Agency(id="A1"),
            service_url="https://example.com",
            structure_url="https://example.com",
        )

    @pytest.mark.parametrize(
        "callback",
        (
            None,
            lambda obj: setattr(obj, "is_external_reference", False),
            lambda obj: setattr(obj, "is_final", False),
            lambda obj: setattr(obj, "maintainer", common.Agency(id="A2")),
            lambda obj: setattr(obj, "service_url", "https://example.com/foo"),
            lambda obj: setattr(obj, "structure_url", "https://example.com/foo"),
        ),
    )
    def test_compare(self, obj: common.MaintainableArtefact, callback) -> None:
        super().test_compare(obj, callback)

    def test_urn(self) -> None:
        ma = common.MaintainableArtefact(id="VARIAB_ALL", urn=URN)

        # Maintainer is parsed from URN
        assert ma.maintainer == Agency(id="IT1")

        # Mismatch raises an exception
        with pytest.raises(ValueError, match="Maintainer FOO does not match URN"):
            common.MaintainableArtefact(maintainer=Agency(id="FOO"), urn=URN)


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

        with pytest.raises(ValueError):
            items[0].get_child("Foo 2")

        # Hierarchical IDs constructed automatically
        assert items[0].child[0].hierarchical_id == "Bar 2.Foo 0.Foo 1"


class TestItemScheme:
    def test_compare0(self, caplog):
        caplog.set_level(logging.DEBUG)

        is0 = ItemScheme()
        is1 = ItemScheme()

        is0.append(Item(id="foo", name="Foo"))
        is1.append(Item(id="foo", name="Bar"))

        assert not is0.compare(is1)

        # Log shows that items with same ID have different name
        assert "Not identical: Item.name=en: Foo != en: Bar" in caplog.messages
        assert (
            "Not identical: ItemScheme.items={'foo': <Item foo: Foo>} != {'foo': <Item foo: Bar>}"
            in caplog.messages
        )

    def test_compare1(self) -> None:
        is0: ItemScheme = ItemScheme(id="is0")
        is0.append(Item(id="foo"))

        is1: ItemScheme = ItemScheme(id="is0")
        is1.append(Item(id="foo"))

        assert is0.compare(is1) is True

        is2: ItemScheme = ItemScheme(id="is0")
        is2.append(Item(id="bar"))

        assert is0.compare(is2) is False

    def test_deepcopy(self) -> None:
        """ItemScheme may be :func:`.deepcopy`'d."""
        is0: ItemScheme = ItemScheme(id="is0")

        deepcopy(is0)

    def test_get_hierarchical(self) -> None:
        is0: ItemScheme = ItemScheme(id="is0")
        foo: Item = Item(id="foo")
        bar: Item = Item(id="bar")
        foo.append_child(bar)

        is0.append(foo)
        is0.append(bar)

        assert bar is is0.get_hierarchical("foo.bar")

        # With non-hierarchical ID
        assert foo is is0.get_hierarchical("foo")

        with pytest.raises(KeyError):
            is0.get_hierarchical("foo.baz")

    def test_other(self) -> None:
        is0: ItemScheme = ItemScheme(id="is0")
        foo0: Item = Item(id="foo0")

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

        foo1: Item = Item(id="foo1")
        foo2: Item = Item(id="foo2")
        items_list = [foo0, foo1, foo2]
        items_dict = {"foo0": foo0, "foo1": foo1, "foo2": foo2}

        # set with a non-dict
        is0.items = {i.id: i for i in items_list}
        assert is0.items == items_dict

        # set with a dict
        is0.items = items_dict
        assert is0.items == items_dict

        # extend()
        is0.items = {foo0.id: foo0}
        is0.extend(items_list[1:])
        assert is0.items == items_dict

        # setdefault()
        bar0 = is0.setdefault(id="bar")
        assert bar0.id == "bar"

        with pytest.raises(ValueError):
            is0.setdefault(foo0, id="bar")

        is0.setdefault(id="bar1", parent="foo0")
        bar1 = is0.setdefault(id="bar1", parent=foo0)

        # get_hierarchical()
        assert is0.get_hierarchical("foo0.bar1") is bar1


class TestRepresentation:
    def test_repr(self) -> None:
        is0: ItemScheme = ItemScheme(id="is0")
        r = Representation(enumerated=is0)
        assert "<Representation: is0, []>" == repr(r)


class TestComponentList:
    def test_compare(self, caplog) -> None:
        """Test comparison of two CL with mismatched components."""

        components = [Component(id=s) for s in ("FOO", "BAR", "BAZ")]

        cl1: ComponentList = ComponentList(id="CL", components=components)
        cl2: ComponentList = ComponentList(id="CL", components=components[:-1])

        # cl1 and cl2 compare as different
        assert False is cl1.compare(cl2)

        # commented: This message is currently disabled
        # # Log message is emitted for mismatched components
        # assert "CL has no component with ID 'BAZ'" in caplog.messages


class TestContact:
    def test_init(self):
        Contact(
            name="Jane Smith", org_unit="Statistics Office", responsibility="Director"
        )

        c1 = Contact()
        c2 = Contact()

        c2.name = "foo"

        assert repr(c1) != repr(c2)


class TestStructure(CompareTests):
    @pytest.fixture
    def obj(self):
        # Use BaseDataStructureDefinition as a concrete/less abstract subclass
        return common.BaseDataStructureDefinition()

    @pytest.mark.parametrize(
        "callback",
        (
            None,
            lambda obj: obj.attributes.getdefault(id="a1"),
            lambda obj: obj.dimensions.getdefault(id="d1"),
        ),
    )
    def test_compare(self, obj: common.Structure, callback) -> None:
        """:py:`compare(…)` is :any:`False` when attributes are changed."""
        super().test_compare(obj, callback)

    def test_grouping(self, obj) -> None:
        # Class has an AttributeDescriptor, DimensionDescriptor
        assert 2 == len(obj.grouping)

        # With GroupDimensionDescriptor, these are each included separately
        obj.group_dimensions = {
            "FOO": model.GroupDimensionDescriptor(id="FOO"),
            "BAR": model.GroupDimensionDescriptor(id="BAR"),
        }
        assert 4 == len(obj.grouping)

    def test_replace_grouping(self, obj) -> None:
        class Foo(model.ComponentList):
            pass

        # Cannot replace with an instance of Foo, because this does not correspond to
        # the type of any member of the class
        with pytest.raises(TypeError, match="No grouping of type"):
            obj.replace_grouping(Foo())


class TestAttributeValue(CompareTests):
    @pytest.fixture
    def obj(self) -> common.AttributeValue:
        return common.AttributeValue(
            start_date=date.fromisoformat("0001-01-01"),
            value="v1",
            value_for=common.DataAttribute(id="da1"),
        )

    @pytest.mark.parametrize(
        "callback",
        (
            None,
            lambda obj: setattr(obj, "start_date", date.fromisoformat("0001-01-02")),
            lambda obj: setattr(obj, "value", "v2"),
            lambda obj: setattr(obj, "value_for", common.DataAttribute(id="da2")),
        ),
    )
    def test_compare(self, obj: common.AttributeValue, callback) -> None:
        """:py:`compare(…)` is :any:`False` when attributes are changed."""
        super().test_compare(obj, callback)


class TestBaseObservation(CompareTests):
    @pytest.fixture
    def obj(self) -> common.BaseObservation:
        return common.BaseObservation(
            attached_attribute={"FOO": common.AttributeValue(value="f1")},
            dimension=common.Key(BAR="b1"),
            group_keys={common.GroupKey(id="g1")},
            series_key=common.SeriesKey(),
            value=1.0,
        )

    @pytest.mark.parametrize(
        "callback",
        (
            None,
            lambda o: o.attached_attribute.popitem(),
            lambda o: setattr(o, "dimension", common.Key(BAR="b2")),
            lambda o: setattr(o, "group_keys", {common.GroupKey(id="g2")}),
            lambda o: setattr(o, "series_key", None),
            lambda o: setattr(o, "value", 1.1),
        ),
    )
    def test_compare(self, obj: common.BaseObservation, callback) -> None:
        """:py:`compare(…)` is :any:`False` when attributes are changed.

        NB for .value_for, see test_v{21,30}.TestObservation.test_compare.
        """
        super().test_compare(obj, callback)


class TestBaseDataSet(CompareTests):
    @pytest.fixture
    def obj(self) -> common.BaseDataSet:
        k = common.Key(FOO=common.KeyValue(id="FOO", value="f1"))
        o = common.BaseObservation(dimension=k, value=1.0)
        result = common.BaseDataSet(
            action=common.ActionType.information,
            valid_from="0001-01-01",
            obs=[o],
            group={common.GroupKey(): [o]},
            series={common.SeriesKey(): [o]},
        )
        return result

    @pytest.mark.parametrize(
        "callback",
        (
            None,
            # Change attributes
            lambda ds: setattr(ds, "action", common.ActionType.delete),
            lambda ds: ds.group.popitem(),  # Remove a group key
            lambda ds: ds.obs.pop(-1),  # Change *number* of obs
            lambda ds: setattr(ds.obs[-1], "value", 1.1),  # Change *value* of one obs
            lambda ds: ds.series.popitem(),  # Remove a series key
            lambda ds: setattr(ds, "valid_from", "0001-01-02"),
        ),
    )
    def test_compare(self, obj: common.BaseDataSet, callback) -> None:
        """:py:`compare(…)` is :any:`False` when attributes are changed."""
        super().test_compare(obj, callback)
