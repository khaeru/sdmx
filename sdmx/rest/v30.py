"""SDMX-REST API v2.1.0.

Note that version 2.1.0 of the REST API corresponds to version 3.0.0 of the overall
SDMX standards. See the
`documentation <https://github.com/sdmx-twg/sdmx-rest/tree/v2.1.0/doc>`_ for further
details.
"""
from collections import ChainMap
from typing import Dict

from . import common
from .common import PathParameter, QueryParameter

#: v2.1.0 specific parameters
PARAM: Dict[str, common.Parameter] = {
    # Path parameters
    "context": PathParameter(
        "context", common.NAMES["context"] | {"metadataprovisionagreement"}
    ),
    "context_d": PathParameter(
        "context", {"datastructure", "dataflow", "provisionagreement", "*"}, "*"
    ),
    "version": PathParameter("version", set(), "+"),
    #
    # Query parameters
    "attributes": QueryParameter("attributes"),
    "c": QueryParameter("c"),
    "detail_s": QueryParameter("detail", common.NAMES["detail_s"] | {"raw"}),
    "measures": QueryParameter("measures"),
    "references_s": QueryParameter(
        "references", common.NAMES["references_s"] | {"ancestors"}
    ),
}


class URL(common.URL):
    """Utility class to build SDMX 3.0 REST web service URLs."""

    _all_parameters = ChainMap(common.PARAM, PARAM)

    def handle_availability(self):
        """Not implemented."""
        raise NotImplementedError

    def handle_data(self):
        self._params.setdefault("agency_id", self.source.id)
        self._path.update({self.resource_type.name: None})
        self.handle_path_params("context_d/agency_id/resource_id/version/key")
        self.handle_query_params(
            "c updated_after first_n_observations last_n_observations "
            "dimension_at_observation attributes measures include_history"
        )

    def handle_metadata(self):
        """Not implemented."""
        raise NotImplementedError

    def handle_registration(self):
        """Not implemented."""
        raise NotImplementedError

    def handle_schema(self):
        super().handle_schema()
        self.handle_query_params("dimension_at_observation")

    def handle_structure(self):
        self._path.update({"structure": None, self.resource_type.name: None})
        super().handle_structure()
