"""Information Model classes common to SDMX 2.1 and 3.0.0."""
import logging
import sys
from collections import ChainMap
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from operator import attrgetter
from typing import (
    ClassVar,
    Dict,
    Generic,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Type,
    TypeVar,
    Union,
)

from sdmx.rest import Resource
from sdmx.util import compare, only

from .internationalstring import (
    DEFAULT_LOCALE,
    InternationalString,
    InternationalStringDescriptor,
)

__all__ = [
    "DEFAULT_LOCALE",
    "InternationalString",
    # In the order they appear in this file
    "Annotation",
    "AnnotableArtefact",
    "IdentifiableArtefact",
    "NameableArtefact",
    "VersionableArtefact",
    "MaintainableArtefact",
    "Item",
    "ItemScheme",
    "FacetType",
    "Facet",
    "Representation",
    "Code",
    "Codelist",
    "ISOConceptReference",
    "Concept",
    "ConceptScheme",
    "Component",
    "ComponentList",
    "Category",
    "CategoryScheme",
    "Categorisation",
    "Contact",
    "Organisation",
    "Agency",
    "OrganisationScheme",
    "AgencyScheme",
    "Structure",
    "StructureUsage",
    "DimensionComponent",
    "Dimension",
    "TimeDimension",
    "DimensionDescriptor",
    "GroupDimensionDescriptor",
    "AttributeRelationship",
    "DimensionRelationship",
    "GroupRelationship",
    "DataAttribute",
    "AttributeDescriptor",
    "ConstraintRole",
    "ConstrainableArtefact",
    "SelectionValue",
    "MemberValue",
    "TimeRangeValue",
    "DataConsumer",
    "DataProvider",
    "DataConsumerScheme",
    "DataProviderScheme",
]

log = logging.getLogger(__name__)

# Utility classes not specified in the SDMX standard


class _MissingID(str):
    def __str__(self):
        return "(missing id)"

    # Supplied to allow this as a default value for dataclass fields
    def __hash__(self):
        return hash(None)  # pragma: no cover

    def __eq__(self, other):
        return isinstance(other, self.__class__)


MissingID = _MissingID()


# §3.2: Base structures


@dataclass
class Annotation:
    #: Can be used to disambiguate multiple annotations for one AnnotableArtefact.
    id: Optional[str] = None
    #: Title, used to identify an annotation.
    title: Optional[str] = None
    #: Specifies how the annotation is processed.
    type: Optional[str] = None
    #: A link to external descriptive text.
    url: Optional[str] = None

    #: Content of the annotation.
    text: InternationalStringDescriptor = InternationalStringDescriptor()


@dataclass
class AnnotableArtefact:
    #: :class:`Annotations <.Annotation>` of the object.
    #:
    #: :mod:`.sdmx` implementation detail: The IM does not specify the name of this
    #: feature.
    annotations: List[Annotation] = field(default_factory=list)

    def get_annotation(self, **attrib):
        """Return a :class:`Annotation` with given `attrib`, e.g. 'id'.

        If more than one `attrib` is given, all must match a particular annotation.

        Raises
        ------
        KeyError
            If there is no matching annotation.
        """
        for anno in self.annotations:
            if all(getattr(anno, key, None) == value for key, value in attrib.items()):
                return anno

        raise KeyError(attrib)

    def pop_annotation(self, **attrib):
        """Remove and return a :class:`Annotation` with given `attrib`, e.g. 'id'.

        If more than one `attrib` is given, all must match a particular annotation.

        Raises
        ------
        KeyError
            If there is no matching annotation.
        """
        for i, anno in enumerate(self.annotations):
            if all(getattr(anno, key, None) == value for key, value in attrib.items()):
                return self.annotations.pop(i)

        raise KeyError(attrib)

    def eval_annotation(self, id: str, globals=None):
        """Retrieve the annotation with the given `id` and :func:`eval` its contents.

        This can be used for unpacking Python values (e.g. :class:`dict`) stored as an
        annotation on an AnnotableArtefact (e.g. :class:`~sdmx.model.Code`).

        Returns :obj:`None` if no attribute exists with the given `id`.
        """
        try:
            value = str(self.get_annotation(id=id).text)
        except KeyError:  # No such attribute
            return None

        try:
            return eval(value, globals or {})
        except Exception as e:  # Something that can't be eval()'d, e.g. a plain string
            log.debug(f"Could not eval({value!r}): {e}")
            return value


