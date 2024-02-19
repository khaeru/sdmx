from sdmx.testing.report import main


def test_report_main(tmp_path):
    # Function runs
    main(tmp_path)

    # Output files are generated
    assert tmp_path.joinpath("all-data.json").exists()
    assert tmp_path.joinpath("index.html").exists()
