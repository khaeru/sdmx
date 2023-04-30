import pandas as pd
import pytest

import sdmx
from sdmx.model import v21 as m


@pytest.mark.parametrize_specimens("path", kind="data")
def test_write_data(tmp_path, specimen, path):
    msg = sdmx.read_sdmx(path)

    # Writer runs
    for i, dataset in enumerate(msg.data):
        if dataset.described_by is None:
            try:
                # Construct a fake/temporary DFD
                dataset.described_by = m.DataflowDefinition(
                    id=f"TEST_DFD_{dataset.structured_by.id}",
                    maintainer=dataset.structured_by.maintainer,
                    version="0.0",
                )
            except AttributeError:
                pytest.skip(reason="No DFD or DSD")

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
