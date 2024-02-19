import logging
import os
from collections import ChainMap
from contextlib import contextmanager
from pathlib import Path
from typing import List, Tuple, Union

import numpy as np
import pandas as pd
import pytest

from sdmx.exceptions import HTTPError
from sdmx.rest import Resource
from sdmx.source import DataContentType, add_source, sources
from sdmx.testing.report import ServiceReporter

log = logging.getLogger(__name__)


# Expected to_pandas() results for data files; see expected_data()
# - Keys are the file name (above) with '.' -> '-': 'foo.xml' -> 'foo-xml'
# - Data is stored in expected/{KEY}.txt
# - Values are either argument to pd.read_csv(); or a dict(use='other-key'),
#   in which case the info for other-key is used instead.
EXPECTED = {
    "ng-flat-xml": dict(index_col=[0, 1, 2, 3, 4, 5]),
    "ng-ts-gf-xml": dict(use="ng-flat-xml"),
    "ng-ts-xml": dict(use="ng-flat-xml"),
    "ng-xs-xml": dict(index_col=[0, 1, 2, 3, 4, 5]),
    # Excluded: this file contains two DataSets, and expected_data() currently
    # only supports specimens with one DataSet
    # 'action-delete-json': dict(header=[0, 1, 2, 3, 4]),
    "xs-json": dict(index_col=[0, 1, 2, 3, 4, 5]),
    "flat-json": dict(index_col=[0, 1, 2, 3, 4, 5]),
    "ts-json": dict(use="flat-json"),
}


def assert_pd_equal(left, right, **kwargs):
    """Assert equality of two pandas objects."""
    if left is None:
        return
    method = {
        pd.Series: pd.testing.assert_series_equal,
        pd.DataFrame: pd.testing.assert_frame_equal,
        np.ndarray: np.testing.assert_array_equal,
    }[left.__class__]
    method(left, right, **kwargs)


def pytest_addoption(parser):
    """Add the ``--sdmx-test-data`` command-line option to pytest."""
    parser.addoption(
        "--sdmx-test-data",
        # Use the environment variable value by default
        default=os.environ.get("SDMX_TEST_DATA", None),
        help="path to SDMX test specimens",
    )


def pytest_configure(config):
    """Handle the ``--sdmx-test-data`` command-line option."""
    # Register "parametrize_specimens" as a known mark to suppress warnings from pytest
    config.addinivalue_line(
        "markers", "parametrize_specimens: (for internal use by sdmx.testing)"
    )

    # Register plugin for reporting service outputs
    config._sdmx_reporter = ServiceReporter(config)
    config.pluginmanager.register(config._sdmx_reporter)

    # Check the value can be converted to a path, and exists
    message = "Give --sdmx-test-data=… or set the SDMX_TEST_DATA environment variable"
    try:
        sdmx_test_data = Path(config.option.sdmx_test_data)
    except TypeError:  # pragma: no cover
        raise RuntimeError(message) from None
    else:  # pragma: no cover
        if not sdmx_test_data.exists():  # pragma: no cover
            # Cannot proceed further; this exception kills the test session
            raise FileNotFoundError(f"SDMX test data in {sdmx_test_data}\n{message}")

    setattr(config, "sdmx_test_data", sdmx_test_data)
    setattr(config, "sdmx_specimens", SpecimenCollection(sdmx_test_data))

    # Add a source globally for use with mock_service_adapter
    # TODO Deduplicate between this and the "testsource" fixture
    info = dict(
        id="MOCK",
        name="Mock source",
        url="mock://example.com/",
        supports={feature: True for feature in list(Resource)},
    )
    add_source(info)


def pytest_generate_tests(metafunc):
    """Generate tests.

    Calls both :func:`parametrize_specimens` and :func:`generate_endpoint_tests`.
    """
    parametrize_specimens(metafunc)
    generate_endpoint_tests(metafunc)


def parametrize_specimens(metafunc):
    """Handle ``@pytest.mark.parametrize_specimens(…)``."""
    try:
        mark = next(metafunc.definition.iter_markers("parametrize_specimens"))
    except StopIteration:
        return

    metafunc.parametrize(
        mark.args[0], metafunc.config.sdmx_specimens.as_params(**mark.kwargs)
    )


