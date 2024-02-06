import re
from datetime import datetime, timedelta, timezone
from io import BytesIO
from itertools import chain

import pandas
import pytest
from lxml import etree

import sdmx
from sdmx import urn
from sdmx.format.xml.v21 import qname
from sdmx.model import common, v21
from sdmx.model.v21 import ContentConstraint, Facet, FacetType, FacetValueType
from sdmx.reader.xml.v21 import Reader, XMLParseError
from sdmx.writer.xml import Element as E


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


def test_gh_142(specimen):
    """Test of https://github.com/khaeru/sdmx/issues/142."""
    with specimen("TEST/gh-142.xml") as f:
        msg = sdmx.read_sdmx(f)

    # Annotations, valid_from and valid_to properties stored on the Codelist *per se*
    cl = msg.codelist["CL_NAICS"]
    assert 3 == len(cl.annotations)
    assert "2021-01-24T08:00:00" == cl.valid_from
    assert "2021-09-24T08:00:00" == cl.valid_to

    # No annotations attached to any Code
    assert all(0 == len(code.annotations) for code in cl)


def test_gh_159():
    """Test of https://github.com/khaeru/sdmx/pull/159."""
    # Agency and contained Contact with distinct names
    elem = E(
        qname("str:Agency"),
        E(qname("com:Name"), "Foo Agency"),
        E(qname("str:Contact"), E(qname("com:Name"), "Jane Smith")),
        id="FOO",
    )

    # - Create a reader
    # - Convert to a file-like object compatible with read_message()
    # - Parse the element
    # - Retrieve the resulting object
    reader = Reader()
    reader.read_message(BytesIO(etree.tostring(elem)))
    obj = reader.pop_single(common.Agency)

    assert "Foo Agency" == str(obj.name)
    assert "Jane Smith" == str(obj.contact[0].name)


def test_gh_164(specimen):
    """Test of https://github.com/khaeru/sdmx/issues/164."""
    with specimen("IMF_STA/DSD_GFS.xml") as f:
        msg = sdmx.read_sdmx(f)

    # Retrieve objects directly from the message
    dsd = msg.structure["DSD_GFS"]
    IMF_CL_COUNTRY = msg.codelist["CL_COUNTRY"]
    IMF_CS_MASTER = msg.concept_scheme["IMF:CS_MASTER"]
    IMF_STA_CS_MASTER = msg.concept_scheme["IMF_STA:CS_MASTER"]

    # Component's concept identity is resolved within the correct concept scheme
    c = dsd.dimensions.get("COUNTRY").concept_identity
    cs = c.parent
    assert cs.urn.endswith("ConceptScheme=IMF:CS_MASTER(4.0.0)")
    assert urn.make(c).endswith("Concept=IMF:CS_MASTER(4.0.0).COUNTRY")

    # The reference is to the full concept scheme in the same message
    assert cs is IMF_CS_MASTER
    assert 56 == len(cs) == len(IMF_CS_MASTER)

    # Concept's core representation, per that scheme, can be retrieved
    assert c.core_representation.enumerated is IMF_CL_COUNTRY

    # Another component's concept identity is resolved within a concept scheme with the
    # same ID, but different maintainer and version:
    c = dsd.attributes.get("STATUS").concept_identity
    cs = c.parent
    assert cs.urn.endswith("ConceptScheme=IMF_STA:CS_MASTER(1.0.1)")
    assert urn.make(c).endswith("Concept=IMF_STA:CS_MASTER(1.0.1).STATUS")

    # The reference is to the full concept scheme in the same message
    assert cs is IMF_STA_CS_MASTER
    assert 12 == len(cs) == len(IMF_STA_CS_MASTER)

    # Concept's core representation as a text / string is parsed and stored
    facet = c.core_representation.non_enumerated[0]
    assert common.FacetValueType["string"] == facet.value_type

    # NoSpecifiedRelationship is correctly parsed
    da = dsd.attributes.get("FULL_CITATION")
    assert isinstance(da.related_to, v21.NoSpecifiedRelationship)


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
    # xml._key0: Create the necessary parent element to test the parsing of its child
    (E(qname("str:DataKeySet"), E(qname("str:Key")), isIncluded="True"), None),
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


def test_availableconstraint_xml_response(specimen):
    """Test of https://github.com/khaeru/sdmx/pull/161"""

    with specimen("IMF_STA/availableconstraint_CPI.xml") as f:
        msg = sdmx.read_sdmx(f)

    res = sdmx.to_pandas(msg.constraint)
    assert len(res) == 1
    assert "CPI" in res.keys()
    assert len(res["CPI"]) == 1
    assert len(res["CPI"][0]) == 3

    assert isinstance(msg.constraint.CPI, ContentConstraint)

    assert list(res["CPI"][0].keys()) == ["COUNTRY", "FREQUENCY", "INDICATOR"]

    expected = pandas.Series(["111", "134"], name="COUNTRY")
    assert expected.equals(res["CPI"][0]["COUNTRY"])
    expected = pandas.Series(["A", "M", "Q"], name="FREQUENCY")
    assert expected.equals(res["CPI"][0]["FREQUENCY"])
    expected = pandas.Series(
        ["PCPIHA_IX", "PCPIHA_PC_CP_A_PT", "PCPI_PC_CP_A_PT"], name="INDICATOR"
    )
    assert expected.equals(res["CPI"][0]["INDICATOR"])
