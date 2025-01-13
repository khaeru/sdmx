import re
from abc import abstractmethod
from collections import ChainMap, defaultdict
from importlib import import_module
from itertools import chain, count
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    Union,
    cast,
)

from lxml import etree
from lxml.etree import QName

import sdmx.urn
from sdmx import message
from sdmx.exceptions import XMLParseError  # noqa: F401
from sdmx.format import Version, list_media_types
from sdmx.model import common
from sdmx.reader.base import BaseReader

if TYPE_CHECKING:
    import types

# Sentinel value for a missing Agency
_NO_AGENCY = common.Agency()


class NotReference(Exception):
    """Raised when the `elem` passed to :class:`.Reference` is not a reference."""


class BaseReference:
    """Temporary class for references.

    - `cls`, `id`, `version`, and `agency_id` are always for a MaintainableArtefact.
    - If the reference target is a MaintainableArtefact (`maintainable` is True),
      `target_cls` and `target_id` are identical to `cls` and `id`, respectively.
    - If the target is not maintainable, `target_cls` and `target_id` describe it.

    `cls_hint` is an optional hint for when the object is instantiated, i.e. a more
    specific override for `cls`/`target_cls`.
    """

    __slots__ = (
        "agency",
        "cls",
        "id",
        "maintainable",
        "target_cls",
        "target_id",
        "version",
    )

    def __init__(self, reader, elem, cls_hint=None):
        parent_tag = elem.tag

        info = self.info_from_element(elem)

        # Find the target class
        target_cls = reader.model.get_class(info["class"], info["package"])

        if target_cls is None:
            # Try the parent tag name
            target_cls = reader.format.class_for_tag(parent_tag)

        if cls_hint and (target_cls is None or issubclass(cls_hint, target_cls)):
            # Hinted class is more specific than target_cls, or failed to find a target
            # class above
            target_cls = cls_hint

        if target_cls is None:
            raise ValueError(f"Unable to determine target class for {info}", info)

        self.maintainable = issubclass(target_cls, common.MaintainableArtefact)

        if self.maintainable:
            # MaintainableArtefact is the same as the target
            cls, info["id"] = target_cls, info["target_id"]
        else:
            # Get the class for the parent MaintainableArtefact
            cls = reader.model.parent_class(target_cls)

        # Store
        self.cls = cls
        self.agency = (
            common.Agency(id=info["agency"]) if info.get("agency", None) else _NO_AGENCY
        )
        self.id = info["id"]
        self.version = info.get("version", None)
        self.target_cls = target_cls
        self.target_id = info["target_id"]

    @classmethod
    @abstractmethod
    def info_from_element(cls, elem) -> dict[str, Any]: ...

    def __str__(self):
        # NB for debugging only
        return (  # pragma: no cover
            f"{self.cls.__name__}={self.agency.id}:{self.id}({self.version}) → "
            f"{self.target_cls.__name__}={self.target_id}"
        )


