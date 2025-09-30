import re
from functools import partial
from itertools import product
from typing import TYPE_CHECKING, cast

import pandas as pd
import pytest

import sdmx
from sdmx import message
from sdmx.convert.pandas import Attributes
from sdmx.format import csv
from sdmx.format.csv.common import CSVFormatOptions, Labels
from sdmx.format.csv.v1 import FormatOptions as V1FormatOptions
from sdmx.format.csv.v2 import FormatOptions as V2FormatOptions
from sdmx.format.csv.v2 import Keys
from sdmx.model import common, v21

if TYPE_CHECKING:
    from pathlib import Path

    from sdmx.types import MaintainableArtefactArgs, ToCSVArgs


MARKS = {
    "ESTAT/esms.xml": pytest.mark.xfail(raises=NotImplementedError),
}


def _add_test_dsd(ds: v21.DataSet) -> None:
    if ds.described_by is None:
        dsd = ds.structured_by
        if dsd is None:
            pytest.skip(reason="No DFD or DSD")
        else:
            # Construct a fake/temporary DFD
            ds.described_by = v21.DataflowDefinition(
                id=f"_TEST_{dsd.id}", maintainer=dsd.maintainer, version="0.0"
            )


@pytest.mark.parametrize_specimens("path", kind="data", marks=MARKS)
@pytest.mark.parametrize("format_options", [None, V1FormatOptions(), V2FormatOptions()])
def test_write_data(tmp_path: "Path", specimen, path, format_options) -> None:
    if ("v3", "csv") == path.parts[-3:-1]:
        pytest.skip("SDMX-CSV 3.0.0 examples cannot be read without DSD")

    msg = cast("message.DataMessage", sdmx.read_sdmx(path))

    kw: "ToCSVArgs" = dict(attributes=Attributes.all, format_options=format_options)
    for i, dataset in enumerate(msg.data):
        _add_test_dsd(dataset)

        # Writer runs successfully
        result = sdmx.to_csv(dataset, rtype=pd.DataFrame, **kw)
        assert isinstance(result, (pd.Series, pd.DataFrame))

        # print(result.head().to_string()) # DEBUG

        # Write directly to file also works
        path_out = tmp_path.joinpath(f"{i}.csv")
        assert None is sdmx.to_csv(dataset, path=path_out, **kw)
        assert path_out.exists()

        # Standard features are respected
        if isinstance(format_options, V1FormatOptions):
            assert "DATAFLOW" == result.columns[0]
            assert "OBS_VALUE" in result.columns
            with open(path_out, "r") as f:
                assert f.readline().startswith("DATAFLOW,")


@pytest.fixture
def messages() -> tuple[message.StructureMessage, message.DataMessage]:
    """:class:`.DataMessage` with complete structures."""
    sm = message.StructureMessage()
    ma_args: "MaintainableArtefactArgs" = dict(
        maintainer=common.Agency(id="AGENCY"), version="1.0"
    )
    dsd = v21.DataStructureDefinition(id="DSD", **ma_args)
    df = v21.DataflowDefinition(id="DF", **ma_args, structure=dsd)
    dd, md, ad = dsd.dimensions, dsd.measures, dsd.attributes
    cs = common.ConceptScheme(id="CS", **ma_args)

    # Code lists
    cl: dict[str, common.Codelist] = dict()

    for concept_id in ("FOO", "BAR", "BAZ", "QUX"):
        cs.setdefault(id=concept_id, name=concept_id.title())
        _cl = cl[concept_id] = common.Codelist(id=f"CL_{concept_id}")
        [
            _cl.setdefault(id=f"{concept_id}{i}", name=f"{concept_id.title()} {i}")
            for i in range(3)
        ]
    # FOO and BAR are dimensions
    dd.getdefault(id="DIM_FOO", concept_identity=cs["FOO"])
    dd.getdefault(id="DIM_BAR", concept_identity=cs["BAR"])
    # The primary measure has an ID different from "OBS_VALUE"
    OBS_VALUE = cs.setdefault(id="OBS_VALUE_X", name="Observation value")
    md.getdefault(id="OBS_VALUE_X", concept_identity=OBS_VALUE)
    # BAZ and QUX are attributes
    ad.getdefault(id="ATTR_BAZ", concept_identity=cs["BAZ"])
    ad.getdefault(id="ATTR_QUX", concept_identity=cs["QUX"])

    ds = v21.DataSet(described_by=df, structured_by=dsd)
    dm = message.DataMessage(dataflow=df, data=[ds])

    obs = []
    for foo, bar in product(cl["FOO"], cl["BAR"]):
        # TODO Add attribute values
        obs.append(
            v21.Observation(
                attached_attribute={
                    "ATTR_BAZ": common.AttributeValue(
                        value=cl["BAZ"]["BAZ0"], value_for=ad.get("ATTR_BAZ")
                    ),
                    "ATTR_QUX": common.AttributeValue(
                        value=cl["QUX"]["QUX0"], value_for=ad.get("ATTR_QUX")
                    ),
                },
                dimension=common.Key(described_by=dd, DIM_FOO=foo, DIM_BAR=bar),
                value="1.23",
                value_for=md.components[0],
            )
        )
    ds.add_obs(obs)
    return sm, dm


