"""Classes for SDMX messages.

:class:`Message` and related classes are not defined in the SDMX
:doc:`information model <implementation>`, but in the :ref:`SDMX-ML standard <formats>`.

:mod:`sdmx` also uses :class:`DataMessage` to encapsulate SDMX-JSON data returned by
data sources.
"""

import logging
import re
from dataclasses import dataclass, field, fields
from datetime import datetime
from itertools import chain
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Generator,
    Optional,
    Text,
    Union,
    get_args,
)

from sdmx import model
from sdmx.dictlike import DictLike, summarize_dictlike
from sdmx.dictlike import DictLikeDescriptor as DLD
from sdmx.format import Version
from sdmx.model import common, v21, v30
from sdmx.model.internationalstring import (
    InternationalString,
    InternationalStringDescriptor,
)
from sdmx.util import compare, direct_fields

if TYPE_CHECKING:
    import requests

log = logging.getLogger(__name__)


def _summarize(obj, include: Optional[list[str]] = None):
    """Helper method for __repr__ on Header and Message (sub)classes."""
    import requests

    include = include or list(map(attrgetter("name"), fields(obj)))
    for name in include:
        attr = getattr(obj, name)
        if attr is None:
            continue
        elif isinstance(attr, datetime):
            s_attr = repr(attr.isoformat())
        elif isinstance(attr, requests.Response):
            # Don't use repr(), which displays the entire response body
            s_attr = str(attr)
        else:
            s_attr = repr(attr)

        yield f"{name}: {s_attr}"


