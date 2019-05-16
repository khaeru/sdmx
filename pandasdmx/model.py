"""SDMX Information Model (SDMX-IM).

This module implements many of the classes described in the SDMX-IM
specification ('spec'), which is available from:

- https://sdmx.org/?page_id=5008
- https://sdmx.org/wp-content/uploads/
    SDMX_2-1-1_SECTION_2_InformationModel_201108.pdf

Details of the implementation:

- Python typing and pydantic are used to enforce the types of attributes
  that reference instances of other classes.
- some classes have additional attributes not mentioned in the spec, to ease
  navigation between related objects. These are marked with comments "pandaSDMX
  extensions not in the IM".
- class definitions are grouped by section of the spec, but these sections
  appear out of order so that dependent classes are defined first.

"""
# TODO for a complete implementation of the spec
# - Enforce TimeKeyValue (instead of KeyValue) for {Generic,StructureSpecific}
#   TimeSeriesDataSet.
#
# TODO for convenience
# - Guess URNs using the standard format.

from copy import copy
from datetime import date, datetime, timedelta
from enum import Enum
from inspect import isclass
from operator import attrgetter
from typing import (
    Any,
    Dict,
    List,
    NewType,
    Optional,
    Set,
    Union,
    )

from pandasdmx.util import (
    BaseModel,
    DictLike,
    get_class_hint,
    validate_dictlike,
    )
from pydantic import validator


# TODO read this from the environment, or use any value set in the SDMX XML
# spec. Currently set to 'en' because test_dsd.py expects it
DEFAULT_LOCALE = 'en'


# 3.2: Base structures

class InternationalString:
    """SDMX-IM InternationalString.

    SDMX-IM LocalisedString is not implemented. Instead, the 'localizations' is
    a mapping where:

     - keys correspond to the 'locale' property of LocalisedString.
     - values correspond to the 'label' property of LocalisedString.
    """
    localizations: Dict[str, str] = {}

    def __init__(self, value=None, **kwargs):
        super().__init__()

        if isinstance(value, str):
            value = {DEFAULT_LOCALE: value}
        elif isinstance(value, tuple) and len(value) == 2:
            value = {value[0]: value[1]}
        elif value is None:
            value = dict(kwargs)
        else:
            raise ValueError(value, kwargs)

        self.localizations = value

    # Convenience access
    def __getitem__(self, locale):
        return self.localizations[locale]

    def __setitem__(self, locale, label):
        self.localizations[locale] = label

    # Duplicate of __getitem__, to pass existing tests in test_dsd.py
    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            try:
                return self.__dict__['localizations'][name]
            except KeyError:
                raise AttributeError(name)

    def __add__(self, other):
        result = copy(self)
        result.localizations.update(other.localizations)
        return result

    def localized_default(self, locale):
        """Return the string in *locale*, or else the first defined."""
        try:
            return self.localizations[locale]
        except KeyError:
            if len(self.localizations):
                # No label in the default locale; use the first stored value
                return next(iter(self.localizations.values()))
            else:
                return ''

    def __str__(self):
        return self.localized_default(DEFAULT_LOCALE)

    def __repr__(self):
        return '\n'.join(['{}: {}'.format(*kv) for kv in
                          sorted(self.localizations.items())])

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, values, field):
        if not isinstance(value, InternationalString):
            value = InternationalString(value)

        # Maybe update existing value
        try:
            existing = values[field.name]
        except KeyError:
            existing = None
        if isinstance(existing, InternationalString):
            existing.localizations.update(value.localizations)
            return existing
        else:
            return value



class InternationalStringTrait():
    """Trait type for InternationalString.

    With trailets.Instance, a locale must be provided for every label:

    >>> class Foo(BaseModel):
    >>>     name = Instance(InternationalString)
    >>>
    >>> f = Foo()
    >>> f.name['en'] = "Foo's name in English"

    With InternationalStringTrait, the DEFAULT_LOCALE is automatically selected
    when setting with a string:

    >>> class Bar(BaseModel):
    >>>     name = InternationalStringTrait
    >>>
    >>> b = Bar()
    >>> b.name = "Bar's name in English"

    """
    # TODO preserve docstring; delete class
    pass