#: Marks for use below.
XFAIL = {
    # Exceptions resulting from querying an endpoint not supported by a service
    "unsupported": pytest.mark.xfail(
        strict=True,
        reason="Not implemented by service",
        raises=(
            HTTPError,  # 401, 404, 405, etc.
            NotImplementedError,  # 501, converted automatically
            ValueError,  # e.g. WB_WDI, returns invalid content type
        ),
    ),
    # Returned by servers that may be temporarily unavailable at the time of test
    503: pytest.mark.xfail(
        raises=HTTPError, reason="503 Server Error: Service Unavailable"
    ),
}


def generate_endpoint_tests(metafunc):
    """pytest hook for parametrizing tests that need an "endpoint" fixture.

    This function relies on the :class:`.DataSourceTest` base class defined in
    :mod:`.test_sources`. It:

    - Generates one parametrization for every :class:`.Resource` (= REST API endpoint).
    - Applies pytest "xfail" (expected failure) marks according to:

      1. :attr:`.Source.supports`, i.e. if the particular source is marked as not
         supporting certain endpoints, the test is expected to fail.
      2. :attr:`.DataSourceTest.xfail`, any other failures defined on the source test
         class (e.g. :class:`.DataSourceTest` subclass).
      3. :attr:`.DataSourceTest.xfail_common`, common failures.
    """
    if "endpoint" not in metafunc.fixturenames:
        return  # Don't need to parametrize this metafunc

    # Arguments to parametrize()
    params = []

    # Use the test class' source_id attr to look up the Source class
    cls = metafunc.cls
    source = sources[cls.source_id]

    # Merge subclass-specific and "common" xfail marks, preferring the former
    xfails = ChainMap(cls.xfail, cls.xfail_common)

    # Iterate over all known endpoints
    for ep in Resource:
        # Accumulate multiple marks; first takes precedence
        marks = []

        # Get any keyword arguments for this endpoint
        args = cls.endpoint_args.get(ep.name, dict())
        if ep is Resource.data and not len(args):
            # args must be specified for a data query; no args → no test
            continue

        # Check if the associated source supports the endpoint
        supported = source.supports[ep]
        if source.data_content_type == DataContentType.JSON and ep is not Resource.data:
            # SDMX-JSON sources only support data queries
            continue
        elif not supported:
            args["force"] = True
            marks.append(XFAIL["unsupported"])

        # Check if the test function's class contains an expected failure for `endpoint`
        xfail = xfails.get(ep.name, None)
        if not marks and xfail:
            # Mark the test as expected to fail
            try:  # Unpack a tuple
                mark = pytest.mark.xfail(raises=xfail[0], reason=xfail[1])
            except TypeError:
                mark = pytest.mark.xfail(raises=xfail)
            marks.append(mark)

            if not supported:  # pragma: no cover; for identifying extraneous entries
                log.info(
                    f"tests for {source.id!r} mention unsupported endpoint {ep.name!r}"
                )

        # Tolerate 503 errors
        if cls.tolerate_503:
            marks.append(XFAIL[503])

        params.append(pytest.param(ep, args, id=ep.name, marks=marks))

    if len(params):
        # Run the test function once for each endpoint
        metafunc.parametrize("endpoint, args", params)
    # commented: for debugging
    # else:
    #     pytest.skip("No endpoints to be tested")


class MessageTest:
    """Base class for tests of specific specimen files."""

    directory: Union[str, Path] = Path(".")
    filename: str

    @pytest.fixture(scope="class")
    def path(self, test_data_path):
        yield test_data_path / self.directory

    @pytest.fixture(scope="class")
    def msg(self, path):
        import sdmx

        return sdmx.read_sdmx(path / self.filename)