@dataclass
class Header:
    """Header of an SDMX-ML message.

    SDMX-JSON messages do not have headers.
    """

    #: (optional) Error code for the message.
    error: Optional[Text] = None
    #: Date and time at which the data was extracted.
    extracted: Optional[datetime] = None
    #: Identifier for the message.
    id: Optional[Text] = None
    #: Date and time at which the message was generated.
    prepared: Optional[datetime] = None
    #: Start of the time period covered by a :class:`.DataMessage`.
    reporting_begin: Optional[datetime] = None
    #: End of the time period covered by a :class:`.DataMessage`.
    reporting_end: Optional[datetime] = None
    #: Intended recipient of the message, e.g. the user's name for an
    #: authenticated service.
    receiver: Optional[model.Agency] = None
    #: The :class:`.Agency` associated with the data :class:`~.source.Source`.
    sender: Optional[model.Agency] = None
    #:
    source: InternationalStringDescriptor = InternationalStringDescriptor()
    #:
    test: bool = False

    def __repr__(self):
        """String representation."""
        lines = ["<Header>"]
        lines.extend(_summarize(self))
        return "\n  ".join(lines)

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two Headers are the same if their corresponding attributes are equal.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare`.
        """
        return all(
            compare(f, self, other, strict)
            for f in map(attrgetter("name"), fields(self))
        )


@dataclass
class Footer:
    """Footer of an SDMX-ML message.

    SDMX-JSON messages do not have footers.
    """

    #:
    severity: Optional[str] = None
    #: The body text of the Footer contains zero or more blocks of text.
    text: list[model.InternationalString] = field(default_factory=list)
    #:
    code: Optional[int] = None

    def __post_init__(self):
        # Convert non-IS members to IS
        self.text = [
            t if isinstance(t, InternationalString) else InternationalString(t)
            for t in self.text
        ]

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two Footers are the same if their :attr:`code`, :attr:`severity`, and
        :attr:`text` are equal.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare`.
        """
        return all(
            compare(f, self, other, strict)
            for f in map(attrgetter("name"), fields(self))
        )


@dataclass
class Message:
    #: SDMX version.
    version: Version = Version["2.1"]

    #: :class:`Header` instance.
    header: Header = field(default_factory=Header)
    #: (optional) :class:`Footer` instance.
    footer: Optional[Footer] = None
    #: :class:`requests.Response` instance for the response to the HTTP request that
    #: returned the Message. This is not part of the SDMX standard.
    response: Optional["requests.Response"] = None

    def __str__(self):
        return repr(self)

    def __repr__(self):
        """String representation."""
        lines = [
            f"<sdmx.{self.__class__.__name__}>",
            repr(self.header).replace("\n", "\n  "),
        ]
        lines.extend(_summarize(self, ["footer", "response"]))
        return "\n  ".join(lines)

    def compare(self, other, strict=True) -> bool:
        """Return :obj:`True` if `self` is the same as `other`.

        Two Messages are the same if their :attr:`header` and :attr:`footer` compare
        equal.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare`.
        """
        return self.header.compare(other.header, strict) and (
            self.footer is other.footer is None
            or self.footer.compare(other.footer, strict)  # type: ignore [union-attr]
        )


class ErrorMessage(Message):
    pass


@dataclass
class StructureMessage(Message):
    """SDMX StructureMessage."""

    #: Collection of :class:`.Categorisation`.
    categorisation: DLD[str, model.Categorisation] = DLD()
    #: Collection of :class:`.CategoryScheme`.
    category_scheme: DLD[str, model.CategoryScheme] = DLD()
    #: Collection of :class:`.Codelist`.
    codelist: DLD[str, model.Codelist] = DLD()
    #: Collection of :class:`.ConceptScheme`.
    concept_scheme: DLD[str, model.ConceptScheme] = DLD()
    #: Collection of :class:`.ContentConstraint`.
    constraint: DLD[str, model.BaseConstraint] = DLD()
    #: Collection of :class:`.CustomTypeScheme`.
    custom_type_scheme: DLD[str, model.CustomTypeScheme] = DLD()
    #: Collection of :class:`Dataflow(Definition) <.BaseDataflow>`.
    dataflow: DLD[str, model.BaseDataflow] = DLD()
    #: Collection of :class:`.HierarchicalCodelist`.
    hierarchical_codelist: DLD[str, v21.HierarchicalCodelist] = DLD()
    #: Collection of :class:`.v30.Hierarchy`.
    hierarchy: DLD[str, v30.Hierarchy] = DLD()
    #: Collection of :class:`Metadataflow(Definition) <.BaseMetadataflow>`.
    metadataflow: DLD[str, model.BaseMetadataflow] = DLD()
    #: Collection of :class:`MetadataStructureDefinition
    #: <.BaseMetadataStructureDefinition>`.
    metadatastructure: DLD[str, model.BaseMetadataStructureDefinition] = DLD()
    #: Collection of :class:`.NamePersonalisationScheme`.
    name_personalisation_scheme: DLD[str, model.NamePersonalisationScheme] = DLD()
    #: Collection of :class:`.OrganisationScheme`.
    organisation_scheme: DLD[str, model.OrganisationScheme] = DLD()
    #: Collection of :class:`.ProvisionAgreement`.
    provisionagreement: DLD[str, model.ProvisionAgreement] = DLD()
    #: Collection of :class:`.RulesetScheme`.
    ruleset_scheme: DLD[str, model.RulesetScheme] = DLD()
    #: Collection of :class:`DataStructureDefinition <.BaseDataStructureDefinition>`.
    structure: DLD[str, model.BaseDataStructureDefinition] = DLD()
    #: Collection of :class:`.StructureSet`.
    structureset: DLD[str, v21.StructureSet] = DLD()
    #: Collection of :class:`.TransformationScheme`.
    transformation_scheme: DLD[str, model.TransformationScheme] = DLD()
    #: Collection of :class:`.UserDefinedOperatorScheme`.
    user_defined_operator_scheme: DLD[str, model.UserDefinedOperatorScheme] = DLD()
    #: Collection of :class:`.ValueList` (SDMX 3.0 only).
    valuelist: DLD[str, v30.ValueList] = DLD()
    #: Collection of :class:`.VTLMappingScheme`.
    vtl_mapping_scheme: DLD[str, model.VTLMappingScheme] = DLD()

    def __post_init__(self):
        # Construct a list referencing all of the collections
        self._collections = [
            getattr(self, f.name) for f in direct_fields(self.__class__)
        ]

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two StructureMessages compare equal if :meth:`.DictLike.compare` is :obj:`True`
        for each of the object collection attributes.

        Parameters
        ----------
        strict : bool, optional
            Passed to :meth:`.DictLike.compare`.
        """
        return super().compare(other, strict) and all(
            getattr(self, f.name).compare(getattr(other, f.name), strict)
            for f in direct_fields(self.__class__)
        )

    def add(self, obj: model.IdentifiableArtefact):
        """Add `obj` to the StructureMessage."""
        for f in direct_fields(self.__class__):
            # NB for some reason mypy complains here, but not in __contains__(), below
            if isinstance(obj, get_args(f.type)[1]):
                getattr(self, f.name)[obj.id] = obj
                return
        raise TypeError(type(obj))

    def get(
        self, obj_or_id: Union[str, model.IdentifiableArtefact]
    ) -> Optional[model.IdentifiableArtefact]:
        """Retrieve `obj_or_id` from the StructureMessage.

        Parameters
        ----------
        obj_or_id : str or .IdentifiableArtefact
            If an IdentifiableArtefact, return an object of the same class and
            :attr:`~.IdentifiableArtefact.id`; if :class:`str`, an object with this ID
            *or* this string as part of its :attr:`~.IdentifiableArtefact.urn`.

            .. todo:: Support passing a URN.

        Returns
        -------
        .IdentifiableArtefact
            with the given ID and possibly class, or :any:`None` if there is no match.

        Raises
        ------
        ValueError
            if there are ≥2 objects with the same `obj_or_id`; for instance, two objects
            of different classes, or two objects of the same class with different
            :attr:`~.MaintainableArtefact.maintainer` or
            :attr:`~.VersionableArtefact.version`.
        """
        id_ = (
            obj_or_id.id
            if isinstance(obj_or_id, model.IdentifiableArtefact)
            else obj_or_id
        )

        # Expression for matching URN. Ensure `id_` appears immediately after one of the
        # separator characters
        urn_expr = re.compile(rf"[=:]{re.escape(id_)}")

        candidates: list[model.IdentifiableArtefact] = []
        for key, obj in chain(*[c.items() for c in self._collections]):
            if id_ in (key, obj.id) or urn_expr.search(obj.urn or ""):
                candidates.append(obj)

        if len(candidates) > 1:
            raise ValueError(f"ambiguous; {repr(obj_or_id)} matches {repr(candidates)}")

        return candidates[0] if len(candidates) == 1 else None

    def iter_collections(self) -> Generator[tuple[str, type], None, None]:
        """Iterate over collections."""
        for f in direct_fields(self.__class__):
            yield f.name, get_args(f.type)[1]

    def iter_objects(
        self, external_reference: bool = True
    ) -> Generator[common.MaintainableArtefact, None, None]:
        """Iterate over all objects in the message."""
        for _, cls in self.iter_collections():
            for obj in self.objects(cls).values():
                if not external_reference and obj.is_external_reference:
                    continue
                yield obj

    def objects(self, cls):
        """Get a reference to the attribute for objects of type `cls`.

        For example, if `cls` is the class :class:`DataStructureDefinition` (not an
        instance), return a reference to :attr:`structure`.
        """
        for f in direct_fields(self.__class__):
            if issubclass(cls, get_args(f.type)[1]):
                return getattr(self, f.name)
        raise TypeError(cls)

    def __contains__(self, item):
        """Return :obj:`True` if `item` is in the StructureMessage."""
        for f in direct_fields(self.__class__):
            if isinstance(item, get_args(f.type)[1]):
                return item in getattr(self, f.name).values()
        raise TypeError(f"StructureMessage has no collection of {type(item)}")

    def __repr__(self):
        """String representation."""
        lines = [super().__repr__()]

        # StructureMessage contents
        for attr in self.__dict__.values():
            if isinstance(attr, DictLike) and attr:
                lines.append(summarize_dictlike(attr))

        return "\n  ".join(lines)


@dataclass
class DataMessage(Message):
    """SDMX Data Message.

    .. note:: A DataMessage may contain zero or more :class:`.DataSet`, so :attr:`data`
       is a list. To retrieve the first (and possibly only) data set in the message,
       access the first element of the list: :py:`msg.data[0]`.
    """

    #: :class:`list` of :class:`.DataSet`.
    data: list[model.BaseDataSet] = field(default_factory=list)
    #: :class:`.DataflowDefinition` that contains the data.
    dataflow: Optional[model.BaseDataflow] = None
    #: The "dimension at observation level".
    observation_dimension: Optional[
        Union[
            model._AllDimensions,
            model.DimensionComponent,
            list[model.DimensionComponent],
        ]
    ] = None

    def __post_init__(self):
        if self.dataflow is None:
            # Create a default of the appropriate class
            self.dataflow = {
                Version["2.1"]: v21.DataflowDefinition,
                Version["3.0.0"]: v30.Dataflow,
            }[self.version]()

    # Convenience access
    @property
    def structure(self):
        """DataStructureDefinition used in the :attr:`dataflow`."""
        return self.dataflow.structure

    @property
    def structure_type(self) -> type[common.Structure]:
        """:class:`.Structure` subtype describing the contained (meta)data."""
        return {
            Version["2.1"]: v21.DataStructureDefinition,
            Version["3.0.0"]: v30.DataStructureDefinition,
        }[self.version]

    def __repr__(self):
        """String representation."""
        lines = [super().__repr__()]

        # DataMessage contents
        if self.data:
            lines.append("DataSet ({})".format(len(self.data)))
        lines.extend(_summarize(self, ("dataflow", "observation_dimension")))

        return "\n  ".join(lines)

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two DataMessages are the same if:

        - :meth:`.Message.compare` is :obj:`True`
        - their :attr:`dataflow` and :attr:`observation_dimension` compare equal.
        - they have the same number of :class:`DataSets <DataSet>`, and
        - corresponding DataSets compare equal (see :meth:`.DataSet.compare`).

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare`.
        """
        return (
            super().compare(other, strict)
            and compare("dataflow", self, other, strict)
            and compare("observation_dimension", self, other, strict)
            and len(self.data) == len(other.data)
            and all(ds[0].compare(ds[1], strict) for ds in zip(self.data, other.data))
        )

    def update(self) -> None:
        """Update :attr:`.observation_dimension`.

        The observation dimensions (or dimension observation) is determined
        automatically if:

        1. There is at least 1 :class:`DataSet <.BaseDataSet>` in the message.
        2. For at least 1 data set:

           - :attr:`~.BaseDataSet.structured_by` is defined.
           - There is at least 1 :class:`.Observation` in the data set. (:meth:`.update`
             checks only the first observation.)
           - The :attr:`.Observation.dimension` is a :class:`.Key` referring to exactly
             1 dimension.

        3. The dimension indicated by (2) is the same for all DataSets in the message.

        If not all these conditions are met, messages are logged with level DEBUG, and
        :attr:`.observation_dimension` is set to :any:`None`.

        .. note:: :meth:`.update` is not automatically called when data sets are added
           to or removed from :attr:`.data`. User code **should** call :meth:`.update`
           to reflect such changes.
        """
        if not self.data:
            log.debug("No DataSet in message")
            self.observation_dimension = None
            return

        dims = set()
        for ds in self.data:
            try:
                assert ds.structured_by

                # Use the first observation
                assert len(ds.obs)
                o0 = ds.obs[0]
                assert o0.dimension

                # Identify the dimensions specified per-observation
                d_a_o = tuple(o0.dimension.values.keys())

                if 1 == len(d_a_o):
                    # Single dimension-at-observation
                    # Record as an attribute of the DataMessage
                    dims.add(ds.structured_by.dimensions.get(d_a_o[0]))
                else:
                    dims.add(d_a_o)
            except AssertionError:
                continue

        if len(dims) == 1 and not all(isinstance(d, tuple) for d in dims):
            self.observation_dimension = dims.pop()
        else:
            if len(dims) == 1:
                log.debug(f"More than 1 dimension at observation level: {dims.pop()}")
            elif len(dims) > 1:
                log.debug(
                    f"Multiple data sets with different observation dimension: {dims}"
                )
            elif not dims:
                log.debug(
                    f"Unable to determine observation dimension for {len(self.data)} "
                    "data set(s). Data set(s) may lack structure reference or "
                    "observations."
                )
            self.observation_dimension = None


@dataclass
class MetadataMessage(DataMessage):
    """SDMX Metadata Message."""

    @property
    def structure_type(self) -> type[common.Structure]:
        return {
            Version["2.1"]: v21.MetadataStructureDefinition,
            Version["3.0.0"]: v30.MetadataStructureDefinition,
        }[self.version]
