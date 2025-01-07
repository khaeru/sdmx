import logging
import os
from collections import ChainMap
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Union

import numpy as np
import pandas as pd
import platformdirs
import pytest
from xdist import is_xdist_worker

from sdmx.exceptions import HTTPError
from sdmx.rest import Resource
from sdmx.session import Session
from sdmx.source import DataContentType, Source, sources
from sdmx.testing.report import ServiceReporter
from sdmx.util.requests import offline, save_response

if TYPE_CHECKING:
    import pytest

log = logging.getLogger(__name__)

# Default directory for local copy of test data/specimens
DATA_DEFAULT_DIR = platformdirs.user_cache_path("sdmx").joinpath("test-data")
DATA_ERROR = (
    "Unable to locate test specimens. Give --sdmx-fetch-data, or use "
    "--sdmx-test-data=… or the SDMX_TEST_DATA environment variable to indicate an "
    "existing directory"
)
# Git remote URL for cloning test data
# DATA_REMOTE_URL = "git@github.com:khaeru/sdmx-test-data.git"
DATA_REMOTE_URL = "https://github.com/khaeru/sdmx-test-data.git"

# Pytest stash keys
KEY_DATA = pytest.StashKey[Path]()
KEY_SPECIMENS = pytest.StashKey["SpecimenCollection"]()
KEY_SOURCE = pytest.StashKey["Source"]()

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


def fetch_data() -> Path:
    """Fetch test data from GitHub."""
    import git

    # Create a lock to avoid concurrency issues when running with pytest-xdist
    DATA_DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
    blf = git.BlockingLockFile(DATA_DEFAULT_DIR, check_interval_s=0.1)
    blf._obtain_lock()

    # Initialize a git Repo object
    repo = git.Repo.init(DATA_DEFAULT_DIR)

    try:
        # Reference to existing 'origin' remote
        origin = repo.remotes["origin"]
        # Ensure the DATA_REMOTE_URL is among the URLs for this remote
        if DATA_REMOTE_URL not in origin.urls:  # pragma: no cover
            origin.set_url(DATA_REMOTE_URL)
    except IndexError:
        # Create a new remote
        origin = repo.create_remote("origin", DATA_REMOTE_URL)

    log.info(f"Fetch test data from {origin} → {repo.working_dir}")

    origin.fetch("refs/heads/main", depth=1)  # Fetch only 1 commit from the remote
    origin_main = origin.refs["main"]  # Reference to 'origin/main'
    try:
        head = repo.heads["main"]  # Reference to existing local 'main'
    except IndexError:
        head = repo.create_head("main", origin_main)  # Create a local 'main'

    if (
        head.commit != origin_main.commit  # Commit differs
        or repo.is_dirty()  # Working dir is dirty
        or len(repo.index.diff(head.commit))
    ):
        # Check out files into the working directory
        head.set_tracking_branch(origin_main).checkout()

    del blf  # Release lock

    return Path(repo.working_dir)


