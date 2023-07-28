from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, List, Optional

from sdmx.util import DictLikeDescriptor

from . import common
from .common import (
    AttributeDescriptor,
    Code,
    Codelist,
    Component,
    ComponentList,
    ConstraintRole,
    ConstraintRoleType,
    DimensionDescriptor,
    Facet,
    GroupDimensionDescriptor,
    IdentifiableArtefact,
    Item,
    ItemScheme,
    MaintainableArtefact,
    MemberValue,
    NameableArtefact,
    Organisation,
    OrganisationScheme,
    Structure,
)

# Classes defined directly in the current file, in the order they appear
__all__ = [
    "CodelistExtension",
    "GeoRefCode",
    "GeoGridCode",
    "GeoFeatureSetCode",
    "GeoCodelist",
    "GeographicCodelist",
    "GeoGridCodelist",
    "ValueItem",
    "ValueList",
    "MetadataProvider",
    "MetadataProviderScheme",
    "Measure",
    "MeasureDescriptor",
    "DataStructureDefinition",
    "CodingFormat",
    "Level",
    "HierarchicalCode",
    "Hierarchy",
    "HierarchyAssociation",
    "Constraint",
    "DataConstraint",
    "MetadataConstraint",
]

# §4.3: Codelist


@dataclass
class CodelistExtension:
    codelist: Codelist
    prefix: Optional[str] = None
    sequence: Optional[int] = None

    mv: List[MemberValue] = field(default_factory=list)


class GeoRefCode(Code):
    """SDMX 3.0 GeoRefCode (abstract class)."""


@dataclass
@NameableArtefact._preserve("eq", "hash", "repr")
class GeoGridCode(GeoRefCode):
    """SDMX 3.0 GridCode."""

    geo_cell: str = ""  # FIXME remove the default


@dataclass
class GeoFeatureSetCode(GeoRefCode):
    """SDMX 3.0 GeoFeatureSetCode."""

    value: str = ""  # FIXME remove the default


#: SDMX 3.0 GeoCodelistType.
GeoCodelistType = Enum("GeoCodelistType", "geographic geogrid")


@dataclass
class GeoCodelist(Codelist[GeoRefCode]):
    """SDMX 3.0 GeoCodelist (abstract class)."""

    geo_type: ClassVar[GeoCodelistType]

    _Item = GeoRefCode


@dataclass
class GeographicCodelist(GeoCodelist):
    """SDMX 3.0 GeographicCodelist."""

    geo_type = GeoCodelistType.geographic

    _Item = GeoFeatureSetCode


@dataclass
class GeoGridCodelist(GeoCodelist):
    """SDMX 3.0 GeoGridCodelist."""

    geo_type = GeoCodelistType.geogrid

    grid_definition: str = ""  # FIXME remove the default

    _Item = GeoGridCode


# §4.4: ValueList


class ValueItem(Item):
    """SDMX 3.0 ValueItem."""

    # FIXME should inherit from EnumeratedItem


class ValueList(ItemScheme[ValueItem]):
    """SDMX 3.0 ValueList."""

    _Item = ValueItem


# §4.7: OrganisationScheme


class MetadataProvider(Organisation):
    """An organization that produces reference metadata."""


class MetadataProviderScheme(OrganisationScheme[MetadataProvider]):
    """A maintained collection of :class:`MetadataProvider`."""

    _Item = MetadataProvider


# §5: Data Structure Definition and Dataset


class Measure(Component):
    """SDMX 3.0 Measure.

    This class is not present in SDMX 2.1; see instead :class:`.v21.PrimaryMeasure`.
    """


class MeasureDescriptor(ComponentList[Measure]):
    """SDMX 3.0 MeasureDescriptor.

    For SDMX 2.1; see instead :class:`.v21.MeasureDescriptor`.
    """

    _Component = Measure


@dataclass(repr=False)
class DataStructureDefinition(Structure, common.BaseDataStructureDefinition):
    """SDMX 3.0 DataStructureDefinition (‘DSD’)."""

    #: A :class:`AttributeDescriptor` that describes the attributes of the data
    #: structure.
    attributes: AttributeDescriptor = field(default_factory=AttributeDescriptor)
    #: A :class:`DimensionDescriptor` that describes the dimensions of the data
    #: structure.
    dimensions: DimensionDescriptor = field(default_factory=DimensionDescriptor)
    #: A :class:`.MeasureDescriptor`.
    measures: MeasureDescriptor = field(default_factory=MeasureDescriptor)
    #: Mapping from  :attr:`.GroupDimensionDescriptor.id` to
    #: :class:`.GroupDimensionDescriptor`.
    group_dimensions: DictLikeDescriptor[
        str, GroupDimensionDescriptor
    ] = DictLikeDescriptor()

    __hash__ = IdentifiableArtefact.__hash__


# §8: Hierarchy


class CodingFormat:
    """SDMX 3.0 CodingFormat."""

    coding_format: Facet


@dataclass
class Level(NameableArtefact):
    child: Optional["Level"] = None
    parent: Optional["Level"] = None

    code_format: CodingFormat = field(default_factory=CodingFormat)


@dataclass
class HierarchicalCode(IdentifiableArtefact):
    #: Date from which the construct is valid.
    valid_from: Optional[str] = None
    #: Date from which the construct is superseded.
    valid_to: Optional[str] = None

    child: List["HierarchicalCode"] = field(default_factory=list)
    parent: List["HierarchicalCode"] = field(default_factory=list)

    #: The Code that is used at the specific point in the hierarchy.
    code: Optional[Code] = None

    level: Optional[Level] = None


@dataclass
class Hierarchy(MaintainableArtefact):
    """SDMX 3.0 Hierarchy."""

    has_format_levels: bool = False

    #: The top :class:`Level` in the hierarchy.
    level: Optional[Level] = None

    #: The top-level :class:`HierarchicalCodes <HierarchicalCode>` in the hierarchy.
    codes: List[HierarchicalCode] = field(default_factory=list)


@dataclass
class HierarchyAssociation(MaintainableArtefact):
    """SDMX 3.0 HierarchyAssociation."""

    #: The context within which the association is performed.
    context_object: Optional[IdentifiableArtefact] = None
    #: The IdentifiableArtefact that needs the Hierarchy.
    linked_object: Optional[IdentifiableArtefact] = None
    #: The Hierarchy that is associated.
    linked_hierarchy: Optional[Hierarchy] = None


# §12.3: Constraints


@dataclass
class Constraint(MaintainableArtefact):
    """SDMX 3.0 Constraint (abstract class).

    For SDMX 2.1, see :class:`.v21.Constraint`.
    """

    # NB the spec gives 1..* for this attribute, but this implementation allows only 1
    role: Optional[ConstraintRole] = None

    def __post_init__(self):
        if isinstance(self.role, str):
            self.role = ConstraintRole(role=ConstraintRoleType[self.role])


class DataConstraint(Constraint):
    pass


class MetadataConstraint(Constraint):
    pass


def __dir__():
    return sorted(__all__ + common.__all__)


def __getattr__(name):
    return getattr(common, name)


get_class = common.ClassFinder(__name__)
