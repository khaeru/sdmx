"""SDMX 2.1 Information Model (SDMX-IM).

This module implements many of the classes described in the SDMX-IM specification
('spec'), which is available from:

- https://sdmx.org/?page_id=5008
- https://sdmx.org/wp-content/uploads/
    SDMX_2-1-1_SECTION_2_InformationModel_201108.pdf

Details of the implementation:

- Python dataclasses and type hinting are used to enforce the types of attributes that
  reference instances of other classes.
- Some classes have convenience attributes not mentioned in the spec, to ease navigation
  between related objects. These are marked “:mod:`sdmx` extension not in the IM.”
- Class definitions are grouped by section of the spec, but these sections appear out
  of order so that dependent classes are defined first.

"""
import logging

# TODO for complete implementation of the IM, enforce TimeKeyValue (instead of KeyValue)
#      for {Generic,StructureSpecific} TimeSeriesDataSet.
from dataclasses import dataclass, field
from typing import Generator, List, Optional, Set, Union

from sdmx.util import DictLikeDescriptor

from . import common
from .common import (
    AttributeRelationship,
    Code,
    Component,
    ComponentList,
    ConstrainableArtefact,
    ConstraintRole,
    DataAttribute,
    DataProvider,
    DimensionComponent,
    DimensionDescriptor,
    GroupDimensionDescriptor,
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
    "MetadataflowDefinition",
    "MetadataStructureDefinition",
]

log = logging.getLogger(__name__)


# §10.3: Constraints


SelectionValue = common.BaseSelectionValue


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


DataKey = common.BaseDataKey

DataKeySet = common.BaseDataKeySet


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


class MeasureDimension(DimensionComponent):
    """SDMX 2.1 MeasureDimension.

    This class is not present in SDMX 3.0.
    """


class PrimaryMeasure(Component):
    """SDMX 2.1 PrimaryMeasure.

    This class is not present in SDMX 3.0; see instead :class:`.v30.Measure`.
    """


class MeasureDescriptor(ComponentList[PrimaryMeasure]):
    """SDMX 2.1 MeasureDescriptor.

    For SDMX 3.0; see instead :class:`.v30.MeasureDescriptor`.
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


class MetadataStructureDefinition(common.BaseMetadataStructureDefinition):
    """SDMX 2.1 MetadataStructureDefinition."""


class MetadataflowDefinition(common.BaseMetadataflow):
    """SDMX 2.1 MetadataflowDefinition."""


def parent_class(cls):
    """Return the class that contains objects of type `cls`.

    E.g. if `cls` is :class:`.PrimaryMeasure`, returns :class:`.MeasureDescriptor`.
    """
    return {
        common.Agency: common.AgencyScheme,
        common.Category: common.CategoryScheme,
        Code: common.Codelist,
        common.Concept: common.ConceptScheme,
        common.Dimension: DimensionDescriptor,
        DataProvider: common.DataProviderScheme,
        GroupDimensionDescriptor: DataStructureDefinition,
        PrimaryMeasure: MeasureDescriptor,
    }[cls]


def __dir__():
    return sorted(__all__ + common.__all__)


def __getattr__(name):
    return getattr(common, name)


get_class = common.ClassFinder(__name__)