class SpecimenCollection:
    """Collection of test specimens."""

    # Path to specimen; file format; data/structure
    # TODO add version
    specimens: List[Tuple[Path, str, str]]

    def __init__(self, base_path):
        self.base_path = base_path
        self.specimens = []

        # XML data files for the ECB exchange rate data flow
        for source_id in ("ECB_EXR",):
            for path in base_path.joinpath(source_id).rglob("*.xml"):
                kind = "data"
                if "structure" in path.name or "common" in path.name:
                    kind = "structure"
                self.specimens.append((path, "xml", kind))

        # JSON data files for ECB and OECD data flows
        for source_id in ("ECB_EXR", "OECD"):
            self.specimens.extend(
                (fp, "json", "data")
                for fp in base_path.joinpath(source_id).rglob("*.json")
            )

        # Miscellaneous XML data files
        self.specimens.extend(
            (base_path.joinpath(*parts), "xml", "data")
            for parts in [
                ("INSEE", "CNA-2010-CONSO-SI-A17.xml"),
                ("INSEE", "IPI-2010-A21.xml"),
                ("ESTAT", "footer.xml"),
                ("ESTAT", "NAMA_10_GDP-ss.xml"),
            ]
        )

        # Miscellaneous XML structure files
        self.specimens.extend(
            (base_path.joinpath(*parts), "xml", "structure")
            for parts in [
                ("BIS", "actualconstraint-0.xml"),
                ("BIS", "hierarchicalcodelist-0.xml"),
                ("ECB", "orgscheme.xml"),
                ("ECB", "structureset-0.xml"),
                ("ESTAT", "apro_mk_cola-structure.xml"),
                ("ESTAT", "GOV_10Q_GGNFA.xml"),
                ("ESTAT", "HCL_WSTATUS_SCL_BNSPART.xml"),
                ("ESTAT", "HCL_WSTATUS_SCL_WSTATUSPR.xml"),
                ("IAEG-SDGs", "metadatastructure-0.xml"),
                ("IMF", "1PI-structure.xml"),
                ("IMF", "CL_AREA-structure.xml"),
                # Manually reduced subset of the response for this DSD. Test for
                # <str:CubeRegion> containing both <com:KeyValue> and <com:Attribute>
                ("IMF", "ECOFIN_DSD-structure.xml"),
                ("IMF", "hierarchicalcodelist-0.xml"),
                ("IMF", "structureset-0.xml"),
                ("IMF_STA", "availableconstraint_CPI.xml"),  # khaeru/sdmx#161
                ("IMF_STA", "DSD_GFS.xml"),  # khaeru/sdmx#164
                ("INSEE", "CNA-2010-CONSO-SI-A17-structure.xml"),
                ("INSEE", "dataflow.xml"),
                ("INSEE", "IPI-2010-A21-structure.xml"),
                ("ISTAT", "22_289-structure.xml"),
                ("ISTAT", "47_850-structure.xml"),
                ("ISTAT", "actualconstraint-0.xml"),
                ("ISTAT", "metadataflow-0.xml"),
                ("ISTAT", "metadatastructure-0.xml"),
                ("OECD", "actualconstraint-0.xml"),
                ("OECD", "metadatastructure-0.xml"),
                ("UNICEF", "GLOBAL_DATAFLOW-structure.xml"),
                ("UNSD", "codelist_partial.xml"),
                ("SDMX", "HCL_TEST_AREA.xml"),
                ("SGR", "common-structure.xml"),
                ("SGR", "hierarchicalcodelist-0.xml"),
                ("SGR", "metadatastructure-0.xml"),
                ("SPC", "actualconstraint-0.xml"),
                ("SPC", "metadatastructure-0.xml"),
                ("TEST", "gh-142.xml"),
                ("TEST", "gh-149.xml"),
            ]
        )

        # Add files from the SDMX 2.1 specification
        v21 = base_path.joinpath("v21", "xml")
        self.specimens.extend((p, "xml", None) for p in v21.glob("**/*.xml"))

        # Add files from the SDMX 3.0 specification
        v3 = base_path.joinpath("v3")

        # commented: SDMX-JSON 2.0 is not yet implemented
        # # SDMX-JSON
        # self.specimens.extend(
        #     (p, "json", "data") for p in v3.joinpath("json", "data").glob("*.json")
        # )
        # for dir in ("metadata", "structure"):
        #     self.specimens.extend(
        #         (p, "json", "structure")
        #         for p in v3.joinpath("json", dir).glob("*.json")
        #     )

        # SDMX-ML
        self.specimens.extend((p, "xml", None) for p in v3.glob("xml/*.xml"))

    @contextmanager
    def __call__(self, pattern="", opened=True):
        """Open the test specimen file with `pattern` in the name."""
        for path, f, k in self.specimens:
            if path.match("*" + pattern + "*"):
                yield open(path, "br") if opened else path
                return
        raise ValueError(pattern)  # pragma: no cover

    def as_params(self, format=None, kind=None, marks=dict()):
        """Generate :func:`pytest.param` from specimens.

        One :func:`~.pytest.param` is generated for each specimen that matches the
        `format` and `kind` arguments (if any). Marks are attached to each param from
        `marks`, wherein the keys are partial paths.
        """
        for path, f, k in self.specimens:
            if (format and format != f) or (kind and kind != k):
                continue
            yield pytest.param(
                path,
                id=str(path.relative_to(self.base_path)),
                marks=marks.get(path, tuple()),
            )

    def expected_data(self, path):
        """Return the expected :func:`.to_pandas()` result for the specimen `path`."""
        try:
            key = path.name.replace(".", "-")
            info = EXPECTED[key]
            if "use" in info:
                # Use the same expected data as another file
                key = info["use"]
                info = EXPECTED[key]
        except KeyError:
            return None

        args = dict(sep=r"\s+", index_col=[0], header=[0])
        args.update(info)

        result = pd.read_csv(
            self.base_path.joinpath("expected", key).with_suffix(".txt"), **args
        )

        # A series; unwrap
        if set(result.columns) == {"value"}:
            result = result["value"]

        return result


