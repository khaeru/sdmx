"""SDMX 2.1 Information Model."""
import logging

# TODO for complete implementation of the IM, enforce TimeKeyValue (instead of KeyValue)
#      for {Generic,StructureSpecific} TimeSeriesDataSet.
from dataclasses import dataclass, field
from typing import (
    ClassVar,
    Dict,
    Generator,
    Generic,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
)

from sdmx.dictlike import DictLikeDescriptor

from . import common
from .common import (
    IT,
    AttributeRelationship,
    Component,
    ComponentList,
    ConstrainableArtefact,
    ConstraintRole,
    DataAttribute,
    DimensionComponent,
    IdentifiableArtefact,
    Key,
    NameableArtefact,
)

# Classes defined directly in the current file, in the order they appear
__all__ = [
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
    "ContentConstraint",
    "MeasureDimension",
    "PrimaryMeasure",
    "MeasureDescriptor",
    "NoSpecifiedRelationship",
    "PrimaryMeasureRelationship",
    "ReportingYearStartDay",
    "DataStructureDefinition",
    "DataflowDefinition",
    "Observation",
    "StructureSpecificDataSet",
    "GenericDataSet",
    "GenericTimeSeriesDataSet",
    "StructureSpecificTimeSeriesDataSet",
    "ReportingCategory",
    "ReportingTaxonomy",
    "TargetObject",
    "DataSetTarget",
    "DimensionDescriptorValuesTarget",
    "IdentifiableObjectTarget",
    "ReportPeriodTarget",
    "MetadataTarget",
    "ReportStructure",
    "MetadataStructureDefinition",
    "MetadataflowDefinition",
    "TargetObjectValue",
    "TargetReportPeriod",
    "TargetIdentifiableObject",
    "TargetObjectKey",
    "ReportedAttribute",
    "EnumeratedAttributeValue",
    "NonEnumeratedAttributeValue",
    "OtherNonEnumeratedAttributeValue",
    "TextAttributeValue",
    "XHTMLAttributeValue",
    "MetadataReport",
    "MetadataSet",
    "Hierarchy",
    "HierarchicalCodelist",
    "ItemAssociation",
    "CodeMap",
    "ItemSchemeMap",
    "CodelistMap",
    "StructureSet",
]

log = logging.getLogger(__name__)


# §10.3: Constraints


class SelectionValue(common.BaseSelectionValue):
    """SDMX 2.1 SelectionValue.

    Identical to its parent class.
    """


class MemberValue(common.BaseMemberValue, SelectionValue):
    """SDMX 2.1 MemberValue."""


class TimeRangeValue(SelectionValue):
    """SDMX 2.1 TimeRangeValue."""


class BeforePeriod(TimeRangeValue, common.Period):
    pass


class AfterPeriod(TimeRangeValue, common.Period):
    pass


@dataclass
class RangePeriod(TimeRangeValue):
    start: common.StartPeriod
    end: common.EndPeriod


class DataKey(common.BaseDataKey):
    """SDMX 2.1 DataKey.

    Identical to its parent class.
    """


class DataKeySet(common.BaseDataKeySet):
    """SDMX 2.1 DataKeySet.

    Identical to its parent class.
    """


@dataclass
class Constraint(common.BaseConstraint):
    """SDMX 2.1 Constraint.

    For SDMX 3.0, see :class:`.v30.Constraint`.
    """

    # NB the spec gives 1..* for this attribute, but this implementation allows only 1
    role: Optional[ConstraintRole] = None
    #: :class:`.DataKeySet` included in the Constraint.
    data_content_keys: Optional[DataKeySet] = None
    # metadata_content_keys: MetadataKeySet = None

    def __contains__(self, value):
        if self.data_content_keys is None:
            raise NotImplementedError("Constraint does not contain a DataKeySet")

        return value in self.data_content_keys


class MemberSelection(common.BaseMemberSelection):
    """SDMX 2.1 MemberSelection."""


