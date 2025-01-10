"""Code for working with :file:`sdmx-test-data`."""

import logging
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Optional

import platformdirs
import pytest

if TYPE_CHECKING:
    from requests_cache import CachedSession

    from sdmx.source import Source

log = logging.getLogger(__name__)

#: Default directory for local copy of sdmx-test-data.
DEFAULT_DIR = platformdirs.user_cache_path("sdmx").joinpath("test-data")

#: Expected to_pandas() results for data files; see :meth:`SpecimenCollection.expected_data`
#:
#: - Keys are the file name (see :func:`.add_specimens`) with '.' -> '-': 'foo.xml' ->
#:   'foo-xml'.
#: - Data is stored in :file:`sdmx-test-data/expected/{KEY}.txt`.
#: - Values are either argument to :func:`pandas.read_csv`; or a dict(use='other-key'),
#:   in which case the info for other-key is used instead.
EXPECTED = {
    "ng-flat-xml": dict(index_col=[0, 1, 2, 3, 4, 5]),
    "ng-ts-gf-xml": dict(use="ng-flat-xml"),
    "ng-ts-xml": dict(use="ng-flat-xml"),
    "ng-xs-xml": dict(index_col=[0, 1, 2, 3, 4, 5]),
    # Excluded: this file contains two DataSets, and
    # :meth:`SpecimenCollection.expected_data` currently only supports specimens with
    # one DataSet.
    # 'action-delete-json': dict(header=[0, 1, 2, 3, 4]),
    "xs-json": dict(index_col=[0, 1, 2, 3, 4, 5]),
    "flat-json": dict(index_col=[0, 1, 2, 3, 4, 5]),
    "ts-json": dict(use="flat-json"),
}

ERROR = (
    "Unable to locate test specimens. Give --sdmx-fetch-data, or use --sdmx-test-data=…"
    "or the SDMX_TEST_DATA environment variable to indicate an existing directory"
)

#: Git remote URL for cloning test data.
REMOTE_URL = "https://github.com/khaeru/sdmx-test-data.git"
# REMOTE_URL = "git@github.com:khaeru/sdmx-test-data.git"


class SpecimenCollection:
    """Collection of test specimens.

    Parameters
    ----------
    path :
       Path containing :file:`sdmx-test-data`, or to which to clone the repository.
    fetch :
       If :any:`True`, call :meth:`fetch`
    """

    #: Base path containing the specimen collection.
    base_path: Path

    #: Each tuple contains:
    #:
    #: 1. Path to specimen file.
    #: 2. Format: one of "csv", "json", "xml".
    #: 3. Message type: either "data", "structure", or None.
    specimens: list[tuple[Path, str, Optional[str]]]

    def __init__(self, path: Path, fetch: bool):
        self.base_path = path

        if fetch:
            self.fetch()

        # Check the base directory exists
        if not self.base_path.exists():  # pragma: no cover
            # Cannot proceed further; this exception kills the test session
            raise FileNotFoundError(f"SDMX test data in {path}\n{ERROR}")

        self.specimens = []
        add_specimens(self.specimens, self.base_path)

    @contextmanager
    def __call__(self, pattern="", opened: bool = True):
        """Open the test specimen file with `pattern` in the name.

        With :py:`opened=True` (default), return a file-like object. With
        :py:`opened=False`, return only the full path to the specimen file.
        """
        for path, f, k in self.specimens:
            if path.match("*" + pattern + "*"):
                yield open(path, "br") if opened else path
                return
        raise ValueError(pattern)  # pragma: no cover

    def as_params(
        self,
        format: Optional[str] = None,
        kind: Optional[str] = None,
        marks: Optional[dict] = None,
    ):
        """Generate :func:`pytest.param` from specimens.

        One :func:`~.pytest.param` is generated for each specimen that matches the
        `format` and `kind` arguments (if any). Marks are attached to each param from
        `marks`, wherein the keys are partial paths.
        """
        # Transform `marks` into a platform-independent mapping from path parts
        _marks = {PurePosixPath(k).parts: v for k, v in (marks or {}).items()}

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
        """Return the expected :func:`.to_pandas` result for the specimen `path`.

        Data is retrieved from :data:`.EXPECTED`.
        """
        import pandas as pd

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

    def fetch(self) -> None:
        """Fetch test data from GitHub."""
        import git

        # Create a lock to avoid concurrency issues when running with pytest-xdist
        self.base_path.mkdir(parents=True, exist_ok=True)
        blf = git.BlockingLockFile(self.base_path, check_interval_s=0.1)
        blf._obtain_lock()

        # Initialize a git Repo object
        repo = git.Repo.init(self.base_path)

        try:
            # Reference to existing 'origin' remote
            origin = repo.remotes["origin"]
            # Ensure the REMOTE_URL is among the URLs for this remote
            if REMOTE_URL not in origin.urls:  # pragma: no cover
                origin.set_url(REMOTE_URL)
        except IndexError:
            # Create a new remote
            origin = repo.create_remote("origin", REMOTE_URL)

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

    def parametrize(self, metafunc) -> None:
        """Handle the ``parametrize_specimens`` mark for a specific test."""
        try:
            mark = next(metafunc.definition.iter_markers("parametrize_specimens"))
        except StopIteration:
            return

        metafunc.parametrize(mark.args[0], self.as_params(**mark.kwargs))


