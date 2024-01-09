"""Information about the SDMX-ML 2.1 file format."""
from sdmx.model import v21

from .common import XMLFormat

FORMAT = XMLFormat(
    model=v21,
    base_ns="http://www.sdmx.org/resources/sdmxml/schemas/v2_1",
    class_tag=[
        ("message.DataMessage", "mes:GenericData"),
        ("message.DataMessage", "mes:GenericTimeSeriesData"),
        ("message.DataMessage", "mes:StructureSpecificTimeSeriesData"),
        ("model.NoSpecifiedRelationship", "str:None"),
        ("model.DataflowDefinition", "str:Dataflow"),
        ("model.DimensionDescriptorValuesTarget", "str:KeyDescriptorValuesTarget"),
        ("model.MetadataflowDefinition", "str:Metadataflow"),
        ("model.MetadataSet", "mes:MetadataSet"),
        ("model.ReportedAttribute", "md:ReportedAttribute"),
        ("model.TargetIdentifiableObject", ":ObjectReference"),
        ("model.TargetIdentifiableObject", "md:ObjectReference"),
        ("model.TargetObjectKey", ":Target"),
        ("model.TargetObjectKey", "md:Target"),
        ("model.TargetReportPeriod", "ReportPeriod"),
        ("model.TargetReportPeriod", "md:ReportPeriod"),
        ("model.MetadataReport", ":Report"),
        ("model.MetadataReport", "md:Report"),
    ]
    + [
        (f"model.{name}", f"str:{name}")
        for name in """
            CodelistMap
            CodeMap
            ContentConstraint
            HierarchicalCodelist
            Hierarchy
            IdentifiableObjectTarget
            MeasureDimension
            MetadataAttribute
            MetadataTarget
            PrimaryMeasure
            ReportPeriodTarget
            ReportStructure
            StructureSet
        """.split()
    ],
)


def __getattr__(name):
    return getattr(FORMAT, name)
