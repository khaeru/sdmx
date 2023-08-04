from operator import add, sub

import sdmx
from sdmx.model.common import DEFAULT_LOCALE, Item
from sdmx.util.item_structure import parse_all, parse_item_description


def test_parse(specimen):
    with specimen("IMF/CL_AREA-structure.xml") as f:
        msg = sdmx.read_sdmx(f)

    cl = msg.codelist["CL_AREA"]

    result = parse_all(cl)

    # Result has one element per item in the scheme
    assert 901 == len(result) == len(cl)

    # 185 items have parseable expressions in their descriptions
    assert 185 == sum(1 if len(v) else 0 for v in result.values())

    # Specific expressions are available and refer to other items in the scheme
    assert [(add, cl["1A"]), (sub, cl["1C"]), (sub, cl["5B"])] == result["9B"]


def test_localizations(caplog):
    """Selection of locale of description for parsing works."""
    i = Item(
        id="FOO",
        description={DEFAULT_LOCALE: "", "zh": "FOO = B + C - D", "ru": ""},
    )

    assert 0 == len(parse_item_description(i))
    assert caplog.messages[-1].endswith("using .localized_default('en')")

    assert 3 == len(parse_item_description(i, locale="zh"))
