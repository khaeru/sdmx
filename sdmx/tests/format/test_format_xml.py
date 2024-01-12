import io
import zipfile

import pytest
import requests

import sdmx
from sdmx.format import xml
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


@pytest.mark.parametrize("version", ["1", 1, None])
def test_install_schemas_invalid_version(version):
    """Ensure invalid versions throw ``NotImplementedError``."""
    with pytest.raises(NotImplementedError):
        sdmx.install_schemas(version=version)


@pytest.mark.network
@pytest.mark.parametrize("version", ["2.1", "3.0"])
def test_install_schemas(tmp_path, version):
    """Test that XSD files are downloaded and ready for use in validation."""
    sdmx.install_schemas(schema_dir=tmp_path, version=version)

    # Look for a couple of the expected files
    files = ["SDMXCommon.xsd", "SDMXMessage.xsd"]
    for schema_doc in files:
        doc = tmp_path.joinpath(schema_doc)
        assert doc.exists()


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
        assert doc.exists()


@pytest.mark.parametrize("version", ["1", 1, None])
def test_validate_xml_invalid_version(version):
    """Ensure validation of invalid versions throw ``NotImplementedError``."""
    with pytest.raises(NotImplementedError):
        # This message doesn't exist, but the version should throw before it is used.
        sdmx.validate_xml("samples/common/common.xml", version=version)


def test_validate_xml_no_schemas(specimen, tmp_path):
    """Check that supplying an invalid schema path will raise ``ValueError``."""
    with specimen("IPI-2010-A21-structure.xml", opened=False) as msg_path:
        with pytest.raises(ValueError):
            # This message doesn't exist, but the schema should throw before it is used.
            sdmx.validate_xml(msg_path, schema_dir=tmp_path)


@pytest.mark.network
def test_validate_xml_from_v2_1_samples(tmp_path):
    """Use official samples to ensure validation of v2.1 messages works correctly."""
    # Grab the latest v2.1 schema release to get the URL to the zip
    release_url = "https://api.github.com/repos/sdmx-twg/sdmx-ml-v2_1/releases/latest"
    gh_headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.get(url=release_url, headers=gh_headers)
    zipball_url = resp.json().get("zipball_url")
    # Download the zipped content and find the schemas within
    resp = requests.get(url=zipball_url, headers=gh_headers)
    zipped = zipfile.ZipFile(io.BytesIO(resp.content))
    zipped.extractall(path=tmp_path)
    extracted_content = list(tmp_path.glob("sdmx-twg-sdmx-ml*"))[0]

    # Schemas as just in a flat directory
    schema_dir = extracted_content.joinpath("schemas")

    # Samples are somewhat spread out, and some are known broken so we pick a bunch
    samples_dir = extracted_content.joinpath("samples")
    samples = [
        samples_dir / "common" / "common.xml",
        samples_dir / "demography" / "demography.xml",
        samples_dir / "demography" / "esms.xml",
        samples_dir / "exr" / "common" / "exr_common.xml",
        samples_dir / "exr" / "ecb_exr_ng" / "ecb_exr_ng_full.xml",
        samples_dir / "exr" / "ecb_exr_ng" / "ecb_exr_ng.xml",
        samples_dir / "query" / "query_cl_all.xml",
        samples_dir / "query" / "response_cl_all.xml",
        samples_dir / "query" / "query_esms_children.xml",
        samples_dir / "query" / "response_esms_children.xml",
    ]

    for sample in samples:
        assert sdmx.validate_xml(sample, schema_dir, version="2.1")


@pytest.mark.network
def test_validate_xml_from_v3_0_samples(tmp_path):
    """Use official samples to ensure validation of v3.0 messages works correctly."""
    # Grab the latest v3.0 schema release to get the URL to the zip
    release_url = "https://api.github.com/repos/sdmx-twg/sdmx-ml/releases/latest"
    gh_headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.get(url=release_url, headers=gh_headers)
    zipball_url = resp.json().get("zipball_url")
    # Download the zipped content and find the schemas within
    resp = requests.get(url=zipball_url, headers=gh_headers)
    zipped = zipfile.ZipFile(io.BytesIO(resp.content))
    zipped.extractall(path=tmp_path)
    extracted_content = list(tmp_path.glob("sdmx-twg-sdmx-ml*"))[0]

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
