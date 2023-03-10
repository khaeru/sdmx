from sdmx.format import xml
from sdmx.model import v21 as model


def test_tag_for_class():
    # ItemScheme is never written to XML; no corresponding tag name
    assert xml.tag_for_class(model.ItemScheme) is None
