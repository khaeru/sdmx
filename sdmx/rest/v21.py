"""SDMX-REST API v1.5.0.

Note that version 1.5.0 of the REST API corresponds to version 2.1 of the overall SDMX
standards. See the `documentation
<https://github.com/sdmx-twg/sdmx-rest/tree/v1.5.0/v2_1/ws/rest/docs>`_ and `OpenAPI
specification
<https://github.com/sdmx-twg/sdmx-rest/blob/v1.5.0/v2_1/ws/rest/src/sdmx-rest.yaml>`_
for further details.
"""
from collections import ChainMap
from typing import Dict
from warnings import warn

from . import common
from .common import OptionalPath, PathParameter, QueryParameter, Resource

#: v1.5.0-specific path and query parameters.
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
    "references_s": QueryParameter(
        "references", common.NAMES["references_s"] | set(Resource)
    ),
    "start_period": QueryParameter("start_period"),
    "end_period": QueryParameter("end_period"),
    "explicit_measure": QueryParameter("explicit_measure", {True, False}),
}


class URL(common.URL):
    """Utility class to build SDMX-REST API v1.5.0 URLs."""

    _all_parameters = ChainMap(common.PARAM, PARAM)

    def handle_availability(self):
        """Handle URL parameters for availability endpoints."""
        self.handle_path_params(self.rt + "/{flow}/{key}/{provider}/{component_id}")
        self.handle_query_params(
            "start_period end_period updated_after references_a mode"
        )

    def handle_data(self):
        """Handle URL parameters for data endpoints."""
        if self._params.pop("agency_id", None):
            warn("'agency_id' argument is redundant for data queries", UserWarning, 2)

        self.handle_path_params(self.rt + "/{flow}/{key}/{provider}")
        self.handle_query_params(
            "start_period end_period updated_after first_n_observations "
            "last_n_observations dimension_at_observation detail_d include_history"
        )

    def handle_metadata(self):
        """Handle URL parameters for metadata endpoints.

        Raises
        ------
        NotImplementedError
            Although it is described in the standards, there are no known SDMX REST data
            sources that support this API endpoint to confirm behaviour. If you are
            aware of one, please `open an issue
            <https://github.com/khaeru/sdmx/issues/new>`_.
        """
        raise NotImplementedError

    def handle_registration(self):
        """Handle URL parameters for registration endpoints.

        Raises
        ------
        ValueError
            Always. This type of query is not included in SDMX-REST v1.5.0.
        """
        raise ValueError(
            "/registration/… queries not supported in the SDMX-REST v1.5.0 API"
        )

    def handle_schema(self):
        """Handle URL parameters for schema endpoints."""
        super().handle_schema()
        self.handle_query_params("explicit_measure")

    def handle_structure(self):
        """Handle URL parameters for structure endpoints.

        .. warning::

           This method currently preserves the behaviour of :meth:`.Client.get` as of
           :mod:`sdmx` version 2.13.1 and earlier. Namely, defaults are supplied for the
           ``?references=…`` query parameter in the following cases:

           - :attr:`.Resource.dataflow` or :attr:`.Resource.datastructure` **and** a
             specific ``resource_id`` is given (that is, not "all") → default
             ``?references=all``.
           - :attr:`.Resource.categoryscheme` → default
             ``?references=parentsandsiblings``.

           These differ from the SDMX-REST v1.5.0 standard, which states the default
           should be ``none`` in all cases. The :mod:`sdmx`-specific defaults **may** be
           deprecated and removed in future versions; to ensure stable behaviour, give
           the parameter explicitly.
        """
        self.handle_path_params(self.rt)
        super().handle_structure()

        # Moved from Client._request_from_args()
        # TODO Consider deprecating and eventually removing these defaults
        if (
            self.resource_type in {Resource.dataflow, Resource.datastructure}
            and self._path["resource_id"] != "all"
        ):
            self.query.setdefault("references", "all")
        elif self.resource_type in {Resource.categoryscheme}:
            self.query.setdefault("references", "parentsandsiblings")