class Annotation(BaseModel):
    id: str = None
    title: str = None
    type: str = None
    url: str = None

    text: InternationalString = InternationalString()


class AnnotableArtefact(BaseModel):
    annotations: List[Annotation] = []


class IdentifiableArtefact(AnnotableArtefact):
    """SDMX-IM IdentifiableArtefact."""
    id: str = None
    uri: str = None
    urn: str = None

    def __eq__(self, other):
        """Equality comparison.

        IdentifiableArtefacts can be compared to other instances. For
        convenience, a string containing the object's ID is also equal to the
        object.
        """
        if isinstance(other, self.__class__):
            return self.id == other.id
        elif isinstance(other, str):
            return self.id == other

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        return self.id if self.id else '<missing id>'

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.id)


class NameableArtefact(IdentifiableArtefact):
    name: InternationalString = InternationalString()
    description: InternationalString = InternationalString()

    def __repr__(self):
        return "<{}: '{}'='{}'>".format(
            self.__class__.__name__,
            self.id,
            str(self.name))


class VersionableArtefact(NameableArtefact):
    version: str = None
    valid_from: str = None
    valid_to: str = None


class MaintainableArtefact(VersionableArtefact):
    is_final: Optional[bool]
    is_external_reference: Optional[bool]
    service_url: Optional[str]
    structure_url: Optional[str]
    maintainer: Optional['Agency']


# 3.4: Data Types

ActionType = Enum('ActionType', 'delete replace append information', type=str)

UsageStatus = Enum('UsageStatus', 'mandatory conditional')

# NB three diagrams in the spec show this enumeration containing
#    'gregorianYearMonth' but not 'gregorianYear' or 'gregorianMonth'. The
#    table in §3.6.3.3 Representation Constructs does the opposite. One ESTAT
#    query (via SGR) shows a real-world usage of 'gregorianYear', so the table
#    is followed.
FacetValueType = Enum(
    'FacetValueType',
    """string bigInteger integer long short decimal float double boolean uri
    count inclusiveValueRange alpha alphaNumeric numeric exclusiveValueRange
    incremental observationalTimePeriod standardTimePeriod basicTimePeriod
    gregorianTimePeriod gregorianYear gregorianMonth gregorianDay
    reportingTimePeriod reportingYear reportingSemester reportingTrimester
    reportingQuarter reportingMonth reportingWeek reportingDay dateTime
    timesRange month monthDay day time duration keyValues identifiableReference
    dataSetReference""")

ConstraintRoleType = Enum('ConstraintRoleType', 'allowable actual')


# 3.5: Item Scheme

class Item(NameableArtefact):
    parent: 'Item' = None
    child: List['Item'] = []

    class Config:
        validate_assignment_exclude = 'parent'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add this Item as a child of its parent
        parent = kwargs.get('parent', None)
        if parent and self not in parent.child:
            parent.child.append(self)

        # Add this Item as a parent of its children
        for c in kwargs.get('child', []):
            c.parent = self

    def __contains__(self, item):
        """Recursive containment."""
        for c in self.child:
            if item == c or item in c:
                return True

    def get_child(self, id):
        """Return the child with the given *id*."""
        for c in self.child:
            if c.id == id:
                return c
        raise ValueError(id)


Item.update_forward_refs()


