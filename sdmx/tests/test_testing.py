import json

from sdmx.testing.report import main


def test_report_main(tmp_path):
    # Example input data
    with open(tmp_path.joinpath("TEST.json"), "w") as f:
        json.dump({"TEST": {"foo": "pass"}}, f)

    # Function runs
    main(tmp_path)

    # Output files are generated
    assert tmp_path.joinpath("all-data.json").exists()
    assert tmp_path.joinpath("index.html").exists()
