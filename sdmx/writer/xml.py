"""SDMX-ML v2.1 writer."""
# Contents of this file are organized in the order:
#
# - Utility methods and global variables.
# - writer functions for sdmx.message classes, in the same order as message.py
# - writer functions for sdmx.model classes, in the same order as model.py

import logging
from pathlib import Path
from typing import IO, Iterable, List, Literal, Optional, cast

from lxml import etree
from lxml.builder import ElementMaker

import sdmx.urn
from sdmx import message
from sdmx.format.xml.v21 import NS, qname, tag_for_class
from sdmx.model import common
from sdmx.model import v21 as model
from sdmx.writer.base import BaseWriter

log = logging.getLogger(__name__)

_element_maker = ElementMaker(nsmap={k: v for k, v in NS.items() if v is not None})

writer = BaseWriter("XML")


def Element(name, *args, **kwargs):
    # Remove None
    kwargs = dict(filter(lambda kv: kv[1] is not None, kwargs.items()))

    return _element_maker(qname(name), *args, **kwargs)


def to_xml(obj, **kwargs):
    """Convert an SDMX *obj* to SDMX-ML.

    Parameters
    ----------
    kwargs
        Passed to :meth:`lxml.etree.to_string`, e.g. `pretty_print` = :obj:`True`.

    Raises
    ------
    NotImplementedError
        If writing specific objects to SDMX-ML has not been implemented in :mod:`sdmx`.
    """
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("xml_declaration", True)
    return etree.tostring(writer.recurse(obj), **kwargs)


def validate_xml(msg: Path | IO, schema_dir: Optional[Path] = None) -> bool:
    """Validate and SDMX message against the XML Schema (XSD) documents.

    The XML Schemas must first be installed or validation will fail. See
    :func:`sdmx.install_schemas` to download the schema files.

    Parameters
    ----------
    msg
        A SDMX-ML Message formatted XML file.
    schema_dir
        The directory to XSD schemas used to validate the message.

    Returns
    -------
    bool
        True if validation passed. False otherwise.
    """
    try:
        import platformdirs
    except ModuleNotFoundError as err:
        log.error(
            "Missing platformdirs. Re-install sdmx with pip install sdmx1[validation]"
        )
        raise err

    # If the user has no preference, get the schemas from the local cache directory
    if not schema_dir:
        schema_dir = platformdirs.user_cache_path("sdmx")

    msg_doc = etree.parse(msg)

    # Make sure the message is a supported type
    supported_elements = [
        "CodelistQuery",
        "DataStructureQuery",
        "GenericData",
        "GenericMetadata",
        "GenericTimeSeriesData",
        "MetadataStructureQuery",
        "Structure",
        "StructureSpecificData",
        "StructureSpecificMetadata",
        "StructureSpecificTimeSeriesData",
    ]
    root_elem_name = msg_doc.docinfo.root_name
    if root_elem_name not in supported_elements:
        raise NotImplementedError

    message_xsd = schema_dir.joinpath("SDMXMessage.xsd")
    if not message_xsd.exists():
        raise ValueError

    # Turn the XSD into a schema object
    xml_schema_doc = etree.parse(message_xsd)
    xml_schema = etree.XMLSchema(xml_schema_doc)

    return xml_schema.validate(msg_doc)
    # return xml_schema.assertValid(msg_doc)