@dataclass
class IdentifiableArtefact(AnnotableArtefact):
    #: Unique identifier of the object.
    id: str = MissingID
    #: Universal resource identifier that may or may not be resolvable.
    uri: Optional[str] = None
    #: Universal resource name. For use in SDMX registries; all registered objects have
    #: a URN.
    urn: Optional[str] = None

    urn_group: Dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if not isinstance(self.id, str):
            raise TypeError(
                f"IdentifiableArtefact.id must be str; got {type(self.id).__name__}"
            )

        if self.urn:
            import sdmx.urn

            self.urn_group = sdmx.urn.match(self.urn)

        try:
            if self.id not in (self.urn_group["item_id"] or self.urn_group["id"]):
                raise ValueError(f"ID {self.id} does not match URN {self.urn}")
        except KeyError:
            pass

    def __eq__(self, other):
        """Equality comparison.

        IdentifiableArtefacts can be compared to other instances. For convenience, a
        string containing the object's ID is also equal to the object.
        """
        if isinstance(other, self.__class__):
            return self.id == other.id
        elif isinstance(other, str):
            return self.id == other

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two IdentifiableArtefacts are the same if they have the same :attr:`id`,
        :attr:`uri`, and :attr:`urn`.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare`.
        """
        return (
            compare("id", self, other, strict)
            and compare("uri", self, other, strict)
            and compare("urn", self, other, strict)
        )

    def __hash__(self):
        return id(self) if self.id == MissingID else hash(self.id)

    def __lt__(self, other):
        return (
            self.id < other.id if isinstance(other, self.__class__) else NotImplemented
        )

    def __str__(self):
        return self.id

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"

    @classmethod
    def _preserve(cls, *names: str):
        """Copy dunder `names` from IdentifiableArtefact to a decorated class."""

        def decorator(other_cls):
            for name in map(lambda s: f"__{s}__", names):
                candidates = filter(None, map(lambda k: getattr(k, name), cls.__mro__))
                setattr(other_cls, name, next(candidates))
            return other_cls

        return decorator


@dataclass
@IdentifiableArtefact._preserve("eq", "post_init")
class NameableArtefact(IdentifiableArtefact):
    #: Multi-lingual name of the object.
    name: InternationalStringDescriptor = InternationalStringDescriptor()
    #: Multi-lingual description of the object.
    description: InternationalStringDescriptor = InternationalStringDescriptor()

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two NameableArtefacts are the same if:

        - :meth:`.IdentifiableArtefact.compare` is :obj:`True`, and
        - they have the same :attr:`name` and :attr:`description`.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare` and :meth:`.IdentifiableArtefact.compare`.
        """
        if not super().compare(other, strict):
            pass
        elif self.name != other.name:
            log.debug(
                f"Not identical: name <{repr(self.name)}> != <{repr(other.name)}>"
            )
        elif self.description != other.description:
            log.debug(
                f"Not identical: description <{repr(self.description)}> != "
                f"<{repr(other.description)}>"
            )
        else:
            return True
        return False

    def _repr_kw(self) -> MutableMapping[str, str]:
        name = self.name.localized_default()
        return dict(
            cls=self.__class__.__name__, id=self.id, name=f": {name}" if name else ""
        )

    def __repr__(self) -> str:
        return "<{cls} {id}{name}>".format(**self._repr_kw())


@dataclass
class VersionableArtefact(NameableArtefact):
    #: A version string following an agreed convention.
    version: Optional[str] = None
    #: Date from which the version is valid.
    valid_from: Optional[str] = None
    #: Date from which the version is superseded.
    valid_to: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        try:
            if self.version and self.version != self.urn_group["version"]:
                raise ValueError(
                    f"Version {self.version} does not match URN {self.urn}"
                )
            else:
                self.version = self.urn_group["version"]
        except KeyError:
            pass

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two VersionableArtefacts are the same if:

        - :meth:`.NameableArtefact.compare` is :obj:`True`, and
        - they have the same :attr:`version`.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare` and :meth:`.NameableArtefact.compare`.
        """
        return super().compare(other, strict) and compare(
            "version", self, other, strict
        )

    def _repr_kw(self) -> MutableMapping[str, str]:
        return ChainMap(
            super()._repr_kw(),
            dict(version=f"({self.version})" if self.version else ""),
        )


