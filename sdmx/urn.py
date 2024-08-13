import re
from typing import Dict, Optional

from sdmx.model import PACKAGE, MaintainableArtefact

#: Regular expression for URNs.
_PATTERN = re.compile(
    r"urn:sdmx:org\.sdmx\.infomodel"
    r"\.(?P<package>[^\.]*)"
    r"\.(?P<class>[^=]*)=((?P<agency>[^:]*):)?"
    r"(?P<id>[^\(]*)(\((?P<version>[\d\.]*)\))?"
    r"(\.(?P<item_id>.*))?"
)


class URN:
    """SDMX Uniform Resource Name (URN).

    For example: "urn:sdmx:org.sdmx.infomodel.codelist.Code=BAZ:FOO(1.2.3).BAR". The
    maintainer ID ("BAZ") and version ("1.2.3") must refer to a
    :class:`.MaintainableArtefact`. If (as in this example) the URN is for a
    non-maintainable child (for example, a :class:`.Item` in a :class:`.ItemScheme`),
    these are the maintainer ID and version of the containing scheme/other maintainable
    parent object.
    """

    #: SDMX :data:`.PACKAGE` corresponding to :attr:`klass`.
    package: str
    klass: str
    agency: str
    id: str
    version: str
    item_id: Optional[str]

    def __init__(self, value, **kwargs) -> None:
        if kwargs:
            self.__dict__.update(kwargs)

        if value is None:
            return

        try:
            match = _PATTERN.match(value)
            assert match is not None
        except (AssertionError, TypeError):
            raise ValueError(f"not a valid SDMX URN: {value}")

        g = self.groupdict = match.groupdict()

        self.package = (
            PACKAGE[g["class"]] if g["package"] == "package" else g["package"]
        )
        self.klass = g["class"]
        self.agency = g["agency"]
        self.id = g["id"]
        self.version = g["version"]
        self.item_id = g["item_id"]

    def __str__(self) -> str:
        return (
            f"urn:sdmx:org.sdmx.infomodel.{self.package}.{self.klass}={self.agency}:"
            f"{self.id}({self.version})"
            + (("." + self.item_id) if self.item_id else "")
        )


def expand(value: str) -> str:
    """Return the full URN for `value`.

    Parameters
    ----------
    value : str
        Either the final part of a valid SDMX URN, for example
        `Codelist=BAZ:FOO(1.2.3)`, or a full URN.

    Returns
    -------
    str
        The full SDMX URN. If `value` is not a partial or full URN, it is returned
        unmodified.

    Raises
    ------
    ValueError
        If `value` is not a valid part of a SDMX URN.
    """
    for candidate in (value, f"urn:sdmx:org.sdmx.infomodel.package.{value}"):
        try:
            return str(URN(candidate))
        except ValueError:
            continue

    return value


def make(
    obj,
    maintainable_parent: Optional["MaintainableArtefact"] = None,
    strict: bool = False,
) -> str:
    """Create an SDMX URN for `obj`.

    If `obj` is not :class:`.MaintainableArtefact`, then `maintainable_parent`
    must be supplied in order to construct the URN.
    """
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
            version=ma.version,
            item_id=item_id,
        )
    )


def match(value: str) -> Dict[str, str]:
    """Match :data:`URN` in `value`, returning a :class:`dict` with the match groups.

    Raises
    ------
    ValueError
        If `value` is not a well-formed SDMX URN.
    """
    return URN(value).groupdict


def normalize(value: str) -> str:
    """Normalize URNs.

    Handle "…DataFlow=…" (SDMX 3.0) vs. "…DataFlowDefinition=…" (SDMX 2.1) in URNs;
    prefer the former.
    """
    return value.replace("Definition=", "=")


def shorten(value: str) -> str:
    """Return a partial URN based on `value`.

    Parameters
    ----------
    value : str
        A full SDMX URN. If the value is not a URN, it is returned unmodified.

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
