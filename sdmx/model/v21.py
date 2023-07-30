"""SDMX 2.1 Information Model (SDMX-IM).

This module implements many of the classes described in the SDMX-IM specification
('spec'), which is available from:

- https://sdmx.org/?page_id=5008
- https://sdmx.org/wp-content/uploads/
    SDMX_2-1-1_SECTION_2_InformationModel_201108.pdf

Details of the implementation:

- Python dataclasses and type hinting are used to enforce the types of attributes that
  reference instances of other classes.
- Some classes have convenience attributes not mentioned in the spec, to ease navigation
  between related objects. These are marked “:mod:`sdmx` extension not in the IM.”
- Class definitions are grouped by section of the spec, but these sections appear out
  of order so that dependent classes are defined first.

"""
import logging
from copy import copy

# TODO for complete implementation of the IM, enforce TimeKeyValue (instead of KeyValue)
#      for {Generic,StructureSpecific} TimeSeriesDataSet.
from dataclasses import InitVar, dataclass, field
from datetime import date, datetime
from itertools import product
from operator import itemgetter
from typing import (
    Any,
    Dict,
    Generator,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from sdmx.util import DictLikeDescriptor, compare

from . import common
from .common import (
    ActionType,
    AttributeDescriptor,
    AttributeRelationship,
    BaseKeyValue,
    Code,
    Component,
    ComponentList,
    ConstrainableArtefact,
    ConstraintRole,
    ConstraintRoleType,
    DataAttribute,
    DataProvider,
    DimensionComponent,
    DimensionDescriptor,
    GroupDimensionDescriptor,
    IdentifiableArtefact,
    MaintainableArtefact,
    MemberValue,
    NameableArtefact,
    SelectionValue,
    Structure,
    StructureUsage,
    TimeDimension,
    TimeRangeValue,
)

# Classes defined directly in the current file, in the order they appear
__all__ = [
    "ComponentValue",
    "DataKey",
    "DataKeySet",
    "Constraint",
    "Period",
    "RangePeriod",
    "MemberSelection",
    "CubeRegion",
    "ContentConstraint",
    "MeasureDimension",
    "PrimaryMeasure",
    "MeasureDescriptor",
    "NoSpecifiedRelationship",
    "PrimaryMeasureRelationship",
    "ReportingYearStartDay",
    "DataStructureDefinition",
    "DataflowDefinition",
    "KeyValue",
    "TimeKeyValue",
    "AttributeValue",
    "Key",
    "GroupKey",
    "SeriesKey",
    "Observation",
    "DataSet",
    "StructureSpecificDataSet",
    "GenericDataSet",
    "GenericTimeSeriesDataSet",
    "StructureSpecificTimeSeriesDataSet",
    "MetadataflowDefinition",
    "MetadataStructureDefinition",
    "Datasource",
    "SimpleDatasource",
    "QueryDatasource",
    "RESTDatasource",
    "ProvisionAgreement",
]

log = logging.getLogger(__name__)


# §10.3: Constraints


@dataclass
class ComponentValue:
    #:
    value_for: Component
    #:
    value: Any


@dataclass
class DataKey:
    #: :obj:`True` if the :attr:`keys` are included in the :class:`.Constraint`;
    # :obj:`False` if they are excluded.
    included: bool
    #: Mapping from :class:`.Component` to :class:`.ComponentValue` comprising the key.
    key_value: Dict[Component, ComponentValue] = field(default_factory=dict)


@dataclass
class DataKeySet:
    #: :obj:`True` if the :attr:`keys` are included in the :class:`.Constraint`;
    #: :obj:`False` if they are excluded.
    included: bool
    #: :class:`DataKeys <.DataKey>` appearing in the set.
    keys: List[DataKey] = field(default_factory=list)

    def __len__(self):
        """:func:`len` of the DataKeySet = :func:`len` of its :attr:`keys`."""
        return len(self.keys)

    def __contains__(self, item):
        return any(item == dk for dk in self.keys)


@dataclass
class Constraint(MaintainableArtefact):
    """SDMX 2.1 Constraint.

    For SDMX 3.0, see :class:`.v30.Constraint`.
    """

    # NB the spec gives 1..* for this attribute, but this implementation allows only 1
    role: Optional[ConstraintRole] = None
    #: :class:`.DataKeySet` included in the Constraint.
    data_content_keys: Optional[DataKeySet] = None
    # metadata_content_keys: MetadataKeySet = None

    def __contains__(self, value):
        if self.data_content_keys is None:
            raise NotImplementedError("Constraint does not contain a DataKeySet")

        return value in self.data_content_keys


@dataclass
class Period:
    is_inclusive: bool
    period: datetime


@dataclass
class RangePeriod(TimeRangeValue):
    start: Period
    end: Period


@dataclass
class MemberSelection:
    #:
    values_for: Component
    #:
    included: bool = True
    #: Value(s) included in the selection. Note that the name of this attribute is not
    #: stated in the IM, so 'values' is chosen for the implementation in this package.
    values: List[SelectionValue] = field(default_factory=list)

    def __contains__(self, value):
        """Compare KeyValue to MemberValue."""
        return any(mv == value for mv in self.values) is self.included

    def __len__(self):
        return len(self.values)

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} {self.values_for.id} "
            f"{'not ' if not self.included else ''}in {{"
            f"{', '.join(map(repr, self.values))}}}>"
        )


