import re
from operator import itemgetter

import pytest

import sdmx
from sdmx import message
from sdmx.model import common, v21


@pytest.mark.parametrize(
    "cls",
    (message.Message, message.DataMessage, message.StructureMessage, message.Footer),
)
def test_compare(cls):
    A = cls()
    B = cls()

    assert A.compare(B) is True


class TestDataMessage:
    def test_update(self, caplog):
        dm = message.DataMessage()

        # A data structure with 3 dimensions
        dsd = v21.DataStructureDefinition()
        dim_foo = dsd.dimensions.getdefault("FOO")
        dsd.dimensions.getdefault("BAR")
        dsd.dimensions.getdefault("BAZ")

        # 0 data sets
        dm.update()
        assert None is dm.observation_dimension
        assert re.match("No DataSet in message", caplog.messages[-1])
        caplog.clear()

        # 1 data set, 0 observations
        ds0 = v21.DataSet(structured_by=dsd)
        dm.data.append(ds0)

        dm.update()
        assert None is dm.observation_dimension
        assert re.match(r"^Unable to .* 1 data set\(s\)", caplog.messages[-1])
        caplog.clear()

        # 1 data set, 1 observation, 3 dimensions at observation ('flat')
        obs0 = v21.Observation(
            dimension=dsd.make_key(common.Key, {"FOO": "f", "BAR": "b", "BAZ": "b"})
        )
        ds0.add_obs([obs0])

        dm.update()
        assert None is dm.observation_dimension
        assert re.match(r"^More than 1 dimension at observation", caplog.messages[-1])
        caplog.clear()

        # 1 data set, 1 observation, 1 dimension at observation
        obs0.dimension = dsd.make_key(common.Key, {"FOO": "f"})

        dm.update()
        assert dim_foo is dm.observation_dimension
        assert 0 == len(caplog.messages)

        # 2 data sets, 1 dimension at observation, but different
        ds1 = v21.DataSet(structured_by=dsd)
        obs1 = v21.Observation(dimension=dsd.make_key(common.Key, {"BAR": "b"}))
        ds1.add_obs([obs1])
        dm.data.append(ds1)

        dm.update()
        assert None is dm.observation_dimension
        assert re.match("Multiple data sets with different observ", caplog.messages[-1])


class TestStructureMessage:
    def test_add_contains_get(self):
        dsd = v21.DataStructureDefinition(id="foo")
        msg = message.StructureMessage()

        # add() stores the object
        msg.add(dsd)
        assert 1 == len(msg.structure)

        # __contains__() works
        assert dsd in msg

        # get() retrieves the object
        assert dsd is msg.get("foo")

        # add() with an object not collected in a StructureMessage raises TypeError
        item = common.Item(id="bar")
        with pytest.raises(TypeError):
            msg.add(item)

        # __contains__() also raises TypeError
        with pytest.raises(TypeError):
            item in msg

        # get() with two objects of the same ID raises ValueError
        msg.add(v21.DataflowDefinition(id="foo"))
        with pytest.raises(ValueError):
            msg.get("foo")

    def test_dictlike_attribute_access(self):
        dsd = v21.DataStructureDefinition(id="foo")
        msg = message.StructureMessage()
        msg.add(dsd)

        # Attribute access works when added to the default, empty DictLike
        assert msg.structure.foo is dsd

    def test_iter_objects(self):
        """:meth:`.iter_objects` can be used to iterate over all objects."""
        msg = message.StructureMessage()

        # Add several objects
        msg.add(common.Codelist(id="CL_FOO"))
        msg.add(common.Codelist(id="CL_BAR", is_external_reference=True))
        msg.add(common.Codelist(id="CL_BAZ"))

        msg.add(common.ConceptScheme(id="CS_FOO"))
        msg.add(common.ConceptScheme(id="CS_BAR", is_external_reference=True))
        msg.add(common.ConceptScheme(id="CS_BAZ"))

        # Method accepts external_reference arg; runs; returns an iterator
        result = msg.iter_objects()

        # All objects
        assert 6 == len(list(result))

        # All objects that are not external references are included
        assert {"CL_FOO", "CL_BAZ", "CS_FOO", "CS_BAZ"} == set(
            obj.id for obj in msg.iter_objects(external_reference=False)
        )

    def test_objects(self):
        """:meth:`.objects` can be used to access a collection according to class."""
        msg = message.StructureMessage()
        cl = common.Codelist(id="foo")
        msg.add(cl)

        assert cl is msg.objects(common.Codelist)["foo"]

        with pytest.raises(TypeError):
            # TypeError is raised for classes not collected in this message
            msg.objects(v21.DataSet)


