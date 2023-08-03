import pytest

import sdmx


@pytest.mark.parametrize_specimens("path", format="json")
def test_json_read(path):
    """Test that the samples from the SDMX-JSON spec can be read."""
    sdmx.read_sdmx(path)


@pytest.mark.xfail(reason="Test some code for the incomplete SDMX-JSON 2.0 reader")
def test_json_read_v2(specimen):
    sdmx.read_sdmx(
        specimen.base_path.joinpath("v3", "json", "structure", "generated-sample.json")
    )


def test_header(specimen):
    with specimen("flat.json") as f:
        resp = sdmx.read_sdmx(f)
    assert resp.header.id == "62b5f19d-f1c9-495d-8446-a3661ed24753"
