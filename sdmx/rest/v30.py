"""SDMX-REST API v2.0.0.

`Documentation <https://github.com/sdmx-twg/sdmx-rest/tree/v2.1.0/doc>`_.
"""
from . import common
from .common import PathParameter, QueryParameter, QueryType

PARAM = {
    # Common path parameters
    "agency_id": common.PARAM["agency_id"],
    "resource_id": common.PARAM["resource_id"],
    # Common query parameters
    ("c", QueryType.data): QueryParameter("c"),  # TODO complete
    ("updated_after", QueryType.data): common.PARAM["updated_after"],
    ("first_n_observations", QueryType.data): common.PARAM["first_n_observations"],
    ("last_n_observations", QueryType.data): common.PARAM["last_n_observations"],
    ("dimension_at_observation", QueryType.data): common.PARAM[
        "dimension_at_observation"
    ],
    ("attributes", QueryType.data): QueryParameter("attributes"),  # TODO complete
    ("measures", QueryType.data): QueryParameter("measures"),  # TODO complete
    ("include_history", QueryType.data): common.PARAM["include_history"],
    ("dimension_at_observation", QueryType.schema): common.PARAM[
        "dimension_at_observation"
    ],
    #
    # v3.0 specific path parameters
    "context": PathParameter(
        "context",
        {
            "dataflow",
            "datastructure",
            "metadataflow",
            "metadataprovisionagreement",
            "metadatastructure",
            "provisionagreement",
        },
    ),
    "version": PathParameter("version", set(), "+"),
    #
    # v3.0 specific query parameters
    ("detail", QueryType.data): QueryParameter("detail"),  # TODO complete
    ("detail", QueryType.structure): QueryParameter("detail"),  # TODO complete
    ("references", QueryType.structure): QueryParameter("references"),  # TODO complete
}


class URL(common.URL):
    """Utility class to build SDMX 3.0 REST web service URLs."""

    _all_parameters = PARAM

    def handle_data(self) -> None:
        super().handle_data()
        self.handle_query_params(
            "c updated_after first_n_observations last_n_observations "
            "dimension_at_observation attributes measures include_history"
        )

    def handle_schema(self) -> None:
        super().handle_schema()
        self.handle_query_params("dimension_at_observation")

    def handle_structure(self) -> None:
        self._path.update({"structure": None, self.resource_type.name: None})
        self.handle_path_params("agency_id/resource_id/version")
        self.handle_query_params("detail references")
