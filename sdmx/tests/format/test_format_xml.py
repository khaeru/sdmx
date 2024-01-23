import io
import re
from pathlib import Path

import pytest

import sdmx
from sdmx.format import Version, xml
from sdmx.format.xml.common import _extracted_zipball
from sdmx.message import StructureMessage
from sdmx.model import v21


def test_ns_prefix():
    with pytest.raises(ValueError):
        xml.v21.ns_prefix("https://example.com")


def test_qname():
    assert f"{{{xml.v21.base_ns}/structure}}Code" == str(xml.v21.qname("str", "Code"))
    assert f"{{{xml.v30.base_ns}/structure}}Code" == str(xml.v30.qname("str", "Code"))


def test_tag_for_class():
    # ItemScheme is never written to XML; no corresponding tag name
    assert xml.v21.tag_for_class(v21.ItemScheme) is None


def test_class_for_tag():
    assert xml.v30.class_for_tag("str:DataStructure") is not None


@pytest.fixture(scope="module")
def mock_gh_api():
    """Mock GitHub API responses to avoid hitting rate limits.

    For each API endpoint URL queried by :func:.`_gh_zipball`, return a pared-down JSON
    response that contains the required "zipball_url" key.
    """
    import requests_mock

    base = "https://api.github.com/repos/sdmx-twg/sdmx-ml"

    with requests_mock.Mocker(real_http=True) as m:
        for v in "2.1", "3.0":
            m.get(
                f"{base}/releases/tags/v{v}",
                json=dict(zipball_url=f"{base}/zipball/v{v}"),
            )
        yield


@pytest.fixture(scope="module")
def installed_schemas(mock_gh_api, tmp_path_factory):
    """Fixture that ensures schemas are installed locally in a temporary directory."""
    dir = tmp_path_factory.mktemp("schemas")
    sdmx.install_schemas(dir.joinpath("2.1"), Version["2.1"])
    sdmx.install_schemas(dir.joinpath("3.0"), Version["3.0.0"])
    yield dir


@pytest.mark.parametrize("version", ["1", 1, None])
def test_install_schemas_invalid_version(version):
    """Ensure invalid versions throw ``NotImplementedError``."""
    with pytest.raises(NotImplementedError):
        sdmx.install_schemas(version=version)


@pytest.mark.network
@pytest.mark.parametrize("version", ["2.1", "3.0"])
def test_install_schemas(installed_schemas, version):
    """Test that XSD files are downloaded and ready for use in validation."""
    # Look for a couple of the expected files
    for schema_doc in ("SDMXCommon.xsd", "SDMXMessage.xsd"):
        assert installed_schemas.joinpath(version, schema_doc).exists()


@pytest.mark.network
def test_install_schemas_in_user_cache():
    """Test that XSD files are downloaded and ready for use in validation."""
    import platformdirs

    cache_dir = platformdirs.user_cache_path("sdmx") / "2.1"
    sdmx.install_schemas()

    # Look for a couple of the expected files
    files = ["SDMXCommon.xsd", "SDMXMessage.xsd"]
    for schema_doc in files:
        doc = cache_dir.joinpath(schema_doc)
        assert doc.exists(), (cache_dir, sorted(cache_dir.glob("*")))


@pytest.mark.parametrize("version", ["1", 1, None])
def test_validate_xml_invalid_version(version):
    """Ensure validation of invalid versions throw ``NotImplementedError``."""
    with pytest.raises(NotImplementedError):
        # This message doesn't exist, but the version should throw before it is used.
        sdmx.validate_xml("samples/common/common.xml", version=version)


def test_validate_xml_no_schemas(tmp_path, specimen, installed_schemas):
    """Check that supplying an invalid schema path will raise ``ValueError``."""
    with specimen("IPI-2010-A21-structure.xml", opened=False) as msg_path:
        with pytest.raises(ValueError):
            sdmx.validate_xml(msg_path, schema_dir=tmp_path)


@pytest.mark.network
def test_validate_xml_from_v2_1_samples(tmp_path, specimen, installed_schemas):
    """Use official samples to ensure validation of v2.1 messages works correctly."""
    extracted_content = _extracted_zipball(Version["2.1"])

    # Schemas as just in a flat directory
    schema_dir = extracted_content.joinpath("schemas")

    # Samples are somewhat spread out, and some are known broken so we pick a bunch
    for parts in [
        ("v21", "xml", "common", "common.xml"),
        ("v21", "xml", "demography", "demography.xml"),
        ("v21", "xml", "demography", "esms.xml"),
        ("ECB_EXR", "common.xml"),
        ("ECB_EXR", "ng-structure-full.xml"),
        ("ECB_EXR", "ng-structure.xml"),
        ("v21", "xml", "query", "query_cl_all.xml"),
        ("v21", "xml", "query", "response_cl_all.xml"),
        ("v21", "xml", "query", "query_esms_children.xml"),
        ("v21", "xml", "query", "response_esms_children.xml"),
    ]:
        with specimen(str(Path(*parts))) as sample:
            assert sdmx.validate_xml(sample, schema_dir, version="2.1")


@pytest.mark.network
def test_validate_xml_invalid_doc(tmp_path, installed_schemas):
    """Ensure that an invalid document fails validation."""
    msg_path = tmp_path / "invalid.xml"

    # Generate a codelist to form a StructureMessage
    ECB = v21.Agency(id="ECB")

    cl = v21.Codelist(
        id="CL_COLLECTION",
        version="1.0",
        is_final=False,
        is_external_reference=False,
        maintainer=ECB,
        name={"en": "Collection indicator code list"},
    )

    # Add items
    CL_ITEMS = [
        dict(id="A", name={"en": "Average of observations through period"}),
        dict(id="B", name={"en": "Beginning of period"}),
        dict(id="B1", name={"en": "Child code of B"}),
    ]
    for info in CL_ITEMS:
        cl.items[info["id"]] = v21.Code(**info)

    msg = StructureMessage(codelist={cl.id: cl})

    msg_path.write_bytes(sdmx.to_xml(msg))

    # Expect validation to fail
    assert not sdmx.validate_xml(msg_path, schema_dir=installed_schemas.joinpath("2.1"))


def test_validate_xml_invalid_message_type():
    """Ensure that an invalid document fails validation."""
    # Create a mangled structure message with its outmost tag changed to be invalid
    msg = StructureMessage()
    invalid_msg = re.sub(b"mes:Structure([ >])", rb"mes:FooBar\1", sdmx.to_xml(msg))

    with pytest.raises(NotImplementedError):
        sdmx.validate_xml(io.BytesIO(invalid_msg))


@pytest.mark.network
def test_validate_xml_from_v3_0_samples(tmp_path, installed_schemas):
    """Use official samples to ensure validation of v3.0 messages works correctly."""
    extracted_content = _extracted_zipball(Version["3.0.0"])

    # Schemas as just in a flat directory
    schema_dir = extracted_content.joinpath("schemas")

    # Samples are somewhat spread out, and some are known broken so we pick a bunch
    samples_dir = extracted_content.joinpath("samples")
    samples = [
        samples_dir / "Codelist" / "codelist.xml",
        samples_dir / "Codelist" / "codelist - extended.xml",
        samples_dir / "Concept Scheme" / "conceptscheme.xml",
        samples_dir / "Data Structure Definition" / "ECB_EXR.xml",
        samples_dir / "Dataflow" / "dataflow.xml",
        samples_dir / "Geospatial" / "geospatial_geographiccodelist.xml",
    ]
    for sample in samples:
        assert sdmx.validate_xml(sample, schema_dir, version="3.0")
