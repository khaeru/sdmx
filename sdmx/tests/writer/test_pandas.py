"""Tests for pandasdmx/writer.py."""

from typing import cast

import pandas as pd
import pandas.testing as pdt
import pytest
from pytest import raises

import sdmx
from sdmx.message import DataMessage, StructureMessage
from sdmx.model import common, v21
from sdmx.model.v21 import TimeDimension
from sdmx.testing import assert_pd_equal

MARKS = {
    "ESTAT/esms.xml": pytest.mark.xfail(raises=NotImplementedError),
}


def test_agencyscheme(specimen) -> None:
    # Convert an agency scheme
    with specimen("ECB/orgscheme.xml") as f:
        msg = sdmx.read_sdmx(f)
        data = sdmx.to_pandas(msg)

    assert data["organisation_scheme"]["SDMX:AGENCIES"]["ESTAT"] == "Eurostat"

    # to_pandas only returns keys for non-empty attributes of StructureMessage
    # https://github.com/dr-leo/pandaSDMX/issues/90
    assert set(data.keys()) == {"organisation_scheme"}

    # Attribute access works
    assert data.organisation_scheme["SDMX:AGENCIES"].ESTAT == "Eurostat"

    with pytest.raises(AttributeError):
        data.codelist
    with pytest.raises(AttributeError):
        data.dataflow
    with pytest.raises(AttributeError):
        data.structure


def test_categoryscheme(specimen) -> None:
    with specimen("IPI-2010-A21-structure.xml") as f:
        msg = sdmx.read_sdmx(f)
        data = sdmx.to_pandas(msg)

    cs = data["category_scheme"]["CLASSEMENT_DATAFLOWS"]

    assert cs.loc["COMPTA-NAT", "name"] == "National accounts (GDP, consumption...)"

    # Children appear
    assert cs.loc["CNA-PIB-2005", "parent"] == "CNA-PIB"


def test_codelist(specimen) -> None:
    # Retrieve codelists from a test specimen and convert to pandas
    with specimen("common-structure.xml") as f:
        dsd_common = sdmx.read_sdmx(f)
    codelists = sdmx.to_pandas(dsd_common)["codelist"]

    # File contains 5 code lists
    assert len(codelists) == 5

    # Code lists have expected number of items
    assert len(codelists["CL_FREQ"]) == 8

    # Items names can be retrieved by ID
    freq = codelists["CL_FREQ"]
    assert freq["A"] == "Annual"

    # Non-hierarchical code list has a string name
    assert freq.name == "Code list for Frequency (FREQ)"

    # Hierarchical code list
    with specimen("codelist_partial.xml") as f:
        msg = sdmx.read_sdmx(f)
        assert isinstance(msg, StructureMessage)

    # Convert single codelist
    CL_AREA = sdmx.to_pandas(msg.codelist["CL_AREA"])

    # Hierichical list has a 'parent' column; parent of Africa is the World
    assert CL_AREA.loc["002", "parent"] == "001"

    # Pandas features can be used to merge parent names
    area_hierarchy = pd.merge(
        CL_AREA,
        CL_AREA,
        how="left",
        left_on="parent",
        right_index=True,
        suffixes=("", "_parent"),
    )
    assert area_hierarchy.loc["002", "name_parent"] == "World"


def test_conceptscheme(specimen) -> None:
    with specimen("common-structure.xml") as f:
        msg = sdmx.read_sdmx(f)
        data = sdmx.to_pandas(msg)

    cdc = data["concept_scheme"]["CROSS_DOMAIN_CONCEPTS"]
    assert cdc.loc["UNIT_MEASURE", "name"] == "Unit of Measure"


@pytest.mark.parametrize_specimens("path", kind="data", marks=MARKS)
def test_data(specimen, path) -> None:
    if ("v3", "csv") == path.parts[-3:-1]:
        pytest.skip("SDMX-CSV 3.0.0 examples cannot be read without DSD")

    msg = sdmx.read_sdmx(path)

    result = sdmx.to_pandas(msg)

    expected = specimen.expected_data(path)
    if expected is not None:
        print(expected, result, sep="\n")
    assert_pd_equal(expected, result)

    # TODO incomplete
    assert isinstance(result, (pd.Series, pd.DataFrame, list)), type(result)