def add_responses(
    session: "CachedSession", file_cache_path: Path, source: "Source"
) -> None:
    """Populate cached responses for `session`.

    Two sources are used:

    1. Responses stored in :file:`sdmx-test-data/responses/`, as indicated by
       `file_cache_path`.
    2. For the ``TEST`` source as indicated by `source`, responses generated by this
       function. These are not stored in sdmx-test-data.
    """

    from requests_cache import FileCache

    import sdmx
    from sdmx.format import MediaType
    from sdmx.message import StructureMessage
    from sdmx.util.requests import save_response

    # Access the file cache in the given directory
    fc = FileCache(file_cache_path)

    # Add to `session` cache
    session.cache.update(fc)
    session.cache.recreate_keys()

    content: bytes = sdmx.to_xml(StructureMessage())
    headers = {"Content-Type": repr(MediaType("generic", "xml", "2.1"))}

    for endpoint in (
        "actualconstraint",
        "agencyscheme",
        "allowedconstraint",
        "attachementconstraint",
        "availableconstraint",
        "categorisation",
        "categoryscheme",
        "codelist",
        "conceptscheme",
        "contentconstraint",
        "customtypescheme",
        "dataconsumerscheme",
        "dataflow",
        "dataproviderscheme",
        "datastructure",
        "hierarchicalcodelist",
        "metadataflow",
        "metadatastructure",
        "namepersonalisationscheme",
        "organisationscheme",
        "organisationunitscheme",
        "process",
        "provisionagreement",
        "reportingtaxonomy",
        "rulesetscheme",
        "schema/datastructure",
        "structure",
        "structureset",
        "transformationscheme",
        "userdefinedoperatorscheme",
        "vtlmappingscheme",
    ):
        url = f"{source.url}/{endpoint}/{source.id}/all/latest"
        save_response(session, method="GET", url=url, content=content, headers=headers)

    for url in (
        f"{source.url}/availableconstraint",
        f"{source.url}/categoryscheme/{source.id}/all/latest?references=parentsandsiblings",
    ):
        save_response(session, method="GET", url=url, content=content, headers=headers)


def add_specimens(target: list[tuple[Path, str, Optional[str]]], base: Path) -> None:
    """Populate the `target` collection with specimens from :file:`sdmx-test-data`."""
    # XML data files for the ECB exchange rate data flow
    for source_id in ("ECB_EXR",):
        for path in base.joinpath(source_id).rglob("*.xml"):
            kind = "data"
            if "structure" in path.name or "common" in path.name:
                kind = "structure"
            target.append((path, "xml", kind))

    # JSON data files for ECB and OECD data flows
    for source_id in ("ECB_EXR", "OECD"):
        target.extend(
            (fp, "json", "data") for fp in base.joinpath(source_id).rglob("*.json")
        )

    # Miscellaneous XML data files
    target.extend(
        (base.joinpath(*parts), "xml", "data")
        for parts in [
            ("constructed", "gh-218.xml"),
            ("INSEE", "CNA-2010-CONSO-SI-A17.xml"),
            ("INSEE", "IPI-2010-A21.xml"),
            ("IMF", "PCPS.xml"),
            ("ESTAT", "esms.xml"),
            ("ESTAT", "footer.xml"),
            ("ESTAT", "NAMA_10_GDP-ss.xml"),
        ]
    )

    # Miscellaneous XML structure files
    target.extend(
        (base.joinpath(*parts), "xml", "structure")
        for parts in [
            ("BIS", "actualconstraint-0.xml"),
            ("BIS", "hierarchicalcodelist-0.xml"),
            ("BIS", "gh-180.xml"),
            ("ECB", "orgscheme.xml"),
            ("ECB", "structureset-0.xml"),
            ("ESTAT", "apro_mk_cola-structure.xml"),
            ("ESTAT", "esms-structure.xml"),
            ("ESTAT", "GOV_10Q_GGNFA.xml"),
            ("ESTAT", "HCL_WSTATUS_SCL_BNSPART.xml"),
            ("ESTAT", "HCL_WSTATUS_SCL_WSTATUSPR.xml"),
            ("IAEG-SDGs", "metadatastructure-0.xml"),
            ("IMF", "01R.xml"),
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

    # Files from the SDMX 2.1 specification
    v21 = base.joinpath("v21", "xml")
    target.extend((p, "xml", None) for p in v21.glob("**/*.xml"))

    # Files from the SDMX 3.0 specification
    v3 = base.joinpath("v3")

    # Files from the SDMX-CSV 2.0.0 specification
    target.extend((p, "csv", "data") for p in v3.joinpath("csv").glob("*.csv"))

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
    target.extend((p, "xml", None) for p in v3.glob("xml/*.xml"))
