"""Information about the SDMX-ML 2.1 file format."""
from sdmx import message
from sdmx.model import v21 as model

from .common import XMLFormat

# Correspondence of message and model classes with XML tag names

_CLS_TAG = []
for c, t in (
    (message.DataMessage, "mes:GenericData"),
    (message.DataMessage, "mes:GenericTimeSeriesData"),
    (message.DataMessage, "mes:StructureSpecificData"),
    (message.DataMessage, "mes:StructureSpecificTimeSeriesData"),
    (message.ErrorMessage, "mes:Error"),
    (message.StructureMessage, "mes:Structure"),
    (model.Agency, "str:Agency"),  # Order matters
    (model.Agency, "mes:Receiver"),
    (model.Agency, "mes:Sender"),
    (model.AttributeDescriptor, "str:AttributeList"),
    (model.DataAttribute, "str:Attribute"),
    (model.DataflowDefinition, "str:Dataflow"),
    (model.DataStructureDefinition, "str:DataStructure"),
    (model.DataStructureDefinition, "com:Structure"),
    (model.DataStructureDefinition, "str:Structure"),
    (model.DimensionDescriptor, "str:DimensionList"),
    (model.GroupDimensionDescriptor, "str:Group"),
    (model.GroupDimensionDescriptor, "str:AttachmentGroup"),
    (model.GroupKey, "gen:GroupKey"),
    (model.Key, "gen:ObsKey"),
    (model.MeasureDescriptor, "str:MeasureList"),
    (model.MetadataflowDefinition, "str:Metadataflow"),
    (model.MetadataStructureDefinition, "str:MetadataStructure"),
    (model.SeriesKey, "gen:SeriesKey"),
):
    _CLS_TAG.append((c, t))


for name in (
    "ContentConstraint",
    "MeasureDimension",
    "PrimaryMeasure",
):
    _CLS_TAG.append((getattr(model, name), f"str:{name}"))

_FORMAT = XMLFormat(
    base_ns="http://www.sdmx.org/resources/sdmxml/schemas/v2_1", class_tag=_CLS_TAG
)


def __getattr__(name):
    return getattr(_FORMAT, name)
