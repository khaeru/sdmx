import io
import logging
from abc import ABC
from datetime import datetime
from http import HTTPStatus
from typing import TYPE_CHECKING, Optional, cast

import pytest
from lxml import etree

import sdmx
import sdmx.writer.xml
from sdmx import message
from sdmx.format.xml import validate_xml
from sdmx.model import common, v21
from sdmx.model import v21 as m
from sdmx.model.v21 import DataSet, DataStructureDefinition, Dimension, Key, Observation
from sdmx.writer.xml import writer as XMLWriter

if TYPE_CHECKING:
    from sdmx.model.common import Structure

log = logging.getLogger(__name__)

# Fixtures


@pytest.fixture(scope="module")
def agency() -> common.Agency:
    return common.Agency(id="TEST")


@pytest.fixture(scope="module")
def header(agency) -> message.Header:
    return message.Header(
        id="N_A",
        prepared=datetime.now(),
        receiver=common.Agency(id="N_A"),
        sender=agency,
    )


@pytest.fixture
def metadata_message(header) -> message.MetadataMessage:
    """A metadata message with the minimum content to write valid SDMX-ML 2.1."""
    a = common.Agency(id="TEST")
    dfd = v21.DataflowDefinition(id="DFD", maintainer=a)
    ma = v21.MetadataAttribute(id="MA")
    rs = v21.ReportStructure(id="RS", components=[ma])
    mdsd = v21.MetadataStructureDefinition(
        id="MDS", maintainer=a, report_structure={rs.id: rs}
    )
    iot = v21.IdentifiableObjectTarget(id="IOT")
    mdt = v21.MetadataTarget(id="MDT", components=[iot])
    mdr = v21.MetadataReport(
        annotations=[v21.Annotation(id="FOO", text="foo value")],
        attaches_to=v21.TargetObjectKey(
            key_values={iot.id: v21.TargetIdentifiableObject(value_for=iot, obj=dfd)}
        ),
        metadata=[
            v21.OtherNonEnumeratedAttributeValue(value_for=ma, value=f"{ma.id} value")
        ],
        target=mdt,
    )
    mds = v21.MetadataSet(
        annotations=[v21.Annotation(id="FOO", text="foo value")],
        structured_by=mdsd,
        report_structure=rs,
        report=[mdr],
    )

    return message.MetadataMessage(header=header, data=[mds])


@pytest.fixture
def structure_message(header) -> message.StructureMessage:
    """A StructureMessage that serializes to XSD-valid SDMX-XML."""
    return message.StructureMessage(header=header)


@pytest.fixture
def dsd(agency):
    dsd = DataStructureDefinition(id="DS_TEST", maintainer=agency, version="1.0")
    dsd.urn = sdmx.urn.make(dsd)

    for order, id in enumerate(["FOO", "BAR", "BAZ"]):
        dsd.dimensions.append(Dimension(id=id, order=order))

    return dsd


@pytest.fixture
def obs(dsd):
    return Observation(dimension=dsd.make_key(Key, dict(FOO=1, BAR=2)), value=42.0)


@pytest.fixture
def dks(dsd):
    dim = dsd.dimensions.get("FOO")
    yield m.DataKeySet(
        included=True,
        keys=[
            m.DataKey(
                included=True,
                key_value={dim: m.ComponentValue(value_for=dim, value="foo0")},
            )
        ],
    )


@pytest.fixture
def submit_structure_response(header, dsd) -> message.SubmitStructureResponse:
    sr = common.SubmissionResult(
        dsd,
        common.ActionType.replace,
        status_message=common.StatusMessage(
            status=common.SubmissionStatusType.success,
            text=[common.MessageText(text="Foo", code=HTTPStatus.OK)],
        ),
    )

    return message.SubmitStructureResponse(header=header, result=[sr])


# Test specific methods associated with specific classes