class ItemScheme(MaintainableArtefact):
    is_partial: Optional[bool]
    items: List[Item] = []

    # Convenience access to items
    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError:
            # Provided to pass test_dsd.py
            return self.__getitem__(name)

    def __getitem__(self, name):
        for i in self.items:
            if i.id == name:
                return i
        raise KeyError(name)

    def __contains__(self, item):
        """Recursive containment."""
        for i in self.items:
            if item == i or item in i:
                return True

    def __repr__(self):
        return "<{}: '{}', {} items>".format(
            self.__class__.__name__,
            self.id,
            len(self.items))

    def setdefault(self, obj=None, **kwargs):
        """Retrieve the item *name*, or add it with *kwargs* and return it.

        The returned object is a reference to an object in the ItemScheme, and
        is of the appropriate class.
        """
        if obj:
            assert not len(kwargs), ValueError('cannot give both *obj* and '
                                               'keyword arguments to '
                                               'setdefault()')
        else:
            # Replace a string 'parent' ID with a reference to the object
            parent = kwargs.pop('parent', None)
            if isinstance(parent, str):
                kwargs['parent'] = self[parent]

            # Instantiate an object of the correct class by introspecting
            # the items hint
            obj = get_class_hint(self, 'items')(**kwargs)

        if obj not in self.items:
            # Add the object to the ItemScheme
            self.items.append(obj)

        return obj


# 3.6: Structure

class FacetType(BaseModel):
    is_sequence: Optional[bool]
    min_length: Optional[int]
    max_length: Optional[int]
    min_value: Optional[float]
    max_value: Optional[float]
    start_value: Optional[float]
    end_value: Optional[str]
    interval: Optional[float]
    time_interval: Optional[timedelta]
    decimals: Optional[int]
    pattern: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]


class Facet(BaseModel):
    type: FacetType = FacetType()
    value: str = None
    value_type: Optional[FacetValueType] = None


class Representation(BaseModel):
    enumerated: ItemScheme = None
    non_enumerated: List[Facet] = []

    def __repr__(self):
        return '<{}: {}, {}>'.format(self.__class__.__name__,
                                     self.enumerated,
                                     self.non_enumerated)


# 4.4: Concept Scheme

class ISOConceptReference(BaseModel):
    agency: str
    id: str
    scheme_id: str


class Concept(Item):
    core_representation: Representation = None
    iso_concept: ISOConceptReference = None


class ConceptScheme(ItemScheme):
    items: List[Concept] = []


# 3.3: Basic Inheritance

class Component(IdentifiableArtefact):
    concept_identity: Concept = None
    local_representation: Representation = None

    def __contains__(self, value):
        for repr in [self.concept_identity.core_representation,
                     self.local_representation]:
            enum = getattr(repr, 'enumerated', None)
            if enum is not None:
                return value in enum
        raise TypeError('membership not defined for non-enumerated'
                        'representations')


class ComponentList(IdentifiableArtefact):
    components: List[Component] = []

    # Convenience access to the components
    def append(self, value):
        self.components.append(value)

    def get(self, id, **kwargs):
        """Return or create the component with the given *id*.

        The *kwargs* are passed to the constructor of Component(), or a
        subclass if 'components' is overridden in a subclass of ComponentList.
        """
        # TODO use an index to speed up
        # TODO don't return missing items or add an option to avoid this

        # Chose an appropriate class specified for the attribute in the
        # ComponentList subclass.
        klass = get_class_hint(self, 'components')

        # Create the candidate
        candidate = klass(id=id, **kwargs)

        # Search for a match
        for c in self.components:
            if c == candidate:
                # Same Component, difference instance. Discard the candidate
                return c

        # No match; store and return the candidate
        self.components.append(candidate)
        return candidate

    # Properties of components
    def __getitem__(self, key):
        """Convenience access to components."""
        return self.components[key]

    def __len__(self):
        return len(self.components)

    def __iter__(self):
        return iter(self.components)

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__,
                                 '; '.join(map(repr, self.components)))


# 4.3: Codelist

class Code(Item):
    pass


class Codelist(ItemScheme):
    items: List[Code] = []


# 4.5: Category Scheme

class Category(Item):
    pass


class CategoryScheme(ItemScheme):
    items: List[Category] = []


class Categorisation(MaintainableArtefact):
    category: Category = None
    artefact: IdentifiableArtefact = None


# 4.6: Organisations

