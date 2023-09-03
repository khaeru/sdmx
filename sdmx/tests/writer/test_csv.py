import pandas as pd
import pytest

import sdmx
from sdmx.model import v21 as m


def _add_test_dsd(ds: m.DataSet) -> None:
    if ds.described_by is None:
        dsd = ds.structured_by
        if dsd is None:
            pytest.skip(reason="No DFD or DSD")
        else:
            # Construct a fake/temporary DFD
            ds.described_by = m.DataflowDefinition(
                id=f"_TEST_{dsd.id}", maintainer=dsd.maintainer, version="0.0"
            )


@pytest.mark.parametrize_specimens("path", kind="data")
def test_write_data(tmp_path, specimen, path):
    msg = sdmx.read_sdmx(path)

    for i, dataset in enumerate(msg.data):
        _add_test_dsd(dataset)

        # Writer runs successfully
        result = sdmx.to_csv(dataset, rtype=pd.DataFrame, attributes="dsgo")

        # Standard features are respected
        assert "DATAFLOW" == result.columns[0]
        assert "OBS_VALUE" in result.columns

        # Write directly to file also works
        path_out = tmp_path.joinpath(f"{i}.csv")
        assert None is sdmx.to_csv(dataset, path=path_out, attributes="dsgo")
        assert path_out.exists()

        with open(path_out, "r") as f:
            assert f.readline().startswith("DATAFLOW,")


def test_rtype_str(tmp_path, specimen):
    with specimen("ECB_EXR/1/M.USD.EUR.SP00.A.xml") as f:
        msg = sdmx.read_sdmx(f)
    ds = msg.data[0]
    _add_test_dsd(ds)

    isinstance(sdmx.to_csv(ds, rtype=str), str)


def test_unsupported(tmp_path, specimen):
    with specimen("ECB_EXR/1/M.USD.EUR.SP00.A.xml") as f:
        msg = sdmx.read_sdmx(f)
    ds = msg.data[0]

    with pytest.raises(ValueError, match="No associated data flow definition for"):
        sdmx.to_csv(ds)

    _add_test_dsd(ds)

    with pytest.raises(ValueError, match="rtype"):
        sdmx.to_csv(ds, rtype=int)

    with pytest.raises(TypeError, match="positional"):
        sdmx.to_csv(ds, "foo")

    with pytest.raises(NotImplementedError, match="labels"):
        sdmx.to_csv(ds, labels="both")

    with pytest.raises(NotImplementedError, match="time_format"):
        sdmx.to_csv(ds, time_format="normalized")
