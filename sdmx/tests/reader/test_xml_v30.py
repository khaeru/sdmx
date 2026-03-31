from typing import cast

import sdmx
from sdmx.model import common
from sdmx.reader.xml.v30 import Reader


class TestReader:
    def test_model_attribute(self):
        import sdmx.model.v30

        r = Reader()
        assert r.model is sdmx.model.v30


class TestMetadataAttributeUsage:
    def test_gh_271(self, specimen) -> None:
        """Check that :class:`.MetadataAttributeUsage` is read correctly.

        cf. :issue:`271`.
        """
        # Message containing <structure:MetadataAttributeUsage> can be read
        with specimen("IMF_STA/DSD_BOP.xml") as f:
            msg = cast(sdmx.message.StructureMessage, sdmx.read_sdmx(f))

        # Retrieve references to DSD and MSD
        dsd = msg.structure["DSD_BOP"]
        msd = msg.metadatastructure["MSD_REF_IMF_DATASET"]

        # Retrieve a single MetadataAttributeUsage from the DSD
        component = dsd.attributes.get("METHODOLOGY")
        # MAU has a DimensionRelationship
        assert isinstance(component.related_to, common.DimensionRelationship)
        assert 5 == len(component.related_to.dimensions)
        # MAU has an association to a MetadataAttribute
        mda1 = component.metadata_attribute
        assert isinstance(mda1, common.MetadataAttribute)

        # DSD has an association to the MSD
        assert dsd.metadata is msd

        # MSD also contains a component with the same ID
        mda2 = msd.attributes.get("METHODOLOGY")

        # These are the same object instances
        assert mda1 is mda2
        assert id(mda1) == id(mda2)