class Contact(BaseModel):
    """Organization contact information.

    IMF is the only data provider that returns messages with :class:`Contact`
    information. These differ from the IM in several ways. This class reflects
    these differences:

    - 'name' and 'org_unit' are InternationalString, instead of strings.
    - 'email' may be a list of e-mail addresses, rather than a single address.
    - 'uri' may be a list of URIs, rather than a single URI.
    """
    name: InternationalString = InternationalString()
    org_unit: InternationalString = InternationalString()
    telephone: str = None
    responsibility: InternationalString = InternationalString()
    email: List[str]
    uri: List[str]


class Organisation(Item):
    contact: List[Contact] = []


Agency = Organisation
DataProvider = Organisation


# Update forward references to 'Agency'
for cls in list(locals().values()):
    if isclass(cls) and issubclass(cls, MaintainableArtefact):
        cls.update_forward_refs()


# Skip the abstract OrganisationScheme class, since it has no particular
# functionality

class AgencyScheme(ItemScheme):
    items: List[Agency] = []


class DataProviderScheme(ItemScheme):
    items: List[DataProvider] = []


# 10.2: Constraint inheritance

class ConstrainableArtefact(BaseModel):
    pass


# 10.3: Constraints

class ConstraintRole(BaseModel):
    role: ConstraintRoleType


class ComponentValue(BaseModel):
    value_for: Component
    value: str


class DataKey(BaseModel):
    included: bool
    key_value: Dict[Component, ComponentValue]

    def __init__(self, *args):
        for component, value in args:
            self.key_value[component] = ComponentValue(value_for=component,
                                                       value=value)

class DataKeySet(BaseModel):
    included: bool
    keys: List[DataKey]


class Constraint(MaintainableArtefact):
    data_content_keys: DataKeySet = None
    # metadata_content_keys: MetadataKeySet = None
    # NB the spec gives 1..* for this attribute, but this implementation allows
    # only 1
    role: ConstraintRole


class SelectionValue(BaseModel):
    pass


class MemberValue(SelectionValue):
    value: str
    cascade_values: bool = None

    def __hash__(self):
        return hash(self.value)


class MemberSelection(BaseModel):
    included: bool = True
    values_for: Component
    # NB the spec does not say what this feature should be named
    values: Set[MemberValue]


class CubeRegion(BaseModel):
    included: bool = True
    member: Dict['Dimension', MemberSelection] = {}

    def __contains__(self, v):
        key, value = v
        kv = self.key_values
        if key not in kv.keys():
            raise KeyError(
                'Unknown key: {0}. Allowed keys are: {1}'.format(
                    key, list(kv.keys())))
        return (value in kv[key]) == self.include

    def to_query_string(self, structure):
        all_values = []

        for dim in structure.dimensions:
            if isinstance(dim, TimeDimension):
                # TimeDimensions handled by query parameters
                continue
            ms = self.member.get(dim, None)
            values = sorted(mv.value for mv in ms.values) if ms else []
            all_values.append('+'.join(values))

        return '.'.join(all_values)


class ContentConstraint(Constraint):
    data_content_region: Optional[CubeRegion] = None
    content: Set[ConstrainableArtefact] = set()
    # metadata_content_region: MetadataTargetRegion = None

    class Config:
        validate_assignment_exclude = 'data_content_region'

    def __contains__(self, v):
        if self.data_content_region:
            result = [v in c for c in self.data_content_region]
            # Remove all cubes where v passed. The remaining ones indicate
            # fails.
            if True in result:
                result.remove(True)
            if result == []:
                return True
            else:
                raise ValueError('Key outside cube region(s).', v, result)
        else:
            raise NotImplementedError(
                'ContentConstraint does not contain a CubeRegion.')

    def to_query_string(self, structure):
        try:
            return self.data_content_region.to_query_string(structure)
        except AttributeError as e:
            raise NotImplementedError(
                'ContentConstraint does not contain a CubeRegion.')


# 5.2: Data Structure Defintion