def pytest_addoption(parser):
    """Add pytest command-line options."""
    parser.addoption(
        "--sdmx-fetch-data",
        action="store_true",
        help="fetch test specimens from GitHub",
    )
    parser.addoption(
        "--sdmx-test-data",
        # Use the environment variable value by default
        default=os.environ.get("SDMX_TEST_DATA", DATA_DEFAULT_DIR),
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

    # Convert the option value to an Path instance attribute on `config`
    try:
        config.stash[KEY_DATA] = Path(config.option.sdmx_test_data)
    except TypeError:  # pragma: no cover
        raise RuntimeError(DATA_ERROR) from None


def pytest_sessionstart(session: "pytest.Session") -> None:
    # Clone the test data if so configured, and not in an xdist worker process
    if session.config.option.sdmx_fetch_data and not is_xdist_worker(session):
        fetch_data()

    # Check the value can be converted to a path, and exists
    path = session.config.stash[KEY_DATA]
    if not path.exists():  # pragma: no cover
        # Cannot proceed further; this exception kills the test session
        raise FileNotFoundError(f"SDMX test data in {path}\n{DATA_ERROR}")

    # Create a SpecimenCollection from the files in the directory
    session.config.stash[KEY_SPECIMENS] = SpecimenCollection(path)

    # Create a test source
    session.config.stash[KEY_SOURCE] = Source(
        id="TEST",
        name="Test source",
        url="https://example.com/sdmx-rest",
        supports={feature: True for feature in list(Resource)},
    )


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

    sc = metafunc.config.stash[KEY_SPECIMENS]
    metafunc.parametrize(mark.args[0], sc.as_params(**mark.kwargs))


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


def generate_endpoint_tests(metafunc):  # noqa: C901  TODO reduce complexity 11 → ≤10
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
    source = (
        sources[cls.source_id]
        if cls.source_id != "TEST"
        else metafunc.config.stash[KEY_SOURCE]
    )

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
    specimens: list[tuple[Path, str, str]]

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
                ("ESTAT", "esms.xml"),
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
                ("ESTAT", "esms-structure.xml"),
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
                ("INSEE", "gh-205.xml"),
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
                ("WB", "gh-78.xml"),
            ]
        )

        # Add files from the SDMX 2.1 specification
        v21 = base_path.joinpath("v21", "xml")
        self.specimens.extend((p, "xml", None) for p in v21.glob("**/*.xml"))

        # Add files from the SDMX 3.0 specification
        v3 = base_path.joinpath("v3")

        # SDMX-CSV
        self.specimens.extend(
            (p, "csv", "data") for p in v3.joinpath("csv").glob("*.csv")
        )

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
        # Transform `marks` into a platform-independent mapping from path parts
        _marks = {PurePosixPath(k).parts: v for k, v in marks.items()}

        for path, f, k in self.specimens:
            if (format and format != f) or (kind and kind != k):
                continue
            p_rel = path.relative_to(self.base_path)
            yield pytest.param(
                path,
                id=str(p_rel),  # String ID for this specimen
                marks=_marks.get(p_rel.parts, tuple()),  # Look up marks via path parts
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
def session_with_pytest_cache(pytestconfig):
    """Fixture:  A :class:`.Session` that caches within :file:`.pytest_cache`.

    This subdirectory is ephemeral, and tests **must** pass whether or not it exists and
    is populated.
    """
    p = pytestconfig.cache.mkdir("sdmx-requests-cache")
    yield Session(cache_name=str(p), backend="filesystem")


@pytest.fixture(scope="session")
def session_with_stored_responses(pytestconfig, test_data_path):
    """Fixture: A :class:`.Session` returns only stored responses from sdmx-test-data.

    This session (a) uses the 'filesystem' :mod:`requests_cache` backend and (b) is
    treated with :func:`.offline`, so that *only* stored responses can be returned.
    """

    import sdmx
    from sdmx.format import MediaType
    from sdmx.message import StructureMessage

    p = test_data_path.joinpath("requests")
    session = Session(cache_name=str(p), backend="filesystem")

    # Populate stored responses for the 'TEST' source. These are not stored in
    # sdmx-test-data; only generated
    content: bytes = sdmx.to_xml(StructureMessage())
    headers = {"Content-Type": repr(MediaType("generic", "xml", "2.1"))}

    source = pytestconfig.stash[KEY_SOURCE]

    for endpoint, params in (
        ("actualconstraint", ""),
        ("agencyscheme", ""),
        ("allowedconstraint", ""),
        ("attachementconstraint", ""),
        ("availableconstraint", ""),
        ("categorisation", ""),
        ("categoryscheme", "?references=parentsandsiblings"),
        ("codelist", ""),
        ("conceptscheme", ""),
        ("contentconstraint", ""),
        ("customtypescheme", ""),
        ("dataconsumerscheme", ""),
        ("dataflow", ""),
        ("dataproviderscheme", ""),
        ("datastructure", ""),
        ("hierarchicalcodelist", ""),
        ("metadataflow", ""),
        ("metadatastructure", ""),
        ("namepersonalisationscheme", ""),
        ("organisationscheme", ""),
        ("organisationunitscheme", ""),
        ("process", ""),
        ("provisionagreement", ""),
        ("reportingtaxonomy", ""),
        ("rulesetscheme", ""),
        ("schema/datastructure", ""),
        ("structure", ""),
        ("structureset", ""),
        ("transformationscheme", ""),
        ("userdefinedoperatorscheme", ""),
        ("vtlmappingscheme", ""),
    ):
        url = f"{source.url}/{endpoint}/{source.id}/all/latest{params}"
        save_response(session, method="GET", url=url, content=content, headers=headers)

    # Raise an exception on any actual attempts to access the network
    offline(session)

    yield session


@pytest.fixture(scope="session")
def specimen(pytestconfig):
    """Fixture: the :class:`SpecimenCollection`."""
    yield pytestconfig.stash[KEY_SPECIMENS]


@pytest.fixture(scope="session")
def test_data_path(pytestconfig):
    """Fixture: the :py:class:`.Path` given as --sdmx-test-data."""
    yield pytestconfig.stash[KEY_DATA]


@pytest.fixture(scope="class")
def testsource(pytestconfig):
    """Fixture: the :attr:`.Source.id` of a temporary data source."""
    s = pytestconfig.stash[KEY_SOURCE]

    sources[s.id] = s

    try:
        yield s.id
    finally:
        sources.pop(s.id)