def install_schemas(schema_dir: Optional[Path] = None) -> None:
    """Cache XML Schema documents locally for use during message validation.

    Parameters
    ----------
    schema_dir
        The directory where XSD schemas will be downloaded to.
    """
    import io
    import zipfile

    import platformdirs
    import requests

    # If the user has no preference, download the schemas to the local cache directory
    if not schema_dir:
        schema_dir = platformdirs.user_cache_path("sdmx")
    schema_dir.mkdir(exist_ok=True, parents=True)

    # Check the latest release to get the URL to the schema zip
    release_url = "https://api.github.com/repos/sdmx-twg/sdmx-ml-v2_1/releases/latest"
    gh_headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    resp = requests.get(url=release_url, headers=gh_headers)
    zipball_url = resp.json().get("zipball_url")

    # Download the zipped content and find the schemas within
    resp = requests.get(url=zipball_url, headers=gh_headers)
    zipped = zipfile.ZipFile(io.BytesIO(resp.content))
    schemas = [n for n in zipped.namelist() if "schemas" in n and n.endswith(".xsd")]

    # Extract the schemas to the destination directory
    # We can't use ZipFile.extract here because it will keep the directory structure
    for xsd in schemas:
        xsd_path = zipfile.Path(zipped, at=xsd)
        target = schema_dir.joinpath(xsd_path.name)
        target.write_text(xsd_path.read_text())


RefStyle = Literal["Ref", "URN"]


def reference(obj, parent=None, tag=None, style=None):
    """Write a reference to `obj`.

    .. todo:: Currently other functions in :mod:`.writer.xml` all pass the `style`
       argument to this function. As an enhancement, allow user or automatic selection
       of different reference styles.
    """
    tag = tag or tag_for_class(obj.__class__)

    elem = Element(tag)

    # assert style
    if style == "URN":
        ref = Element(":URN", obj.urn)
    elif style == "Ref":
        # Element attributes
        attrib = dict(id=obj.id)

        # Identify a maintainable artifact; either `obj` or its `parent`
        if isinstance(obj, model.MaintainableArtefact):
            ma = obj
            attrib.update(version=obj.version)
        else:
            try:
                # Get the ItemScheme for an Item
                parent = parent or obj.get_scheme()
            except AttributeError:  # pragma: no cover
                # No `parent` and `obj` is not an Item with a .get_scheme() method
                # NB this does not occur in the test suite
                pass

            if not parent:
                raise NotImplementedError(
                    f"Cannot write reference to {obj!r} without parent"
                )

            ma = parent
            attrib.update(
                maintainableParentVersion=ma.version,
                maintainableParentID=ma.id,
            )

        attrib.update(
            agencyID=getattr(ma.maintainer, "id", None),
            package=model.PACKAGE[type(ma).__name__],
        )

        # "class" attribute: either the type of `obj`, or the item type of an ItemScheme
        for candidate in (type(obj), getattr(type(ma), "_Item", None)):
            try:
                attrib["class"] = etree.QName(tag_for_class(candidate)).localname
                break
            except ValueError:
                pass

        ref = Element(":Ref", **attrib)

    elem.append(ref)
    return elem


# Writers for sdmx.message classes


@writer
def _dm(obj: message.DataMessage):
    struct_spec = len(obj.data) and isinstance(
        obj.data[0],
        (model.StructureSpecificDataSet, model.StructureSpecificTimeSeriesDataSet),
    )

    elem = Element("mes:StructureSpecificData" if struct_spec else "mes:GenericData")

    header = writer.recurse(obj.header)
    elem.append(header)

    # Set of DSDs already referenced in the header
    structures = set()

    for ds in obj.data:
        attrib = dict()
        dsd_ref = None

        # Add any new DSD reference to header
        if ds.structured_by and id(ds.structured_by) not in structures:
            attrib["structureID"] = ds.structured_by.id

            # Reference by URN if possible, otherwise with a <Ref> tag
            style: RefStyle = "URN" if ds.structured_by.urn else "Ref"
            dsd_ref = reference(ds.structured_by, tag="com:Structure", style=style)

            if isinstance(obj.observation_dimension, model.DimensionComponent):
                attrib["dimensionAtObservation"] = obj.observation_dimension.id

            header.append(Element("mes:Structure", **attrib))
            header[-1].append(dsd_ref)

            # Record this object so it is not added a second time
            structures.add(id(ds.structured_by))

        # Add data
        elem.append(writer.recurse(ds))

    if obj.footer:
        elem.append(writer.recurse(obj.footer))

    return elem