# NB CubeRegion and ContentConstraint are moved below, after Dimension, since CubeRegion
#   references that class.


# (continued from §10.3)
@dataclass
class CubeRegion:
    #:
    included: bool = True
    #:
    member: Dict[DimensionComponent, MemberSelection] = field(default_factory=dict)

    def __contains__(self, other: Union["Key", "KeyValue"]) -> bool:
        """Membership test.

        `other` may be either:

        - :class:`.Key` —all its :class:`.KeyValue` are checked.
        - :class:`.KeyValue` —only the one :class:`.Dimension` for which `other` is a
          value is checked

        Returns
        -------
        bool
            :obj:`True` if:

            - :attr:`.included` *and* `other` is in the CubeRegion;
            - if :attr:`.included` is :obj:`False` *and* `other` is outside the
              CubeRegion; or
            - the `other` is KeyValue referencing a Dimension that is not included in
              :attr:`.member`.
        """
        if isinstance(other, Key):
            result = all(other[ms.values_for.id] in ms for ms in self.member.values())
        elif other.value_for is None:
            # No Dimension reference to use
            result = False
        elif other.value_for not in self.member or len(self.member) > 1:
            # This CubeRegion doesn't have a MemberSelection for the KeyValue's
            # Component; or it concerns additional Components, so inclusion can't be
            # determined
            return True
        else:
            # Check whether the KeyValue is in the indicated dimension
            result = other.value in self.member[other.value_for]

        # Return the correct sense
        return result is self.included

    def to_query_string(self, structure):
        all_values = []

        for dim in structure.dimensions:
            if isinstance(dim, TimeDimension):
                # TimeDimensions handled by query parameters
                continue
            ms = self.member.get(dim, None)
            values = sorted(mv.value for mv in ms.values) if ms else []
            all_values.append("+".join(values))

        return ".".join(all_values)

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} {'in' if self.included else 'ex'}clude "
            f"{' '.join(map(repr, self.member.values()))}>"
        )


# (continued from §10.3)
@dataclass
@NameableArtefact._preserve("repr")
class ContentConstraint(Constraint, common.BaseContentConstraint):
    #: :class:`CubeRegions <.CubeRegion>` included in the ContentConstraint.
    data_content_region: List[CubeRegion] = field(default_factory=list)
    #:
    content: Set[ConstrainableArtefact] = field(default_factory=set)
    # metadata_content_region: MetadataTargetRegion = None

    def __contains__(self, value):
        if self.data_content_region:
            return all(value in cr for cr in self.data_content_region)
        else:
            raise NotImplementedError("ContentConstraint does not contain a CubeRegion")

    def to_query_string(self, structure):
        cr_count = len(self.data_content_region)
        try:
            if cr_count > 1:
                log.warning(f"to_query_string() using first of {cr_count} CubeRegions")

            return self.data_content_region[0].to_query_string(structure)
        except IndexError:
            raise RuntimeError("ContentConstraint does not contain a CubeRegion")

    def iter_keys(
        self,
        obj: Union["DataStructureDefinition", "DataflowDefinition"],
        dims: List[str] = [],
    ) -> Generator["Key", None, None]:
        """Iterate over keys.

        A warning is logged if `obj` is not already explicitly associated to this
        ContentConstraint, i.e. present in :attr:`.content`.

        See also
        --------
        .DataStructureDefinition.iter_keys
        """
        if obj not in self.content:
            log.warning(f"{repr(obj)} is not in {repr(self)}.content")

        yield from obj.iter_keys(constraint=self, dims=dims)