EXPECTED = [
    # Structure messages
    (
        "IPI-2010-A21-structure.xml",
        """<sdmx.StructureMessage>
  <Header>
    id: 'categorisation_1450864290565'
    prepared: '2015-12-23T09:51:30.565000+00:00'
    receiver: <Agency unknown>
    sender: <Agency FR1: Institut national de la statistique et des études économiques>
    source: fr: Banque de données macro-économiques
    test: False
  response: <Response [None]>
  Categorisation (1): CAT_IPI-2010_IPI-2010-A21
  CategoryScheme (1): CLASSEMENT_DATAFLOWS
  Codelist (7): CL_FREQ CL_NAF2_A21 CL_NATURE CL_UNIT CL_AREA CL_TIME_C...
  ConceptScheme (1): CONCEPTS_INSEE
  DataflowDefinition (1): IPI-2010-A21
  DataStructureDefinition (1): IPI-2010-A21""",
    ),
    (
        # This message shows the summarization feature: the DFD list is truncated
        "dataflow.xml",
        """<sdmx.StructureMessage>
  <Header>
    id: 'dataflow_ENQ-CONJ-TRES-IND-PERSP_1450865196042'
    prepared: '2015-12-23T10:06:36.042000+00:00'
    receiver: <Agency unknown>
    sender: <Agency FR1: Institut national de la statistique et des études économiques>
    source: fr: Banque de données macro-économiques
    test: False
  response: <Response [None]>
  DataflowDefinition (663): ACT-TRIM-ANC BPM6-CCAPITAL BPM6-CFINANCIER ...
  DataStructureDefinition (663): ACT-TRIM-ANC BPM6-CCAPITAL BPM6-CFINAN...""",
    ),
    # Data messages
    (
        "sg-xs.xml",
        """<sdmx.DataMessage>
  <Header>
    id: 'Generic'
    prepared: '2010-01-04T16:21:49+01:00'
    sender: <Agency ECB>
    source: """
        """
    test: False
  response: <Response [None]>
  DataSet (1)
  dataflow: <DataflowDefinition (missing id)>
  observation_dimension: <Dimension CURRENCY>""",
    ),
    (
        # This message has two DataSets:
        "action-delete.json",
        """<sdmx.DataMessage>
  <Header>
    id: '62b5f19d-f1c9-495d-8446-a3661ed24753'
    prepared: '2012-11-29T08:40:26+00:00'
    sender: <Agency ECB: European Central Bank>
    source: """
        """
    test: False
  response: <Response [None]>
  DataSet (2)
  dataflow: <DataflowDefinition (missing id)>
  observation_dimension: [<Dimension CURRENCY>]""",
    ),
]


@pytest.mark.parametrize(
    "pattern, expected", EXPECTED, ids=list(map(itemgetter(0), EXPECTED))
)
def test_message_repr(specimen, pattern, expected):
    import requests

    with specimen(pattern) as f:
        msg = sdmx.read_sdmx(f)

    # Attach a response object, as if the Message resulted from a requests query
    msg.response = requests.Response()

    if isinstance(expected, re.Pattern):
        assert expected.fullmatch(repr(msg))
    else:
        # __repr__() and __str__() give the same, expected result
        assert expected == repr(msg) == str(msg)
