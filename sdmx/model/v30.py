"""SDMX 3.0 Information Model."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Set

from . import common
from .common import (
    Code,
    Codelist,
    Component,
    ComponentList,
    ConstrainableArtefact,
    ConstraintRole,
    ConstraintRoleType,
    IdentifiableArtefact,
    MaintainableArtefact,
    NameableArtefact,
    Organisation,
    OrganisationScheme,
)
from .internationalstring import InternationalStringDescriptor

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
    "DataflowRelationship",
    "MeasureRelationship",
    "ObservationRelationship",
    "DataStructureDefinition",
    "Dataflow",
    "Observation",
    "StructureSpecificDataSet",
    "MetadataAttributeDescriptor",
    "IdentifiableObjectSelection",
    "MetadataStructureDefinition",
    "Metadataflow",
    "MetadataAttributeValue",
    "CodedMetadataAttributeValue",
    "UncodedMetadataAttributeValue",
    "OtherUncodedAttributeValue",
    "TextAttributeValue",
    "XHTMLAttributeValue",
    "TargetIdentifiableObject",
    "MetadataSet",
    "Hierarchy",
    "HierarchyAssociation",
    "SelectionValue",
    "MemberValue",
    "TimeRangeValue",
    "BeforePeriod",
    "AfterPeriod",
    "RangePeriod",
    "DataKey",
    "DataKeySet",
    "Constraint",
    "MemberSelection",
    "DataConstraint",
    "MetadataConstraint",
]

# §4.3: Codelist


@dataclass
class CodeSelection:
    mv: List["MemberValue"] = field(default_factory=list)


class ExclusiveCodeSelection(CodeSelection):
    pass


class InclusiveCodeSelection(CodeSelection):
    pass


@dataclass
class CodelistExtension:
    extends: Codelist
    prefix: Optional[str] = None
    sequence: Optional[int] = None

    selection: Optional[CodeSelection] = None


class GeoRefCode(Code):
    """SDMX 3.0 GeoRefCode (abstract class)."""


@dataclass
@NameableArtefact._preserve("eq", "hash", "repr")
class GeoGridCode(GeoRefCode):
    """SDMX 3.0 GridCode."""

    geo_cell: str = ""  # FIXME remove the default


@dataclass
@NameableArtefact._preserve("eq", "hash", "repr")
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


@dataclass
@IdentifiableArtefact._preserve("hash")
class EnumeratedItem(common.AnnotableArtefact):
    """SDMX 3.0 EnumeratedItem.

    This class is similar to :meth:`.Item`, but with a only subset of its features; i.e.
    no :attr:`IdentifiableArtefact.urn`.
    """

    #: Identifier of the item.
    id: str = common.MissingID

    #: Multi-lingual name of the object. Analogous to :attr:`NameableArtefact.name`.
    name: InternationalStringDescriptor = InternationalStringDescriptor()
    #: Multi-lingual description of the object. Analogous to
    #: :attr:`NameableArtefact.description`.
    description: InternationalStringDescriptor = InternationalStringDescriptor()

    def __iter__(self, recurse=True):
        # Mirrors Item.__iter__
        yield self


class ValueItem(EnumeratedItem):
    """SDMX 3.0 ValueItem."""


class EnumeratedList(common.MaintainableArtefact):
    pass


@dataclass
class ValueList(EnumeratedList):
    """SDMX 3.0 ValueList."""

    _Item = ValueItem

    items: List[ValueItem] = field(default_factory=list)

    def append(self, item: ValueItem) -> None:
        self.items.append(item)


# §4.7: OrganisationScheme


class MetadataProvider(Organisation):
    """An organization that produces reference metadata."""


class MetadataProviderScheme(OrganisationScheme[MetadataProvider]):
    """A maintained collection of :class:`MetadataProvider`."""

    _Item = MetadataProvider


# §12.3: Constraints


@dataclass
class SelectionValue(common.BaseSelectionValue):
    #: Date from which the DataKey is valid.
    valid_from: Optional[str] = None
    #: Date from which the DataKey is superseded.
    valid_to: Optional[str] = None


class MemberValue(common.BaseMemberValue, SelectionValue):
    """SDMX 3.0 MemberValue."""


class TimeRangeValue(SelectionValue):
    """SDMX 3.0 TimeRangeValue."""


class BeforePeriod(TimeRangeValue, common.Period):
    pass


class AfterPeriod(TimeRangeValue, common.Period):
    pass


@dataclass
class RangePeriod(TimeRangeValue):
    start: Optional[common.StartPeriod] = None
    end: Optional[common.EndPeriod] = None


@dataclass
class DataKey(common.BaseDataKey):
    #: Date from which the DataKey is valid.
    valid_from: Optional[str] = None
    #: Date from which the DataKey is superseded.
    valid_to: Optional[str] = None


@dataclass
class DataKeySet(common.BaseDataKeySet):
    #: TODO the SDMX 3.0 spec is ambiguous about this: the diagram shows "member" as an
    #: attribute of :class:`.DataKey`, but the table lists it as an attribute of
    #: DataKeySet.
    member: Any = None


@dataclass
class Constraint(common.BaseConstraint):
    """SDMX 3.0 Constraint (abstract class).

    For SDMX 2.1, see :class:`.v21.Constraint`.
    """

    role: Optional[ConstraintRole] = None

    def __post_init__(self):
        if isinstance(self.role, str):
            self.role = ConstraintRole(role=ConstraintRoleType[self.role])


@dataclass
class MemberSelection(common.BaseMemberSelection):
    """SDMX 3.0 MemberSelection."""

    #: Whether Codes should retain the prefix specified in a code list extension.
    remove_prefix: bool = False


@dataclass
@NameableArtefact._preserve("repr")
class DataConstraint(Constraint):
    #:
    content: Set[ConstrainableArtefact] = field(default_factory=set)

    data_content_keys: Optional[DataKeySet] = None
    data_content_region: Optional[common.CubeRegion] = None

    def __contains__(self, name):
        raise NotImplementedError  # pragma: no cover


class MetadataConstraint(Constraint):
    metadata_content_region: Optional[common.MetadataTargetRegion] = None

    def __contains__(self, name):
        raise NotImplementedError  # pragma: no cover


# §5.3: Data Structure Definition


@dataclass
class Measure(Component):
    """SDMX 3.0 Measure.

    This class is not present in SDMX 2.1; see instead :class:`.v21.PrimaryMeasure`.
    """

    #:
    concept_role: Optional[common.Concept] = None


class MeasureDescriptor(ComponentList[Measure]):
    """SDMX 3.0 MeasureDescriptor.

    For SDMX 2.1 see instead :class:`.v21.MeasureDescriptor`.
    """

    _Component = Measure


class DataflowRelationship(common.AttributeRelationship):
    """SDMX 3.0 DataflowRelationship.

    Indicates that the attribute is attached to the entire data set. Compare with
    :class:`.v21.NoSpecifiedRelationship`.
    """


class MeasureRelationship(common.AttributeRelationship):
    """SDMX 3.0 MeasureRelationship."""


class ObservationRelationship(common.AttributeRelationship):
    """SDMX 3.0 ObservationRelationship.

    Indicates that the attribute is attached to a particular observation. Compare with
    :class:`.v21.PrimaryMeasureRelationship.`
    """


@dataclass(repr=False)
@IdentifiableArtefact._preserve("hash")
class DataStructureDefinition(common.BaseDataStructureDefinition):
    """SDMX 3.0 DataStructureDefinition (‘DSD’)."""

    MemberValue = MemberValue
    MemberSelection = MemberSelection
    ConstraintType = DataConstraint

    #: A :class:`.MeasureDescriptor`.
    measures: MeasureDescriptor = field(default_factory=MeasureDescriptor)


@dataclass(repr=False)
@IdentifiableArtefact._preserve("hash")
class Dataflow(common.BaseDataflow):
    #:
    structure: DataStructureDefinition = field(default_factory=DataStructureDefinition)


# §5.4: Data Set


@dataclass
class Observation(common.BaseObservation):
    #:
    value_for: Optional[Measure] = None


class DataSet(common.BaseDataSet):
    """SDMX 3.0 Data Set."""


class StructureSpecificDataSet(DataSet):
    """SDMX 3.0 StructureSpecificDataSet.

    This subclass has no additional functionality compared to DataSet.
    """


# §7.3 Metadata Structure Definition


class MetadataAttributeDescriptor(common.ComponentList):
    """SDMX 3.0 MetadataAttributeDescriptor."""

    _Component = common.MetadataAttribute


class IdentifiableObjectSelection:
    """SDMX 3.0 IdentifiableObjectSelection."""


@dataclass
@MaintainableArtefact._preserve("hash")
class MetadataStructureDefinition(common.BaseMetadataStructureDefinition):
    """SDMX 3.0 MetadataStructureDefinition."""

    #: A :class:`MetadataAttributeDescriptor` that describes the attributes of the
    #: metadata structure.
    #:
    #: .. note:: The SDMX 3.0.0 IM (version 1.0 / 2021-10) does not give a name for this
    #:    association. :mod:`sdmx` uses `attributes` for consistency with
    #:    :class:`.DataStructureDefinition`.
    attributes: MetadataAttributeDescriptor = field(
        default_factory=MetadataAttributeDescriptor
    )


class Metadataflow(common.BaseMetadataflow):
    """SDMX 3.0 MetadataflowDefinition."""

    structure: MetadataStructureDefinition


# §7.4: Metadata Set


class MetadataAttributeValue:
    """SDMX 3.0 MetadataAttributeValue.

    Analogous to :class:`.v21.ReportedAttribute`.
    """

    # NB the IM specifies this is a subclass of common.AttributeValue, but the
    #    implementation in .common has both Coded- and UncodedAttributeValue, which
    #    offends mypy.

    parent: Optional["MetadataAttributeValue"] = None
    child: List["MetadataAttributeValue"] = field(default_factory=list)


class CodedMetadataAttributeValue(MetadataAttributeValue):
    """SDMX 3.0 CodedMetadataAttributeValue.

    Analogous to :class:`.v21.EnumeratedAttributeValue`.
    """

    value_of: common.Code


class UncodedMetadataAttributeValue(MetadataAttributeValue):
    """SDMX 3.0 UncodedMetadataAttributeValue."""

    pass


class OtherUncodedAttributeValue(UncodedMetadataAttributeValue):
    """SDMX 3.0 OtherUncodedAttributeValue."""

    value: str
    start_time: date


class TextAttributeValue(UncodedMetadataAttributeValue, common.BaseTextAttributeValue):
    """SDMX 3.0 TextAttributeValue."""


class XHTMLAttributeValue(
    UncodedMetadataAttributeValue, common.BaseXHTMLAttributeValue
):
    """SDMX 3.0 XHTMLAttributeValue."""


class TargetIdentifiableObject:
    """SDMX 3.0 TargetIdentifiableObject."""


@dataclass
class MetadataSet(MaintainableArtefact, common.BaseMetadataSet):
    """SDMX 3.0 MetadataSet.

    .. note:: Contrast :class:`.v21.MetadataSet`, which is a :class:`.NameableArtefact`.
    """

    # NB Would prefer to type as datetime.date, but VersionableArtefact currently uses
    #    str
    valid_from: Optional[str] = None
    # NB Would prefer to type as datetime.date, but VersionableArtefact currently uses
    #    str
    valid_to: Optional[str] = None
    set_id: Optional[str] = None

    described_by: Optional[Metadataflow] = None

    # described_by: Optional[MetadataProvisionAgreement] = None

    structured_by: Optional[MetadataAttributeDescriptor] = None

    #: Analogous to :attr:`.v21.MetadataSet.published_by`.
    provided_by: Optional[MetadataProvider] = None

    attaches_to: List[TargetIdentifiableObject] = field(default_factory=list)

    metadata: List[MetadataAttributeValue] = field(default_factory=list)


# §8: Hierarchy


@dataclass
class Hierarchy(MaintainableArtefact):
    """SDMX 3.0 Hierarchy."""

    has_formal_levels: bool = False

    #: The top :class:`Level` in the hierarchy.
    level: Optional[common.Level] = None

    #: The top-level :class:`HierarchicalCodes <HierarchicalCode>` in the hierarchy.
    codes: Dict[str, common.HierarchicalCode] = field(default_factory=dict)


@dataclass
class HierarchyAssociation(MaintainableArtefact):
    """SDMX 3.0 HierarchyAssociation."""

    #: The context within which the association is performed.
    context_object: Optional[IdentifiableArtefact] = None
    #: The IdentifiableArtefact that needs the Hierarchy.
    linked_object: Optional[IdentifiableArtefact] = None
    #: The Hierarchy that is associated.
    linked_hierarchy: Optional[Hierarchy] = None


CF = common.ClassFinder(
    __name__,
    parent_map={
        Measure: MeasureDescriptor,
        common.MetadataAttribute: MetadataAttributeDescriptor,
    },
)
get_class = CF.get_class
parent_class = CF.parent_class
__dir__ = CF.dir
__getattr__ = CF.getattr
