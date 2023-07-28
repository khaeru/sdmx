import re
from functools import lru_cache
from operator import itemgetter
from typing import Iterable, List, Mapping, Optional, Tuple

from lxml.etree import QName

from sdmx.model import common as model

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
    "DataConsumer",
    "DataConsumerScheme",
    "DataProvider",
    "DataProviderScheme",
    "TimeDimension",
]

CT2 = [
    (model.Agency, "mes:Receiver"),
    (model.Agency, "mes:Sender"),
    (model.Dimension, "str:Dimension"),  # Order matters
    (model.Dimension, "str:DimensionReference"),
    (model.Dimension, "str:GroupDimension"),
    (model.StructureUsage, "com:StructureUsage"),
]

NS = {
    "": None,
    "xml": "http://www.w3.org/XML/1998/namespace",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}


class XMLFormat:
    NS: Mapping[str, Optional[str]]
    _class_tag: List

    def __init__(self, base_ns: str, class_tag: Iterable[Tuple[type, str]]):
        self.base_ns = base_ns

        self.NS = NS.copy()
        self.NS.update(
            com=f"{base_ns}/common",
            data=f"{base_ns}/data/structurespecific",
            str=f"{base_ns}/structure",
            mes=f"{base_ns}/message",
            gen=f"{base_ns}/data/generic",
            footer=f"{base_ns}/message/footer",
        )

        self._class_tag = []
        self._class_tag.extend(
            (getattr(model, name), self.qname("str", name)) for name in CT1
        )
        self._class_tag.extend((c, self.qname(t)) for c, t in CT2)
        self._class_tag.extend((c, self.qname(t)) for c, t in class_tag)

    def __eq__(self, other):
        return self.base_ns == other.base_ns

    def __hash__(self):
        return hash(self.base_ns)

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
