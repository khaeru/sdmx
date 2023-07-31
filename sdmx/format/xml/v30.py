"""Information about the SDMX-ML 3.0 file format."""
from sdmx import message
from sdmx.model import v30 as model

from . import common

_CLS_TAG = []

for c, t in (
    (message.DataMessage, "mes:StructureSpecificData"),
    (message.ErrorMessage, "mes:Error"),
    (message.StructureMessage, "mes:Structure"),
    (model.AttributeDescriptor, "str:AttributeList"),
    (model.DataAttribute, "str:Attribute"),
    (model.ObservationRelationship, "str:Observation"),
    (model.Dataflow, "str:Dataflow"),
    (model.DataStructureDefinition, "str:DataStructure"),
    (model.DataStructureDefinition, "com:Structure"),
    (model.DataStructureDefinition, "str:Structure"),
    (model.DimensionDescriptor, "str:DimensionList"),
    (model.GroupDimensionDescriptor, "str:Group"),
    (model.GroupDimensionDescriptor, "str:AttachmentGroup"),
    (model.GroupKey, "gen:GroupKey"),
    (model.Key, "gen:ObsKey"),
    (model.MeasureDescriptor, "str:MeasureList"),
    (model.Metadataflow, "str:Metadataflow"),
    (model.MetadataStructureDefinition, "str:MetadataStructure"),
    (model.SeriesKey, "gen:SeriesKey"),
    (model.StructureUsage, "com:StructureUsage"),
):
    _CLS_TAG.append((c, t))


for name in (
    "CodelistExtension",
    "DataConstraint",
    "GeoFeatureSetCode",
    "GeographicCodelist",
    "GeoGridCode",
    "GeoGridCodelist",
    "Measure",
    "MetadataConstraint",
    "ValueItem",
    "ValueList",
):
    _CLS_TAG.append((getattr(model, name), f"str:{name}"))


_FORMAT = common.XMLFormat(
    base_ns="http://www.sdmx.org/resources/sdmxml/schemas/v3_0", class_tag=_CLS_TAG
)


def __getattr__(name):
    return getattr(_FORMAT, name)
