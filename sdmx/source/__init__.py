import importlib.resources
import json
from dataclasses import dataclass, field
from enum import Enum
from importlib import import_module
from io import IOBase
from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Tuple, Type, Union

from requests import Response

from sdmx.format import Version
from sdmx.model.v21 import DataStructureDefinition
from sdmx.rest import Resource

if TYPE_CHECKING:
    import sdmx.rest.common

#: Data sources registered with :mod:`sdmx`.
sources: Dict[str, "Source"] = {}

#: Valid data content types for SDMX REST API messages.
DataContentType = Enum("DataContentType", "CSV JSON XML")

#: Default values for :attr:`.Source.supports`. Most of these values indicate REST API
#: endpoints that are described in the standards but are not implemented by any source
#: currently in :file:`sources.json`; these all return 404.
SDMX_ML_SUPPORTS = {
    Resource.availableconstraint: False,
    Resource.attachementconstraint: False,
    Resource.customtypescheme: False,
    Resource.data: True,
    Resource.metadata: True,
    Resource.namepersonalisationscheme: False,
    Resource.organisationunitscheme: False,
    Resource.process: False,
    Resource.reportingtaxonomy: False,
    Resource.rulesetscheme: False,
    Resource.schema: False,
    Resource.transformationscheme: False,
    Resource.userdefinedoperatorscheme: False,
    Resource.vtlmappingscheme: False,
}


@dataclass
class Source:
    """SDMX-IM RESTDatasource.

    This class describes the location and features supported by an SDMX REST API data
    source/web service.

    It also provides three hooks, with default implementations. Subclasses may override
    the hooks in order to handle specific features of different REST web services:

    .. autosummary::
       handle_response
       finish_message
       modify_request_args
    """

    #: :attr:`~.IdentifiableArtefact.id` of the :attr:`DataProvider`.
    id: str

    #: Base URL (API entry point) for queries.
    url: str

    #: Human-readable name of the data source.
    name: str

    #: Additional HTTP headers to supply by default with all requests.
    headers: Dict[str, Any] = field(default_factory=dict)

    #: :class:`.DataContentType` indicating the type of data returned by the source.
    data_content_type: DataContentType = DataContentType.XML

    #: SDMX REST API version(s) supported. Default: :class:`.Version["2.1"] <.Version>`
    #: only.
    versions: Set[Version] = field(default_factory=lambda: {Version["2.1"]})

    #: Mapping from :class:`.Resource` values to :class:`bool` indicating support for
    #: SDMX-REST endpoints and features. If not supplied, the defaults from
    #: :data:`SDMX_ML_SUPPORTS` are used.
    #:
    #: Two additional keys are valid:
    #:
    #: - ``"preview"=True`` if the source supports ``?detail=serieskeysonly``.
    #:   See :meth:`.preview_data`.
    #: - ``"structure-specific data"=True`` if the source can return structure-
    #:   specific data messages.
    supports: Dict[Union[str, Resource], bool] = field(default_factory=dict)

    def __post_init__(self):
        # Sanity check: _id attribute of a subclass matches the loaded ID.
        assert getattr(self, "_id", self.id) == self.id

        # Convert an e.g. string to a DataContentType member
        if not isinstance(self.data_content_type, DataContentType):
            self.data_content_type = DataContentType[self.data_content_type]

        # Convert str to a Version member
        self.versions = set(
            map(lambda v: v if isinstance(v, Version) else Version[v], self.versions)
        )

        # Default feature support: True for sdmx_ml, False otherwise
        sdmx_ml = self.data_content_type is DataContentType.XML

        # Update mapping of supported features
        for feature in list(Resource) + ["preview", "structure-specific data"]:
            # String name of a Resource enumeration member
            f_name = getattr(feature, "value", feature)

            # In order of precedence:
            # 1. The value already in `supports`.
            # 2. A value loaded from sources.json, appearing with a string key `f_name`
            #    in `supports`.
            # 3. The value in `SDMX_ML_SUPPORTS`, if any.
            # 4. The value `sdmx_ml`.
            self.supports.setdefault(
                feature,
                self.supports.pop(f_name, SDMX_ML_SUPPORTS.get(feature, sdmx_ml)),
            )

    def get_url_class(self) -> Type["sdmx.rest.common.URL"]:
        """Return a class for constructing URLs for this Source.

        - If :attr:`.versions` includes *only* SDMX 3.0.0, return :class:`.v30.URL`.
        - If :attr:`.versions` includes SDMX 2.1, return :class:`.v21.URL`.
        - Raise an exception for other :attr:`.versions` that are not supported.
        """
        if {Version["3.0.0"]} == self.versions:
            import sdmx.rest.v30

            return sdmx.rest.v30.URL
        elif Version["2.1"] in self.versions:
            import sdmx.rest.v21

            return sdmx.rest.v21.URL
        else:  # pragma: no cover
            raise NotImplementedError(f"Query against {self.versions}")

    # Hooks
    def handle_response(
        self, response: Response, content: IOBase
    ) -> Tuple[Response, IOBase]:
        """Handle response content of unknown type.

        This hook is called by :meth:`.Client.get` *only* when the `content` cannot be
        parsed as XML or JSON.

        See :meth:`.estat.Source.handle_response` and
        :meth:`.sgr.Source.handle_response` for example implementations.
        """
        return response, content

    def finish_message(self, message, request, **kwargs):
        """Postprocess retrieved message.

        This hook is called by :meth:`.Client.get` after a :class:`.Message` object has
        been successfully parsed from the query response.

        See :meth:`.estat.Source.finish_message` for an example implementation.
        """
        return message

    def modify_request_args(self, kwargs):
        """Modify arguments used to build query URL.

        This hook is called by :meth:`.Client.get` to modify the keyword arguments
        before the query URL is built.

        The default implementation handles requests for 'structure-specific data' by
        adding an HTTP 'Accepts:' header when a 'dsd' is supplied as one of the
        `kwargs`.

        See :meth:`.sgr.Source.modify_request_args` for an example override.

        Returns
        -------
        None
        """
        if self.data_content_type is DataContentType.XML:
            dsd = kwargs.get("dsd", None)
            if isinstance(dsd, DataStructureDefinition):
                kwargs.setdefault("headers", {})
                kwargs["headers"].setdefault(
                    "Accept",
                    "application/vnd.sdmx.structurespecificdata+xml;version=2.1",
                )