@dataclass
@NameableArtefact._preserve("repr")
class ContentConstraint(Constraint, common.BaseContentConstraint):
    #: :class:`CubeRegions <.CubeRegion>` included in the ContentConstraint.
    data_content_region: List[common.CubeRegion] = field(default_factory=list)
    #:
    content: Set[ConstrainableArtefact] = field(default_factory=set)
    metadata_content_region: Optional[common.MetadataTargetRegion] = None

    def __contains__(self, value):
        if self.data_content_region:
            return all(value in cr for cr in self.data_content_region)
        else:
            raise NotImplementedError("ContentConstraint does not contain a CubeRegion")

    def to_query_string(self, structure):
        cr_count = len(self.data_content_region)
        try:
            if cr_count > 1:
                log.warning(f"to_query_string() using first of {cr_count} CubeRegions")

            return self.data_content_region[0].to_query_string(structure)
        except IndexError:
            raise RuntimeError("ContentConstraint does not contain a CubeRegion")

    def iter_keys(
        self,
        obj: Union["DataStructureDefinition", "DataflowDefinition"],
        dims: List[str] = [],
    ) -> Generator[Key, None, None]:
        """Iterate over keys.

        A warning is logged if `obj` is not already explicitly associated to this
        ContentConstraint, i.e. present in :attr:`.content`.

        See also
        --------
        .DataStructureDefinition.iter_keys
        """
        if obj not in self.content:
            log.warning(f"{repr(obj)} is not in {repr(self)}.content")

        yield from obj.iter_keys(constraint=self, dims=dims)


# §5.3: Data Structure Definition


@dataclass
class MeasureDimension(DimensionComponent):
    """SDMX 2.1 MeasureDimension.

    This class is not present in SDMX 3.0.
    """

    #:
    concept_role: Optional[common.Concept] = None


class PrimaryMeasure(Component):
    """SDMX 2.1 PrimaryMeasure.

    This class is not present in SDMX 3.0; see instead :class:`.v30.Measure`.
    """


class MeasureDescriptor(ComponentList[PrimaryMeasure]):
    """SDMX 2.1 MeasureDescriptor.

    For SDMX 3.0 see instead :class:`.v30.MeasureDescriptor`.
    """

    _Component = PrimaryMeasure


class NoSpecifiedRelationship(AttributeRelationship):
    """Indicates that the attribute is attached to the entire data set."""


class PrimaryMeasureRelationship(AttributeRelationship):
    """Indicates that the attribute is attached to a particular observation."""


class ReportingYearStartDay(DataAttribute):
    """SDMX 2.1 ReportingYearStartDay.

    This class is deleted in SDMX 3.0.
    """


@dataclass(repr=False)
@IdentifiableArtefact._preserve("hash")
class DataStructureDefinition(common.BaseDataStructureDefinition):
    """SDMX 2.1 DataStructureDefinition (‘DSD’)."""

    MemberValue = MemberValue
    MemberSelection = MemberSelection
    ConstraintType = ContentConstraint

    #: A :class:`.MeasureDescriptor`.
    measures: MeasureDescriptor = field(default_factory=MeasureDescriptor)


@dataclass(repr=False)
@IdentifiableArtefact._preserve("hash")
class DataflowDefinition(common.BaseDataflow):
    #:
    structure: DataStructureDefinition = field(default_factory=DataStructureDefinition)


# §5.4: Data Set


@dataclass
class Observation(common.BaseObservation):
    #:
    value_for: Optional[PrimaryMeasure] = None


@dataclass
class DataSet(common.BaseDataSet):
    """SDMX 2.1 DataSet."""

    #: Named ``attachedAttribute`` in the IM.
    attrib: DictLikeDescriptor[str, common.AttributeValue] = DictLikeDescriptor()


class StructureSpecificDataSet(DataSet):
    """SDMX 2.1 StructureSpecificDataSet.

    This subclass has no additional functionality compared to DataSet.
    """


class GenericDataSet(DataSet):
    """SDMX 2.1 GenericDataSet.

    This subclass has no additional functionality compared to DataSet.
    """


