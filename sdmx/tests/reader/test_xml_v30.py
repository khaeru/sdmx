from sdmx.reader.xml.v30 import Reader


class TestReader:
    def test_model_attribute(self):
        import sdmx.model.v30

        r = Reader()
        assert r.model is sdmx.model.v30
