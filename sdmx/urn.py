import re
from dataclasses import InitVar, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sdmx.model.common import MaintainableArtefact

#: Regular expression for URNs.
_PATTERN = re.compile(
    r"urn:sdmx:org\.sdmx\.infomodel"
    r"\.(?P<package>[^\.]*)"
    r"\.(?P<class>[^=]*)=((?P<agency>[^:]*):)?"
    r"(?P<id>[^\(]*)(\((?P<version>[\w\.-]*)\))?"
    r"(\.(?P<item_id>.*))?"
)


@dataclass(slots=True)
class URN:
    """SDMX Uniform Resource Name (URN)."""

    #: Existing URN to parse, for example
    #: "urn:sdmx:org.sdmx.infomodel.codelist.Code=BAZ:FOO(1.2.3).BAR". The maintainer ID
    #: ("BAZ") and version ("1.2.3") must refer to a :class:`.MaintainableArtefact`. If
    #: (as in this example) the URN is for a non-maintainable child (for example, a
    #: :class:`.Item` in a :class:`.ItemScheme`), these are the maintainer ID and
    #: version of the containing scheme/other maintainable parent object.
    value: InitVar[str | None] = None

    #: SDMX :data:`.PACKAGE` corresponding to :attr:`klass`.
    package: str = ""

    #: SDMX object class.
    klass: str = ""

    #: ID of the :class:`.Agency` that is the :attr:`.MaintainableArtefact.maintainer`.
    agency: str = ""

    #: ID of the :class:`.MaintainableArtefact`.
    id: str = ""

    #: :attr:`.VersionableArtefact.version` of the maintainable artefact.parent.
    version: str = ""

    #: ID of an item within a maintainable parent. Optional.
    item_id: str = ""

    def __post_init__(self, value: str | None) -> None:
        if value is None:
            return

        try:
            match = _PATTERN.match(value)
            assert match is not None
        except (AssertionError, TypeError):
            raise ValueError(f"not a valid SDMX URN: {value}")

        # Update attributes from the match
        g = match.groupdict()
        self.klass = g["class"]
        self.agency = g["agency"]
        self.id = g["id"]
        self.version = g["version"]
        self.item_id = g["item_id"]

        if g["package"] == "package":
            # Replace the placeholder value "package" with the actual package associated
            # with class
            from sdmx.model.v21 import PACKAGE

            self.package = PACKAGE[g["class"]]
        else:
            self.package = g["package"]

    def __str__(self) -> str:
        return (
            f"urn:sdmx:org.sdmx.infomodel.{self.package}.{self.klass}={self.agency}:"
            f"{self.id}({self.version})"
            + (("." + self.item_id) if self.item_id else "")
        )


def expand(value: str) -> str:
    """Return the full URN for `value`.

    Example
    -------
    >>> expand("Code=BAZ:FOO(1.2.3).BAR")
    "urn:sdmx:org.sdmx.infomodel.codelist.Code=BAZ:FOO(1.2.3).BAR"

    Parameters
    ----------
    value : str
        Either the final / :func:`.shorten`'d part of a valid SDMX URN, or a full URN.

    Returns
    -------
    str
        The full SDMX URN. If `value` is not a partial or full URN, it is returned
        unmodified.
    """
    for candidate in (value, f"urn:sdmx:org.sdmx.infomodel.package.{value}"):
        try:
            return str(URN(candidate))
        except ValueError:
            continue

    return value


def make(
    obj, maintainable_parent: "MaintainableArtefact | None" = None, strict: bool = False
) -> str:
    """Create an SDMX URN for `obj`.

    If `obj` is not :class:`.MaintainableArtefact`, then `maintainable_parent` must be
    supplied in order to construct the URN.
    """
    from sdmx.model.common import MaintainableArtefact
    from sdmx.model.v21 import PACKAGE

    if not isinstance(obj, MaintainableArtefact):
        ma = maintainable_parent or obj.get_scheme()
        item_id = obj.id
    else:
        ma, item_id = obj, None

    if not isinstance(ma, MaintainableArtefact):
        raise ValueError(
            f"Neither {obj!r} nor {maintainable_parent!r} are maintainable"
        )
    elif ma.maintainer is None:
        raise ValueError(f"Cannot construct URN for {ma!r} without maintainer")
    elif strict and ma.version is None:
        raise ValueError(f"Cannot construct URN for {ma!r} without version")

    return str(
        URN(
            None,
            package=PACKAGE[obj.__class__.__name__],
            klass=obj.__class__.__name__,
            agency=ma.maintainer.id,
            id=ma.id,
            version=str(ma.version) if ma.version else "",
            item_id=item_id,
        )
    )


def match(value: str) -> dict[str, str]:
    """Match :data:`URN` in `value`, returning a :class:`dict` with the match groups.

    Example
    -------
    >>> match("urn:sdmx:org.sdmx.infomodel.codelist.Code=BAZ:FOO(1.2.3).BAR")
    {
        "package": "codelist",
        "class": "Code",
        "agency": "BAZ",
        "id": "FOO",
        "version": "1.2.3",
        "item_id": "BAR",
    }

    Raises
    ------
    ValueError
        If `value` is not a well-formed SDMX URN.
    """
    urn = URN(value)

    return {
        "package": urn.package,
        "class": urn.klass,
        "agency": urn.agency,
        "id": urn.id,
        "version": urn.version,
        "item_id": urn.item_id,
    }


def normalize(value: str) -> str:
    """‘Normalize’ a URN.

    Handle "…DataFlow=…" (SDMX 3.0) vs. "…DataFlowDefinition=…" (SDMX 2.1) in URNs;
    prefer the former.
    """
    return value.replace("Definition=", "=")


def shorten(value: str) -> str:
    """Return a partial URN based on `value`.

    Example
    -------
    >>> shorten("urn:sdmx:org.sdmx.infomodel.codelist.Code=BAZ:FOO(1.2.3).BAR")
    "Code=BAZ:FOO(1.2.3).BAR"

    Parameters
    ----------
    value : str
        A full SDMX URN. If `value` is not a URN, it is returned unmodified.

    Returns
    -------
    str
        `value`, but without the leading text
        :py:`"urn:sdmx:org.sdmx.infomodel.{package}."`
    """
    try:
        return str(URN(value)).split(".", maxsplit=4)[-1]
    except ValueError:
        return value