@pytest.fixture(scope="session")
def test_data_path(pytestconfig):
    """Fixture: the :py:class:`.Path` given as --sdmx-test-data."""
    yield pytestconfig.sdmx_test_data


@pytest.fixture(scope="session")
def specimen(pytestconfig):
    """Fixture: the :class:`SpecimenCollection`."""
    yield pytestconfig.sdmx_specimens


@pytest.fixture(scope="session")
def mock_service_adapter():
    from requests_mock import Adapter

    import sdmx
    from sdmx.format import MediaType
    from sdmx.message import StructureMessage

    a = Adapter()

    common = dict(
        content=sdmx.to_xml(StructureMessage()),
        status_code=200,
        headers={"Content-Type": repr(MediaType("generic", "xml", "2.1"))},
    )
    for path in (
        "actualconstraint/MOCK/all/latest",
        "agencyscheme/MOCK/all/latest",
        "allowedconstraint/MOCK/all/latest",
        "attachementconstraint/MOCK/all/latest",
        "availableconstraint",
        "categorisation/MOCK/all/latest",
        "categoryscheme/MOCK/all/latest",
        "codelist/MOCK/all/latest",
        "conceptscheme/MOCK/all/latest",
        "contentconstraint/MOCK/all/latest",
        "customtypescheme/MOCK/all/latest",
        "dataconsumerscheme/MOCK/all/latest",
        "dataflow/MOCK/all/latest",
        "dataproviderscheme/MOCK/all/latest",
        "datastructure/MOCK/all/latest",
        "hierarchicalcodelist/MOCK/all/latest",
        "metadataflow/MOCK/all/latest",
        "metadatastructure/MOCK/all/latest",
        "namepersonalisationscheme/MOCK/all/latest",
        "organisationscheme/MOCK/all/latest",
        "organisationunitscheme/MOCK/all/latest",
        "process/MOCK/all/latest",
        "provisionagreement/MOCK/all/latest",
        "reportingtaxonomy/MOCK/all/latest",
        "rulesetscheme/MOCK/all/latest",
        "schema/datastructure/MOCK/all/latest",
        "structure/MOCK/all/latest",
        "structureset/MOCK/all/latest",
        "transformationscheme/MOCK/all/latest",
        "userdefinedoperatorscheme/MOCK/all/latest",
        "vtlmappingscheme/MOCK/all/latest",
    ):
        a.register_uri("GET", f"mock://example.com/{path}", **common)

    yield a


@pytest.fixture(scope="class")
def testsource():
    """Fixture: the :attr:`.Source.id` of a non-existent data source."""
    id = "TEST"
    add_source(dict(id=id, name="Test source", url="https://example.com/sdmx-rest"))

    try:
        yield id
    finally:
        sources.pop(id)
