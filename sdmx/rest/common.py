"""Information related to the SDMX-REST web service standard."""
import abc
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar, Optional, Set
from warnings import warn

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
class URL(abc.ABC):
    """Utility class to build SDMX REST web service URLs."""

    source: "sdmx.source.Source"

    resource_type: Resource

    resource_id: str

    provider: Optional[str] = None

    # Data provider ID to use in the URL
    agencyID: Optional[str] = None

    version: Optional[str] = None

    key: Optional[str] = None

    _resource_types_with_key: ClassVar[Set[Resource]] = {
        Resource.data,
        Resource.actualconstraint,
    }

    def __post_init__(self):
        if self.resource_type in self._resource_types_with_key:
            # Requests for data do not specific an agency in the URL
            if self.provider is not None:
                warn(f"'provider' argument is redundant for {self.resource_type!r}")
            self.agency_id = None
        else:
            self.agency_id = (
                self.provider if self.provider else getattr(self.source, "id", None)
            )

    @abc.abstractmethod
    def join(self) -> str:
        """Join the URL parts, returning a complete URL."""