@writer
def _sm(obj: message.StructureMessage):
    # Store a reference to the overal Message for writing references
    setattr(writer, "_message", obj)

    elem = Element("mes:Structure")

    # Empty header element
    elem.append(writer.recurse(obj.header))

    structures = Element("mes:Structures")
    elem.append(structures)

    for attr, tag in [
        # Order is important here to avoid forward references
        ("organisation_scheme", "OrganisationSchemes"),
        ("dataflow", "Dataflows"),
        ("category_scheme", "CategorySchemes"),
        ("categorisation", "Categorisations"),
        ("codelist", "Codelists"),
        ("concept_scheme", "Concepts"),
        ("structure", "DataStructures"),
        ("constraint", "Constraints"),
        ("provisionagreement", "ProvisionAgreements"),
    ]:
        coll = getattr(obj, attr)
        if not len(coll):
            continue
        container = Element(f"str:{tag}")
        for s in filter(lambda s: not s.is_external_reference, coll.values()):
            container.append(writer.recurse(s))
        if len(container):
            structures.append(container)

    if obj.footer:
        elem.append(writer.recurse(obj.footer))

    return elem


@writer
def _em(obj: message.ErrorMessage):
    elem = Element("mes:Error")
    elem.append(writer.recurse(obj.header))

    if obj.footer:
        elem.append(writer.recurse(obj.footer))

    return elem


@writer
def _header(obj: message.Header):
    elem = Element("mes:Header")
    if obj.id:
        elem.append(Element("mes:ID", obj.id))
    elem.append(Element("mes:Test", str(obj.test).lower()))
    if obj.prepared:
        elem.append(Element("mes:Prepared", obj.prepared.isoformat()))
    if obj.sender:
        elem.append(writer.recurse(obj.sender, _tag="mes:Sender"))
    if obj.receiver:
        elem.append(writer.recurse(obj.receiver, _tag="mes:Receiver"))
    if obj.source:
        elem.extend(i11lstring(obj.source, "mes:Source"))
    return elem


@writer
def _footer(obj: message.Footer):
    elem = Element("footer:Footer")

    attrs = dict()
    if obj.code:
        attrs["code"] = str(obj.code)
    if obj.severity:
        attrs["severity"] = str(obj.severity)

    mes = Element("footer:Message", **attrs)
    elem.append(mes)

    for text in obj.text:
        mes.extend(i11lstring(text, "com:Text"))

    return elem


# Writers for sdmx.model classes
# §3.2: Base structures


def i11lstring(obj, name) -> List[etree._Element]:
    """InternationalString.

    Returns a list of elements with name `name`.
    """
    elems = []

    for locale, label in obj.localizations.items():
        child = Element(name, label)
        child.set(qname("xml", "lang"), locale)
        elems.append(child)

    return elems


@writer
def _a(obj: model.Annotation):
    elem = Element("com:Annotation")
    if obj.id:
        elem.attrib["id"] = obj.id
    if obj.title:
        elem.append(Element("com:AnnotationTitle", obj.title))
    if obj.type:
        elem.append(Element("com:AnnotationType", obj.type))
    elem.extend(i11lstring(obj.text, "com:AnnotationText"))
    return elem


def annotable(obj, *args, **kwargs) -> etree._Element:
    # Determine tag
    tag = kwargs.pop("_tag", tag_for_class(obj.__class__))

    # Write Annotations
    e_anno = Element("com:Annotations", *[writer.recurse(a) for a in obj.annotations])
    if len(e_anno):
        args = args + (e_anno,)

    try:
        return Element(tag, *args, **kwargs)
    except AttributeError:  # pragma: no cover
        print(repr(obj), tag, kwargs)
        raise


def identifiable(obj, *args, **kwargs) -> etree._Element:
    """Write :class:`.IdentifiableArtefact`.

    Unless the keyword argument `_with_urn` is :data:`False`, a URN is generated for
    objects lacking one, and forwarded to :func:`annotable`
    """
    kwargs.setdefault("id", obj.id)
    try:
        with_urn = kwargs.pop("_with_urn", True)
        urn = obj.urn or (
            sdmx.urn.make(obj, kwargs.pop("parent", None)) if with_urn else None
        )
        if urn:
            kwargs.setdefault("urn", urn)
    except (AttributeError, ValueError):
        pass
    return annotable(obj, *args, **kwargs)


