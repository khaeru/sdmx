import re
from functools import lru_cache
from itertools import chain
from operator import itemgetter
from typing import Iterable, List, Mapping, Optional, Tuple

from lxml.etree import QName

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
    "CodelistMap",
    "CodeMap",
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
    "StructureSet",
    "TimeDimension",
    "TransformationScheme",
    "UserDefinedOperatorScheme",
]

# XML tag name and class name differ
CT2 = [
    ("model.Agency", "str:Agency"),  # Order matters
    ("model.Agency", "mes:Receiver"),
    ("model.Agency", "mes:Sender"),
    ("model.Concept", "str:ConceptIdentity"),
    ("model.Codelist", "str:Enumeration"),  # This could possibly be ItemScheme
    ("model.Dimension", "str:Dimension"),  # Order matters
    ("model.Dimension", "str:DimensionReference"),
    ("model.Dimension", "str:GroupDimension"),
    ("model.StructureUsage", "com:StructureUsage"),
    ("model.AttributeDescriptor", "str:AttributeList"),
    ("model.DataAttribute", "str:Attribute"),
    ("model.DataStructureDefinition", "str:DataStructure"),
    ("model.DataStructureDefinition", "com:Structure"),
    ("model.DataStructureDefinition", "str:Structure"),
    ("model.DimensionDescriptor", "str:DimensionList"),
    ("model.GroupDimensionDescriptor", "str:Group"),
    ("model.GroupDimensionDescriptor", "str:AttachmentGroup"),
    ("model.GroupKey", "gen:GroupKey"),
    ("model.Key", "gen:ObsKey"),
    ("model.MeasureDescriptor", "str:MeasureList"),
    ("model.MetadataStructureDefinition", "str:MetadataStructure"),
    ("model.SeriesKey", "gen:SeriesKey"),
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
    "data": "{}/data/structurespecific",
    "str": "{}/structure",
    "mes": "{}/message",
    "gen": "{}/data/generic",
    "footer": "{}/message/footer",
}


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
                    r"(\{(?P<ns_full>.*)\}|(?P<ns_key>.*):)(?P<name>.*)", ns_or_name
                )
                assert match
                name = match.group("name")
                ns_key = match.group("ns_key")
                if ns_key:
                    ns = self.NS[ns_key]
                else:
                    ns = match.group("ns_full")
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