#: Mapping from format_options=… argument → expected initial columns.
EXP_COLS_START = {
    csv.v1.FormatOptions: ["DATAFLOW"],
    csv.v2.FormatOptions: ["STRUCTURE", "STRUCTURE_ID", "ACTION"],
    type(None): [
        "STRUCTURE",
        "STRUCTURE_ID",
        "ACTION",
    ],  # Default: same as SDMX-CSV 2.x
}

#: Mapping from labels= keyword argument → expected column names.
EXP_COLS = {
    Labels.id: [
        "DIM_FOO",
        "DIM_BAR",
        "OBS_VALUE_X",
        "ATTR_BAZ",
        "ATTR_QUX",
    ],
    Labels.both: [
        "DIM_FOO: Foo",
        "DIM_BAR: Bar",
        "OBS_VALUE_X: Observation value",
        "ATTR_BAZ: Baz",
        "ATTR_QUX: Qux",
    ],
    Labels.name: [
        "DIM_FOO",
        "Foo",
        "DIM_BAR",
        "Bar",
        "OBS_VALUE_X",
        "Observation value",
        "ATTR_BAZ",
        "Baz",
        "ATTR_QUX",
        "Qux",
    ],
}


@pytest.mark.parametrize(
    "keys",
    (
        Keys.none,
        pytest.param(Keys.both, marks=pytest.mark.xfail(raises=NotImplementedError)),
        pytest.param(Keys.obs, marks=pytest.mark.xfail(raises=NotImplementedError)),
        pytest.param(Keys.both, marks=pytest.mark.xfail(raises=NotImplementedError)),
    ),
)
def test_write_keys(
    messages: tuple[message.StructureMessage, message.DataMessage], keys: Keys
) -> None:
    """SDMX-CSV can be produced with :attr:`Labels.both` and :attr:`Labels.name`."""
    sm, dm = messages

    fo = csv.v2.FormatOptions()
    result = sdmx.to_csv(
        dm, rtype=pd.DataFrame, format_options=fo, keys=keys, attributes=Attributes.all
    )
    assert isinstance(result, pd.DataFrame)

    assert EXP_COLS_START[type(fo)] + EXP_COLS[Labels.id] == result.columns.to_list()
    assert len(dm.data[0]) == len(result)


@pytest.mark.parametrize("fo", [None, csv.v1.FormatOptions(), csv.v2.FormatOptions()])
@pytest.mark.parametrize("labels", list(Labels))
def test_write_labels(
    messages: tuple[message.StructureMessage, message.DataMessage],
    fo: CSVFormatOptions,
    labels: Labels,
) -> None:
    """SDMX-CSV can be produced with :attr:`Labels.both` and :attr:`Labels.name`."""
    sm, dm = messages

    if type(fo) is csv.v1.FormatOptions and labels is Labels.name:
        pytest.skip(reason="Invalid combination")

    result = sdmx.to_csv(
        dm,
        rtype=pd.DataFrame,
        format_options=fo,
        labels=labels,
        attributes=Attributes.all,
    )
    assert isinstance(result, pd.DataFrame)

    # print(result.to_string())  # DEBUG
    expr = re.compile("_X" if type(fo) is csv.v1.FormatOptions else "^$")
    assert (
        list(map(partial(expr.sub, ""), EXP_COLS_START[type(fo)] + EXP_COLS[labels]))
        == result.columns.to_list()
    )
    assert len(dm.data[0]) == len(result)


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

    with pytest.raises(NotImplementedError, match="time_format"):
        sdmx.to_csv(ds, time_format="normalized")
