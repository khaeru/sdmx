"""SDMX-ML 3.0.0 reader."""
from itertools import product

import sdmx.urn
from sdmx.format import Version, list_media_types
from sdmx.model import common
from sdmx.model import v30 as model

from . import v21

_VERSION = Version["3.0.0"]

# In SDMX-ML 3.0, individual classes of ItemScheme are collected in separate XML
# container elements. Skip all of these.
SKIP = """
    str:AgencySchemes str:ConceptSchemes str:CustomTypeSchemes str:GeographicCodelists
    str:GeoGridCodelists str:NamePersonalisationSchemes str:RulesetSchemes
    str:TransformationSchemes str:UserDefinedOperatorSchemes str:ValueLists
    str:VtlMappingSchemes
"""


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
    media_types = list_media_types(base="xml", version=_VERSION)
    xml_version = _VERSION
    Reference = Reference


v21.PARSE.update({k: None for k in product(v21.to_tags(SKIP), ["start", "end"])})


v21.end("str:GeoCell str:GridDefinition")(v21._text)
v21.end("str:GeographicCodelist str:ValueList")(v21._itemscheme)
v21.start("str:GeoFeatureSetCode str:GeoGridCode str:ValueItem", only=False)(
    v21._item_start
)
v21.end("str:GeoFeatureSetCode str:GeoGridCode str:ValueItem", only=False)(v21._item)


@v21.end("str:Codelist")
def _cl(reader, elem):
    try:
        sdmx.urn.match(elem.text)
    except ValueError:
        result = v21._itemscheme(reader, elem)
        result.extends = reader.pop_all(model.CodelistExtension)
        return result
    else:
        reader.push(elem, elem.text)


@v21.end("str:CodelistExtension")
def _cl_ext(reader, elem):
    return model.CodelistExtension(
        codelist=reader.pop_resolved_ref("Codelist"),
        mv=reader.pop_all(model.MemberValue),
    )


@v21.end("str:ExclusiveCodeSelection str:InclusiveCodeSelection")
def _code_selection(reader, elem):
    print(elem)


@v21.end("str:MemberValue")
def _mv(reader, elem):
    return common.MemberValue(value=elem.text)


@v21.end("str:GeoGridCodelist")
def _ggcl(reader, elem):
    result = v21._itemscheme(reader, elem)
    result.grid_definition = reader.pop_single("GridDefinition")
    return result


@v21.end("str:GeoGridCode", only=False)
def _ggc_end(reader, elem):
    result = v21._item(reader, elem)
    result.geo_cell = reader.pop_single("GeoCell")
    return result
