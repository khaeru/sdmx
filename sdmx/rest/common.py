"""Information related to the SDMX-REST web service standard."""
import abc
import re
from copy import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

if TYPE_CHECKING:
    import sdmx.source

# Mapping from Resource value to class name.
CLASS_NAME = {
    "dataflow": "DataflowDefinition",
    "datastructure": "DataStructureDefinition",
}

# Inverse of :data:`CLASS_NAME`.
VALUE = {v: k for k, v in CLASS_NAME.items()}

#: Response codes defined by the SDMX-REST standard.
RESPONSE_CODE = {
    200: "OK",
    304: "No changes",
    400: "Bad syntax",
    401: "Unauthorized",
    403: "Semantic error",  # or "Forbidden"
    404: "Not found",
    406: "Not acceptable",
    413: "Request entity too large",
    414: "URI too long",
    500: "Internal server error",
    501: "Not implemented",
    503: "Unavailable",
}


class Resource(str, Enum):
    """Enumeration of SDMX-REST API resources.

    This class merges the "resources" defined in Section V of the SDMX 2.1 and 3.0
    standards; in the latter, only five values (availability, data, metadata, schema,
    structure) are used as the first part of a URL path; however, the choice of this
    first part and allowable query parameters depend on the more detailed list.

    ============================= ======================================================
    :class:`Enum` member          :mod:`sdmx.model` class
    ============================= ======================================================
    ``actualconstraint``          :class:`.ContentConstraint`
    ``agencyscheme``              :class:`.AgencyScheme`
    ``allowedconstraint``         :class:`.ContentConstraint`
    ``attachementconstraint``     :class:`.AttachmentConstraint`
    ``availableconstraint``       :class:`.ContentConstraint`
    ``categorisation``            :class:`.Categorisation`
    ``categoryscheme``            :class:`.CategoryScheme`
    ``codelist``                  :class:`.Codelist`
    ``conceptscheme``             :class:`.ConceptScheme`
    ``contentconstraint``         :class:`.ContentConstraint`
    ``customtypescheme``          :class:`.CustomTypeScheme`.
    ``data``                      :class:`.DataSet`
    ``dataflow``                  :class:`Dataflow(Definition) <.BaseDataflow>`
    ``dataconsumerscheme``        :class:`.DataConsumerScheme`
    ``dataproviderscheme``        :class:`.DataProviderScheme`
    ``datastructure``             :class:`DataStructureDefinition <.BaseDataStructureDefinition>`
    ``hierarchicalcodelist``      :class:`.v21.HierarchicalCodelist`.
    ``metadata``                  :class:`MetadataSet <.BaseMetadataSet>`.
    ``metadataflow``              :class:`Metadataflow(Definition) <.Metadataflow>`
    ``metadatastructure``         :class:`MetadataStructureDefinition <.BaseMetadataStructureDefinition>`
    ``namepersonalisationscheme`` :class:`.NamePersonalisationScheme`.
    ``organisationscheme``        :class:`.OrganisationScheme`
    ``provisionagreement``        :class:`.ProvisionAgreement`
    ``rulesetscheme``             :class:`.RulesetScheme`.
    ``structure``                 Mixed.
    ``structureset``              :class:`.StructureSet`.
    ``transformationscheme``      :class:`.TransformationScheme`.
    ``userdefinedoperatorscheme`` :class:`.UserdefinedoperatorScheme`.
    ``vtlmappingscheme``          :class:`.VTLMappingScheme`.
    ----------------------------- ------------------------------------------------------
    ``organisationunitscheme``    Not implemented.
    ``process``                   Not implemented.
    ``reportingtaxonomy``         Not implemented.
    ``schema``                    Not implemented.
    ============================= ======================================================

    """  # noqa: E501

    actualconstraint = "actualconstraint"
    agencyscheme = "agencyscheme"
    allowedconstraint = "allowedconstraint"
    attachementconstraint = "attachementconstraint"
    availableconstraint = "availableconstraint"
    categorisation = "categorisation"
    categoryscheme = "categoryscheme"
    codelist = "codelist"
    conceptscheme = "conceptscheme"
    contentconstraint = "contentconstraint"
    customtypescheme = "customtypescheme"
    data = "data"
    dataconsumerscheme = "dataconsumerscheme"
    dataflow = "dataflow"
    dataproviderscheme = "dataproviderscheme"
    datastructure = "datastructure"
    hierarchicalcodelist = "hierarchicalcodelist"
    metadata = "metadata"
    metadataflow = "metadataflow"
    metadatastructure = "metadatastructure"
    namepersonalisationscheme = "namepersonalisationscheme"
    organisationscheme = "organisationscheme"
    organisationunitscheme = "organisationunitscheme"
    process = "process"
    provisionagreement = "provisionagreement"
    registration = "registration"
    reportingtaxonomy = "reportingtaxonomy"
    rulesetscheme = "rulesetscheme"
    schema = "schema"
    structure = "structure"
    structureset = "structureset"
    transformationscheme = "transformationscheme"
    userdefinedoperatorscheme = "userdefinedoperatorscheme"
    vtlmappingscheme = "vtlmappingscheme"

    @classmethod
    def from_obj(cls, obj):
        """Return an enumeration value based on the class of `obj`."""
        value = obj.__class__.__name__
        return cls[VALUE.get(value, value)]

    @classmethod
    def class_name(cls, value: "Resource", default=None) -> str:
        """Return the name of a :mod:`sdmx.model` class from an enum value.

        Values are returned in lower case.
        """
        return CLASS_NAME.get(value.value, value.value)

    @classmethod
    def describe(cls):
        return "{" + " ".join(v.name for v in cls._member_map_.values()) + "}"


