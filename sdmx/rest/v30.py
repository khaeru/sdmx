"""SDMX-REST API v2.0.0.

`Documentation <https://github.com/sdmx-twg/sdmx-rest/tree/v2.1.0/doc>`_.
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
    "version": PathParameter("version", set(), "+"),
    #
    # Query parameters
    "attributes": QueryParameter("attributes"),  # TODO complete
    "c": QueryParameter("c"),  # TODO complete
    "detail_s": QueryParameter("detail", common.NAMES["detail_s"] | {"raw"}),
    "measures": QueryParameter("measures"),  # TODO complete
    "references_s": QueryParameter(
        "references", common.NAMES["references_s"] | {"ancestors"}
    ),
}


class URL(common.URL):
    """Utility class to build SDMX 3.0 REST web service URLs."""

    _all_parameters = ChainMap(common.PARAM, PARAM)

    def handle_availability(self):
        raise NotImplementedError

    def handle_data(self):
        super().handle_data()
        self.handle_query_params(
            "c updated_after first_n_observations last_n_observations "
            "dimension_at_observation attributes measures include_history"
        )

    def handle_metadata(self):
        raise NotImplementedError

    def handle_schema(self):
        super().handle_schema()
        self.handle_query_params("dimension_at_observation")

    def handle_structure(self):
        self._path.update({"structure": None, self.resource_type.name: None})
        super().handle_structure()