def test_data_decimal() -> None:
    """Test handling of "," as a decimal separator."""
    # Data set with string values containing "," as a decimal separator
    ds = v21.DataSet(
        obs=[
            v21.Observation(dimension=common.Key(FOO="A"), value="1"),
            v21.Observation(dimension=common.Key(FOO="B"), value="1,0"),
            v21.Observation(dimension=common.Key(FOO="C"), value="100,1"),
        ]
    )

    # Expected result
    exp = pd.Series(
        [1.0, 1.0, 100.1],
        index=pd.MultiIndex.from_product([list("ABC")], names=["FOO"]),
        name="value",
    )

    # Conversion occurs without error
    result = sdmx.to_pandas(ds)
    # Result is as expected
    pdt.assert_series_equal(exp, result)


def test_data_arguments(specimen) -> None:
    # The identity here is not important; any non-empty DataMessage will work
    with specimen("INSEE/CNA-2010-CONSO-SI-A17.xml") as f:
        msg = sdmx.read_sdmx(f)

    # Attributes must be a string
    with raises(TypeError):
        sdmx.to_pandas(msg, attributes=2)

    # Attributes must contain only 'dgso'
    with raises(ValueError):
        sdmx.to_pandas(msg, attributes="foobarbaz")


@pytest.mark.parametrize_specimens("path", kind="data", marks=MARKS)
def test_data_attributes(path) -> None:
    if ("v3", "csv") == path.parts[-3:-1]:
        pytest.skip("SDMX-CSV 3.0.0 examples cannot be read without DSD")

    msg = sdmx.read_sdmx(path)

    result = sdmx.to_pandas(msg, attributes="osgd")
    # TODO incomplete
    assert isinstance(result, (pd.Series, pd.DataFrame, list)), type(result)


def test_dataflow(specimen) -> None:
    # Read the INSEE dataflow definition
    with specimen("INSEE/dataflow") as f:
        msg = sdmx.read_sdmx(f)

    # Convert to pandas
    result = sdmx.to_pandas(msg, include="dataflow")

    # Number of Dataflows described in the file
    assert len(result["dataflow"]) == 663

    # ID and names of first Dataflows
    mbop = "Monthly Balance of Payments - "
    expected = pd.Series(
        {
            "ACT-TRIM-ANC": "Activity by sex and age - Quarterly series",
            "BPM6-CCAPITAL": "{}Capital account".format(mbop),
            "BPM6-CFINANCIER": "{}Financial account".format(mbop),
            "BPM6-CTRANSACTION": "{}Current transactions account".format(mbop),
            "BPM6-TOTAL": "{}Overall total and main headings".format(mbop),
        }
    )
    assert_pd_equal(result["dataflow"].head(), expected)


@pytest.mark.network
def test_dataset_constraint(specimen) -> None:
    """'constraint' argument to writer.write_dataset."""
    with specimen("ng-ts.xml") as f:
        msg = sdmx.read_sdmx(f)
        assert isinstance(msg, DataMessage)

    # Fetch the message's DSD
    assert msg.structure.is_external_reference
    # NB the specimen included in tests/data has 'ECB_EXR_NG' as the data structure ID;
    #    but a query against the web service gives 'ECB_EXR1' for the same data
    #    structure.
    id = "ECB_EXR1"
    dsd = cast(
        StructureMessage,
        sdmx.Client(msg.structure.maintainer.id).get("datastructure", id),
    ).structure[id]

    # Create a ContentConstraint
    cc = dsd.make_constraint({"CURRENCY": "JPY+USD"})

    # Write the message without constraint
    s1 = sdmx.to_pandas(msg)
    assert len(s1) == 12
    assert set(s1.index.to_frame()["CURRENCY"]) == {"CHF", "GBP", "JPY", "USD"}

    # Writing using constraint produces a fewer items; only those matching the
    # constraint
    s2 = sdmx.to_pandas(msg, constraint=cc)
    assert len(s2) == 6
    assert set(s2.index.to_frame()["CURRENCY"]) == {"JPY", "USD"}


