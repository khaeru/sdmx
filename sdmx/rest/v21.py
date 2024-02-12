"""SDMX-REST API v1.5.0.

`Documentation <https://github.com/sdmx-twg/sdmx-rest/tree/v1.5.0/v2_1/ws/rest/docs>`_.
"""
from collections import ChainMap
from typing import Dict
from warnings import warn

from . import common
from .common import OptionalPath, PathParameter, QueryParameter

#: v1.5.0 specific parameters
PARAM: Dict[str, common.Parameter] = {
    # Path parameters
    # NB the text and YAML OpenAPI specification disagree on whether this is required
    "component_id": OptionalPath("component_id"),
    "context": PathParameter("context", common.NAMES["context"]),
    "flow": OptionalPath("resource_id"),
    "provider": OptionalPath("provider"),
    "version": PathParameter("version", set(), "latest"),
    #
    # Query parameters
    "detail_d": QueryParameter(
        "detail", {"dataonly", "full", "nodata", "serieskeysonly"}
    ),
    "detail_s": QueryParameter("detail", common.NAMES["detail_s"]),
    # TODO handle allowable values like "codelist"
    "references_s": QueryParameter("references", common.NAMES["references_s"]),
    "start_period": QueryParameter("start_period"),
    "end_period": QueryParameter("end_period"),
    "explicit_measure": QueryParameter("explicit_measure", {True, False}),
}


class URL(common.URL):
    """Utility class to build SDMX 2.1 REST web service URLs.

    See also
    --------
    https://github.com/sdmx-twg/sdmx-rest/blob/v1.5.0/v2_1/ws/rest/src/sdmx-rest.yaml
    """

    _all_parameters = ChainMap(common.PARAM, PARAM)

    def handle_availability(self):
        self._path.update({self.resource_type.name: None})
        self.handle_path_params("flow/key/provider/component_id")
        self.handle_query_params(
            "start_period end_period updated_after references_a mode"
        )

    def handle_data(self):
        if self._params.pop("agency_id", None):
            warn("'agency_id' argument is redundant for data queries", UserWarning, 2)

        self._path.update({self.resource_type.name: None})
        self.handle_path_params("flow/key/provider")
        self.handle_query_params(
            "start_period end_period updated_after first_n_observations "
            "last_n_observations dimension_at_observation detail_d include_history"
        )

    def handle_metadata(self):
        raise NotImplementedError

    def handle_schema(self):
        super().handle_schema()
        self.handle_query_params("dimension_at_observation explicit_measure")

    def handle_structure(self):
        self._path.update({self.resource_type.name: None})
        super().handle_structure()
