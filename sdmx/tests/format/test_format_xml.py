import pytest

from sdmx.format import xml
from sdmx.model import v21


def test_ns_prefix():
    with pytest.raises(ValueError):
        xml.v21.ns_prefix("https://example.com")


def test_qname():
    assert f"{{{xml.v21.base_ns}/structure}}Code" == str(xml.v21.qname("str", "Code"))
    assert f"{{{xml.v30.base_ns}/structure}}Code" == str(xml.v30.qname("str", "Code"))


def test_tag_for_class():
    # ItemScheme is never written to XML; no corresponding tag name
    assert xml.v21.tag_for_class(v21.ItemScheme) is None


def test_class_for_tag():
    assert xml.v30.class_for_tag("str:DataStructure") is not None