class DimensionComponent(Component):
    order: Optional[int]


class Dimension(DimensionComponent):
    pass


CubeRegion.update_forward_refs()


class TimeDimension(DimensionComponent):
    pass


class MeasureDimension(DimensionComponent):
    pass


class PrimaryMeasure(Component):
    pass


class MeasureDescriptor(ComponentList):
    components: List[PrimaryMeasure] = []


class AttributeRelationship(BaseModel):
    dimensions: List[Dimension] = []
    group: 'GroupDimensionDescriptor' = None


NoSpecifiedRelationship = AttributeRelationship
PrimaryMeasureRelationship = AttributeRelationship
GroupRelationship = AttributeRelationship
DimensionRelationship = AttributeRelationship


class DataAttribute(Component):
    related_to: AttributeRelationship = None
    usage_status: UsageStatus = None


class ReportingYearStartDay(DataAttribute):
    pass


class AttributeDescriptor(ComponentList):
    components: List[DataAttribute] = []


class Structure(MaintainableArtefact):
    grouping: ComponentList = None


class StructureUsage(MaintainableArtefact):
    structure: Structure = None


class DimensionDescriptor(ComponentList):
    components: List[Union[Dimension, MeasureDimension, TimeDimension]] = []

    def order_key(self, key):
        """Return a key ordered according to the DSD."""
        result = key.__class__()
        for dim in sorted(self.components, key=attrgetter('order')):
            try:
                result[dim.id] = key[dim.id]
            except KeyError:
                continue
        return result

    @classmethod
    def from_key(cls, key):
        """Create a new DimensionDescriptor from a *key*.

        For each KeyValue in the *key*:
        - A new Dimension is created.
        - A new Codelist is created, containing the KeyValue.value.
        """
        dd = cls()
        for id, kv in key.values.items():
            d = Dimension(id=id)
            cl = Codelist(id=id)
            d.local_representation.enumerated = cl
            cl.items.append(Code(id=kv.value))
            dd.components.append(d)
        return dd


class GroupDimensionDescriptor(DimensionDescriptor):
    attachment_constraint: bool = None
    # constraint: AttachmentConstraint = None


AttributeRelationship.update_forward_refs()


class DataStructureDefinition(Structure, ConstrainableArtefact):
    attributes: AttributeDescriptor = AttributeDescriptor()
    dimensions: DimensionDescriptor = DimensionDescriptor()
    measures: MeasureDescriptor = None
    group_dimensions: GroupDimensionDescriptor = None

    # Convenience methods
    def attribute(self, id, **kwargs):
        return self.attributes.get(id, **kwargs)

    def dimension(self, id, **kwargs):
        return self.dimensions.get(id, **kwargs)

    def make_constraint(self, key):
        """Return a ContentConstraint for a dict of *keys*."""
        # Make a copy to avoid pop()'ing off the object in the calling scope
        key = key.copy()

        cr = CubeRegion()
        for dim in self.dimensions:
            mvs = set()
            try:
                for value in key.pop(dim.id).split('+'):
                    # TODO validate values
                    mvs.add(MemberValue(value=value))
            except KeyError:
                continue
            else:
                cr.member[dim] = MemberSelection(included=True,
                                                 values_for=dim,
                                                 values=mvs)

        assert len(key) == 0

        return ContentConstraint(data_content_region=cr,
            role=ConstraintRole(role=ConstraintRoleType.allowable))

    @classmethod
    def from_keys(cls, keys):
        """Create a new DataStructureDefinition from some *keys*.

        The DSD.dimensions refers to a set of Concepts and Codelists, each
        containing all the values observed across *keys* for that dimension.
        """
        iter_keys = iter(keys)
        dd = DimensionDescriptor.from_key(next(iter_keys))
        for k in iter_keys:
            for i, (id, kv) in enumerate(k.values.items()):
                dd[i].local_representation.enumerated.items.append(
                    Code(id=kv.value))
        return cls(dimensions=dd)