def test_dataset_datetime(specimen) -> None:
    """Test datetime arguments to write_dataset()."""
    # Load structure
    with specimen("IPI-2010-A21-structure.xml") as f:
        dsd = cast(StructureMessage, sdmx.read_sdmx(f)).structure["IPI-2010-A21"]
        TIME_PERIOD = dsd.dimensions.get("TIME_PERIOD")
        FREQ = dsd.dimensions.get("FREQ")

    assert isinstance(TIME_PERIOD, TimeDimension)

    # Load data, two ways
    with specimen("IPI-2010-A21.xml") as f:
        msg = sdmx.read_sdmx(f, structure=dsd)
        assert isinstance(msg, DataMessage)
        ds = msg.data[0]
    with specimen("IPI-2010-A21.xml") as f:
        msg_no_structure = sdmx.read_sdmx(f)
        assert isinstance(msg_no_structure, DataMessage)

    other_dims = list(
        filter(lambda n: n != "TIME_PERIOD", [d.id for d in dsd.dimensions.components])
    )

    def expected(df, axis=0, cls=pd.DatetimeIndex):
        axes = ["index", "columns"] if axis else ["columns", "index"]
        assert getattr(df, axes[0]).names == other_dims
        assert isinstance(getattr(df, axes[1]), cls)

    # Write with datetime=str
    df = sdmx.to_pandas(ds, datetime="TIME_PERIOD")
    expected(df)

    # Write with datetime=Dimension instance
    df = sdmx.to_pandas(ds, datetime=TIME_PERIOD)
    expected(df)

    # Write with datetime=True fails because the data message contains no
    # actual structure information
    with pytest.raises(ValueError, match=r"no TimeDimension in \[.*\]"):
        sdmx.to_pandas(msg_no_structure, datetime=True)
    with pytest.raises(ValueError, match=r"no TimeDimension in \[.*\]"):
        sdmx.to_pandas(msg_no_structure.data[0], datetime=True)

    # DataMessage parsed with a DSD allows write_dataset to infer the
    # TimeDimension
    df = sdmx.to_pandas(msg, datetime=True)
    expected(df)
    # Same for DataSet
    df = sdmx.to_pandas(ds, datetime=True)
    expected(df)

    # As above, with axis=1
    df = sdmx.to_pandas(ds, datetime=dict(dim="TIME_PERIOD", axis=1))
    expected(df, axis=1)
    df = sdmx.to_pandas(ds, datetime=dict(dim=TIME_PERIOD, axis=1))
    expected(df, axis=1)
    ds.structured_by = dsd
    df = sdmx.to_pandas(ds, datetime=dict(axis=1))
    expected(df, axis=1)
    df = sdmx.to_pandas(msg, datetime=dict(axis=1))
    expected(df, axis=1)

    # Write with freq='M' works
    df = sdmx.to_pandas(ds, datetime=dict(dim="TIME_PERIOD", freq="M"))
    expected(df, cls=pd.PeriodIndex)

    # Write with freq='Y' (in older pandas, freq='A') works
    df = sdmx.to_pandas(ds, datetime=dict(dim="TIME_PERIOD", freq="Y"))
    expected(df, cls=pd.PeriodIndex)
    # …but the index is not unique, because month information was discarded
    assert not df.index.is_unique

    # Write specifying the FREQ dimension by name fails
    with pytest.raises(
        ValueError,
        match="cannot convert to PeriodIndex with " r"non-unique freq=\['A', 'M'\]",
    ):
        sdmx.to_pandas(ds, datetime=dict(dim="TIME_PERIOD", freq="FREQ"))

    # Remove non-monthly obs
    # TODO use a constraint, when this is supported
    ds.obs = list(filter(lambda o: o.key.FREQ != "A", ds.obs))

    # Now specifying the dimension by name works
    df = sdmx.to_pandas(ds, datetime=dict(dim="TIME_PERIOD", freq="FREQ"))

    # and FREQ is no longer in the columns index
    other_dims.pop(other_dims.index("FREQ"))
    expected(df, cls=pd.PeriodIndex)

    # Specifying a Dimension works
    df = sdmx.to_pandas(ds, datetime=dict(dim=TIME_PERIOD, freq=FREQ))
    expected(df, cls=pd.PeriodIndex)

    # As above, using DSD attached to the DataMessage
    df = sdmx.to_pandas(msg, datetime=dict(dim=TIME_PERIOD, freq="FREQ"))
    expected(df, cls=pd.PeriodIndex)

    # Invalid arguments
    with pytest.raises(ValueError, match="X"):
        sdmx.to_pandas(msg, datetime=dict(dim=TIME_PERIOD, freq="X"))
    with pytest.raises(ValueError, match="foo"):
        sdmx.to_pandas(ds, datetime=dict(foo="bar"))
    with pytest.raises(ValueError, match="43"):
        sdmx.to_pandas(ds, datetime=43)


def test_list_of_obs(specimen) -> None:
    """Bare list of observations can be written."""
    with specimen("ng-ts.xml") as f:
        msg = sdmx.read_sdmx(f)
        assert isinstance(msg, DataMessage)

    sdmx.to_pandas(msg.data[0].obs)


@pytest.mark.parametrize_specimens("path", kind="structure")
def test_structure(path) -> None:
    msg = sdmx.read_sdmx(path)

    sdmx.to_pandas(msg)

    # TODO test contents