class TestNameableArtefact:
    def test_xsd(self, structure_message):
        """Annotations for a NameableArtefact are output in the correct order.

        In https://github.com/khaeru/sdmx/issues/210 it was reported that
        <com:Annotations> incorrectly appeared before <com:Name>.
        """
        # Common arguments
        args = dict(
            # Identifiable Artefact
            id="FOO",
            # Nameable Artefact
            name="foo",
            description="bar",
            # VersionableArtefact
            version="1",
            # MaintainableArtefact
            maintainer=common.Agency(id="N_A"),
            is_external_reference=False,
            is_final=True,
        )
        dsd = v21.DataStructureDefinition(**args)
        na = v21.DataflowDefinition(
            annotations=[v21.Annotation(id="baz", text="qux")],  # Annotable Artefact
            **args,  # Identifiable, Nameable, Versionable, Maintainable
            structure=dsd,  # Dataflow-specific attributes
        )
        structure_message.dataflow[na.id] = na

        # Write to SDMX-ML
        buf = io.BytesIO(sdmx.to_xml(structure_message))

        # Validate using XSD. Fails with v2.19.1.
        assert validate_xml(buf), buf.getvalue().decode()


def test_contact() -> None:
    c = m.Contact(
        name="John Smith",
        org_unit="Human Resources",
        telephone="+1234567890",
        uri=["https://example.org"],
        email=["john.smith@example.org"],
    )

    result = sdmx.to_xml(c, pretty_print=True)

    assert result.decode().endswith(
        """
  <com:Name xml:lang="en">John Smith</com:Name>
  <str:Department xml:lang="en">Human Resources</str:Department>
  <str:Telephone>+1234567890</str:Telephone>
  <str:URI>https://example.org</str:URI>
  <str:Email>john.smith@example.org</str:Email>
</str:Contact>
"""
    )


def test_codelist(codelist):
    result = sdmx.to_xml(codelist, pretty_print=True)
    print(result.decode())


def test_DataKeySet(dks):
    """:class:`.DataKeySet` can be written to XML."""
    sdmx.to_xml(dks)


def test_ContentConstraint(dsd, dks):
    """:class:`.ContentConstraint` can be written to XML."""
    sdmx.to_xml(
        m.ContentConstraint(
            role=m.ConstraintRole(role=m.ConstraintRoleType.allowable),
            content=[dsd],
            data_content_keys=dks,
        )
    )


def test_ds(dsd, obs) -> None:
    # Write DataSet with Observations not in Series
    ds = DataSet(structured_by=dsd)
    ds.obs.append(obs)

    result = sdmx.to_xml(ds, pretty_print=True)
    # print(result.decode())
    del result


def test_ds_structurespecific(dsd):
    series_key = dsd.make_key(m.SeriesKey, dict(FOO=1, BAR=2))
    primary_measure = m.PrimaryMeasure(id="OBS_VALUE")
    observations = [
        m.Observation(
            series_key=series_key,
            dimension=dsd.make_key(m.Key, dict(BAZ=3)),
            value_for=primary_measure,
            value=25,
        ),
        m.Observation(
            series_key=series_key,
            dimension=dsd.make_key(m.Key, dict(BAZ=4)),
            value_for=primary_measure,
            value=0,
        ),
    ]
    series = {series_key: observations}
    ds = m.StructureSpecificDataSet(structured_by=dsd, series=series)
    dm = message.DataMessage(data=[ds])
    result = sdmx.to_xml(dm, pretty_print=True)
    exp = (
        '    <Series FOO="1" BAR="2">\n'
        '      <Obs OBS_VALUE="25" BAZ="3"/>\n'
        '      <Obs OBS_VALUE="0" BAZ="4"/>\n'
        "    </Series>"
    )
    assert exp in result.decode()


def test_obs(obs):
    # Generate <gen:ObsKey> element for 2+-dimensional Observation.dimension
    exp = (
        '<gen:ObsKey><gen:Value id="FOO" value="1"/>'
        '<gen:Value id="BAR" value="2"/></gen:ObsKey>'
    )
    assert exp in sdmx.to_xml(obs).decode()

    # Exception raised in structure-specific data because `obs` fixture has no value_for
    with pytest.raises(
        ValueError,
        match="Observation.value_for is None when writing structure-specific data",
    ):
        XMLWriter.recurse(obs, struct_spec=True)