class XMLEventReader(BaseReader):
    """Populate the parser, format, and model attributes of :class:`Reader`."""

    # Defined on BaseReader
    suffixes = [".xml"]

    #: SDMX-ML version handled by this reader.
    xml_version: ClassVar[Version]

    #: Reference to the module defining the format read.
    format: ClassVar["types.ModuleType"]
    #: Reference to the module defining the information model read.
    model: ClassVar["types.ModuleType"]

    #: :class:`.BaseReference` subclass used by this reader.
    Reference: ClassVar[type[BaseReference]]

    #: Mapping from (QName, ["start", "end"]) to a function that parses the
    #: element/event or else None (no parsing).
    parser: ClassVar[dict[tuple[QName, str], Callable]]

    # One-way counter for use in stacks
    _count: Iterator[int]

    def __init_subclass__(cls: type["XMLEventReader"]):
        # Empty dictionary
        cls.parser = {}

        name = {Version["2.1"]: "v21", Version["3.0.0"]: "v30"}[cls.xml_version]
        cls.format = import_module(f"sdmx.format.xml.{name}")
        cls.model = import_module(f"sdmx.model.{name}")
        cls.media_types = list_media_types(base="xml", version=cls.xml_version)

    def __init__(self):
        # Initialize counter
        self._count = count()

    # BaseReader methods

    def convert(
        self,
        data,
        structure=None,
        _events=None,
        **kwargs,
    ) -> message.Message:
        # Initialize stacks
        self.stack: dict[Union[type, str], dict[Union[str, int], Any]] = defaultdict(
            dict
        )

        # Elements to ignore when parsing finishes
        self.ignore = set()

        # If calling code provided a {Metad,D}ataStructureDefinition, add it to a stack,
        # and let it be ignored when parsing finishes
        structure = self._handle_deprecated_kwarg(structure, kwargs)
        self.push(structure)
        self.ignore.add(id(structure))

        if _events is None:
            events = cast(
                Iterator[tuple[str, etree._Element]],
                etree.iterparse(data, events=("start", "end")),
            )
        else:
            events = _events

        try:
            # Use the etree event-driven parser
            # NB (typing) iterparse() returns tuples. For "start" and "end", the second
            #    item is etree._Element, but for other events, e.g. "start-ns", it is
            #    not. types-lxml accurately reflects this. Narrow the type here for the
            #    following code.
            for event, element in events:
                try:
                    # Retrieve the parsing function for this element & event
                    func = self.parser[self.format.qname(element.tag), event]
                except KeyError:  # pragma: no cover
                    if QName(element.tag).namespace == "http://www.w3.org/1999/xhtml":
                        continue
                    # Don't know what to do for this (element, event)
                    raise NotImplementedError(element.tag, event) from None

                if func is None:
                    continue  # Explicitly no parser for this (element, event) → skip

                result = func(self, element)  # Parse the element
                self.push(result)  # Store the result

                if event == "end":
                    element.clear()  # Free memory

        except Exception as exc:
            # Parsing failed; display some diagnostic information
            self._dump()
            print(etree.tostring(element, pretty_print=True).decode())
            raise XMLParseError from exc

        # Parsing complete; count uncollected items from the stacks, which represent
        # parsing errors

        # Remove some internal items
        self.pop_single("SS without structure")
        self.pop_single("DataSetClass")

        # Count only non-ignored items
        uncollected = -1
        for key, objects in self.stack.items():
            uncollected += sum(
                [1 if id(o) not in self.ignore else 0 for o in objects.values()]
            )

        if uncollected > 0:  # pragma: no cover
            self._dump()
            raise RuntimeError(f"{uncollected} uncollected items")

        return cast(message.Message, self.get_single(message.Message, subclass=True))

    @classmethod
    def start(cls, names: str, only: bool = True):
        """Decorator for a function that parses "start" events for XML elements."""

        def decorator(func):
            for tag in map(cls.format.qname, names.split()):
                cls.parser[tag, "start"] = func
                if only:
                    cls.parser[tag, "end"] = None
            return func

        return decorator

    @classmethod
    def end(cls, names: str, only: bool = True):
        """Decorator for a function that parses "end" events for XML elements."""

        def decorator(func):
            for tag in map(cls.format.qname, names.split()):
                cls.parser[tag, "end"] = func
                if only:
                    cls.parser[tag, "start"] = None
            return func

        return decorator

    @classmethod
    def possible_reference(cls, cls_hint: Optional[type] = None, unstash: bool = False):
        """Decorator for a function where the `elem` parsed may be a Reference.

        Before calling the decorated function, attempt to parse the `elem` as a
        :class:`.Reference`. If successful, return the reference instead of calling the
        function. If `elem` does not contain a reference, call the decorated function.

        Parameters
        ----------
        cls_hint :
            Passed to :class:`.Reference`.
        unstash : bool, optional
            If :data:`True`, call :meth:`.unstash` after successfully resolving a
            reference.
        """

        def decorator(func):
            def wrapped(reader: "XMLEventReader", elem):
                try:
                    # Identify a reference
                    result = reader.Reference(
                        reader,
                        elem,
                        cls_hint=cls_hint or reader.class_for_tag(elem.tag),
                    )
                except NotReference:
                    # Call the wrapped function
                    result = func(reader, elem)
                else:
                    # Successful; unstash if configured
                    if unstash:
                        reader.unstash()

                return result

            return wrapped

        return decorator

    # Stack handling

    def _clean(self):  # pragma: no cover
        """Remove empty stacks."""
        for key in list(self.stack.keys()):
            if len(self.stack[key]) == 0:
                self.stack.pop(key)

    def _dump(self):  # pragma: no cover
        """Print the stacks, for debugging."""
        self._clean()
        print("\n\n")
        for key, values in self.stack.items():
            print(f"--- {key} ---")
            if isinstance(values, Mapping):
                print(
                    *map(lambda kv: f"{kv[0]} ({id(kv[1])}) {kv[1]!s}", values.items()),
                    sep="\n",
                    end="\n\n",
                )
        print("\nIgnore:\n", self.ignore)

    def push(self, stack_or_obj, obj=None):
        """Push an object onto a stack."""
        if stack_or_obj is None:
            return
        elif obj is None:
            # Add the object to a stack based on its class
            obj = stack_or_obj
            s = stack_or_obj.__class__
        elif isinstance(stack_or_obj, str):
            # Stack with a string name
            s = stack_or_obj
        else:
            # Element; use its local name
            s = QName(stack_or_obj).localname

        # Get the ID for the element in the stack: its .id attribute, if any, else a
        # unique number
        id = getattr(obj, "id", next(self._count)) or next(self._count)

        if id in self.stack[s]:
            # Avoid a collision for two distinct objects with the same ID, e.g. with
            # different maintainers (ECB:AGENCIES vs. SDMX:AGENCIES). Re-insert with
            # numerical keys. This means the objects cannot be retrieved by their ID,
            # but the code does not rely on this.
            self.stack[s][next(self._count)] = self.stack[s].pop(id)
            id = next(self._count)

        self.stack[s][id] = obj

    def stash(self, *stacks):
        """Temporarily hide all objects in the given `stacks`."""
        self.push("_stash", {s: self.stack.pop(s, dict()) for s in stacks})

    def unstash(self):
        """Restore the objects hidden by the last :meth:`stash` call to their stacks.

        Calls to :meth:`.stash` and :meth:`.unstash` should be matched 1-to-1; if the
        latter outnumber the former, this will raise :class:`.KeyError`.
        """
        for s, values in (self.pop_single("_stash") or {}).items():
            self.stack[s].update(values)

    # Delegate to version-specific module
    @classmethod
    def class_for_tag(cls, tag: str) -> type:
        return cls.format.class_for_tag(tag)

    @classmethod
    def qname(cls, ns_or_name, name=None) -> QName:
        return cls.format.qname(ns_or_name, name)

    def get_single(
        self,
        cls_or_name: Union[type, str],
        id: Optional[str] = None,
        version: Optional[str] = None,
        subclass: bool = False,
    ) -> Optional[Any]:
        """Return a reference to an object while leaving it in its stack.

        Always returns 1 object. Returns :obj:`None` if no matching object exists, or if
        2 or more objects meet the conditions.

        If `id` (and `version`) is/are given, only return an IdentifiableArtefact with
        the matching ID (and version).

        If `cls_or_name` is a class and `subclass` is :obj:`True`; check all objects in
        the stack `cls_or_name` *or any stack for a subclass of this class*.
        """
        if subclass:
            keys: Iterable[Union[type, str]] = filter(
                matching_class(cls_or_name), self.stack.keys()
            )
            results: Mapping = ChainMap(*[self.stack[k] for k in keys])
        else:
            results = self.stack.get(cls_or_name, dict())

        if id and version:
            for v in results.values():
                if v.id == id and v.version == version:
                    return v
            return None
        elif id:
            return results.get(id)
        elif len(results) != 1:
            # 0 or ≥2 results
            return None
        else:
            return next(iter(results.values()))

    def pop_all(self, cls_or_name: Union[type, str], subclass=False) -> Sequence:
        """Pop all objects from stack *cls_or_name* and return.

        If `cls_or_name` is a class and `subclass` is :obj:`True`; return all objects in
        the stack `cls_or_name` *or any stack for a subclass of this class*.
        """
        if subclass:
            keys: Iterable[Union[type, str]] = list(
                filter(matching_class(cls_or_name), self.stack.keys())
            )
            result: Iterable = chain(*[self.stack.pop(k).values() for k in keys])
        else:
            result = self.stack.pop(cls_or_name, dict()).values()

        return list(result)

    def pop_single(self, cls_or_name: Union[type, str]):
        """Pop a single object from the stack for `cls_or_name` and return."""
        try:
            return self.stack[cls_or_name].popitem()[1]
        except KeyError:
            return None

    def peek(self, cls_or_name: Union[type, str]):
        """Get the object at the top of stack `cls_or_name` without removing it."""
        try:
            key, value = self.stack[cls_or_name].popitem()
            self.stack[cls_or_name][key] = value
            return value
        except KeyError:  # pragma: no cover
            return None

    def pop_resolved_ref(self, cls_or_name: Union[type, str]):
        """Pop a reference to `cls_or_name` and resolve it."""
        return self.resolve(self.pop_single(cls_or_name))

    def reference(self, elem, cls_hint=None) -> "BaseReference":
        return self.Reference(self, elem, cls_hint=cls_hint)

    def resolve(self, ref):
        """Resolve the Reference instance `ref`, returning the referred object."""
        if not isinstance(ref, BaseReference):
            # None, already resolved, or not a Reference
            return ref

        # Try to get the target directly
        target = self.get_single(
            ref.target_cls, ref.target_id, ref.version, subclass=True
        )

        if target:
            return target

        # MaintainableArtefact with is_external_reference=True; either a new object, or
        # reference to an existing object
        target_or_parent = self.maintainable(
            ref.cls, None, id=ref.id, maintainer=ref.agency, version=ref.version
        )

        if ref.maintainable:
            # `target_or_parent` is the target
            return target_or_parent

        # At this point, trying to resolve a reference to a child object of a parent
        # MaintainableArtefact; `target_or_parent` is the parent
        parent = target_or_parent

        if parent.is_external_reference:
            # Create the child
            return parent.setdefault(id=ref.target_id)
        else:
            try:
                # Access the child. Mismatch here will raise KeyError
                return parent[ref.target_id]
            except KeyError:
                if isinstance(parent, common.ItemScheme):
                    return parent.get_hierarchical(ref.target_id)
                raise  # pragma: no cover

    def annotable(self, cls, elem, **kwargs):
        """Create a AnnotableArtefact of `cls` from `elem` and `kwargs`.

        Collects all parsed <com:Annotation>.
        """
        if elem is not None:
            kwargs.setdefault("annotations", [])
            kwargs["annotations"].extend(self.pop_all(common.Annotation))
        return cls(**kwargs)

    def identifiable(self, cls, elem, **kwargs):
        """Create a IdentifiableArtefact of `cls` from `elem` and `kwargs`."""
        setdefault_attrib(kwargs, elem, "id", "urn", "uri")
        return self.annotable(cls, elem, **kwargs)

    def nameable(self, cls, elem, **kwargs):
        """Create a NameableArtefact of `cls` from `elem` and `kwargs`.

        Collects all parsed :class:`.InternationalString` localizations of <com:Name>
        and <com:Description>.
        """
        obj = self.identifiable(cls, elem, **kwargs)
        if elem is not None:
            add_localizations(obj.name, self.pop_all("Name"))
            add_localizations(obj.description, self.pop_all("Description"))
        return obj

    def maintainable(self, cls, elem, **kwargs):
        """Create or retrieve a MaintainableArtefact of `cls` from `elem` and `kwargs`.

        Following the SDMX-IM class hierarchy, :meth:`maintainable` calls
        :meth:`nameable`, which in turn calls :meth:`identifiable`, etc. (Since no
        concrete class is versionable but not maintainable, no separate method is
        created, for better performance). For all of these methods:

        - Already-parsed items are removed from the stack only if `elem` is not
          :obj:`None`.
        - `kwargs` (e.g. 'id') take precedence over any values retrieved from
          attributes of `elem`.

        If `elem` is None, :meth:`maintainable` returns a MaintainableArtefact with
        the is_external_reference attribute set to :obj:`True`. Subsequent calls with
        the same object ID will return references to the same object.
        """
        setdefault_attrib(
            kwargs,
            elem,
            "isExternalReference",
            "isFinal",
            "validFrom",
            "validTo",
            "version",
        )

        # Ensure is_external_reference and is_final are bool
        try:
            kwargs["is_external_reference"] = kwargs["is_external_reference"] == "true"
        except (KeyError, SyntaxError):
            kwargs.setdefault("is_external_reference", elem is None)
        kwargs["is_final"] = kwargs.get("is_final", None) == "true"

        # Create a candidate object
        obj = self.nameable(cls, elem, **kwargs)

        try:
            # Retrieve the Agency.id for obj.maintainer
            maint = self.get_single(common.Agency, elem.attrib["agencyID"])
        except (AttributeError, KeyError):
            pass
        else:
            # Elem contains a maintainer ID
            if maint is None:
                # …but it did not correspond to an existing object; create one
                maint = common.Agency(id=elem.attrib["agencyID"])
                self.push(maint)
                # This object is never collected; ignore it at end of parsing
                self.ignore.add(id(maint))
            obj.maintainer = maint

        # Maybe retrieve an existing object of the same class, ID, and version (if any)
        existing = self.get_single(cls, obj.id, version=obj.version)

        if existing and (
            existing.compare(obj, strict=True)
            or (existing.urn or sdmx.urn.make(existing)) == sdmx.urn.make(obj)
        ):
            if elem is not None:
                # Update `existing` from `obj` to preserve references
                # If `existing` was a forward reference <Ref/>, its URN was not stored.
                for attr in list(kwargs.keys()) + ["urn"]:
                    setattr(existing, attr, getattr(obj, attr))

            # Discard the candidate
            obj = existing
        elif obj.is_external_reference:
            # A new external reference. Ensure it has a URN.
            obj.urn = obj.urn or sdmx.urn.make(obj)
            # Push onto the stack to be located by next calls
            self.push(obj)

        return obj


def add_localizations(target: common.InternationalString, values: list) -> None:
    """Add localized strings from *values* to *target*."""
    target.localizations.update({locale: label for locale, label in values})


def matching_class(cls):
    """Filter condition; see :meth:`.get_single` and :meth:`.pop_all`."""
    return lambda item: isinstance(item, type) and issubclass(item, cls)


def setdefault_attrib(target, elem, *names):
    """Update `target` from :py:`elem.attrib` for the given `names`."""
    try:
        for name in names:
            try:
                target.setdefault(to_snake(name), elem.attrib[name])
            except KeyError:
                pass
    except AttributeError:
        pass  # No elem.attrib; elem is None


TO_SNAKE_RE = re.compile("([A-Z]+)")


def to_snake(value):
    """Convert *value* from lowerCamelCase to snake_case."""
    return TO_SNAKE_RE.sub(r"_\1", value).lower()
