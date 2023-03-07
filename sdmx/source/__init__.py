import json
from enum import Enum
from importlib import import_module
from io import IOBase, TextIOWrapper
from typing import Any, Dict, Optional, Tuple, Union

from pkg_resources import resource_stream
from requests import Response

from sdmx.model import DataStructureDefinition
from sdmx.rest import Resource
from sdmx.util import BaseModel, validator

sources: Dict[str, "Source"] = {}

DataContentType = Enum("DataContentType", "XML JSON")


class Source(BaseModel):
    """SDMX-IM RESTDatasource.

    This class describes the location and features supported by an SDMX data source.
    Subclasses may override the hooks in order to handle specific features of different
    REST web services:

    .. autosummary::
       handle_response
       finish_message
       modify_request_args

    """

    #: ID of the data source
    id: str

    #: Base URL for queries
    url: str

    #: Human-readable name of the data source
    name: str

    headers: Dict[str, Any] = {}

    #: :class:`.DataContentType` indicating the type of data returned by the source.
    data_content_type: DataContentType = DataContentType.XML

    #: Mapping from :class:`.Resource` values to :class:`bool` indicating support for
    #: SDMX-REST endpoints and features. Most of these values indicate endpoints that
    #: are described in the standards but are not implemented by any source currently in
    #: :file:`sources.json`; these all return 404.
    #:
    #: Two additional keys are valid:
    #:
    #: - ``'preview'=True`` if the source supports ``?detail=serieskeysonly``.
    #:   See :meth:`.preview_data`.
    #: - ``'structure-specific data'=True`` if the source can return structure-
    #:   specific data messages.
    supports: Dict[Union[str, Resource], bool] = {
        Resource.data: True,
        Resource.attachementconstraint: False,
        Resource.customtypescheme: False,
        Resource.metadata: False,
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

    @classmethod
    def from_dict(cls, info):
        return cls(**info)

    def __init__(self, **kwargs):
        # Merge supports values with defaults
        supports = kwargs.pop("supports", dict())

        super().__init__(**kwargs)

        self.supports.update(supports)

        # Set default supported features
        for feature in list(Resource) + ["preview", "structure-specific data"]:
            self.supports.setdefault(
                feature, self.data_content_type == DataContentType.XML
            )

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
                    "application/vnd.sdmx.structurespecificdata+xml;" "version=2.1",
                )

    @validator("id")
    def _validate_id(cls, value):
        assert getattr(cls, "_id", value) == value
        return value

    @validator("data_content_type", pre=True)
    def _validate_dct(cls, value):
        if isinstance(value, DataContentType):
            return value
        else:
            return DataContentType[value]


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
        SourceClass = getattr(mod, "Source")

    sources[id] = SourceClass.from_dict(_info)


def list_sources():
    """Return a sorted list of valid source IDs.

    These can be used to create :class:`Client` instances.
    """
    return sorted(sources.keys())


def load_package_sources():
    """Discover all sources listed in :file:`sources.json`."""
    with resource_stream("sdmx", "sources.json") as f:
        # TextIOWrapper is for Python 3.5 compatibility
        for info in json.load(TextIOWrapper(f)):
            add_source(info)


load_package_sources()
