import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from itertools import chain

import pytest
from lxml import etree

import sdmx
from sdmx.format.xml import qname
from sdmx.model.v21 import Facet, FacetType, FacetValueType
from sdmx.reader.xml import Reader, XMLParseError
from sdmx.writer.xml import Element as E


# Read example data files
@pytest.mark.parametrize_specimens("path", format="xml", kind="data")
def test_read_xml(path):
    sdmx.read_sdmx(path)


# Read example structure files
@pytest.mark.parametrize_specimens("path", format="xml", kind="structure")
def test_read_xml_structure(path):
    sdmx.read_sdmx(path)


def test_read_xml_structure_insee(specimen):
    with specimen("IPI-2010-A21-structure.xml") as f:
        msg = sdmx.read_sdmx(f)

    # Same objects referenced
    assert id(msg.dataflow["IPI-2010-A21"].structure) == id(
        msg.structure["IPI-2010-A21"]
    )

    # Number of dimensions loaded correctly
    dsd = msg.structure["IPI-2010-A21"]
    assert len(dsd.dimensions) == 4


# Read structure-specific messages
def test_read_ss_xml(specimen):
    with specimen("M.USD.EUR.SP00.A.xml", opened=False) as f:
        msg_path = f
        dsd_path = f.parent / "structure.xml"

    # Read the DSD
    dsd = sdmx.read_sdmx(dsd_path).structure["ECB_EXR1"]

    # Read a data message
    msg = sdmx.read_sdmx(msg_path, dsd=dsd)
    ds = msg.data[0]

    # The dataset in the message is structured by the DSD
    assert ds.structured_by is dsd

    # Structures referenced in the dataset are from the dsd
    s0_key = list(ds.series.keys())[0]

    # AttributeValue.value_for
    assert s0_key.attrib["DECIMALS"].value_for is dsd.attributes.get("DECIMALS")

    # SeriesKey.described_by
    assert s0_key.described_by is dsd.dimensions

    # Key.described_by
    assert ds.obs[0].key.described_by is dsd.dimensions

    # KeyValue.value_for
    assert ds.obs[0].key.values[0].value_for is dsd.dimensions.get("FREQ")

    # DSD information that is not in the data message can be looked up through
    # navigating object relationships
    TIME_FORMAT = s0_key.attrib["TIME_FORMAT"].value_for
    assert len(TIME_FORMAT.related_to.dimensions) == 5


def test_gh_104(caplog, specimen):
    """Test of https://github.com/khaeru/sdmx/issues/104.

    See also
    --------
    .test_sources.TestISTAT.test_gh_104
    """
    # Read a DSD
    with specimen("22_289-structure.xml", opened=False) as f:
        dsd_path = f
        msg_path = f.parent / "22_289.xml"

    # Read the DSD, change its ID
    dsd = sdmx.read_sdmx(dsd_path).structure["DCIS_POPRES1"]
    dsd.id = "FOO"

    # Read a data message; use is logged
    sdmx.read_sdmx(msg_path, dsd=dsd)
    assert re.match(
        r"Use provided <DataStructureDefinition IT1:FOO\(1\.0\): .* for "
        'structureRef="IT1_DCIS_POPRES1_1_0" not defined in message',
        caplog.messages[-1],
    )


def test_gh_116(specimen):
    """Test of https://github.com/khaeru/sdmx/issues/116.

    See also
    --------
    .test_sources.TestESTAT.test_gh_116
    """
    with specimen("ESTAT/GOV_10Q_GGNFA.xml") as f:
        msg = sdmx.read_sdmx(f)

    # Both versions of the GEO codelist are accessible in the message
    cl1 = msg.codelist["ESTAT:GEO(13.0)"]
    cl2 = msg.codelist["ESTAT:GEO(13.1)"]

    # cl1 is complete and items are available
    assert not cl1.is_partial and 0 < len(cl1)
    # cl2 is partial, and fewer codes are included than in cl1
    assert cl2.is_partial and 0 < len(cl2) < len(cl1)

    cl3 = msg.codelist["ESTAT:UNIT(15.1)"]
    cl4 = msg.codelist["ESTAT:UNIT(15.2)"]

    # cl3 is complete and items are available
    assert not cl3.is_partial and 0 < len(cl3)
    # cl4 is partial, and fewer codes are included than in cl1
    assert cl4.is_partial and 0 < len(cl4) < len(cl3)


# Each entry is a tuple with 2 elements:
# 1. an instance of lxml.etree.Element to be parsed.
# 2. Either:
#   - A sdmx.model object, in which case the parsed element must match the object.
#   - A string, in which case parsing the element is expected to fail, raising an
#     exception matching the string.
ELEMENTS = [
    # xml._datetime()
    (  # with 5 decimal places
        E(qname("mes:Extracted"), "2020-08-18T00:14:31.59849+05:00"),
        datetime(2020, 8, 18, 0, 14, 31, 598490, tzinfo=timezone(timedelta(hours=5))),
    ),
    (  # with 7 decimal places
        E(qname("mes:Extracted"), "2020-08-18T01:02:03.4567891+00:00"),
        datetime(2020, 8, 18, 1, 2, 3, 456789, tzinfo=timezone.utc),
    ),
    (  # with "Z"
        E(qname("mes:Extracted"), "2020-08-18T00:14:31.59849Z"),
        datetime(2020, 8, 18, 0, 14, 31, 598490, tzinfo=timezone.utc),
    ),
    (  # with 7 decimal places AND "Z"; a message is logged on DEBUG (not checked)
        E(qname("mes:Extracted"), "2020-08-18T01:02:03.4567891Z"),
        datetime(2020, 8, 18, 1, 2, 3, 456789, tzinfo=timezone.utc),
    ),
    # xml._facet()
    (
        E(qname("str:TextFormat"), isSequence="False", startValue="3.4", endValue="1"),
        None,
    ),
    # …attribute names are munged; default textType is supplied
    (
        E(qname("str:EnumerationFormat"), minLength="1", maxLength="6"),
        Facet(
            type=FacetType(min_length=1, max_length=6),
            value_type=FacetValueType["string"],
        ),
    ),
    # …invalid attributes cause an exception
    (
        E(qname("str:TextFormat"), invalidFacetTypeAttr="foo"),
        re.compile("unexpected keyword argument 'invalid_facet_type_attr'"),
    ),
    # xml._dk
    (E(qname("str:Key")), None),
    # xml._dks
    (E(qname("str:DataKeySet"), isIncluded="true"), None),
    # xml._pa
    (E(qname("str:ProvisionAgreement")), None),
]


@pytest.mark.parametrize(
    "elem, expected", ELEMENTS, ids=list(map(str, range(len(ELEMENTS))))
)
def test_parse_elem(elem, expected):
    """Test individual XML elements.

    This method allows unit-level testing of specific XML elements appearing in SDMX-ML
    messages. Add elements by extending the list passed to the parametrize() decorator.
    """
    # Convert to a file-like object compatible with read_message()
    tmp = BytesIO(etree.tostring(elem))

    # Create a reader
    reader = Reader()

    if isinstance(expected, (str, re.Pattern)):
        # Parsing the element raises an exception
        with pytest.raises(XMLParseError, match=expected):
            reader.read_message(tmp)
    else:
        # The element is parsed successfully
        result = reader.read_message(tmp)

        if not result:
            stack = list(chain(*[s.values() for s in reader.stack.values()]))
            assert len(stack) == 1
            result = stack[0]

        if expected:
            # Expected value supplied
            assert expected == result