@dataclass
class MaintainableArtefact(VersionableArtefact):
    #: True if the object is final; otherwise it is in a draft state.
    is_final: Optional[bool] = None
    #: :obj:`True` if the content of the object is held externally; i.e., not
    #: the current :class:`Message`.
    is_external_reference: Optional[bool] = None
    #: URL of an SDMX-compliant web service from which the object can be retrieved.
    service_url: Optional[str] = None
    #: URL of an SDMX-ML document containing the object.
    structure_url: Optional[str] = None
    #: Association to the Agency responsible for maintaining the object.
    maintainer: Optional["Agency"] = None

    def __post_init__(self):
        super().__post_init__()
        try:
            if self.maintainer and self.maintainer.id != self.urn_group["agency"]:
                raise ValueError(
                    f"Maintainer {self.maintainer} does not match URN {self.urn}"
                )
            else:
                self.maintainer = Agency(id=self.urn_group["agency"])
        except KeyError:
            pass

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two MaintainableArtefacts are the same if:

        - :meth:`.VersionableArtefact.compare` is :obj:`True`, and
        - they have the same :attr:`maintainer`.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare` and :meth:`.VersionableArtefact.compare`.
        """
        return super().compare(other, strict) and compare(
            "maintainer", self, other, strict
        )

    def _repr_kw(self) -> MutableMapping[str, str]:
        return ChainMap(
            super()._repr_kw(),
            dict(maint=f"{self.maintainer}:" if self.maintainer else ""),
        )

    def __repr__(self) -> str:
        return "<{cls} {maint}{id}{version}{name}>".format(**self._repr_kw())


# §3.4: Data Types


ActionType = Enum("ActionType", "delete replace append information")

ConstraintRoleType = Enum("ConstraintRoleType", "allowable actual")

# NB three diagrams in the spec show this enumeration containing 'gregorianYearMonth'
#    but not 'gregorianYear' or 'gregorianMonth'. The table in §3.6.3.3 Representation
#    Constructs does the opposite. One ESTAT query (via SGR) shows a real-world usage
#    of 'gregorianYear'; while one query shows usage of 'gregorianYearMonth'; so all
#    three are included.
FacetValueType = Enum(
    "FacetValueType",
    """string bigInteger integer long short decimal float double boolean uri count
    inclusiveValueRange alpha alphaNumeric numeric exclusiveValueRange incremental
    observationalTimePeriod standardTimePeriod basicTimePeriod gregorianTimePeriod
    gregorianYear gregorianMonth gregorianYearMonth gregorianDay reportingTimePeriod
    reportingYear reportingSemester reportingTrimester reportingQuarter reportingMonth
    reportingWeek reportingDay dateTime timesRange month monthDay day time duration
    keyValues identifiableReference dataSetReference""",
)

UsageStatus = Enum("UsageStatus", "mandatory conditional")


# §3.5: Item Scheme

IT = TypeVar("IT", bound="Item")


@dataclass
@NameableArtefact._preserve("eq", "hash", "repr")
class Item(NameableArtefact, Generic[IT]):
    parent: Optional[Union[IT, "ItemScheme"]] = None
    child: List[IT] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()

        try:
            # Add this Item as a child of its parent
            self.parent.append_child(self)
        except AttributeError:
            pass  # No parent

        # Add this Item as a parent of its children
        for c in self.child:
            c.parent = self

    def __contains__(self, item):
        """Recursive containment."""
        for c in self.child:
            if item == c or item in c:
                return True

    def __iter__(self, recurse=True):
        yield self
        for c in self.child:
            yield from iter(c)

    @property
    def hierarchical_id(self):
        """Construct the ID of an Item in a hierarchical ItemScheme.

        Returns, for example, 'A.B.C' for an Item with id 'C' that is the child of an
        item with id 'B', which is the child of a root Item with id 'A'.

        See also
        --------
        .ItemScheme.get_hierarchical
        """
        return (
            f"{self.parent.hierarchical_id}.{self.id}"
            if isinstance(self.parent, self.__class__)
            else self.id
        )

    def append_child(self, other: IT):
        if other not in self.child:
            self.child.append(other)
        other.parent = self

    def get_child(self, id) -> IT:
        """Return the child with the given *id*."""
        for c in self.child:
            if c.id == id:
                return c
        raise ValueError(id)

    def get_scheme(self):
        """Return the :class:`ItemScheme` to which the Item belongs, if any."""
        try:
            # Recurse
            return self.parent.get_scheme()
        except AttributeError:
            # Either this Item is a top-level Item whose .parent refers to the
            # ItemScheme, or it has no parent
            return self.parent


@dataclass
class ItemScheme(MaintainableArtefact, Generic[IT]):
    """SDMX-IM Item Scheme.

    The IM states that ItemScheme “defines a *set* of :class:`Items <.Item>`…” To
    simplify indexing/retrieval, this implementation uses a :class:`dict` for the
    :attr:`items` attribute, in which the keys are the :attr:`~.IdentifiableArtefact.id`
    of the Item.

    Because this may change in future versions, user code should not access
    :attr:`items` directly. Instead, use the :func:`getattr` and indexing features of
    ItemScheme, or the public methods, to access and manipulate Items:

    >>> foo = ItemScheme(id='foo')
    >>> bar = Item(id='bar')
    >>> foo.append(bar)
    >>> foo
    <ItemScheme: 'foo', 1 items>
    >>> (foo.bar is bar) and (foo['bar'] is bar) and (bar in foo)
    True

    """

    # TODO add delete()
    # TODO add sorting capability; perhaps sort when new items are inserted

    # NB the IM does not specify; this could be True by default, but would need to check
    # against the automatic construction in .reader.*.
    is_partial: Optional[bool] = None

    #: Members of the ItemScheme. Both ItemScheme and Item are abstract classes.
    #: Concrete classes are paired: for example, a :class:`.Codelist` contains
    #: :class:`Codes <.Code>`.
    items: Dict[str, IT] = field(default_factory=dict)

    # The type of the Items in the ItemScheme. This is necessary because the type hint
    # in the class declaration is static; not meant to be available at runtime.
    _Item: ClassVar[Type] = Item

    # Convenience access to items
    def __getattr__(self, name: str) -> IT:
        # Provided to pass test_dsd.py
        try:
            return self.__getitem__(name)
        except KeyError:
            raise AttributeError(name)

    def __getitem__(self, name: str) -> IT:
        return self.items[name]

    def get_hierarchical(self, id: str) -> IT:
        """Get an Item by its :attr:`~.Item.hierarchical_id`."""
        if "." not in id:
            return self.items[id]
        else:
            for item in self.items.values():
                if item.hierarchical_id == id:
                    return item
        raise KeyError(id)

    def __contains__(self, item: Union[str, IT]) -> bool:
        """Check containment.

        No recursive search on children is performed as these are assumed to be included
        in :attr:`items`. Allow searching by Item or its id attribute.
        """
        if isinstance(item, str):
            return item in self.items
        return item in self.items.values()

    def __iter__(self):
        return iter(self.items.values())

    def extend(self, items: Iterable[IT]):
        """Extend the ItemScheme with members of `items`.

        Parameters
        ----------
        items : iterable of :class:`.Item`
            Elements must be of the same class as :attr:`items`.
        """
        for i in items:
            self.append(i)

    def __len__(self):
        return len(self.items)

    def append(self, item: IT):
        """Add *item* to the ItemScheme.

        Parameters
        ----------
        item : same class as :attr:`items`
            Item to add.
        """
        if item.id in self.items:
            raise ValueError(f"Item with id {repr(item.id)} already exists")
        self.items[item.id] = item
        if item.parent is None:
            item.parent = self

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two ItemSchemes are the same if:

        - :meth:`.MaintainableArtefact.compare` is :obj:`True`, and
        - their :attr:`items` have the same keys, and corresponding
          :class:`Items <Item>` compare equal.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare` and :meth:`.MaintainableArtefact.compare`.
        """
        if not super().compare(other, strict):
            pass
        elif set(self.items) != set(other.items):
            log.debug(
                f"ItemScheme contents differ: {repr(set(self.items))} != "
                + repr(set(other.items))
            )
        else:
            for id, item in self.items.items():
                if not item.compare(other.items[id], strict):
                    log.debug(f"…for items with id={repr(id)}")
                    return False
            return True

        return False

    def __repr__(self):
        return "<{cls} {maint}{id}{version} ({N} items){name}>".format(
            **self._repr_kw(), N=len(self.items)
        )

    def setdefault(self, obj=None, **kwargs) -> IT:
        """Retrieve the item *name*, or add it with *kwargs* and return it.

        The returned object is a reference to an object in the ItemScheme, and is of the
        appropriate class.
        """
        if obj and len(kwargs):
            raise ValueError(
                "cannot give both *obj* and keyword arguments to setdefault()"
            )

        if not obj:
            # Replace a string 'parent' ID with a reference to the object
            parent = kwargs.pop("parent", None)
            if isinstance(parent, str):
                kwargs["parent"] = self[parent]

            # Instantiate an object of the correct class
            obj = self._Item(**kwargs)

        try:
            # Add the object to the ItemScheme
            self.append(obj)
        except ValueError:
            # Already present; return the existing object, discard the candidate
            return self[obj.id]
        else:
            return obj


# §3.6: Structure


@dataclass
class FacetType:
    #:
    is_sequence: Optional[bool] = None
    #:
    min_length: Optional[int] = None
    #:
    max_length: Optional[int] = None
    #:
    min_value: Optional[float] = None
    #:
    max_value: Optional[float] = None
    #:
    start_value: Optional[float] = None
    #:
    end_value: Optional[str] = None
    #:
    interval: Optional[float] = None
    #:
    time_interval: Optional[timedelta] = None
    #:
    decimals: Optional[int] = None
    #:
    pattern: Optional[str] = None
    #:
    start_time: Optional[datetime] = None
    #:
    end_time: Optional[datetime] = None
    #: SDMX 3.0 only; not present in SDMX 2.1
    sentinel_values: Optional[str] = None

    def __post_init__(self):
        for name in "max_length", "min_length":
            try:
                setattr(self, name, int(getattr(self, name)))
            except TypeError:
                pass


@dataclass
class Facet:
    #:
    type: FacetType = field(default_factory=FacetType)
    #:
    value: Optional[str] = None
    #:
    value_type: Optional[FacetValueType] = None


@dataclass
class Representation:
    #:
    enumerated: Optional[ItemScheme] = None
    #:
    non_enumerated: List[Facet] = field(default_factory=list)

    def __repr__(self):
        return "<{}: {}, {}>".format(
            self.__class__.__name__, self.enumerated, self.non_enumerated
        )


# §4.3: Codelist


@dataclass
@NameableArtefact._preserve("eq", "hash", "repr")
class Code(Item["Code"]):
    """SDMX Code."""

    __post_init__ = Item.__post_init__


class Codelist(ItemScheme[IT]):
    """SDMX Codelist."""

    _Item = Code


# §4.4: Concept Scheme


@dataclass
class ISOConceptReference:
    #:
    agency: str
    #:
    id: str
    #:
    scheme_id: str


class Concept(Item["Concept"]):
    #:
    core_representation: Optional[Representation] = None
    #:
    iso_concept: Optional[ISOConceptReference] = None


class ConceptScheme(ItemScheme[Concept]):
    _Item = Concept


# SDMX 2.1 §3.3: Basic Inheritance
# SDMX 3.0 §3.6: The Structure Pattern


@dataclass
@IdentifiableArtefact._preserve("hash", "repr")
class Component(IdentifiableArtefact):
    #:
    concept_identity: Optional[Concept] = None
    #:
    local_representation: Optional[Representation] = None

    def __contains__(self, value):
        for repr in [
            getattr(self.concept_identity, "core_representation", None),
            self.local_representation,
        ]:
            enum = getattr(repr, "enumerated", None)
            if enum is not None:
                return value in enum
        raise TypeError("membership not defined for non-enumerated representations")


CT = TypeVar("CT", bound=Component)


@dataclass
class ComponentList(IdentifiableArtefact, Generic[CT]):
    #:
    components: List[CT] = field(default_factory=list)
    #: Counter used to automatically populate :attr:`.DimensionComponent.order` values.
    auto_order = 1

    # The default type of the Components in the ComponentList. See comment on
    # ItemScheme._Item
    _Component: ClassVar[Type] = Component

    # Convenience access to the components
    def append(self, value: CT) -> None:
        """Append *value* to :attr:`components`."""
        if hasattr(value, "order") and value.order is None:
            value.order = max(self.auto_order, len(self.components) + 1)
            self.auto_order = value.order + 1
        self.components.append(value)

    def extend(self, values: Iterable[CT]) -> None:
        """Extend :attr:`components` with *values*."""
        for value in values:
            self.append(value)

    def get(self, id) -> CT:
        """Return the component with the given *id*."""
        # Search for an existing Component
        for c in self.components:
            if c.id == id:
                return c
        raise KeyError(id)

    def getdefault(self, id, cls=None, **kwargs) -> CT:
        """Return or create the component with the given *id*.

        If the component is automatically created, its :attr:`.Dimension.order`
        attribute is set to the value of :attr:`auto_order`, which is then incremented.

        Parameters
        ----------
        id : str
            Component ID.
        cls : type, optional
            Hint for the class of a new object.
        kwargs
            Passed to the constructor of :class:`.Component`, or a Component subclass if
            :attr:`.components` is overridden in a subclass of ComponentList.
        """
        try:
            return self.get(id)
        except KeyError:
            pass  # No match

        # Create a new object of a class:
        # 1. Given by the cls argument,
        # 2. Specified by a subclass' _default_type attribute, or
        # 3. Hinted for a subclass' components attribute.
        cls = cls or self._Component
        component = cls(id=id, **kwargs)

        if "order" not in kwargs and hasattr(component, "order"):
            # For automatically created dimensions, give a serial value to the order
            # property
            component.order = self.auto_order
            self.auto_order += 1

        self.components.append(component)
        return component

    # Properties of components
    def __getitem__(self, key) -> CT:
        """Convenience access to components."""
        return self.components[key]

    def __len__(self):
        return len(self.components)

    def __iter__(self):
        return iter(self.components)

    def __repr__(self):
        return "<{}: {}>".format(
            self.__class__.__name__, "; ".join(map(repr, self.components))
        )

    def __eq__(self, other):
        """ID equal and same components occur in same order."""
        return super().__eq__(other) and all(
            s == o for s, o in zip(self.components, other.components)
        )

    # Must be reset because __eq__ is defined
    def __hash__(self):
        return super().__hash__()

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two ComponentLists are the same if:

        - :meth:`.IdentifiableArtefact.compare` is :obj:`True`, and
        - corresponding :attr:`components` compare equal.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare` and :meth:`.IdentifiableArtefact.compare`.
        """
        return super().compare(other, strict) and all(
            c.compare(other.get(c.id), strict) for c in self.components
        )


