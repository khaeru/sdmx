"""SDMX-REST API v1.5.0.

`Documentation <https://github.com/sdmx-twg/sdmx-rest/tree/v1.5.0/v2_1/ws/rest/docs>`_.
"""
from warnings import warn

from . import common
from .common import PathParameter, QueryParameter, QueryType

PARAM = {
    # Common path parameters
    "agency_id": common.PARAM["agency_id"],
    "resource_id": common.PARAM["resource_id"],
    # Common query parameters
    ("start_period", QueryType.availability): common.PARAM["start_period"],
    ("end_period", QueryType.availability): common.PARAM["end_period"],
    ("updated_after", QueryType.availability): common.PARAM["updated_after"],
    ("mode", QueryType.availability): common.PARAM["mode"],
    ("start_period", QueryType.data): common.PARAM["start_period"],
    ("end_period", QueryType.data): common.PARAM["end_period"],
    ("updated_after", QueryType.data): common.PARAM["updated_after"],
    ("first_n_observations", QueryType.data): common.PARAM["first_n_observations"],
    ("last_n_observations", QueryType.data): common.PARAM["last_n_observations"],
    ("dimension_at_observation", QueryType.data): common.PARAM[
        "dimension_at_observation"
    ],
    ("include_history", QueryType.data): common.PARAM["include_history"],
    ("dimension_at_observation", QueryType.schema): common.PARAM[
        "dimension_at_observation"
    ],
    ("explicit_measure", QueryType.schema): common.PARAM["explicit_measure"],
    #
    # v2.1 specific path parameters
    "context": PathParameter(
        "context",
        {
            "dataflow",
            "datastructure",
            "metadataflow",
            "metadatastructure",
            "provisionagreement",
        },
    ),
    "version": PathParameter("version", set(), "latest"),
    #
    # v2.1 specific query parameters
    ("detail", QueryType.data): QueryParameter(
        "detail",
        {
            "dataonly",
            "full",
            "nodata",
            "serieskeysonly",
        },
    ),
    ("detail", QueryType.structure): QueryParameter(
        "detail",
        {
            "allcompletestubs",
            "allstubs",
            "full",
            "referencecompletestubs",
            "referencepartial",
            "referencestubs",
        },
    ),
    ("references", QueryType.structure): QueryParameter(
        "references",  # TODO handle allowable values like "codelist"
        {
            "all",
            "children",
            "descendants",
            "none",
            "parents",
            "parentsandsibling",
        },
    ),
    ("references", QueryType.availability): QueryParameter(
        "references",
        {
            "all",
            "codelist",
            "conceptscheme",
            "dataflow",
            "dataproviderscheme",
            "datastructure",
            "none",
        },
    ),
}


class URL(common.URL):
    """Utility class to build SDMX 2.1 REST web service URLs.

    See also
    --------
    https://github.com/sdmx-twg/sdmx-rest/blob/v1.5.0/v2_1/ws/rest/src/sdmx-rest.yaml
    """

    _all_parameters = PARAM

    def handle_availability(self) -> None:
        self._path.update({self.resource_type.name: None})

        self._path["flow_ref"] = self._params.pop("resource_id")

        if "key" in self._params:
            self._path["key"] = self._params.pop("key")

        # TODO handle providerRef
        # TODO handle componentID
        self.handle_query_params(
            "start_period end_period updated_after references mode"
        )

    def handle_data(self) -> None:
        if self._params.pop("agency_id", None):
            warn("'agency_id' argument is redundant for data queries", UserWarning, 2)

        super().handle_data()

        self.handle_query_params(
            "start_period end_period updated_after first_n_observations "
            "last_n_observations dimension_at_observation detail include_history"
        )

    def handle_schema(self) -> None:
        super().handle_schema()
        self.handle_query_params("dimension_at_observation explicit_measure")

    def handle_structure(self) -> None:
        self._path.update({self.resource_type.name: None})
        self.handle_path_params("agency_id/resource_id/version")
        self.handle_query_params("detail references")
