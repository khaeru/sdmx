"""Information about the SDMX-ML 3.0 file format."""
from sdmx.model import v30

from .common import XMLFormat

FORMAT = XMLFormat(
    model=v30,
    base_ns="http://www.sdmx.org/resources/sdmxml/schemas/v3_0",
    class_tag=[
        ("model.DataflowRelationship", "str:None"),
        ("model.ObservationRelationship", "str:Observation"),
        ("model.Dataflow", "str:Dataflow"),
        ("model.MetadataAttributeDescriptor", "str:MetadataAttributeList"),
        ("model.Metadataflow", "str:Metadataflow"),
        ("model.MetadataSet", "mes:MetadataSet"),
    ]
    + [
        (f"model.{name}", f"str:{name}")
        for name in """
            ExclusiveCodeSelection
            InclusiveCodeSelection
            CodelistExtension
            DataConstraint
            GeoFeatureSetCode
            GeographicCodelist
            GeoGridCode
            GeoGridCodelist
            Hierarchy
            Measure
            MetadataAttribute
            MetadataConstraint
            ValueItem
            ValueList
        """.split()
    ],
)


def __getattr__(name):
    return getattr(FORMAT, name)
