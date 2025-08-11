import pytest

from sdmx import message
from sdmx.model.common import Agency, Codelist
from sdmx.model.v21 import Annotation

CL_ITEMS = [
    dict(id="A", name={"en": "Average of observations through period"}),
    dict(id="B", name={"en": "Beginning of period"}),
    dict(id="B1", name={"en": "Child code of B"}, parent="B"),
]


@pytest.fixture
def codelist():
    """A Codelist for writer testing."""
    ECB = Agency(id="ECB")

    cl = Codelist(
        id="CL_COLLECTION",
        version="1.0",
        is_final=False,
        is_external_reference=False,
        maintainer=ECB,
        name={"en": "Collection indicator code list"},
    )

    # Add items
    for info in CL_ITEMS:
        # For B1, this also adds a hierarchical relationship to B
        code = cl.setdefault(**info)
        # FIXME setdefault should do this automatically
        if "parent" not in info:
            code.parent = cl

    # Add an annotation
    cl.items["A"].annotations.append(
        Annotation(id="A1", type="NOTE", text={"en": "Text annotation on Code A."})
    )

    return cl


# Classes from sdmx.message


@pytest.fixture
def footer():
    """A :class:`.Footer` for writer testing."""
    return message.Footer(
        code=123,
        severity="information",
        text=["Here is one string.", "Here is another."],
    )


@pytest.fixture
def structuremessage(codelist, footer):
    """A :class:`.StructureMessage.` for writer testing."""
    return message.StructureMessage(codelist={codelist.id: codelist}, footer=footer)


@pytest.fixture
def datamessage(footer):
    return message.DataMessage(footer=footer)


@pytest.fixture
def errormessage(footer):
    return message.ErrorMessage(footer=footer)
