from typing import cast

import pytest

from sdmx.model.internationalstring import DEFAULT_LOCALE, InternationalString
from sdmx.model.v21 import Item


class TestInternationalString:
    def test_add(self) -> None:
        is0 = InternationalString(
            {"en": "European Central Bank", "de": "Europäische Zentralbank"}
        )
        is1 = InternationalString(
            {"fi": "Euroopan keskuspankki", "fr": "Banque centrale européenne"}
        )
        is2 = is0 + is1
        assert {"en", "de", "fi", "fr"} == set(is2.localizations)

    def test_eq(self) -> None:
        # Compares equal with same contents
        is1 = InternationalString(en="Foo", fr="Le foo")
        is2 = InternationalString(en="Foo", fr="Le foo")
        assert is1 == is2

        # Comparison with other types not implemented
        assert (
            InternationalString("European Central Bank")
            == {"en": "European Central Bank"}
        ) is False

    def test_other(self) -> None:
        # Constructor; the .name attribute is an InternationalString
        i: Item = Item(id="ECB")

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
        # NB User code that uses mypy should avoid these shorthands, as they interfere
        #    with type inference
        i.name = cast(InternationalString, "European Central Bank")
        assert 1 == len(i.name.localizations)
        assert i.name.localizations[DEFAULT_LOCALE] == "European Central Bank"

        # Setting with a (locale, text) tuple
        i.name = cast(InternationalString, ("FI", "Euroopan keskuspankki"))
        assert 1 == len(i.name.localizations)

        # Setting with a dict()
        i.name = cast(InternationalString, {"IT": "Banca centrale europea"})
        assert 1 == len(i.name.localizations)

        # Using some other type is an error
        with pytest.raises(ValueError):
            i.name = 123  # type: ignore [assignment]

        # Same, but in the constructor
        i2: Item = Item(id="ECB", name="European Central Bank")

        # str() uses the default locale
        assert str(i2.name) == "European Central Bank"

        # Giving empty dict is equivalent to giving nothing
        i3: Item = Item(id="ECB", name={})
        assert i3.name.localizations == Item(id="ECB").name.localizations

        # Create with iterable of 2-tuples
        i4: Item = Item(
            id="ECB",
            name=[
                ("DE", "Europäische Zentralbank"),
                ("FR", "Banque centrale européenne"),
            ],
        )
        assert i4.name["FR"] == "Banque centrale européenne"
