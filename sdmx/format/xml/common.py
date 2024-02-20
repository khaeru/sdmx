import logging
import re
import zipfile
from functools import lru_cache
from itertools import chain
from operator import itemgetter
from pathlib import Path
from shutil import copytree
from typing import IO, Iterable, List, Mapping, Optional, Tuple, Union

from lxml import etree
from lxml.etree import QName

from sdmx.format import Version

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
    ("model.Annotation", "com:Annotation"),
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


def validate_xml(
    msg: Union[Path, IO],
    schema_dir: Optional[Path] = None,
    version: Union[str, Version] = Version["2.1"],
) -> bool:
    """Validate and SDMX message against the XML Schema (XSD) documents.

    The XML Schemas must first be installed or validation will fail. See
    :func:`sdmx.install_schemas` to download the schema files.

    Parameters
    ----------
    msg
        A SDMX-ML Message formatted XML file.
    schema_dir
        The directory to XSD schemas used to validate the message.
    version
        The SDMX-ML schema version to validate against. One of ``2.1`` or ``3.0``.

    Returns
    -------
    bool
        True if validation passed. False otherwise.
    """
    schema_dir, version = _handle_validate_args(schema_dir, version)

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
        raise ValueError(f"Could not find XSD files in {schema_dir}")

    # Turn the XSD into a schema object
    xml_schema_doc = etree.parse(message_xsd)
    xml_schema = etree.XMLSchema(xml_schema_doc)

    try:
        xml_schema.assertValid(msg_doc)
    except etree.DocumentInvalid as err:
        log.error(err)
    finally:
        return xml_schema.validate(msg_doc)


def _extracted_zipball(version: Version) -> Path:
    """Retrieve, cache, and extract the SDMX-ML schemas for `version`.

    1. Query the GitHub REST API to identify a URL for the `version` in zipball format.
    2. Download and cache the zipball. The file is not downloaded if it already exists.
    3. Unpack the archive.

    Actions (2) and (3) are performed in the user's cache directory (for instance,
    :file:`$HOME/.cache/sdmx/`). :func:`install_schemas` handles copying the extracted
    files to other locations.

    Returns
    -------
    Path
        Path to the root folder of the unpacked archive.
    """
    import platformdirs
    import requests

    # Map SDMX-ML schema versions to repo paths
    # Check the latest release to get the URL to the schema zip
    url = (
        "https://api.github.com/repos/sdmx-twg/sdmx-ml/releases/tags/"
        + {Version["2.1"]: "v2.1", Version["3.0.0"]: "v3.0.0"}[version]
    )
    gh_headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    release_json = requests.get(url=url, headers=gh_headers).json()
    try:
        zipball_url = release_json["zipball_url"]
    except KeyError:  # pragma: no cover
        log.debug(release_json)
        raise RuntimeError("Failed to download SDMX-ML schema bundle")

    # Make a request for the zipball
    resp = requests.get(url=zipball_url, headers=gh_headers)

    # Filename indicated by the HTTP response
    filename = resp.headers["content-disposition"].split("filename=")[-1]
    # Location for the cached zipball
    target = platformdirs.user_cache_path("sdmx").joinpath(filename)

    # Avoid downloading if the same file is already present
    if target.exists():
        log.info(f"Use existing {target}")
        resp.close()
    else:
        # Write response content to file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(resp.content)

    with zipfile.ZipFile(target) as zf:
        # Unpack the entire archive
        zf.extractall(target.parent)
        # The first name list is the top-level directory within the file
        subdir = zf.namelist()[0]

    return target.parent.joinpath(subdir)


def _handle_validate_args(
    schema_dir: Optional[Path], version: Union[str, Version]
) -> Tuple[Path, Version]:
    """Handle arguments for :func:`.install_schemas` and :func:`.validate_xml`."""
    import platformdirs

    supported = {Version["2.1"], Version["3.0.0"]}
    try:
        version = Version[version] if isinstance(version, str) else version
        assert version in supported
    except (AssertionError, KeyError):
        raise NotImplementedError(
            f"SDMX-ML version must be one of {supported}; got {version}"
        ) from None

    # If the user has no preference, download the schemas to the local cache directory
    if not schema_dir:
        schema_dir = platformdirs.user_cache_path("sdmx") / version.name
    schema_dir.mkdir(exist_ok=True, parents=True)

    return schema_dir, version


def install_schemas(
    schema_dir: Optional[Path] = None,
    version: Union[str, Version] = Version["2.1"],
) -> Path:
    """Install SDMX-ML XML Schema documents for use with :func:`.validate_xml`.

    Parameters
    ----------
    schema_dir : .Path, optional
        The directory where XSD schemas will be downloaded to. Default: a subdirectory
        named :file:`sdmx/{version}` within the :meth:`platformdirs.user_cache_path`.
    version : str or Version, optional
        The SDMX-ML schema version to install. One of :py:`Version["2.1"]` (default),
        :py:`Version["3.0.0"]`, or :class:`str` equivalent.

    Returns
    -------
    .Path
        The path containing the installed schemas. If `schema_dir` is given, the return
        value is identical to the parameter.
    """
    schema_dir, version = _handle_validate_args(schema_dir, version)

    # Copy the entire "schemas" subtree recursively
    copytree(
        _extracted_zipball(version).joinpath("schemas"), schema_dir, dirs_exist_ok=True
    )
    return schema_dir


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
