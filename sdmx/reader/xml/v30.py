"""SDMX-ML 3.0.0 reader."""
from typing import Any, Dict

import sdmx.urn
from sdmx.format import Version, list_media_types
from sdmx.model import common
from sdmx.model import v30 as model

from . import v21


class Reference(v21.Reference):
    @classmethod
    def info_from_element(cls, elem):
        try:
            result = sdmx.urn.match(elem.text)
            # If the URN doesn't specify an item ID, it is probably a reference to a
            # MaintainableArtefact, so target_id and id are the same
            result.update(target_id=result["item_id"] or result["id"])
        except ValueError:
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
    str:GeographicCodelists str:GeoGridCodelists str:NamePersonalisationSchemes
    str:RulesetSchemes str:TransformationSchemes str:UserDefinedOperatorSchemes
    str:ValueLists str:VtlMappingSchemes
    """
)(None)

# New qnames in SDMX-ML 3.0 parsed using existing methods from .reader.xml.v21
end("str:GeoCell str:GridDefinition")(v21._text)
end("str:GeographicCodelist str:ValueList")(v21._itemscheme)
start("str:GeoFeatureSetCode str:GeoGridCode str:ValueItem", only=False)(
    v21._item_start
)
end("str:GeoFeatureSetCode str:GeoGridCode str:ValueItem", only=False)(v21._item_end)
end("str:Measure")(v21._component)


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
    return model.CodelistExtension(
        codelist=reader.pop_resolved_ref("Codelist"),
        mv=reader.pop_all(model.MemberValue),
    )


@end("str:ExclusiveCodeSelection str:InclusiveCodeSelection")
def _code_selection(reader, elem):
    raise NotImplementedError


@end("str:MemberValue")
def _mv(reader, elem):
    return common.MemberValue(value=elem.text)


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
