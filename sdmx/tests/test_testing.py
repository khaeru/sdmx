import json
import sys

import pytest

from sdmx.testing.report import main


@pytest.mark.skipif(
    sys.version_info.minor < 9,
    reason="Uses dict() | other, not available in Python 3.8",
)
def test_report_main(tmp_path):
    # Example input data
    with open(tmp_path.joinpath("TEST.json"), "w") as f:
        json.dump({"TEST": {"foo": "pass"}}, f)

    # Function runs
    main(tmp_path)

    # Output files are generated
    assert tmp_path.joinpath("all-data.json").exists()
    assert tmp_path.joinpath("index.html").exists()