def nameable(obj, *args, **kwargs) -> etree._Element:
    return identifiable(
        obj,
        *i11lstring(obj.name, "com:Name"),
        *i11lstring(obj.description, "com:Description"),
        *args,
        **kwargs,
    )


def maintainable(obj, *args, **kwargs) -> etree._Element:
    kwargs.setdefault("version", obj.version)
    kwargs.setdefault("isExternalReference", str(obj.is_external_reference).lower())
    kwargs.setdefault("isFinal", str(obj.is_final).lower())
    kwargs.setdefault("agencyID", getattr(obj.maintainer, "id", None))
    return nameable(obj, *args, **kwargs)


# §3.5: Item Scheme


@writer
def _item(obj: model.Item, **kwargs):
    elem = nameable(obj, **kwargs)

    if isinstance(obj.parent, obj.__class__):
        # Reference to parent Item
        e_parent = Element("str:Parent")
        e_parent.append(Element(":Ref", id=obj.parent.id, style="Ref"))
        elem.append(e_parent)

    if isinstance(obj, common.Organisation):
        elem.extend(writer.recurse(c) for c in obj.contact)

    return elem


@writer
def _is(obj: model.ItemScheme):
    elem = maintainable(obj)

    # Pass _with_urn to identifiable(): don't generate URNs for Items in `obj` which do
    # not already have them
    elem.extend(writer.recurse(i, _with_urn=False) for i in obj.items.values())
    return elem


# §3.6: Structure


@writer
def _facet(obj: model.Facet):
    # TODO textType should be CamelCase
    return Element("str:TextFormat", textType=getattr(obj.value_type, "name", None))


@writer
def _rep(obj: common.Representation, tag, style="URN"):
    elem = Element(f"str:{tag}")
    if obj.enumerated is not None:
        elem.append(reference(obj.enumerated, tag="str:Enumeration", style=style))
    if obj.non_enumerated:
        elem.extend(writer.recurse(facet) for facet in obj.non_enumerated)
    return elem


# §4.4: Concept Scheme


@writer
def _concept(obj: model.Concept, **kwargs):
    elem = _item(obj, **kwargs)

    if obj.core_representation:
        elem.append(writer.recurse(obj.core_representation, "CoreRepresentation"))

    return elem


# §4.6: Organisations


@writer
def _contact(obj: model.Contact):
    elem = Element("str:Contact")
    elem.extend(
        i11lstring(obj.name, "com:Name")
        + i11lstring(obj.org_unit, "str:Department")
        + i11lstring(obj.responsibility, "str:Role")
        + ([Element("str:Telephone", obj.telephone)] if obj.telephone else [])
        + [Element("str:URI", text=value) for value in obj.uri]
        + [Element("str:Email", text=value) for value in obj.email]
    )
    return elem


# §3.3: Basic Inheritance


@writer
def _component(obj: model.Component, dsd):
    child = []
    attrib = dict()

    try:
        child.append(
            reference(obj.concept_identity, tag="str:ConceptIdentity", style="Ref")
        )
    except AttributeError:  # pragma: no cover
        pass  # concept_identity is None

    try:
        child.append(
            writer.recurse(obj.local_representation, "LocalRepresentation", style="Ref")
        )
    except NotImplementedError:
        pass  # None

    if isinstance(obj, model.DataAttribute) and obj.usage_status:
        child.append(writer.recurse(obj.related_to, dsd))

        # assignmentStatus attribute
        if obj.usage_status:
            attrib["assignmentStatus"] = obj.usage_status.name.title()
    elif isinstance(obj, model.Dimension):
        # position attribute
        attrib["position"] = str(obj.order)

    return identifiable(obj, *child, **attrib)


@writer
def _cl(obj: model.ComponentList, *args):
    elem = identifiable(obj)
    elem.extend(writer.recurse(c, *args) for c in obj.components)
    return elem