def test_reference() -> None:
    cl = m.Codelist(id="FOO", version="1.0")
    c = m.Code(id="BAR")
    cl.append(c)

    # <Ref …> to Item has maintainableParentVersion, but no version
    result = sdmx.writer.xml.reference(c, style="Ref")
    result_str = etree.tostring(result).decode()
    assert 'maintainableParentVersion="1.0"' in result_str
    assert 'version="1.0"' not in result_str

    # <Ref …> to ItemScheme has version, but not maintainableParentVersion
    result = sdmx.writer.xml.reference(cl, style="Ref")
    result_str = etree.tostring(result).decode()
    assert 'maintainableParentVersion="1.0"' not in result_str
    assert 'version="1.0"' in result_str


def test_VersionableArtefact() -> None:
    """:class:`VersionableArtefact` with :class:`.Version` instance can be written."""
    cl: common.Codelist = common.Codelist(id="FOO", version=common.Version("1.2.3"))

    # Written to XML without error
    result = sdmx.to_xml(cl).decode()
    assert 'version="1.2.3"' in result


# sdmx.message classes


def test_Footer(footer):
    """:class:`.Footer` can be written."""
    sdmx.to_xml(footer)


def test_structuremessage(tmp_path, header, structuremessage) -> None:
    structuremessage.header = header
    result = sdmx.to_xml(structuremessage, pretty_print=True)

    # Message can be round-tripped to/from file
    path = tmp_path / "output.xml"
    path.write_bytes(result)
    msg = cast(message.StructureMessage, sdmx.read_sdmx(path))

    # Contents match the original object
    assert (
        msg.codelist["CL_COLLECTION"]["A"].name["en"]
        == structuremessage.codelist["CL_COLLECTION"]["A"].name["en"]
    )

    # False because `structuremessage` lacks URNs, which are constructed automatically
    # by `to_xml`
    assert not msg.compare(structuremessage, strict=True, allow_implied_urn=False)
    # Compares equal when allowing this difference
    assert msg.compare(structuremessage, strict=False)


def test_DataMessage(datamessage):
    """:class:`.DataMessage` can be written."""
    sdmx.to_xml(datamessage)


def test_MetadataMessage(metadata_message, *, debug: bool = False) -> None:
    """:class:`.MetadataMessage` can be written."""
    # Write to SDMX-ML
    buf = io.BytesIO(sdmx.to_xml(metadata_message, pretty_print=debug))

    # Validate using XSD
    assert validate_xml(buf), buf.getvalue().decode()


def test_ErrorMessage(errormessage):
    """:class:`.ErrorMessage` can be written."""
    sdmx.to_xml(errormessage)


def test_SubmitStructureResponse(submit_structure_response) -> None:
    """:class:`SubmitStructureResponse` can be written to valid SDMX-ML."""
    # Object can be written to SDMX-ML without error
    data = io.BytesIO(sdmx.to_xml(submit_structure_response, pretty_print=True))

    # SDMX-ML validates using the DSD
    assert validate_xml(data), "Invalid SDMX-ML"


@pytest.mark.usefixtures("tmp_path", "installed_schemas", "specimen")
class RoundTripTests(ABC):
    """Abstract base class for tests that read-write-read SDMX-ML."""

    structure_class: type["Structure"] = common.Structure

    def rw_test(
        self,
        request,
        specimen_id: str,
        structure_id: Optional[str],
        *,
        strict: bool,
        validate: bool,
    ) -> None:
        # Unpack fixture using the request_fixture
        tmp_path = request.getfixturevalue("tmp_path")
        specimen = request.getfixturevalue("specimen")
        schemas_dir = request.getfixturevalue("installed_schemas")

        if structure_id:
            # Read {D,Metad}ataStructure from file
            with specimen(structure_id) as f:
                structure = cast("message.StructureMessage", sdmx.read_sdmx(f)).objects(
                    self.structure_class
                )[0]
        else:
            structure = None

        # Read message, using the `structure`, if any
        with specimen(specimen_id) as f:
            msg0 = sdmx.read_sdmx(f, structure=structure)

        # Write to a bytes buffer (faster than to file)
        data = io.BytesIO(sdmx.to_xml(msg0, pretty_print=True))

        # Validate using XSD
        assert not validate or validate_xml(data, schemas_dir), "Invalid SDMX-ML"

        # Contents can be read again
        try:
            msg1 = sdmx.read_sdmx(data, structure=structure)
        except Exception:  # pragma: no cover
            path = tmp_path.joinpath("output.xml")
            path.write_bytes(data.getbuffer())
            log.error(f"See {path}")
            raise

        # Contents are identical
        try:
            assert msg0.compare(msg1, strict)
        except AssertionError:  # pragma: no cover
            path = tmp_path.joinpath("output.xml")
            path.write_bytes(data.getbuffer())
            log.error(f"compare(…, strict={strict}) = False; see {path}")
            raise


