import pickle
from dataclasses import dataclass
from typing import Generator, Type

import pytest

import sdmx
from sdmx.dictlike import DictLike, DictLikeDescriptor
from sdmx.util import only, parse_content_type


class TestDictLike:
    @pytest.fixture
    def Foo(self) -> Generator[Type, None, None]:
        # Example class
        @dataclass
        class Foo:
            items: DictLikeDescriptor[str, int] = DictLikeDescriptor()

        yield Foo

    def test_init(self):
        # NB use with "assert False" in DictLike.__setitem__
        DictLike(foo=1)
        DictLike((("foo", 1),))
        DictLike(dict(foo=1))

    def test_class(self):
        dl = DictLike()

        # Set by item name
        dl["TIME_PERIOD"] = 3
        dl["CURRENCY"] = "USD"

        # Access by attribute name
        assert dl.TIME_PERIOD == 3

        # Access by item index
        assert dl[1] == "USD"

        # Access beyond index
        with pytest.raises(KeyError):
            dl["FOO"]

        with pytest.raises(IndexError):
            dl[2]

        with pytest.raises(AttributeError):
            dl.FOO

        # copy() returns same class
        copied = dl.copy()
        assert isinstance(copied, DictLike)
        assert copied.TIME_PERIOD == dl.TIME_PERIOD

    def test_validation(self, Foo) -> None:
        f = Foo()
        assert type(f.items) is DictLike
        assert (str, int) == f.items._types

        # Can be set with DictLike
        f.items = DictLike(a=1, b=2)
        assert type(f.items) is DictLike

        # Can be set with dict()
        f.items = {"a": 1, "b": 2}
        assert type(f.items) is DictLike

        # Type checking on creation
        with pytest.raises(TypeError):
            f = Foo(items={1: "a"})

        # Type checking on assignment
        f = Foo()
        with pytest.raises(TypeError):
            f.items = {1: "a"}

        # Type checking on setting elements
        f = Foo(items={"a": 1})
        with pytest.raises(TypeError):
            f.items[123] = 456

        # With no initial value set
        f = Foo()
        with pytest.raises(TypeError):
            f.items[123] = 456

    def test_compare(self, caplog):
        dl1 = DictLike(a="foo", b="bar")
        dl2 = DictLike(c="baz", a="foo")

        assert not dl1.compare(dl2)
        assert "Not identical: ['a', 'b'] / ['a', 'c']" in caplog.messages

    def test_pickle(self, specimen):
        """Instances included in a Pydantic model can be pickled."""
        with specimen("sg-xs.xml") as f:
            msg1 = sdmx.read_sdmx(f)

        value = pickle.dumps(msg1)
        msg2 = pickle.loads(value)

        assert msg1.compare(msg2)


def test_only():
    assert None is only(filter(lambda x: x == "foo", ["bar", "baz"]))
    assert None is only(filter(lambda x: x == "foo", ["foo", "bar", "foo"]))


def test_parse_content_type():
    """:func:`.parse_content_type` handles whitespace, quoting, and empty params."""
    assert (
        "application/foo",
        dict(version="1.2", charset="UTF-8"),
    ) == parse_content_type("application/foo; version = 1.2 ; ;charset='UTF-8'")