class MeasureDimension(DimensionComponent):
    """SDMX 2.1 MeasureDimension.

    This class is not present in SDMX 3.0.
    """


class PrimaryMeasure(Component):
    """SDMX 2.1 PrimaryMeasure.

    This class is not present in SDMX 3.0; see instead :class:`.v30.Measure`.
    """


class MeasureDescriptor(ComponentList[PrimaryMeasure]):
    """SDMX 2.1 MeasureDescriptor.

    For SDMX 3.0; see instead :class:`.v30.MeasureDescriptor`.
    """

    _Component = PrimaryMeasure


class _NoSpecifiedRelationship(AttributeRelationship):
    pass


#: A singleton. Indicates that the attribute is attached to the entire data set.
NoSpecifiedRelationship = _NoSpecifiedRelationship()


class _PrimaryMeasureRelationship(AttributeRelationship):
    pass


#: A singleton.
PrimaryMeasureRelationship = _PrimaryMeasureRelationship()


class ReportingYearStartDay(DataAttribute):
    pass


class _NullConstraintClass:
    """Constraint that allows anything."""

    def __contains__(self, value):
        return True


_NullConstraint = _NullConstraintClass()


@dataclass(repr=False)
class DataStructureDefinition(
    Structure, ConstrainableArtefact, common.BaseDataStructureDefinition
):
    """SDMX 2.1 DataStructureDefinition (‘DSD’)."""

    #: A :class:`AttributeDescriptor` that describes the attributes of the data
    #: structure.
    attributes: AttributeDescriptor = field(default_factory=AttributeDescriptor)
    #: A :class:`DimensionDescriptor` that describes the dimensions of the data
    #: structure.
    dimensions: DimensionDescriptor = field(default_factory=DimensionDescriptor)
    #: A :class:`.MeasureDescriptor`.
    measures: MeasureDescriptor = field(default_factory=MeasureDescriptor)
    #: Mapping from  :attr:`.GroupDimensionDescriptor.id` to
    #: :class:`.GroupDimensionDescriptor`.
    group_dimensions: DictLikeDescriptor[
        str, GroupDimensionDescriptor
    ] = DictLikeDescriptor()

    __hash__ = IdentifiableArtefact.__hash__

    # Convenience methods
    def iter_keys(
        self, constraint: Optional[Constraint] = None, dims: List[str] = []
    ) -> Generator["Key", None, None]:
        """Iterate over keys.

        Parameters
        ----------
        constraint : Constraint, optional
            If given, only yield Keys that are within the constraint.
        dims : list of str, optional
            If given, only iterate over allowable values for the Dimensions with these
            IDs. Other dimensions have only a single value like "(DIM_ID)", where
            DIM_ID is the ID of the dimension.
        """
        # NB for performance, the implementation tries to use iterators and avoid
        #    constructing full-length tuples/lists at any point

        _constraint = constraint or _NullConstraint
        dims = dims or [dim.id for dim in self.dimensions.components]

        # Utility to return an immutable function that produces KeyValues. The
        # arguments are frozen so these can be set using loop variables and stored in a
        # map() object that isn't modified on future loops
        def make_factory(id=None, value_for=None):
            return lambda value: KeyValue(id=id, value=value, value_for=value_for)

        # List of iterables of (dim.id, KeyValues) along each dimension
        all_kvs: List[Iterable[KeyValue]] = []

        # Iterate over dimensions
        for dim in self.dimensions.components:
            if (
                dim.id not in dims
                or dim.local_representation is None
                or dim.local_representation.enumerated is None
            ):
                # `dim` is not enumerated by an ItemScheme, or not included in the
                # `dims` argument and not to be iterated over. Create a placeholder.
                all_kvs.append(
                    [KeyValue(id=dim.id, value=f"({dim.id})", value_for=dim)]
                )
            else:
                # Create a KeyValue for each Item in the ItemScheme; filter through any
                # constraint.
                all_kvs.append(
                    filter(
                        _constraint.__contains__,
                        map(
                            make_factory(id=dim.id, value_for=dim),
                            dim.local_representation.enumerated,
                        ),
                    ),
                )

        # Create Key objects from Cartesian product of KeyValues along each dimension
        # NB this does not work with DataKeySet
        # TODO improve to work with DataKeySet
        yield from filter(_constraint.__contains__, map(Key, product(*all_kvs)))

    def make_constraint(self, key):
        """Return a constraint for `key`.

        `key` is a :class:`dict` wherein:

        - keys are :class:`str` ids of Dimensions appearing in this DSD's
          :attr:`dimensions`, and
        - values are '+'-delimited :class:`str` containing allowable values, *or*
          iterables of :class:`str`, each an allowable value.

        For example::

            cc2 = dsd.make_constraint({'foo': 'bar+baz', 'qux': 'q1+q2+q3'})

        ``cc2`` includes any key where the 'foo' dimension is 'bar' *or* 'baz', *and*
        the 'qux' dimension is one of 'q1', 'q2', or 'q3'.

        Returns
        -------
        ContentConstraint
            A constraint with one :class:`CubeRegion` in its
            :attr:`data_content_region <ContentConstraint.data_content_region>` ,
            including only the values appearing in `key`.

        Raises
        ------
        ValueError
            if `key` contains a dimension IDs not appearing in :attr:`dimensions`.
        """
        # Make a copy to avoid pop()'ing off the object in the calling scope
        key = key.copy()

        cr = CubeRegion()
        for dim in self.dimensions:
            mvs = set()
            try:
                values = key.pop(dim.id)
            except KeyError:
                continue

            values = values.split("+") if isinstance(values, str) else values
            for value in values:
                # TODO validate values
                mvs.add(MemberValue(value=value))

            cr.member[dim] = MemberSelection(included=True, values_for=dim, values=mvs)

        if len(key):
            raise ValueError(
                "Dimensions {!r} not in {!r}".format(list(key.keys()), self.dimensions)
            )

        return ContentConstraint(
            data_content_region=[cr],
            role=ConstraintRole(role=ConstraintRoleType.allowable),
        )

    @classmethod
    def from_keys(cls, keys):
        """Return a new DSD given some *keys*.

        The DSD's :attr:`dimensions` refers to a set of new :class:`Concepts <Concept>`
        and :class:`Codelists <Codelist>`, created to represent all the values observed
        across *keys* for each dimension.

        Parameters
        ----------
        keys : iterable of :class:`Key`
            or of subclasses such as :class:`SeriesKey` or :class:`GroupKey`.
        """
        iter_keys = iter(keys)
        dd = DimensionDescriptor.from_key(next(iter_keys))

        for k in iter_keys:
            for i, (id, kv) in enumerate(k.values.items()):
                try:
                    dd[i].local_representation.enumerated.append(Code(id=str(kv.value)))
                except ValueError:
                    pass  # Item already exists

        return cls(dimensions=dd)

    def make_key(self, key_cls, values: Mapping, extend=False, group_id=None):
        """Make a :class:`.Key` or subclass.

        Parameters
        ----------
        key_cls : Key or SeriesKey or GroupKey
            Class of Key to create.
        values : dict
            Used to construct :attr:`.Key.values`.
        extend : bool, optional
            If :obj:`True`, make_key will not return :class:`KeyError` on missing
            dimensions. Instead :attr:`dimensions` (`key_cls` is Key or SeriesKey) or
            :attr:`group_dimensions` (`key_cls` is GroupKey) will be extended by
            creating new Dimension objects.
        group_id : str, optional
            When `key_cls` is :class`.GroupKey`, the ID of the
            :class:`.GroupDimensionDescriptor` that structures the key.

        Returns
        -------
        Key
            An instance of `key_cls`.

        Raises
        ------
        KeyError
            If any of the keys of `values` is not a Dimension or Attribute in the DSD.
        """
        # Methods to get dimensions and attributes
        get_method = "getdefault" if extend else "get"
        dim = getattr(self.dimensions, get_method)
        attr = getattr(self.attributes, get_method)

        # Arguments for creating the Key
        args: Dict[str, Any] = dict(described_by=self.dimensions)

        if key_cls is GroupKey:
            # Get the GroupDimensionDescriptor, if indicated by group_id
            gdd = self.group_dimensions.get(group_id, None)

            if group_id and not gdd and not extend:
                # Cannot create
                raise KeyError(group_id)
            elif group_id and extend:
                # Create the GDD
                gdd = GroupDimensionDescriptor(id=group_id)
                self.group_dimensions[gdd.id] = gdd

                # GroupKey will have same ID and be described by the GDD
                args = dict(id=group_id, described_by=gdd)

                # Dimensions to be retrieved from the GDD
                def dim(id):
                    # Get from the DimensionDescriptor
                    new_dim = self.dimensions.getdefault(id)
                    # Add to the GDD
                    gdd.components.append(new_dim)
                    return gdd.get(id)

            else:
                # Not described by anything
                args = dict()

        key = key_cls(**args)

        # Convert keyword arguments to either KeyValue or AttributeValue
        keyvalues = []
        for order, (id, value) in enumerate(values.items()):
            if id in self.attributes.components:
                # Reference a DataAttribute from the AttributeDescriptor
                da = attr(id)
                # Store the attribute value, referencing da
                key.attrib[da.id] = AttributeValue(value=value, value_for=da)
                continue

            # Reference a Dimension from the DimensionDescriptor. If extend=False and
            # the Dimension does not exist, this will raise KeyError
            args = dict(id=id, value=value, value_for=dim(id))

            # Retrieve the order
            order = args["value_for"].order

            # Store a KeyValue, to be sorted later
            keyvalues.append((order, KeyValue(**args)))

        # Sort the values according to *order*
        key.values.update({kv.id: kv for _, kv in sorted(keyvalues)})

        return key