# §4.5: Category Scheme


class Category(Item["Category"]):
    """SDMX-IM Category."""


class CategoryScheme(ItemScheme[Category]):
    _Item = Category


@dataclass
class Categorisation(MaintainableArtefact):
    #:
    category: Optional[Category] = None
    #:
    artefact: Optional[IdentifiableArtefact] = None


# §4.6: Organisations


@dataclass
class Contact:
    """Organization contact information.

    IMF is the only known data provider that returns messages with :class:`Contact`
    information. These differ from the IM in several ways. This class reflects these
    differences:

    - 'name' and 'org_unit' are InternationalString, instead of strings.
    - 'email' may be a list of e-mail addresses, rather than a single address.
    - 'fax' may be a list of fax numbers, rather than a single number.
    - 'uri' may be a list of URIs, rather than a single URI.
    - 'x400' may be a list of strings, rather than a single string.
    """

    #:
    name: InternationalStringDescriptor = InternationalStringDescriptor()
    #:
    org_unit: InternationalStringDescriptor = InternationalStringDescriptor()
    #:
    telephone: Optional[str] = None
    #:
    responsibility: InternationalStringDescriptor = InternationalStringDescriptor()
    #:
    email: List[str] = field(default_factory=list)
    #:
    fax: List[str] = field(default_factory=list)
    #:
    uri: List[str] = field(default_factory=list)
    #:
    x400: List[str] = field(default_factory=list)


