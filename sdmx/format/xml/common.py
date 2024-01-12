import logging
import re
from functools import lru_cache
from itertools import chain
from operator import itemgetter
from pathlib import Path
from typing import IO, Iterable, List, Mapping, Optional, Tuple, Union

from lxml import etree
from lxml.etree import QName

log = logging.getLogger(__name__)

# Tags common to SDMX-ML 2.1 and 3.0

# XML tag name ("str" namespace) and class name are the same
CT1 = [
    "Agency",
    "AgencyScheme",
    "Categorisation",
    "Category",
    "CategoryScheme",
    "Code",
    "Codelist",
    "Concept",
    "ConceptScheme",
    "CustomType",
    "CustomTypeScheme",
    "DataConsumer",
    "DataConsumerScheme",
    "DataProvider",
    "DataProviderScheme",
    "HierarchicalCode",
    "Level",
    "NamePersonalisation",
    "NamePersonalisationScheme",
    "Ruleset",
    "RulesetScheme",
    "TimeDimension",
    "TransformationScheme",
    "UserDefinedOperatorScheme",
]

# XML tag name and class name differ
CT2 = [
    ("model.Agency", "str:Agency"),  # Order matters
    ("model.Agency", "mes:Receiver"),
    ("model.Agency", "mes:Sender"),
    ("model.AttributeDescriptor", "str:AttributeList"),
    ("model.Concept", "str:ConceptIdentity"),
    ("model.Codelist", "str:Enumeration"),  # This could possibly be ItemScheme
    ("model.Dimension", "str:Dimension"),  # Order matters
    ("model.Dimension", "str:DimensionReference"),
    ("model.Dimension", "str:GroupDimension"),
    ("model.DataAttribute", "str:Attribute"),
    ("model.DataStructureDefinition", "str:DataStructure"),
    ("model.DimensionDescriptor", "str:DimensionList"),
    ("model.GroupDimensionDescriptor", "str:Group"),
    ("model.GroupDimensionDescriptor", "str:AttachmentGroup"),
    ("model.GroupKey", "gen:GroupKey"),
    ("model.Key", "gen:ObsKey"),
    ("model.MeasureDescriptor", "str:MeasureList"),
    ("model.MetadataStructureDefinition", "str:MetadataStructure"),
    ("model.SeriesKey", "gen:SeriesKey"),
    ("model.Structure", "com:Structure"),
    ("model.Structure", "str:Structure"),
    ("model.StructureUsage", "com:StructureUsage"),
    ("model.VTLMappingScheme", "str:VtlMappingScheme"),
    # Message classes
    ("message.DataMessage", "mes:StructureSpecificData"),
    ("message.MetadataMessage", "mes:GenericMetadata"),
    ("message.MetadataMessage", "mes:StructureSpecificMetadata"),
    ("message.ErrorMessage", "mes:Error"),
    ("message.StructureMessage", "mes:Structure"),
]

NS = {
    "": None,
    "xml": "http://www.w3.org/XML/1998/namespace",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    # To be formatted
    "com": "{}/common",
    "md": "{}/metadata/generic",
    "data": "{}/data/structurespecific",
    "str": "{}/structure",
    "mes": "{}/message",
    "gen": "{}/data/generic",
    "footer": "{}/message/footer",
}


def validate_xml(msg: Union[Path, IO], schema_dir: Optional[Path] = None) -> bool:
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
    import platformdirs

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

    try:
        xml_schema.assertValid(msg_doc)
    except etree.DocumentInvalid as err:
        log.error(err)
    finally:
        return xml_schema.validate(msg_doc)


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
        "X-GitHub-Api-Version": "2022-11-28",
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


class XMLFormat:
    NS: Mapping[str, Optional[str]]
    _class_tag: List

    def __init__(self, model, base_ns: str, class_tag: Iterable[Tuple[str, str]]):
        from sdmx import message  # noqa: F401

        self.base_ns = base_ns

        # Construct name spaces
        self.NS = {
            prefix: url if url is None else url.format(base_ns)
            for prefix, url in NS.items()
        }

        # Construct class-tag mapping
        self._class_tag = []

        # Defined in this file
        for name in CT1:
            self._class_tag.append((getattr(model, name), self.qname("str", name)))

        # Defined in this file + those passed to the constructor
        for expr, tag in chain(CT2, class_tag):
            self._class_tag.append((eval(expr), self.qname(tag)))

    @lru_cache()
    def ns_prefix(self, url) -> str:
        """Return the namespace prefix from :attr:`.NS` given its full `url`."""
        for prefix, _url in self.NS.items():
            if url == _url:
                return prefix
        raise ValueError(url)

    @lru_cache()
    def qname(self, ns_or_name, name=None) -> QName:
        """Return a fully-qualified tag `name` in namespace `ns`."""
        if isinstance(ns_or_name, QName):
            # Already a QName; do nothing
            return ns_or_name
        else:
            if name is None:
                match = re.fullmatch(
                    r"(\{(?P<ns_full>.*)\}|(?P<ns_key>.*):)?(?P<name>.*)", ns_or_name
                )
                assert match
                name = match.group("name")
                if ns_key := match.group("ns_key"):
                    ns = self.NS[ns_key]
                elif ns := match.group("ns_full"):
                    pass
                else:
                    ns = None
            else:
                ns = self.NS[ns_or_name]

            return QName(ns, name)

    @lru_cache()
    def class_for_tag(self, tag) -> Optional[type]:
        """Return a message or model class for an XML tag."""
        qname = self.qname(tag)
        results = map(itemgetter(0), filter(lambda ct: ct[1] == qname, self._class_tag))
        try:
            return next(results)
        except StopIteration:
            return None

    @lru_cache()
    def tag_for_class(self, cls):
        """Return an XML tag for a message or model class."""
        results = map(itemgetter(1), filter(lambda ct: ct[0] is cls, self._class_tag))
        try:
            return next(results)
        except StopIteration:
            return None

    # __eq__ and __hash__ to enable lru_cache()
    def __eq__(self, other):
        return self.base_ns == other.base_ns  # pragma: no cover

    def __hash__(self):
        return hash(self.base_ns)
