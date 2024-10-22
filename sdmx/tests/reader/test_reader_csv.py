from functools import lru_cache
from typing import TYPE_CHECKING

import pytest

from sdmx.reader.csv import Reader

if TYPE_CHECKING:
    from sdmx.model import v30


class TestReader:
    @pytest.mark.parametrize(
        "mt, expected",
        [
            ("foo", False),
            ("application/vnd.sdmx.data+csv; version=1.0.0", True),
            ("application/vnd.sdmx.metadata+csv; version=2.0.0", True),
        ],
    )
    def test_handles_media_type(self, mt, expected) -> None:
        assert expected is Reader.handles_media_type(mt)

    @pytest.mark.parametrize("value, expected", [(".csv", True), (".xlsx", False)])
    def test_supports_suffix(self, value, expected) -> None:
        assert expected is Reader.supports_suffix(value)


@lru_cache
def get_dfd(n_measure: int = 1) -> "v30.Dataflow":
    from sdmx.model import common, v30

    m = common.Agency(id="ESTAT")
    dsd = v30.DataStructureDefinition(maintainer=m)
    dsd.dimensions.append(v30.Dimension(id="DIM_1"))
    dsd.dimensions.append(v30.Dimension(id="DIM_2"))
    dsd.dimensions.append(v30.Dimension(id="DIM_3"))

    if n_measure == 1:
        dsd.measures.append(v30.Measure(id="OBS_VALUE"))
    else:
        for i in range(1, n_measure + 1):
            dsd.measures.append(v30.Measure(id=f"OBS_VALUE{i}"))

    dsd.attributes.append(common.DataAttribute(id="ATTR_2"))
    dsd.attributes.append(common.DataAttribute(id="ATTR_3"))
    dsd.attributes.append(common.DataAttribute(id="ATTR_1"))

    dfd = v30.Dataflow(id="NA_MAIN", maintainer=m, version="1.6.0", structure=dsd)

    return dfd


@pytest.mark.parametrize_specimens("path", format="csv")
def test_read_specimen(path):
    """Test that the samples from the SDMX-CSV spec can be read."""
    import sdmx

    if path.stem in ("example-02", "example-03"):
        dfd: "v30.Dataflow" = get_dfd(2)
    else:
        dfd = get_dfd()

    kwargs = dict(structure=dfd)

    if path.stem == "example-04":
        kwargs.update(delimiter=";")

    result = sdmx.read_sdmx(path, **kwargs)

    # # DEBUG
    # from icecream import ic
    #
    # ic(result)
    # for i, ds in enumerate(result.data):
    #     try:
    #         ic(i, ds.action, sdmx.to_pandas(ds, attributes="dsgo"))
    #     except Exception as e:
    #         ic(e)
    #         pass

    del result