@dataclass
@NameableArtefact._preserve("eq", "hash", "repr")
class Organisation(Item["Organisation"]):
    #:
    contact: List[Contact] = field(default_factory=list)


class Agency(Organisation):
    """SDMX-IM Organization.

    This class is identical to its parent class.
    """


# DataProvider delayed until after ConstrainableArtefact, below


class OrganisationScheme(ItemScheme[IT]):
    """SDMX OrganisationScheme (abstract class)."""

    _Item = Organisation


class AgencyScheme(OrganisationScheme[Agency]):
    _Item = Agency


# DataProviderScheme delayed until after DataProvider, below


# SDMX 3.0 §5.3: Data Structure Definition


@dataclass(repr=False)
class Structure(MaintainableArtefact):
    #:
    grouping: Optional[ComponentList] = None


class StructureUsage(MaintainableArtefact):
    #:
    structure: Optional[Structure] = None


@dataclass
@IdentifiableArtefact._preserve("eq", "hash", "repr")
class DimensionComponent(Component):
    """SDMX DimensionComponent (abstract class)."""

    #:
    order: Optional[int] = None


@dataclass
@IdentifiableArtefact._preserve("eq", "hash", "repr")
class Dimension(DimensionComponent):
    """SDMX Dimension."""


class TimeDimension(DimensionComponent):
    """SDMX TimeDimension."""