@dataclass(repr=False)
@IdentifiableArtefact._preserve("hash")
class DataflowDefinition(common.BaseDataflowDefinition):
    #:
    structure: DataStructureDefinition = field(default_factory=DataStructureDefinition)

    def iter_keys(
        self, constraint: Optional[Constraint] = None, dims: List[str] = []
    ) -> Generator["Key", None, None]:
        """Iterate over keys.

        See also
        --------
        .DataStructureDefinition.iter_keys
        """
        yield from self.structure.iter_keys(constraint=constraint, dims=dims)


# §5.4: Data Set


def value_for_dsd_ref(kind, args, kwargs):
    """Maybe replace a string 'value_for' in *kwargs* with a DSD reference."""
    try:
        dsd = kwargs.pop("dsd")
        descriptor = getattr(dsd, kind + "s")
        kwargs["value_for"] = descriptor.get(kwargs["value_for"])
    except KeyError:
        pass
    return args, kwargs


@dataclass
class KeyValue(BaseKeyValue):
    """One value in a multi-dimensional :class:`Key`."""

    #:
    id: str
    #: The actual value.
    value: Any
    #:
    value_for: Optional[DimensionComponent] = None

    dsd: InitVar[DataStructureDefinition] = None

    def __post_init__(self, dsd):
        if dsd:
            self.value_for = getattr(dsd, "dimensions").get(self.value_for)

    def __eq__(self, other):
        """Compare the value to a simple Python built-in type or other key-like.

        `other` may be :class:`.KeyValue` or :class:`.ComponentValue`; if so, and both
        `self` and `other` have :attr:`.value_for`, these must refer to the same object.
        """
        other_value = self._compare_value(other)
        result = self.value == other_value
        if isinstance(other, (KeyValue, ComponentValue)):
            result &= (
                self.value_for in (None, other.value_for) or other.value_for is None
            )
        return result

    @staticmethod
    def _compare_value(other):
        if isinstance(other, (KeyValue, ComponentValue, MemberValue)):
            return other.value
        else:
            return other

    def __lt__(self, other):
        return self.value < self._compare_value(other)

    def __str__(self):
        return f"{self.id}={self.value}"

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id}={self.value}>"

    def __hash__(self):
        # KeyValue instances with the same id & value hash identically
        return hash(self.id + str(self.value))