class DataflowDefinition(StructureUsage, ConstrainableArtefact):
    structure: DataStructureDefinition = DataStructureDefinition()


# 5.4: Data Set

class KeyValue(BaseModel):
    id: str
    value: Any = ...

    def __eq__(self, other):
        """Compare the value to a Python built-in type, e.g. str."""
        return self.value == other

    def __str__(self):
        return '{0.id}={0.value}'.format(self)

    def __repr__(self):
        return '<{0.__class__.__name__}: {0.id}={0.value}>'.format(self)

    def __hash__(self):
        # KeyValue instances with the same id & value hash identically
        return hash(self.id + str(self.value))


TimeKeyValue = KeyValue


def value_for_dsd_ref(args, kwargs):
    """Maybe replace a string 'value_for' in *kwargs* with a DSD reference."""
    try:
        dsd = kwargs.pop('dsd')
        kwargs['value_for'] = dsd.attributes.get(kwargs['value_for'])
    except KeyError:
        pass
    return args, kwargs


class AttributeValue(BaseModel):
    """SDMX-IM AttributeValue.

    In the spec, AttributeValue is an abstract class. Here, it serves as both
    the concrete subclasses CodedAttributeValue and UncodedAttributeValue.
    """
    # TODO separate and enforce properties of Coded- and UncodedAttributeValue
    value: Union[str, Code]
    value_for: DataAttribute = None
    start_date: Optional[date]

    def __init__(self, *args, **kwargs):
        args, kwargs = value_for_dsd_ref(args, kwargs)
        super(AttributeValue, self).__init__(*args, **kwargs)

    def __eq__(self, other):
        """Compare the value to a Python built-in type, e.g. str."""
        return self.value == other

    def __str__(self):
        return self.value

    def __repr__(self):
        return '<{}: {}={}>'.format(self.__class__.__name__, self.value_for,
                                    self.value)


@validate_dictlike('attrib', 'values')
class Key(BaseModel):
    """SDMX Key class.

    The constructor takes an optional list of keyword arguments; the keywords
    are used as Dimension IDs, and the values as KeyValues.

    For convience, the values of the key may be accessed directly:

    >>> k = Key(foo=1, bar=2)
    >>> k.values['foo']
    1
    >>> k['foo']
    1

    """
    attrib: DictLike[str, AttributeValue] = DictLike()
    values: DictLike[str, KeyValue] = DictLike()
    described_by: DimensionDescriptor = None

    def __init__(self, arg=None, **kwargs):
        super().__init__()
        if arg:
            if len(kwargs):
                raise ValueError("Key() accepts either a single argument, or "
                                 "keyword arguments; not both.")
            kwargs.update(arg)
        self.described_by = kwargs.pop('described_by', None)
        for id, value in kwargs.items():
            self.values[id] = KeyValue(id=id, value=value)

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
        print(self, name)
        return self.values[name]

    def __setitem__(self, name, value):
        # Convert a bare string or other Python object to a KeyValue instance
        if not isinstance(value, KeyValue):
            value = KeyValue(id=name, value=value)
        self.values[name] = value

    # Convenience access to values by attribute
    def __getattr__(self, name):
        try:
            return super().__getattr__(name)
        except AttributeError as e:
            try:
                return self.__getitem__(name)
            except KeyError:
                raise e

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
        if not isinstance(other, Key):
            raise NotImplementedError
        result = copy(self)
        for id, value in other.values.items():
            result[id] = value
        return result

    def __radd__(self, other):
        if other is None:
            return copy(self)
        else:
            raise NotImplementedError

    def __eq__(self, other):
        if hasattr(other, 'values'):
            return all([a == b for a, b in zip(self.values, other.values)])
        elif isinstance(other, str) and len(self.values) == 1:
            print(self.values)
            return self.values[0] == other
        else:
            raise ValueError(other)

    def __hash__(self):
        # Hash of the individual KeyValues, in order
        return hash(tuple(hash(kv) for kv in self.values.values()))

    # Representations

    def __str__(self):
        return '({})'.format(', '.join(map(str, self.values.values())))

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__,
                                 ', '.join(map(str, self.values.values())))

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
    id: str = None
    described_by: GroupDimensionDescriptor = None