@dataclass
class DimensionDescriptor(ComponentList[DimensionComponent]):
    """Describes a set of dimensions.

    IM: “An ordered set of metadata concepts that, combined, classify a statistical
    series, and whose values, when combined (the key) in an instance such as a data set,
    uniquely identify a specific observation.”

    :attr:`.components` is a :class:`list` (ordered) of :class:`Dimension`,
    :class:`MeasureDimension`, and/or :class:`TimeDimension`.
    """

    _Component = Dimension

    def assign_order(self):
        """Assign the :attr:`.DimensionComponent.order` attribute.

        The Dimensions in :attr:`components` are numbered, starting from 1.
        """
        for i, component in enumerate(self.components):
            component.order = i + 1

    def order_key(self, key):
        """Return a key ordered according to the DSD."""
        result = key.__class__()
        for dim in sorted(self.components, key=attrgetter("order")):
            try:
                result[dim.id] = key[dim.id]
            except KeyError:
                continue
        return result

    @classmethod
    def from_key(cls, key):
        """Create a new DimensionDescriptor from a *key*.

        For each :class:`KeyValue` in the *key*:

        - A new :class:`Dimension` is created.
        - A new :class:`Codelist` is created, containing the
          :attr:`KeyValue.value`.

        Parameters
        ----------
        key : :class:`Key` or :class:`GroupKey` or :class:`SeriesKey`
        """
        dd = cls()
        for order, (id, kv) in enumerate(key.values.items()):
            cl = Codelist(id=id)
            cl.append(Code(id=str(kv.value)))
            dd.components.append(
                Dimension(
                    id=id,
                    local_representation=Representation(enumerated=cl),
                    order=order,
                )
            )
        return dd