class GenericTimeSeriesDataSet(DataSet):
    """SDMX 2.1 GenericTimeSeriesDataSet.

    This subclass has no additional functionality compared to DataSet.
    """


class StructureSpecificTimeSeriesDataSet(DataSet):
    """SDMX 2.1 StructureSpecificTimeSeriesDataSet.

    This subclass has no additional functionality compared to DataSet.
    """


# §7.3 Metadata Structure Definition


class ReportingCategory(common.Item):
    """SDMX 2.1 ReportingCategory."""


class ReportingTaxonomy(common.ItemScheme):
    """SDMX 2.1 ReportingTaxonomy."""


class TargetObject(common.Component):
    """SDMX 2.1 TargetObject."""


class DataSetTarget(TargetObject):
    """SDMX 2.1 DataSetTarget."""


class DimensionDescriptorValuesTarget(TargetObject):
    """SDMX 2.1 DimensionDescriptorValuesTarget."""


class IdentifiableObjectTarget(TargetObject):
    """SDMX 2.1 IdentifiableObjectTarget."""


class ReportPeriodTarget(TargetObject):
    """SDMX 2.1 ReportPeriodTarget."""


class MetadataTarget(ComponentList):
    """SDMX 2.1 MetadataTarget."""

    _Component = TargetObject


@dataclass
class ReportStructure(ComponentList):
    """SDMX 2.1 ReportStructure."""

    _Component = common.MetadataAttribute

    report_for: List[MetadataTarget] = field(default_factory=list)


@dataclass
@common.MaintainableArtefact._preserve("hash")
class MetadataStructureDefinition(common.BaseMetadataStructureDefinition):
    """SDMX 2.1 MetadataStructureDefinition."""

    report_structure: DictLikeDescriptor[str, ReportStructure] = DictLikeDescriptor()

    #: Association to 1 or more :class:`.MetadataTarget`
    target: DictLikeDescriptor[str, MetadataTarget] = DictLikeDescriptor()


@dataclass
class MetadataflowDefinition(common.BaseMetadataflow):
    """SDMX 2.1 MetadataflowDefinition."""

    # NB narrows the type of common.StructureUsage.structure
    structure: Optional[MetadataStructureDefinition] = None


# §7.4: Metadata Set


@dataclass
class TargetObjectValue:
    """SDMX 2.1 TargetObjectValue."""

    value_for: TargetObject


@dataclass
class TargetReportPeriod(TargetObjectValue):
    """SDMX 2.1 TargetReportPeriod."""

    report_period: str


@dataclass
class TargetIdentifiableObject(TargetObjectValue):
    """SDMX 2.1 TargetIdentifiableObject."""

    obj: IdentifiableArtefact


@dataclass
class TargetObjectKey:
    """SDMX 2.1 TargetObjectKey."""

    key_values: DictLikeDescriptor[str, TargetObjectValue] = DictLikeDescriptor()


@dataclass
class ReportedAttribute:
    """SDMX 2.1 ReportedAttribute.

    Analogous to :class:`.v30.MetadataAttributeValue`.
    """

    value_for: common.MetadataAttribute
    parent: Optional["ReportedAttribute"] = None
    child: List["ReportedAttribute"] = field(default_factory=list)

    def __getitem__(self, index: int) -> "ReportedAttribute":
        return self.child[index]

    def __len__(self) -> int:
        return len(self.child)


class EnumeratedAttributeValue(ReportedAttribute):
    """SDMX 2.1 EnumeratedAttributeValue.

    Analogous to :class:`.v30.CodedMetadataAttributeValue`.
    """

    value: str

    #: .. note::
    #:
    #:    The SDMX 2.1 IM (2011-08) gives this as `valueFor`, but this name duplicates
    #:    :attr:`.ReportedAttribute.value_for`. :mod:`sdmx` uses `value_of` for
    #:    consistency with :attr:`.v30.CodedMetadataAttributeValue.value_of`.
    value_of: common.Code


class NonEnumeratedAttributeValue(ReportedAttribute):
    """SDMX 2.1 NonEnumeratedAttributeValue."""


