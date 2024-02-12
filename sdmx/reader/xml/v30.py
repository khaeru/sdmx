"""SDMX-ML 3.0.0 reader."""
from typing import Any, Dict

import sdmx.urn
from sdmx.format import Version, list_media_types
from sdmx.model import common
from sdmx.model import v30 as model

from . import v21


class Reference(v21.Reference):
    """Parse SDMX-ML 3.0 references."""

    @classmethod
    def info_from_element(cls, elem):
        try:
            result = sdmx.urn.match(elem.text)
            # If the URN doesn't specify an item ID, it is probably a reference to a
            # MaintainableArtefact, so target_id and id are the same
            result.update(target_id=result["item_id"] or result["id"])
        except ValueError:
            # Bare string that is the ID of e.g. a component (dimension)
            if id := (elem.text or "").strip():
                result = {"id": id, "target_id": id, "class": None, "package": None}
            else:
                raise v21.NotReference

        return result


class Reader(v21.Reader):
    xml_version = Version["3.0.0"]
    media_types = list_media_types(base="xml", version=xml_version)
    Reference = Reference


# Rewrite the v21.Reader collection of parsers to refer to SDMX-ML 3.0.0 namespaces
# instead of SDMX-ML 2.1
new_parsers = dict()
for (tag, event), func in v21.Reader.parser.items():
    # Construct a new tag using the same prefix (e.g. "str") and local name
    new_tag = Reader.format.qname(
        v21.Reader.format.ns_prefix(tag.namespace), tag.localname
    )
    # Store a reference to the same function
    new_parsers[(new_tag, event)] = func
# Replace the parser collection
Reader.parser = new_parsers

# Shorthand
start = Reader.start
end = Reader.end

# In SDMX-ML 3.0, individual classes of ItemScheme are collected in separate XML
# container elements. Skip all of these.
start(
    """
    str:AgencySchemes str:ConceptSchemes str:CustomTypeSchemes str:DataConstraints
    str:GeographicCodelists str:GeoGridCodelists str:Hierarchies
    str:NamePersonalisationSchemes str:RulesetSchemes str:TransformationSchemes
    str:UserDefinedOperatorSchemes str:ValueLists str:VtlMappingSchemes
    """
)(None)

# New qnames in SDMX-ML 3.0 parsed using existing methods from .reader.xml.v21
end("str:GeoCell str:GridDefinition str:Value")(v21._text)
end("str:GeographicCodelist str:ValueList")(v21._itemscheme)
start("str:GeoFeatureSetCode str:GeoGridCode str:ValueItem", only=False)(
    v21._item_start
)
end("str:GeoFeatureSetCode str:GeoGridCode str:ValueItem", only=False)(v21._item_end)
start("str:Measure str:MetadataAttribute", only=False)(v21._component_start)
end("str:Measure str:MetadataAttribute", only=False)(v21._component_end)
end("str:MetadataAttributeList")(v21._cl)
end("str:DataConstraint")(v21._cc)
end("str:KeyValue")(v21._ms)
end("str:Observation")(v21._ar_kind)


@end("str:Codelist")
def _cl(reader, elem):
    try:
        sdmx.urn.match(elem.text)
    except ValueError:
        result = v21._itemscheme(reader, elem)
        result.extends = reader.pop_all(model.CodelistExtension)
        return result
    else:
        reader.push(elem, elem.text)


@end("str:CodelistExtension")
def _cl_ext(reader, elem):
    cs = reader.pop_all(model.CodeSelection, subclass=True) or [None]
    assert 1 == len(cs)
    return model.CodelistExtension(
        extends=reader.pop_resolved_ref("Codelist"),
        prefix=elem.attrib.get("prefix", None),
        selection=cs[0],
    )


@end("str:ExclusiveCodeSelection str:InclusiveCodeSelection")
def _code_selection(reader, elem):
    return reader.class_for_tag(elem.tag)(mv=reader.pop_all(model.MemberValue))


@end("str:MemberValue")
def _mv(reader, elem):
    return reader.model.MemberValue(value=elem.text)


@end("str:GeoGridCodelist")
def _ggcl(reader, elem):
    result = v21._itemscheme(reader, elem)
    result.grid_definition = reader.pop_single("GridDefinition")
    return result


@end("str:GeoGridCode", only=False)
def _ggc_end(reader, elem):
    result = v21._item_end(reader, elem)
    result.geo_cell = reader.pop_single("GeoCell")
    return result


# §5.3: Data Structure Definition


@end("str:AttributeRelationship")
def _ar(reader: Reader, elem):
    dsd = reader.peek("current DSD")

    refs = reader.pop_all(reader.Reference)
    if not len(refs):
        return

    # Iterate over parsed references to Components
    args: Dict[str, Any] = dict(dimensions=list())
    for ref in refs:
        # Use the <Ref id="..."> to retrieve a Component from the DSD
        if issubclass(ref.target_cls, model.DimensionComponent):
            component = dsd.dimensions.get(ref.target_id)
            args["dimensions"].append(component)
        elif ref.target_cls is model.Measure:
            # Since <str:AttributeList> occurs before <str:MeasureList>, this is
            # usually a forward reference. We *could* eventually resolve it to confirm
            # consistency (the referenced ID is same as the PrimaryMeasure.id), but
            # that doesn't affect the returned value, since PrimaryMeasureRelationship
            # has no attributes.
            return model.ObservationRelationship()
        elif ref.target_cls is model.GroupDimensionDescriptor:
            args["group_key"] = dsd.group_dimensions[ref.target_id]

    ref = reader.pop_single("AttachmentGroup")
    if ref:
        args["group_key"] = dsd.group_dimensions[ref.target_id]

    if len(args["dimensions"]):
        return common.DimensionRelationship(**args)


# §5.4: Data Set


@end(":Value")
def _complex_value(reader: Reader, elem):
    try:
        reader.push("ComplexValue", model.InternationalString(reader.pop_all("Text")))
    except Exception:  # pragma: no cover
        raise NotImplementedError


@end(":Comp")
def _complex(reader: Reader, elem):
    ds = reader.get_single("DataSet")

    assert ds is not None
    da = ds.structured_by.attributes.getdefault(elem.attrib["id"])

    reader.stack.setdefault("Attributes", {-1: {}})

    reader.stack["Attributes"][-1][da.id] = model.AttributeValue(
        value=reader.pop_all("ComplexValue"), value_for=da
    )


# §8: Hierarchy


@end("str:Hierarchy")
def _h(reader: Reader, elem):
    cls = reader.class_for_tag(elem.tag)
    return reader.maintainable(
        cls,
        elem,
        has_formal_levels=eval(elem.attrib["hasFormalLevels"].title()),
        codes={c.id: c for c in reader.pop_all(model.HierarchicalCode)},
        level=reader.pop_single(common.Level),
    )