@dataclass
class Parameter(abc.ABC):
    """SDMX query parameter."""

    #: Keyword argument to :class:`.URL` understood by this parameter.
    name: str

    #: Allowable values.
    values: set = field(default_factory=set)

    #: Default value.
    default: Optional[str] = None

    @abc.abstractmethod
    def handle(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """Return a dict to update :attr:`.URL.path` or :attr:`.URL.query`."""


@dataclass
class PathParameter(Parameter):
    """SDMX query parameter appearing as a part of the path component of a URL."""

    def handle(self, parameters):
        """Return a length-1 dict to update :attr:`.URL.path`."""
        # Retrieve the value from `parameters`
        value = parameters.pop(self.name, None) or self.default

        # Check against allowable values
        if value is None:
            raise ValueError(f"Missing required parameter {self.name!r}")
        elif len(self.values) and value not in self.values:
            raise ValueError(f"{self.name}={value!r} not among {self.values}")

        # Return
        return {self.name: value}


@dataclass
class OptionalPath(Parameter):
    """Like :class:`.PathParameter`, but optional.

    If the corresponding keyword is missing
    """

    def handle(self, parameters):
        if value := parameters.pop(self.name, None):
            assert value in self.values or 0 == len(self.values)
            return {self.name: value}
        else:
            return {}


@dataclass
class QueryParameter(PathParameter):
    """SDMX query parameter appearing as part of the query string component of a URL.

    This version also responds to, for instance, :py:`fooBar="..."` when the
    :attr:`.name` is :py:`"foo_bar"`.
    """

    def __post_init__(self):
        # Convert self.name to lowerCamelCase as appearing in query strings
        self.camelName = re.sub(r"_([a-z])", lambda x: x.group(1).upper(), self.name)

    def handle(self, parameters):
        """Return a length-0 or -1 dict to update :attr:`.URL.query`."""
        if present := {self.name, self.camelName} & set(parameters):
            if 2 == len(present):
                raise ValueError(f"Cannot give both {self.name} and {self.camelName}")

            value = parameters.pop(present.pop())
            if value is None:
                return {}
            elif len(self.values) and value not in self.values:
                raise ValueError(f"{self.name}={value!r} not among {self.values}")

            return {self.camelName: value}
        else:
            return {}


@dataclass
class PositiveIntParam(QueryParameter):
    """A query parameter that must be a positive integer."""

    def handle(self, parameters):
        result = super().handle(parameters)
        try:
            k = list(result)[0]
        except IndexError:
            return result
        try:
            assert result[k] > 0
            result[k] = str(result[k])
        except (AssertionError, TypeError):
            raise ValueError(f"{k} must be positive integer; got {result[k]}")
        else:
            return result


# Todo: transcribe:
# - common:IDType
# - common:NCNameIDType
# - common:VersionType

PARAM: Dict[str, Parameter] = {
    # Path parameters
    "agency_id": PathParameter("agency_id"),
    "key": OptionalPath("key"),
    "resource_id": PathParameter("resource_id", set(), "all"),
    #
    # Query parameters
    "dimension_at_observation": QueryParameter("dimension_at_observation"),
    "first_n_observations": PositiveIntParam("first_n_observations"),
    "include_history": QueryParameter("include_history", {True, False}),
    "last_n_observations": PositiveIntParam("last_n_observations"),
    "mode": QueryParameter("mode", {"available", "exact"}),
    "references_a": QueryParameter(
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
    "updated_after": QueryParameter("updated_after"),  # Also availability
}

#: Common lists of names used in both :data:`.v21.PARAM` and :data:`.v30.PARAM`. The
#: parameters in the latter generally have 1 or more additional entries.
NAMES = {
    "context": {
        "dataflow",
        "datastructure",
        "metadataflow",
        "metadatastructure",
        "provisionagreement",
    },
    "detail_s": {
        "allcompletestubs",
        "allstubs",
        "full",
        "referencecompletestubs",
        "referencepartial",
        "referencestubs",
    },
    "references_s": {
        "all",
        "children",
        "descendants",
        "none",
        "parents",
        "parentsandsiblings",
    },
}


class URL(abc.ABC):
    """Abstract base utility class to build SDMX-REST API URLs.

    Parameters
    ----------
    source : .Source
        Provides a base URL (API entry point) and optional modification of the complete
        URL.
    resource_type : .Resource
        Indicates the type of query to be made.
    """

    #: SDMX REST web service to query.
    source: "sdmx.source.Source"

    #: Type of resource to be retrieved; a member of :class:`.Resource`.
    resource_type: Resource

    #: Pieces for the hierarchical path component of the URL. If
    _path: Dict[str, Optional[str]]

    #: Pieces for the query component of the URL.
    query: Dict[str, str]

    # Keyword arguments to the constructor
    _params: dict

    _all_parameters: ClassVar[Mapping[Any, Parameter]]

    def __init__(self, source: "sdmx.source.Source", resource_type: Resource, **kwargs):
        # Check for duplicates in kwargs["params"] and kwargs directly
        params = copy(kwargs)
        params_dict = params.pop("params", {})
        if overlap := set(params) & set(params_dict):
            raise ValueError(f"Duplicate values for query parameters {overlap}")
        params.update(params_dict)

        self.source = source
        self.resource_type = resource_type

        # Store the keyword arguments
        self._params = params

        # Internal
        self._path = dict()
        self.query = dict()

        # Identify the query type
        if resource_type.name in {
            "data",
            "metadata",
            "schema",
            "structure",
            "registration",
        }:
            query_type = resource_type.name
        elif resource_type.name in {"availableconstraint"}:
            query_type = "availability"
        else:
            query_type = "structure"

        # Dispatch to a method appropriate to the Version and QueryType
        getattr(self, f"handle_{query_type}")()

        if len(self._params):
            raise ValueError(f"Unexpected/unhandled parameters {self._params}")

    # General-purpose methods

    def handle_path_params(self, expr: str) -> None:
        """Extend :attr:`.path` with parts from `expr`, a "/"-delimited string.

        In an `expr` such as :py:`"/foo/{param}/"`:

        - Parts enclosed in braces like :py:`"{param}"` are looked up in
          :attr:`._all_parameters``, and the resulting :class:`.Parameter` instance
          consumes a keyword argument.
        - Parts that are plain strings like :py:`"foo"` are passed through directly.
        """
        for part in expr.split("/"):
            if part.startswith("{"):
                param = self._all_parameters[part.strip("{}")]
                self._path.update(param.handle(self._params))
            else:
                self._path.update({part: None})

    def handle_query_params(self, expr: str) -> None:
        """Extend :attr:`.query` with parts from `expr`, a " "-delimited string."""
        for p in map(self._all_parameters.__getitem__, expr.split()):
            self.query.update(p.handle(self._params))

    # Handlers for different QueryTypes
    @abc.abstractmethod
    def handle_availability(self) -> None:
        """Handle URL parameters for availability endpoints (abstract method)."""

    @abc.abstractmethod
    def handle_data(self) -> None:
        """Handle URL parameters for data endpoints (abstract method)."""

    @abc.abstractmethod
    def handle_metadata(self) -> None:
        """Handle URL parameters for metadata endpoints (abstract method)."""

    @abc.abstractmethod
    def handle_registration(self) -> None:
        """Handle URL parameters for registration endpoints (abstract method)."""

    def handle_schema(self) -> None:
        """Handle URL parameters for schema endpoints."""
        self._params.setdefault("agency_id", self.source.id)
        self.handle_path_params(
            self.rt + "/{context}/{agency_id}/{resource_id}/{version}"
        )
        self.handle_query_params("dimension_at_observation")

    def handle_structure(self) -> None:
        """Handle URL parameters for structure endpoints."""
        self._params.setdefault("agency_id", self.source.id)
        self.handle_path_params("{agency_id}/{resource_id}/{version}")
        self.handle_query_params("detail_s references_s")

    def join(self, *, with_query: bool = True) -> str:
        """Join the URL parts, returning a complete URL.

        Parameters
        ----------
        with_query : bool
            If :any:`False`, omit :attr:`.query` from the joined URL.
        """
        # Keep the URL scheme, netloc, and any path from the source's base URL
        parts = list(urlsplit(self.source.url)[:3]) + [None, None]

        # Assemble path string
        parts[2] = re.sub("([^/])$", r"\1/", parts[2] or "") + "/".join(
            (value or name) for name, value in self._path.items()
        )

        if with_query:
            # Assemble query string
            parts[3] = "&".join(f"{k}={v}" for k, v in self.query.items())

        return urlunsplit(parts)

    @property
    def rt(self) -> str:
        """Shorthand access to :class:`str` name of :attr:`.resource_type`."""
        return self.resource_type.name