class OtherNonEnumeratedAttributeValue(NonEnumeratedAttributeValue):
    """SDMX 2.1 OtherNonEnumeratedAttributeValue."""

    value: str


class TextAttributeValue(NonEnumeratedAttributeValue, common.BaseTextAttributeValue):
    """SDMX 2.1 TextAttributeValue."""


@dataclass
class XHTMLAttributeValue(NonEnumeratedAttributeValue, common.BaseXHTMLAttributeValue):
    """SDMX 2.1 XHTMLAttributeValue."""

    value: str


@dataclass
class MetadataReport:
    """SDMX 2.1 MetadataReport."""

    metadata: List[ReportedAttribute] = field(default_factory=list)
    target: Optional[MetadataTarget] = None
    attaches_to: Optional[TargetObjectKey] = None


@dataclass
class MetadataSet(NameableArtefact, common.BaseMetadataSet):
    """SDMX 2.1 MetadataSet.

    .. note:: Contrast :class:`.v30.MetadataSet`, which is a
       :class:`.MaintainableArtefact`.
    """

    described_by: Optional[MetadataflowDefinition] = None
    # described_by: Optional[ReportStructure] = None
    structured_by: Optional[MetadataStructureDefinition] = None

    #: Analogous to :attr:`.v30.MetadataSet.provided_by`.
    published_by: Optional[common.DataProvider] = None

    report: List[MetadataReport] = field(default_factory=list)


# §8 Hierarchical Code List


@dataclass
class Hierarchy(NameableArtefact):
    """SDMX 2.1 Hierarchy."""

    has_formal_levels: bool = False

    #: Hierarchical codes in the hierarchy.
    codes: Dict[str, common.HierarchicalCode] = field(default_factory=dict)

    level: Optional[common.Level] = None


@dataclass
class HierarchicalCodelist(common.MaintainableArtefact):
    """SDMX 2.1 HierarchicalCodelist."""

    hierarchy: List[Hierarchy] = field(default_factory=list)

    def __repr__(self) -> str:
        tmp = super(NameableArtefact, self).__repr__()[:-1]
        return f"{tmp}: {len(self.hierarchy)} hierarchies>"


# §9: Structure Set and Mappings


@dataclass
class ItemAssociation(common.AnnotableArtefact, Generic[IT]):
    """SDMX 2.1 ItemAssociation."""

    _Item: ClassVar[Type[common.Item]] = common.Item

    source: Optional[IT] = None
    target: Optional[IT] = None


class CodeMap(ItemAssociation[common.Code]):
    """SDMX 2.1 CodeMap."""

    _Item = common.Code


IAT = TypeVar("IAT", bound="ItemAssociation")
IST = TypeVar("IST", bound="common.ItemScheme")


@dataclass
class ItemSchemeMap(NameableArtefact, Generic[IST, IAT]):
    """SDMX 2.1 ItemSchemeMap."""

    _ItemAssociation: ClassVar[Type[ItemAssociation]] = ItemAssociation

    source: Optional[IST] = None
    target: Optional[IST] = None

    item_association: List[IAT] = field(default_factory=list)


class CodelistMap(ItemSchemeMap[common.Codelist, CodeMap]):
    """SDMX 2.1 CodelistMap."""

    _ItemAssociation = CodeMap


@dataclass
class StructureSet(common.MaintainableArtefact):
    """SDMX 2.1 StructureSet."""

    item_scheme_map: List[ItemSchemeMap] = field(default_factory=list)


CF = common.ClassFinder(
    __name__,
    name_map={
        "Dataflow": "DataflowDefinition",
        "DataStructure": "DataStructureDefinition",
        "MetadataStructure": "MetadataStructureDefinition",
        "Metadataflow": "MetadataflowDefinition",
    },
    parent_map={
        common.HierarchicalCode: Hierarchy,
        PrimaryMeasure: MeasureDescriptor,
        MetadataTarget: MetadataStructureDefinition,
    },
)
get_class = CF.get_class
parent_class = CF.parent_class
__dir__ = CF.dir
__getattr__ = CF.getattr