@pytest.mark.parametrize(
    "specimen_id, structure_id",
    [
        (
            "INSEE/CNA-2010-CONSO-SI-A17.xml",
            "INSEE/CNA-2010-CONSO-SI-A17-structure.xml",
        ),
        ("INSEE/IPI-2010-A21.xml", "INSEE/IPI-2010-A21-structure.xml"),
        ("ECB_EXR/1/M.USD.EUR.SP00.A.xml", "ECB_EXR/1/structure.xml"),
        ("ECB_EXR/ng-ts.xml", "ECB_EXR/ng-structure-full.xml"),
        ("ECB_EXR/ng-ts-ss.xml", "ECB_EXR/ng-structure-full.xml"),
        # DSD reference does not round-trip correctly
        pytest.param(
            "ECB_EXR/rg-xs.xml",
            "ECB_EXR/rg-structure-full.xml",
            marks=pytest.mark.xfail(raises=RuntimeError),
        ),
        # Example of a not-implemented feature: DataSet with groups
        pytest.param(
            "ECB_EXR/sg-ts-gf.xml",
            "ECB_EXR/sg-structure-full.xml",
            marks=pytest.mark.xfail(raises=NotImplementedError),
        ),
    ],
)
class TestRoundTripData(RoundTripTests):
    """Test that SDMX-ML DataMessages can be 'round-tripped'."""

    structure_class = common.BaseDataStructureDefinition

    def test_specimens(self, request, specimen_id: str, structure_id: str) -> None:
        self.rw_test(request, specimen_id, structure_id, strict=False, validate=False)


@pytest.mark.parametrize(
    "specimen_id, structure_id",
    [
        ("ESTAT/esms.xml", "ESTAT/esms-structure.xml"),
    ],
)
class TestRoundTripMetadata(RoundTripTests):
    """Test that SDMX-ML MetadataMessages can be 'round-tripped'."""

    structure_class = common.BaseMetadataStructureDefinition

    def test_specimens(self, request, specimen_id: str, structure_id: str) -> None:
        self.rw_test(request, specimen_id, structure_id, strict=True, validate=True)


@pytest.mark.parametrize(
    "specimen_id, strict",
    [
        ("BIS/gh-180.xml", False),
        ("ECB/orgscheme.xml", True),
        ("ECB_EXR/1/structure-full.xml", False),
        ("ESTAT/apro_mk_cola-structure.xml", True),
        ("ESTAT/esms-structure.xml", True),
        pytest.param(
            "ISTAT/47_850-structure.xml",
            True,
            marks=[pytest.mark.skip(reason="Slow")],
        ),
        ("IMF/ECOFIN_DSD-structure.xml", True),
        ("IMF/datastructure-0.xml", True),
        ("IMF/hierarchicalcodelist-1.xml", True),
        ("INSEE/CNA-2010-CONSO-SI-A17-structure.xml", False),
        ("INSEE/IPI-2010-A21-structure.xml", False),
        ("INSEE/dataflow.xml", False),
        ("OECD/actualconstraint-0.xml", True),
        ("SGR/common-structure.xml", True),
        ("UNSD/codelist_partial.xml", True),
        ("TEST/gh-149.xml", False),
    ],
)
class TestRoundTripStructure(RoundTripTests):
    """Test that SDMX-ML StructureMessages can be 'round-tripped'."""

    def test_specimens(self, request, specimen_id, strict) -> None:
        self.rw_test(request, specimen_id, None, strict=strict, validate=False)