class GroupDimensionDescriptor(DimensionDescriptor):
    #:
    attachment_constraint: Optional[bool] = None
    # #:
    # constraint: Optional[AttachmentConstraint] = None

    def assign_order(self):
        """:meth:`assign_order` has no effect for GroupDimensionDescriptor."""
        pass


class AttributeRelationship:
    pass


@dataclass
class DimensionRelationship(AttributeRelationship):
    #:
    dimensions: List[DimensionComponent] = field(default_factory=list)
    #: NB the IM says "0..*" here in a diagram, but the text does not match.
    group_key: Optional["GroupDimensionDescriptor"] = None


@dataclass
class GroupRelationship(AttributeRelationship):
    #: “Retained for compatibility reasons” in SDMX 2.1 versus 2.0; not used by
    #: :mod:`sdmx`.
    group_key: Optional["GroupDimensionDescriptor"] = None


@dataclass
@NameableArtefact._preserve("eq", "hash")
class DataAttribute(Component):
    #:
    related_to: Optional[AttributeRelationship] = None
    #:
    usage_status: Optional[UsageStatus] = None


class AttributeDescriptor(ComponentList[DataAttribute]):
    _Component = DataAttribute


class BaseDataStructureDefinition:
    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two DataStructureDefinitions are the same if each of :attr:`attributes`,
        :attr:`dimensions`, :attr:`measures`, and :attr:`group_dimensions` compares
        equal.

        Parameters
        ----------
        strict : bool, optional
            Passed to :meth:`.ComponentList.compare`.
        """
        return all(
            getattr(self, attr).compare(getattr(other, attr), strict)
            for attr in ("attributes", "dimensions", "measures", "group_dimensions")
        )


###


class _AllDimensions:
    pass


#: A singleton.
AllDimensions = _AllDimensions()

###


class BaseKeyValue:
    pass


# SDMX 2.1 §10.2: Constraint inheritance
# SDMX 3.0 §12: Constraints


@dataclass
class ConstraintRole:
    #:
    role: ConstraintRoleType


class ConstrainableArtefact:
    """SDMX ConstrainableArtefact."""


class SelectionValue:
    """SDMX SelectionValue."""


@dataclass
class MemberValue(SelectionValue):
    #:
    value: str
    #:
    cascade_values: Optional[bool] = None

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return self.value == (other.value if isinstance(other, BaseKeyValue) else other)

    def __repr__(self):
        return f"{repr(self.value)}" + (" + children" if self.cascade_values else "")


class TimeRangeValue(SelectionValue):
    """SDMX TimeRangeValue."""


# Continued now that ConstrainableArtefact is defined


class DataConsumer(Organisation, ConstrainableArtefact):
    """SDMX DataConsumer."""


class DataProvider(Organisation, ConstrainableArtefact):
    """SDMX DataProvider."""


class DataConsumerScheme(OrganisationScheme[DataConsumer]):
    _Item = DataConsumer


class DataProviderScheme(OrganisationScheme[DataProvider]):
    _Item = DataProvider


# Abstract base classes
# - In the order they appear in .v21
class BaseContentConstraint:
    pass


class BaseDataSet(AnnotableArtefact):
    pass


class BaseDataflowDefinition(StructureUsage):
    pass


class BaseMetadataflowDefinition(StructureUsage):
    pass


class BaseProvisionAgreement(MaintainableArtefact):
    pass


# Internal

#: The SDMX-IM defines 'packages'; these are used in URNs.
PACKAGE = dict()

_PACKAGE_CLASS: Dict[str, set] = {
    "base": {"Agency", "AgencyScheme", "DataProvider", "DataProviderScheme"},
    "categoryscheme": {"Category", "Categorisation", "CategoryScheme"},
    "codelist": {"Code", "Codelist"},
    "conceptscheme": {"Concept", "ConceptScheme"},
    "datastructure": {
        "DataflowDefinition",
        "DataStructureDefinition",
        "StructureUsage",
    },
    "metadatastructure": {"MetadataflowDefinition", "MetadataStructureDefinition"},
    "registry": {"ContentConstraint", "ProvisionAgreement"},
}

for package, classes in _PACKAGE_CLASS.items():
    PACKAGE.update({cls: package for cls in classes})


@dataclass
class ClassFinder:
    module_name: str

    @lru_cache()
    def __call__(self, name: Union[str, Resource], package=None) -> Optional[Type]:
        """Return a class for `name` and (optional) `package` names."""
        mod = sys.modules[self.module_name]

        if isinstance(name, Resource):
            # Convert a Resource enumeration value to a string

            # Expected class name in lower case; maybe just the enumeration value
            match = Resource.class_name(name).lower()

            # Match class names in lower case. If no match or >2, only() returns None,
            # and KeyError occurs below
            name = only(filter(lambda g: g.lower() == match, dir(mod)))

        # Change names that differ between URNs and full class names
        name = {
            "Dataflow": "DataflowDefinition",
            "Metadataflow": "MetadataflowDefinition",
        }.get(name, name)

        try:
            cls = getattr(mod, name)
        except (AttributeError, TypeError):
            return None

        if package and package != PACKAGE[cls.__name__]:
            raise ValueError(f"Package {repr(package)} invalid for {name}")

        return cls

    # To allow lru_cache() above
    def __hash__(self):
        return hash(self.module_name)
