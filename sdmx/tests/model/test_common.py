from dataclasses import dataclass

import pytest

from sdmx.model.common import (
    Agency,
    AnnotableArtefact,
    Annotation,
    Contact,
    IdentifiableArtefact,
    Item,
    ItemScheme,
    MaintainableArtefact,
    NameableArtefact,
    Representation,
)
from sdmx.model.v21 import AttributeDescriptor, DataStructureDefinition


class TestAnnotableArtefact:
    def test_eval_annotation(self, caplog) -> None:
        aa = AnnotableArtefact()

        value = dict(foo=1.1, bar=2, baz=True)

        aa.annotations.append(Annotation(id="test-anno0", text=repr(value)))
        aa.annotations.append(Annotation(id="test-anno1", text="value['foo']"))

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
            IdentifiableArtefact(id="BAD_URN", urn=urn)

        # IdentifiableArtefact is hashable
        ia = IdentifiableArtefact()
        assert hash(ia) == id(ia)

        ia = IdentifiableArtefact(id="foo")
        assert hash(ia) == hash("foo")

        # Subclass is hashable
        ad = AttributeDescriptor()
        assert hash(ad) == id(ad)

    def test_hash_subclass(self):
        @dataclass
        class Foo(IdentifiableArtefact):
            __hash__ = IdentifiableArtefact.__hash__

        f = Foo(id="FOO")
        assert hash("FOO") == hash(f)

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


class TestNameableArtefact:
    def test_eq(self):
        na = NameableArtefact(id="FOO", name="Foo")
        assert na == "FOO"

    def test_namea(self, caplog) -> None:
        na1 = NameableArtefact(name=dict(en="Name"), description=dict(en="Description"))
        na2 = NameableArtefact()

        assert not na1.compare(na2)
        assert caplog.messages[-1] == "Not identical: name <en: Name> != <>"

        na2.name["en"] = "Name"

        assert not na1.compare(na2)
        assert (
            caplog.messages[-1] == "Not identical: description <en: Description> != <>"
        )

        na2.description["en"] = "Description"

        assert na1.compare(na2)


class TestMaintainableArtefact:
    def test_urn(self):
        urn = (
            "urn:sdmx:org.sdmx.infomodel.conceptscheme.ConceptScheme="
            "IT1:VARIAB_ALL(9.6)"
        )
        ma = MaintainableArtefact(id="VARIAB_ALL", urn=urn)

        # Version is parsed from URN
        assert ma.version == "9.6"

        # Mismatch raises an exception
        with pytest.raises(ValueError, match="Version 9.7 does not match URN"):
            MaintainableArtefact(version="9.7", urn=urn)

        # Maintainer is parsed from URN
        assert ma.maintainer == Agency(id="IT1")

        # Mismatch raises an exception
        with pytest.raises(ValueError, match="Maintainer FOO does not match URN"):
            MaintainableArtefact(maintainer=Agency(id="FOO"), urn=urn)


class TestItemScheme:
    def test_compare(self) -> None:
        is0: ItemScheme = ItemScheme(id="is0")
        is0.append(Item(id="foo"))

        is1: ItemScheme = ItemScheme(id="is0")
        is1.append(Item(id="foo"))

        assert is0.compare(is1) is True

        is2: ItemScheme = ItemScheme(id="is0")
        is2.append(Item(id="bar"))

        assert is0.compare(is2) is False

    def test_get_hierarchical(self) -> None:
        is0: ItemScheme = ItemScheme(id="is0")
        foo: Item = Item(id="foo")
        bar: Item = Item(id="bar")
        foo.append_child(bar)

        is0.append(foo)
        is0.append(bar)

        assert bar is is0.get_hierarchical("foo.bar")

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


class TestContact:
    def test_init(self):
        c1 = Contact()
        c2 = Contact()

        c2.name = "foo"

        assert repr(c1) != repr(c2)
