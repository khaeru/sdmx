import logging
import os
import re
from collections import ChainMap
from pathlib import Path
from typing import TYPE_CHECKING, Union

import numpy as np
import pandas as pd
import pytest
import responses
from xdist import is_xdist_worker

from sdmx.exceptions import HTTPError
from sdmx.format import Version
from sdmx.rest import Resource
from sdmx.session import Session
from sdmx.source import DataContentType, Source, get_source
from sdmx.testing.report import ServiceReporter
from sdmx.util.requests import offline

from . import data

if TYPE_CHECKING:
    import pytest

log = logging.getLogger(__name__)

# Pytest stash keys
KEY_DATA = pytest.StashKey[Path]()
KEY_SPECIMENS = pytest.StashKey["data.SpecimenCollection"]()
KEY_SOURCE = pytest.StashKey["Source"]()


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
    """Add pytest command-line options."""
    parser.addoption(
        "--sdmx-fetch-data",
        action="store_true",
        help="fetch test specimens from GitHub",
    )
    parser.addoption(
        "--sdmx-test-data",
        # Use the environment variable value by default
        default=os.environ.get("SDMX_TEST_DATA", data.DEFAULT_DIR),
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
        raise RuntimeError(data.ERROR) from None


def pytest_sessionstart(session: "pytest.Session") -> None:
    """Create session-wide objects.

    These are used by the fixtures :func:`.specimen`, :func:`.testsource`.
    """
    c = session.config

    # Create a SpecimenCollection from the files in the directory
    c.stash[KEY_SPECIMENS] = data.SpecimenCollection(
        c.stash[KEY_DATA],
        # Fetch the test data if so configured, and not in an xdist worker process
        c.option.sdmx_fetch_data and not is_xdist_worker(session),
    )

    # Create a test source
    c.stash[KEY_SOURCE] = Source(
        id="TEST",
        name="Test source",
        url="https://example.com/sdmx-rest",
        supports={feature: True for feature in list(Resource)},
    )


def pytest_generate_tests(metafunc):
    """Generate tests.

    Calls both :func:`parametrize_specimens` and :func:`generate_endpoint_tests`.
    """
    # Handle the 'parametrize_specimens' mark
    metafunc.config.stash[KEY_SPECIMENS].parametrize(metafunc)
    # Handle the 'endpoint' fixture request
    generate_endpoint_tests(metafunc)


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
        get_source(cls.source_id)
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


@pytest.fixture(scope="session")
def installed_schemas(mock_gh_api, tmp_path_factory):
    """Fixture that ensures schemas are installed locally in a temporary directory."""
    from sdmx.format.xml.common import install_schemas

    dir = tmp_path_factory.mktemp("schemas")

    with mock_gh_api:
        install_schemas(dir.joinpath("2.1"), Version["2.1"])
        install_schemas(dir.joinpath("3.0"), Version["3.0.0"])

    yield dir


@pytest.fixture(scope="session")
def mock_gh_api():
    """Mock GitHub API responses to avoid hitting rate limits.

    For each API endpoint URL queried by :func:.`_gh_zipball`, return a pared-down JSON
    response that contains the required "zipball_url" key.
    """
    base = "https://api.github.com/repos/sdmx-twg/sdmx-ml"

    # TODO Improve .util.requests to provide (roughly) the same functionality, then drop
    # use of responses here
    mock = responses.RequestsMock(assert_all_requests_are_fired=False)
    mock.add_passthru(re.compile(rf"{base}/zipball/\w+"))
    mock.add_passthru(re.compile(r"https://codeload.github.com/\w+"))

    for v in "2.1", "3.0", "3.0.0":
        mock.get(
            url=f"{base}/releases/tags/v{v}",
            json=dict(zipball_url=f"{base}/zipball/v{v}"),
        )

    yield mock


@pytest.fixture(scope="session")
def session_with_pytest_cache(pytestconfig):
    """Fixture:  A :class:`.Session` that caches within :file:`.pytest_cache`.

    This subdirectory is ephemeral, and tests **must** pass whether or not it exists and
    is populated.
    """
    p = pytestconfig.cache.mkdir("sdmx-requests-cache")
    yield Session(cache_name=str(p), backend="filesystem")


@pytest.fixture(scope="session")
def session_with_stored_responses(pytestconfig):
    """Fixture: A :class:`.Session` returns only stored responses from sdmx-test-data.

    This session…

    1. uses the 'memory' :mod:`requests_cache` backend;
    2. contains the responses from :func:`.testing.data.add_responses`; and
    3. is treated with :func:`.offline`, so that *only* stored responses can be
       returned.
    """
    session = Session(backend="memory")

    data.add_responses(
        session,
        pytestconfig.stash[KEY_DATA].joinpath("recorded"),
        pytestconfig.stash[KEY_SOURCE],
    )

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
    from sdmx.source import sources

    s = pytestconfig.stash[KEY_SOURCE]

    sources[s.id] = s

    try:
        yield s.id
    finally:
        sources.pop(s.id)