#: Synonym for :class:`.KeyValue`.
TimeKeyValue = KeyValue


@dataclass
class AttributeValue:
    """SDMX 2.1 AttributeValue.

    In the spec, AttributeValue is an abstract class. Here, it serves as both the
    concrete subclasses CodedAttributeValue and UncodedAttributeValue.
    """

    # TODO separate and enforce properties of Coded- and UncodedAttributeValue
    #:
    value: Union[str, Code]
    #:
    value_for: Optional[DataAttribute] = None
    #:
    start_date: Optional[date] = None

    dsd: InitVar[DataStructureDefinition] = None

    def __post_init__(self, dsd):
        if dsd:
            self.value_for = getattr(dsd, "attributes").get(self.value_for)

    def __eq__(self, other):
        """Compare the value to a Python built-in type, e.g. str."""
        return self.value == other

    def __str__(self):
        # self.value directly for UncodedAttributeValue
        return self.value if isinstance(self.value, str) else self.value.id

    def __repr__(self):
        return "<{}: {}={}>".format(self.__class__.__name__, self.value_for, self.value)

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two AttributeValues are equal if their properties are equal.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare`.
        """
        return all(
            compare(attr, self, other, strict)
            for attr in ["start_date", "value", "value_for"]
        )


@dataclass
class Key:
    """SDMX Key class.

    The constructor takes an optional list of keyword arguments; the keywords are used
    as Dimension or Attribute IDs, and the values as KeyValues.

    For convenience, the values of the key may be accessed directly:

    >>> k = Key(foo=1, bar=2)
    >>> k.values['foo']
    1
    >>> k['foo']
    1

    Parameters
    ----------
    dsd : DataStructureDefinition
        If supplied, the :attr:`~.DataStructureDefinition.dimensions` and
        :attr:`~.DataStructureDefinition.attributes` are used to separate the `kwargs`
        into :class:`KeyValues <.KeyValue>` and
        :class:`AttributeValues <.AttributeValue>`. The `kwargs` for
        :attr:`described_by`, if any, must be
        :attr:`~.DataStructureDefinition.dimensions` or appear in
        :attr:`~.DataStructureDefinition.group_dimensions`.
    kwargs
        Dimension and Attribute IDs, and/or the class properties.

    """

    #:
    attrib: DictLikeDescriptor[str, AttributeValue] = DictLikeDescriptor()
    #:
    described_by: Optional[DimensionDescriptor] = None
    #: Individual KeyValues that describe the key.
    values: DictLikeDescriptor[str, KeyValue] = DictLikeDescriptor()

    def __init__(self, arg: Union[Mapping, Sequence[KeyValue], None] = None, **kwargs):
        # Handle kwargs corresponding to attributes
        self.attrib.update(kwargs.pop("attrib", {}))

        # DimensionDescriptor
        dd = kwargs.pop("described_by", None)
        self.described_by = dd

        if arg and isinstance(arg, Mapping):
            if len(kwargs):
                raise ValueError(
                    "Key() accepts either a single argument, or keyword arguments; not "
                    "both."
                )
            kwargs.update(arg)

        kvs: Iterable[Tuple] = []

        if isinstance(arg, Sequence):
            # Sequence of already-prepared KeyValues; assume already sorted
            kvs = map(lambda kv: (kv.id, kv), arg)
        else:
            # Convert bare keyword arguments to KeyValue
            _kvs = []
            for order, (id, value) in enumerate(kwargs.items()):
                args = dict(id=id, value=value)
                if dd:
                    # Reference the Dimension
                    args["value_for"] = dd.get(id)
                    # Use the existing Dimension's order attribute
                    order = args["value_for"].order

                # Store a KeyValue, to be sorted later
                _kvs.append((order, (id, KeyValue(**args))))

            # Sort the values according to *order*, then unwrap
            kvs = map(itemgetter(1), sorted(_kvs))

        self.values.update(kvs)

    def __len__(self):
        """The length of the Key is the number of KeyValues it contains."""
        return len(self.values)

    def __contains__(self, other):
        """A Key contains another if it is a superset."""
        try:
            return all([self.values[k] == v for k, v in other.values.items()])
        except KeyError:
            # 'k' in other does not appear in this Key()
            return False

    def __iter__(self):
        yield from self.values.values()

    # Convenience access to values by name
    def __getitem__(self, name):
        return self.values[name]

    def __setitem__(self, name, value):
        # Convert a bare string or other Python object to a KeyValue instance
        if not isinstance(value, KeyValue):
            value = KeyValue(id=name, value=value)
        self.values[name] = value

    # Convenience access to values by attribute
    def __getattr__(self, name):
        try:
            return self.values[name]
        except KeyError:
            raise AttributeError(name)

    # Copying
    def __copy__(self):
        result = Key()
        if self.described_by:
            result.described_by = self.described_by
        for kv in self.values.values():
            result[kv.id] = kv
        return result

    def copy(self, arg=None, **kwargs):
        result = copy(self)
        for id, value in kwargs.items():
            result[id] = value
        return result

    def __add__(self, other):
        if other is None:
            other_values = dict()
        elif not isinstance(other, Key):
            raise NotImplementedError
        else:
            other_values = other.values
        result = copy(self)
        for id, value in other_values.items():
            result[id] = value
        return result

    def __radd__(self, other):
        if other is None:
            return copy(self)
        else:
            raise NotImplementedError

    def __eq__(self, other):
        if hasattr(other, "values"):
            # Key
            return all(
                [a == b for a, b in zip(self.values.values(), other.values.values())]
            )
        elif hasattr(other, "key_value"):
            # DataKey
            return all(
                [a == b for a, b in zip(self.values.values(), other.key_value.values())]
            )
        elif isinstance(other, str) and len(self.values) == 1:
            return self.values[0] == other
        else:
            raise ValueError(other)

    def __hash__(self):
        # Hash of the individual KeyValues, in order
        return hash(tuple(hash(kv) for kv in self.values.values()))

    # Representations

    def __str__(self):
        return "({})".format(", ".join(map(str, self.values.values())))

    def __repr__(self):
        return "<{}: {}>".format(
            self.__class__.__name__, ", ".join(map(str, self.values.values()))
        )

    def order(self, value=None):
        if value is None:
            value = self
        try:
            return self.described_by.order_key(value)
        except AttributeError:
            return value

    def get_values(self):
        return tuple([kv.value for kv in self.values.values()])


class GroupKey(Key):
    #:
    id: Optional[str] = None
    #:
    described_by: Optional[GroupDimensionDescriptor] = None

    def __init__(self, arg: Optional[Mapping] = None, **kwargs):
        # Remove the 'id' keyword argument
        id = kwargs.pop("id", None)
        super().__init__(arg, **kwargs)
        self.id = id


@dataclass
class SeriesKey(Key):
    #: :mod:`sdmx` extension not in the IM.
    group_keys: Set[GroupKey] = field(default_factory=set)

    __eq__ = Key.__eq__
    __hash__ = Key.__hash__
    __repr__ = Key.__repr__

    @property
    def group_attrib(self):
        """Return a view of attributes on all :class:`GroupKey` including the series."""
        # Needed to pass existing tests
        view = dict()
        for gk in self.group_keys:
            view.update(gk.attrib)
        return view


@dataclass
class Observation:
    """SDMX 2.1 Observation.

    This class also implements the IM classes ObservationValue, UncodedObservationValue,
    and CodedObservation.
    """

    #:
    attached_attribute: DictLikeDescriptor[str, AttributeValue] = DictLikeDescriptor()
    #:
    series_key: Optional[SeriesKey] = None
    #: Key for dimension(s) varying at the observation level.
    dimension: Optional[Key] = None
    #: Data value.
    value: Optional[Union[Any, Code]] = None
    #:
    value_for: Optional[PrimaryMeasure] = None
    #: :mod:`sdmx` extension not in the IM.
    group_keys: Set[GroupKey] = field(default_factory=set)

    @property
    def attrib(self):
        """Return a view of combined observation, series & group attributes."""
        view = self.attached_attribute.copy()
        view.update(getattr(self.series_key, "attrib", {}))
        for gk in self.group_keys:
            view.update(gk.attrib)
        return view

    @property
    def dim(self):
        return self.dimension

    @property
    def key(self):
        """Return the entire key, including KeyValues at the series level."""
        return (self.series_key or SeriesKey()) + self.dimension

    def __len__(self):
        # FIXME this is unintuitive; maybe deprecate/remove?
        return len(self.key)

    def __str__(self):
        return "{0.key}: {0.value}".format(self)

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two Observations are equal if:

        - their :attr:`dimension`, :attr:`value`, :attr:`series_key`, and
          :attr:`value_for` are all equal,
        - their corresponding :attr:`attached_attribute` and :attr:`group_keys` are all
          equal.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare`.
        """
        return (
            all(
                compare(attr, self, other, strict)
                for attr in ["dimension", "series_key", "value", "value_for"]
            )
            and self.attached_attribute.compare(other.attached_attribute)
            and self.group_keys == other.group_keys
        )


@dataclass
class DataSet(common.BaseDataSet):
    # SDMX-IM features

    #:
    action: Optional[ActionType] = None
    #:
    attrib: DictLikeDescriptor[str, AttributeValue] = DictLikeDescriptor()
    #:
    valid_from: Optional[str] = None
    #:
    described_by: Optional[DataflowDefinition] = None
    #:
    structured_by: Optional[DataStructureDefinition] = None

    #: All observations in the DataSet.
    obs: List[Observation] = field(default_factory=list)

    #: Map of series key → list of observations.
    #: :mod:`sdmx` extension not in the IM.
    series: DictLikeDescriptor[SeriesKey, List[Observation]] = DictLikeDescriptor()
    #: Map of group key → list of observations.
    #: :mod:`sdmx` extension not in the IM.
    group: DictLikeDescriptor[GroupKey, List[Observation]] = DictLikeDescriptor()

    def __post_init__(self):
        if self.action and not isinstance(self.action, ActionType):
            self.action = ActionType[self.action]

    def __len__(self):
        return len(self.obs)

    def _add_group_refs(self, target):
        """Associate *target* with groups in this dataset.

        *target* may be an instance of SeriesKey or Observation.
        """
        for group_key in self.group:
            if group_key in (target if isinstance(target, SeriesKey) else target.key):
                target.group_keys.add(group_key)
                if isinstance(target, Observation):
                    self.group[group_key].append(target)

    def add_obs(self, observations, series_key=None):
        """Add *observations* to a series with *series_key*.

        Checks consistency and adds group associations."""
        if series_key is not None:
            # Associate series_key with any GroupKeys that apply to it
            self._add_group_refs(series_key)
            # Maybe initialize empty series
            self.series.setdefault(series_key, [])

        for obs in observations:
            # Associate the observation with any GroupKeys that contain it
            self._add_group_refs(obs)

            # Store a reference to the observation
            self.obs.append(obs)

            if series_key is not None:
                if obs.series_key is None:
                    # Assign the observation to the SeriesKey
                    obs.series_key = series_key
                else:
                    # Check that the Observation is not associated with a different
                    # SeriesKey
                    assert obs.series_key is series_key

                # Store a reference to the observation
                self.series[series_key].append(obs)

    def __str__(self):
        return (
            f"<DataSet structured_by={self.structured_by!r} with {len(self)} "
            "observations>"
        )

    def compare(self, other, strict=True):
        """Return :obj:`True` if `self` is the same as `other`.

        Two DataSets are the same if:

        - their :attr:`action`, :attr:`valid_from` compare equal.
        - all dataset-level attached attributes compare equal.
        - they have the same number of observations, series, and groups.

        Parameters
        ----------
        strict : bool, optional
            Passed to :func:`.compare`.
        """
        return (
            compare("action", self, other, strict)
            and compare("valid_from", self, other, strict)
            and self.attrib.compare(other.attrib, strict)
            and len(self.obs) == len(other.obs)
            and len(self.series) == len(other.series)
            and len(self.group) == len(other.group)
            and all(o[0].compare(o[1], strict) for o in zip(self.obs, other.obs))
        )


class StructureSpecificDataSet(DataSet):
    """SDMX 2.1 StructureSpecificDataSet.

    This subclass has no additional functionality compared to DataSet.
    """


class GenericDataSet(DataSet):
    """SDMX 2.1 GenericDataSet.

    This subclass has no additional functionality compared to DataSet.
    """


class GenericTimeSeriesDataSet(DataSet):
    """SDMX 2.1 GenericTimeSeriesDataSet.

    This subclass has no additional functionality compared to DataSet.
    """


class StructureSpecificTimeSeriesDataSet(DataSet):
    """SDMX 2.1 StructureSpecificTimeSeriesDataSet.

    This subclass has no additional functionality compared to DataSet.
    """


# §7.3 Metadata Structure Definition


class MetadataflowDefinition(common.BaseMetadataflowDefinition, ConstrainableArtefact):
    """SDMX 2.1 MetadataflowDefinition."""


class MetadataStructureDefinition(Structure, ConstrainableArtefact):
    """SDMX 2.1 MetadataStructureDefinition."""


# §11: Data Provisioning


class Datasource:
    url: str


class SimpleDatasource(Datasource):
    pass


class QueryDatasource(Datasource):
    # Abstract.
    # NB the SDMX-IM inconsistently uses this name and 'WebServicesDatasource'.
    pass


class RESTDatasource(QueryDatasource):
    pass


@dataclass
class ProvisionAgreement(common.BaseProvisionAgreement, ConstrainableArtefact):
    #:
    structure_usage: Optional[StructureUsage] = None
    #:
    data_provider: Optional[DataProvider] = None


def parent_class(cls):
    """Return the class that contains objects of type `cls`.

    E.g. if `cls` is :class:`.PrimaryMeasure`, returns :class:`.MeasureDescriptor`.
    """
    return {
        common.Agency: common.AgencyScheme,
        common.Category: common.CategoryScheme,
        Code: common.Codelist,
        common.Concept: common.ConceptScheme,
        common.Dimension: DimensionDescriptor,
        DataProvider: common.DataProviderScheme,
        GroupDimensionDescriptor: DataStructureDefinition,
        PrimaryMeasure: MeasureDescriptor,
    }[cls]


def __dir__():
    return sorted(__all__ + common.__all__)


def __getattr__(name):
    return getattr(common, name)


get_class = common.ClassFinder(__name__)