# §4.5: CategoryScheme


@writer
def _cat(obj: model.Categorisation):
    elem = maintainable(obj)
    elem.extend(
        [
            reference(obj.artefact, tag="str:Source", style="Ref"),
            reference(obj.category, tag="str:Target", style="Ref"),
        ]
    )
    return elem


# §10.3: Constraints


@writer
def _dk(obj: model.DataKey):
    elem = Element("str:Key", isIncluded=str(obj.included).lower())
    for value_for, cv in obj.key_value.items():
        elem.append(Element("com:KeyValue", id=value_for.id))
        elem[-1].append(Element("com:Value", cv.value))
    return elem


@writer
def _dks(obj: model.DataKeySet):
    elem = Element("str:DataKeySet", isIncluded=str(obj.included).lower())
    elem.extend(writer.recurse(dk) for dk in obj.keys)
    return elem


@writer
def _ms(obj: model.MemberSelection):
    tag = {
        model.Dimension: "KeyValue",
        model.DataAttribute: "Attribute",
    }[type(obj.values_for)]

    elem = Element(f"com:{tag}", id=obj.values_for.id)
    elem.extend(
        # cast(): as of PR#30, only MemberValue is supported here
        Element("com:Value", cast(model.MemberValue, mv).value)
        for mv in obj.values
    )
    return elem


@writer
def _cr(obj: model.CubeRegion):
    elem = Element("str:CubeRegion", include=str(obj.included).lower())
    elem.extend(writer.recurse(ms) for ms in obj.member.values())
    return elem


@writer
def _cc(obj: model.ContentConstraint):
    assert obj.role is not None
    elem = maintainable(
        obj, type=obj.role.role.name.replace("allowable", "allowed").title()
    )

    # Constraint attachment: written before data_content_keys or data_content_region
    for ca in obj.content:
        elem.append(Element("str:ConstraintAttachment"))
        elem[-1].append(reference(ca, style="Ref"))

    # NB this is a property of Constraint, not ContentConstraint, so the code should be
    #    copied/reused for AttachmentConstraint.
    if obj.data_content_keys is not None:
        elem.append(writer.recurse(obj.data_content_keys))

    elem.extend(writer.recurse(dcr) for dcr in obj.data_content_region)

    return elem


# §5.2: Data Structure Definition


@writer
def _nsr(obj: model.NoSpecifiedRelationship, *args):
    elem = Element("str:AttributeRelationship")
    elem.append(Element("str:None"))
    return elem


@writer
def _pmr(obj: model.PrimaryMeasureRelationship, dsd: model.DataStructureDefinition):
    elem = Element("str:AttributeRelationship")
    elem.append(Element("str:PrimaryMeasure"))
    try:
        ref_id = dsd.measures[0].id
    except IndexError:
        ref_id = "(not implemented)"  # MeasureDescriptor is empty
    elem[-1].append(Element(":Ref", id=ref_id))
    return elem


@writer
def _dr(obj: common.DimensionRelationship, *args):
    elem = Element("str:AttributeRelationship")
    for dim in obj.dimensions:
        elem.append(Element("str:Dimension"))
        elem[-1].append(Element(":Ref", id=dim.id))
    return elem


@writer
def _gr(obj: common.GroupRelationship, *args):
    elem = Element("str:AttributeRelationship")
    elem.append(Element("str:Group"))
    elem[-1].append(Element(":Ref", id=getattr(obj.group_key, "id", None)))
    return elem


@writer
def _gdd(obj: model.GroupDimensionDescriptor):
    elem = identifiable(obj)
    for dim in obj.components:
        elem.append(Element("str:GroupDimension"))
        elem[-1].append(Element("str:DimensionReference"))
        elem[-1][0].append(Element(":Ref", id=dim.id))
    return elem