@dataclass
class _NoSource(Source):
    pass


NoSource = _NoSource(id="", url="", name="")


def add_source(
    info: Union[Dict, str], id: Optional[str] = None, override: bool = False, **kwargs
) -> None:
    """Add a new data source.

    The *info* expected is in JSON format:

    .. code-block:: json

        {
          "id": "ESTAT",
          "documentation": "http://data.un.org/Host.aspx?Content=API",
          "url": "http://ec.europa.eu/eurostat/SDMX/diss-web/rest",
          "name": "Eurostat",
          "supports": {"codelist": false, "preview": true}
        }

    …with unspecified values using the defaults; see :class:`Source`.

    Parameters
    ----------
    info : dict-like
        String containing JSON information about a data source.
    id : str
        Identifier for the new datasource. If :obj:`None` (default), then `info['id']`
        is used.
    override : bool
        If :obj:`True`, replace any existing data source with *id*. Otherwise, raise
        :class:`ValueError`.
    **kwargs
        Optional callbacks for *handle_response* and *finish_message* hooks.

    """
    _info = json.loads(info) if isinstance(info, str) else info
    id = id or _info["id"]

    _info.update(kwargs)

    if not override and id in sources:
        raise ValueError(f"Data source {repr(id)} already defined; use override=True")

    # Maybe import a subclass that defines a hook
    SourceClass = Source
    try:
        mod = import_module("." + id.lower(), "sdmx.source")
    except ImportError:
        pass
    else:
        SourceClass = getattr(mod, "Source", None) or SourceClass

    sources[id] = SourceClass(**_info)


def list_sources():
    """Return a sorted list of valid source IDs.

    These can be used to create :class:`Client` instances.
    """
    return sorted(sources.keys())


def load_package_sources():
    """Discover all sources listed in :file:`sources.json`."""
    try:
        ref = importlib.resources.files("sdmx").joinpath("sources.json")
    except AttributeError:  # Python <3.9
        from copy import copy

        with importlib.resources.path("sdmx", "sources.json") as path:
            ref = copy(path)

    with ref.open("rb") as f:
        for info in json.load(f):
            add_source(info)


load_package_sources()
