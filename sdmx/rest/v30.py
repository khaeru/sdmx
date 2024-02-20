"""SDMX-REST API v2.1.0.

Note that version 2.1.0 of the REST API corresponds to version 3.0.0 of the overall
SDMX standards. See the `documentation
<https://github.com/sdmx-twg/sdmx-rest/tree/v2.1.0/doc>`__ and `OpenAPI specification
<https://github.com/sdmx-twg/sdmx-rest/blob/v2.1.0/api/sdmx-rest.yaml>`__ for further
details.
"""
from collections import ChainMap
from typing import Dict

from . import common
from .common import PathParameter, QueryParameter, Resource

#: v2.1.0-specific path and query parameters.
PARAM: Dict[str, common.Parameter] = {
    # Path parameters
    "component_id": PathParameter("component_id"),
    "context": PathParameter(
        "context", common.NAMES["context"] | {"metadataprovisionagreement"}
    ),
    "context_d": PathParameter(
        "context", {"datastructure", "dataflow", "provisionagreement", "*"}, "*"
    ),
    "provider_id": PathParameter("provider_id"),
    "version": PathParameter("version", set(), "+"),
    #
    # Query parameters
    "attributes": QueryParameter("attributes"),
    "c": QueryParameter("c"),
    "detail_m": QueryParameter("detail", {"allstubs", "full"}),
    "detail_s": QueryParameter("detail", common.NAMES["detail_s"] | {"raw"}),
    "measures": QueryParameter("measures"),
    "references_s": QueryParameter(
        "references", common.NAMES["references_s"] | {"ancestors"} | set(Resource)
    ),
    "updated_after": QueryParameter("update_after"),
    "updated_before": QueryParameter("update_before"),
}


class URL(common.URL):
    """Utility class to build SDMX-REST API v2.1.0 URLs."""

    _all_parameters = ChainMap(common.PARAM, PARAM)

    def handle_availability(self):
        """Handle URL parameters for availability endpoints."""
        self._params.setdefault("agency_id", self.source.id)
        self.handle_path_params(
            "availability/{context_d}/{agency_id}/{resource_id}/{version}/{key}/"
            "{component_id}"
        )
        self.handle_query_params("c mode references_a updated_after")

    def handle_data(self):
        """Handle URL parameters for data endpoints."""
        self._params.setdefault("agency_id", self.source.id)
        self.handle_path_params(
            self.rt + "/{context_d}/{agency_id}/{resource_id}/{version}/{key}"
        )
        self.handle_query_params(
            "c updated_after first_n_observations last_n_observations "
            "dimension_at_observation attributes measures include_history"
        )

    def handle_metadata(self):
        """Handle URL parameters for metadata endpoints."""
        self._path.update({"metadata": None})
        if self.resource_type == common.Resource.metadataflow:
            self.handle_path_params(
                "metadataflow/{agency_id}/{resource_id}/{version}/{provider_id}"
            )
        elif self.resource_type == common.Resource.metadata:
            self.handle_path_params("metadataset/{provider_id}/{resource_id}/{version}")
        else:
            self.handle_path_params(self.rt + "/{agency_id}/{resource_id}/{version}")
        self.handle_query_params("detail_s")

    def handle_registration(self):
        """Handle URL parameters for registration endpoints."""
        self.handle_path_params("registration")
        if "context" in self._params:
            self.handle_path_params("{context_d}/{agency_id}/{resource_id}/{version}")
            self.handle_query_params("updated_after updated_before")
        elif "agency_id" in self._params:
            self.handle_path_params("provider/{agency_id}/{provider_id}")
            self.handle_query_params("updated_after updated_before")
        else:
            self.handle_path_params("id/{resource_id}")  # "registrationID" in the spec
            # No query parameters

    def handle_structure(self):
        """Handle URL parameters for structure endpoints."""
        self.handle_path_params(f"structure/{self.rt}")
        super().handle_structure()