class SeriesKey(Key):
    # pandaSDMX extensions not in the IM
    group_keys: Set[GroupKey] = set()

    @property
    def group_attrib(self):
        """Return a view of combined group attributes."""
        # Needed to pass existing tests
        view = DictLike()
        for gk in self.group_keys:
            view.update(gk.attrib)
        return view


@validate_dictlike('attached_attribute')
class Observation(BaseModel):
    """SDMX-IM Observation.

    This class also implements the spec classes ObservationValue,
    UncodedObservationValue, and CodedObservation.
    """
    attached_attribute: DictLike[str, AttributeValue] = DictLike()
    series_key: SeriesKey = None
    dimension: Key = None
    value: Union[Any, Code] = None
    value_for: PrimaryMeasure = None

    # pandaSDMX extensions not in the IM
    group_keys: Set[GroupKey] = set()


    @property
    def attrib(self):
        """Return a view of combined observation, series & group attributes."""
        view = self.attached_attribute.copy()
        view.update(getattr(self.series_key, 'attrib', {}))
        for gk in self.group_keys:
            view.update(gk.attrib)
        return view

    @property
    def dim(self):
        return self.dimension

    @property
    def key(self):
        """Return the entire key, including KeyValues at the series level."""
        return self.series_key + self.dimension

    def __len__(self):
        # FIXME this is unintuitive; maybe deprecate/remove?
        return len(self.key)

    def __str__(self):
        return '{0.key}: {0.value}'.format(self)


@validate_dictlike('attrib')
class DataSet(AnnotableArtefact):
    # SDMX-IM features
    action: ActionType = None
    attrib: DictLike[str, AttributeValue] = DictLike()
    valid_from: str = None
    structured_by: DataStructureDefinition = None
    obs: List[Observation] = []

    # pandaSDMX extensions not in the IM
    # Map of series key → list of observations
    series: DictLike[SeriesKey, List[Observation]] = DictLike()
    # Map of group key → list of observations
    group: DictLike[GroupKey, List[Observation]] = DictLike()

    def _add_group_refs(self, target):
        """Associate *target* with groups in this dataset.

        *target* may be an instance of SeriesKey or Observation.
        """
        for group_key in self.group:
            if group_key in (target if isinstance(target, SeriesKey) else
                             target.key):
                target.group_keys.add(group_key)
                if isinstance(target, Observation):
                    self.group[group_key].append(target)

    def add_obs(self, observations, series_key=None):
        """Add *observations* to a series with *series_key*.

        Checks consistency and adds group associations."""
        if series_key:
            # Associate series_key with any GroupKeys that apply to it
            self._add_group_refs(series_key)
            if series_key not in self.series:
                # Initialize empty series
                self.series[series_key] = []

        for obs in observations:
            # Associate the observation with any GroupKeys that contain it
            self._add_group_refs(obs)

            # Store a reference to the observation
            self.obs.append(obs)

            if series_key:
                # Check that the Observation is not associated with a different
                # SeriesKey
                assert obs.series_key is series_key, \
                    (obs.series_key, id(obs.series_key), series_key, id(series_key))
                # Store a reference to the observation
                self.series[series_key].append(obs)

    @validator('action')
    def _validate_action(cls, value):
        if value in ActionType:
            return value
        else:
            return ActionType[value]


class _AllDimensions:
    pass


AllDimensions = _AllDimensions()


# 11. Data Provisioning

class Datasource(BaseModel):
    url: str


class SimpleDatasource(Datasource):
    pass


class QueryDatasource(Datasource):
    # Abstract.
    # NB the SDMX-IM inconsistently uses this name and 'WebServicesDatasource'.
    pass


class RESTDatasource(QueryDatasource):
    pass
