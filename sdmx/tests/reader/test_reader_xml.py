import pytest

import sdmx
from sdmx.message import Message


@pytest.mark.parametrize_specimens("path", format="xml")
def test_read_xml(path) -> None:
    """XML specimens can be read."""
    if "esms_structured" in path.name or "query_" in str(path):
        pytest.xfail("Not implemented")

    result = sdmx.read_sdmx(path)
    assert isinstance(result, Message)


@pytest.mark.parametrize(
    "message_path, structure_path, structure_id",
    (
        # Structure-specific data; same as test_reader_xml_v21.test_read_ss_xml but
        # without additional assertions
        ("M.USD.EUR.SP00.A.xml", "ECB_EXR/1/structure.xml", "ECB_EXR1"),
        ("demography_xs.xml", "demography.xml", "DEMOGRAPHY"),
        # Structure-specific metadata
        ("esms_structured.xml", "v21/xml/demography/esms.xml", "ESMS_SIMPLE"),
    ),
)
def test_read_xml_ss(specimen, message_path, structure_path, structure_id) -> None:
    """Structure-specific (meta)data specimens can be read *using* their structures.

    Note that :func:`.test_read_xml` tests some of the same {Metad,D}ataMessage
    specimens, but *without* supplying the [MD]SD; in those cases, the [MD]SD contents
    are inferred while parsing. This test, in contrast, parses with the [MD]SD
    available.
    """
    # Read the structure message and retrieve the structure object
    with specimen(structure_path) as f:
        sm = sdmx.read_sdmx(f)

    # Structure may be for data or metadata
    for name in "structure", "metadatastructure":
        try:
            s = getattr(sm, name)[structure_id]
        except KeyError:
            pass
        else:
            break

    assert s

    # The (meta)data message can be read using its associated structure
    with specimen(message_path) as f:
        result = sdmx.read_sdmx(f, dsd=s)

    assert isinstance(result, Message)