@writer
def _dsd(obj: model.DataStructureDefinition):
    elem = maintainable(obj)
    elem.append(Element("str:DataStructureComponents"))

    # Write in a specific order
    elem[-1].append(writer.recurse(obj.dimensions, None))
    for group in obj.group_dimensions.values():
        elem[-1].append(writer.recurse(group))
    elem[-1].append(writer.recurse(obj.attributes, obj))
    elem[-1].append(writer.recurse(obj.measures, None))

    return elem


@writer
def _dfd(obj: model.DataflowDefinition):
    elem = maintainable(obj)
    elem.append(reference(obj.structure, tag="str:Structure", style="Ref"))
    return elem


# §5.4: Data Set


def _av(name: str, obj: Iterable[model.AttributeValue]):
    elements = []
    for av in obj:
        assert av.value_for
        elements.append(Element("gen:Value", id=av.value_for.id, value=av.value))
    return Element(name, *elements)


def _kv(name: str, obj: Iterable[model.KeyValue]):
    elements = []
    for kv in obj:
        assert kv.value_for
        elements.append(Element("gen:Value", id=kv.value_for.id, value=str(kv.value)))
    return Element(name, *elements)


@writer
def _sk(obj: model.SeriesKey):
    elem = []

    elem.append(_kv("gen:SeriesKey", obj))
    if len(obj.attrib):
        elem.append(_av("gen:Attributes", obj.attrib.values()))

    return tuple(elem)


@writer
def _obs(obj: model.Observation, struct_spec=False):
    if struct_spec:
        obs_attrs = {}
        for key, av in obj.attached_attribute.items():
            obs_attrs[key] = str(av.value)
        if obj.value is not None:
            if obj.value_for is None:
                raise ValueError(
                    "Observation.value_for is None when writing structure-specific data"
                )
            # NB this is usually OBS_VALUE, but not necessarily; see #67.
            value_key = obj.value_for.id
            obs_attrs[value_key] = str(obj.value)
        if obj.dimension:
            for key, dv in obj.dimension.values.items():
                obs_attrs[key] = str(dv.value)

        return Element(":Obs", **obs_attrs)

    elem = Element("gen:Obs")

    if obj.dimension:
        if len(obj.dimension) == 1:
            # Observation in a series; at most one dimension given by the Key
            elem.append(
                Element("gen:ObsDimension", value=obj.dimension.values[0].value)
            )
        else:
            # Top-level observation, not associated with a SeriesKey
            elem.append(_kv("gen:ObsKey", obj.dimension))

    elem.append(Element("gen:ObsValue", value=str(obj.value)))

    if len(obj.attached_attribute):
        elem.append(_av("gen:Attributes", obj.attached_attribute.values()))

    return elem


@writer
def _ds(obj: model.DataSet):
    if len(obj.group):
        raise NotImplementedError("to_xml() for DataSet with groups")

    attrib = dict()
    if obj.action:
        attrib["action"] = str(obj.action)
    if obj.structured_by:
        attrib["structureRef"] = obj.structured_by.id
    elem = Element("mes:DataSet", **attrib)

    # AttributeValues attached to the data set
    if len(obj.attrib):
        elem.append(_av("gen:Attributes", obj.attrib.values()))

    obs_to_write = set(map(id, obj.obs))

    struct_spec = isinstance(
        obj, (model.StructureSpecificDataSet, model.StructureSpecificTimeSeriesDataSet)
    )

    for sk, observations in obj.series.items():
        if struct_spec:
            series_attrs = {}
            for key, sk_dim in sk.values.items():
                series_attrs[key] = str(sk_dim.value)
            for key, sk_att in sk.attrib.items():
                series_attrs[key] = str(sk_att.value)
            elem.append(Element(":Series", **series_attrs))
        else:
            elem.append(Element("gen:Series"))
            elem[-1].extend(writer.recurse(sk))
        elem[-1].extend(
            writer.recurse(obs, struct_spec=struct_spec) for obs in observations
        )
        obs_to_write -= set(map(id, observations))

    # Observations not in any series
    for obs in filter(lambda o: id(o) in obs_to_write, obj.obs):
        elem.append(writer.recurse(obs, struct_spec=struct_spec))

    return elem
