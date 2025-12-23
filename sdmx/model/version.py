import operator
import re
from collections.abc import Callable
from dataclasses import InitVar, dataclass, field, replace
from functools import cache
from itertools import zip_longest

import packaging.version

#: Regular expressions (:class:`re.Pattern`) for version strings.
#:
#: - :py:`"2_1"` SDMX 2.1, e.g. "1.0"
#: - :py:`"3_0"` SDMX 3.0, e.g. "1.0.0-draft"
VERSION_PATTERNS = {
    "2_1": re.compile(r"^(?P<release>[0-9]+(?:\.[0-9]+){1})$"),
    "3_0": re.compile(r"^(?P<release>[0-9]+(?:\.[0-9]+){2})(-(?P<ext>.+))?$"),
}


def _cmp_method(op: Callable) -> Callable:
    """Shorthand for comparison methods."""

    def cmp(self, other) -> bool:
        try:
            return op(self._key, other._key)
        except AttributeError:
            if isinstance(other, str):
                return op(self, Version(other))
            else:
                return NotImplemented

    return cmp


def _release_component(index: int) -> Callable[["Version"], int]:
    """Shorthand for properties that access release components."""

    def getter(self) -> int:
        return self.release[index] if len(self.release) >= index + 1 else 0

    return getter


@dataclass(unsafe_hash=True, slots=True)
class Version(packaging.version._BaseVersion):
    """Class representing a version.

    The SDMX Information Model **does not** specify a Version class; instead,
    :attr:`.VersionableArtefact.version` is described as “a version **string** following
    SDMX versioning rules.”

    In order to simplify application of those ‘rules’, and to handle differences between
    SDMX 2.1 and 3.x, this class extends :class:`packaging.version._BaseVersion`, and
    thus is comparable with :class:`packaging.version.Version`. It implements the
    particular form of version specifiers laid out by the SDMX standards. Specifically:

    - :attr:`kind` identifies whether a Version instance is an SDMX 2.1, SDMX 3.x, or
      Python-style version string.
    - :attr:`patch` and :attr:`ext` attributes match the particular terms used in the
      SDMX 3.0 standards.
    - The :class:`str` representation of a Version uses the SDMX 3.0 style of separating
      the :attr:`ext` with a hyphen ("1.0.0-dev1"). This differs from the Python
      specification, which uses either (a) no separator for a ‘pre-release’ ("1.0rc1"),
      (b) a period for a ‘post-’ and/or ‘development release’ ("1.0.post2.dev3"), or
      (c) plus and period symbols for ‘local parts’ ("1.0+local1.local2").
    - :meth:`increment`, an added convenience method.
    - The class is comparable and interchangeable with :class:`str` version expressions.

    Parameters
    ----------
    value :
        String version expression.
    """

    value: InitVar[str | None] = None

    #: :py:`"2_1"` or :py:`"3_0"` for SDMX-compatible versions. :py:`"py"` for a Python
    #: version specifier.
    kind: str = "py"

    #: Same as :attr:`packaging.version.Version.epoch`.
    epoch: int = 0
    #: Same as :attr:`packaging.version.Version.release`.
    release: tuple[int, ...] = field(default=(0,))
    #: Same as :attr:`packaging.version.Version.pre`.
    pre: tuple[str, int] | None = None
    #: Same as :attr:`packaging.version.Version.post`.
    post: tuple[str, int] | None = None
    #: Same as :attr:`packaging.version.Version.dev`.
    dev: tuple[str, int] | None = None
    #: Same as :attr:`packaging.version.Version.local`.
    local: tuple[str | int, ...] = field(default_factory=tuple)

    def __post_init__(self, value: str | None) -> None:
        # Parse as a SDMX-compatible version
        for kind, pattern in VERSION_PATTERNS.items():
            if value is None:
                break
            if match := pattern.fullmatch(value):
                self.kind = kind

                # Store the parsed out pieces of the version
                gd = match.groupdict()
                self.release = tuple(int(i) for i in gd.pop("release").split("."))
                ext = gd.pop("ext", None)
                self.local = (ext,) if ext else tuple()

                # No further parsing
                value = None
                break

        if value is not None:
            # Parse `value` as if it were a ordinary Python version specifier
            self.kind = "py"

            v = packaging.version.Version(value)  # Raises on an invalid expression

            # Update fields with the parsed segments and components
            self.epoch = v.epoch
            self.release = v.release
            self.pre = v._version.pre
            self.post = v._version.post
            self.dev = v._version.dev
            self.local = v._version.local or ()

        # Set _BaseVersion._key for comparison
        self._key = packaging.version._cmpkey(
            self.epoch,
            self.release,
            self.pre,
            self.post,
            self.dev,
            self.local if self.local else None,
        )

    __eq__ = _cmp_method(operator.eq)
    __ge__ = _cmp_method(operator.ge)
    __gt__ = _cmp_method(operator.gt)
    __le__ = _cmp_method(operator.le)
    __lt__ = _cmp_method(operator.lt)
    __ne__ = _cmp_method(operator.ne)

    major = property(_release_component(0))
    minor = property(_release_component(1))
    patch = property(_release_component(2))
    micro = property(_release_component(2))

    @property
    def ext(self) -> str | None:
        """SDMX 3.0 version 'extension'.

        For :py:`kind="py"`, this is equivalent to
        :attr:`packaging.version.Version.local`.
        """
        return "".join(map(str, self.local)) if self.local else None

    def increment(
        self,
        major: bool | int | None = None,
        minor: bool | int | None = None,
        patch: bool | int | None = None,
        ext: bool | int | None = None,
        *,
        micro: bool | int | None = None,
        local: bool | int | None = None,
    ) -> "Version":
        """Return a Version that is incrementally greater than the current Version.

        Each argument may be one of:

        - :class:`int`: the respective release component or extension is incremented by
          this amount. If the argument is :py:`0`, the current value is preserved
          exactly.
        - :any:`True`: same as :py:`1`.
        - :any:`False`: same as :py:`0`.
        - :any:`None` (default): if any 'larger' component is incremented, zero the
          respective component. For instance, if :py:`major=1, minor=None`, then the
          major release component is incremented, and the minor release component is
          reset to :py:`0`.

        If no arguments are given, then by default :py:`minor=1` and :py:`ext=1`.

        Parameters
        ----------
        major :
            If given, increment the :attr:`Version.major
            <packaging.version.Version.major>` component of the :attr:`release` segment
            by this amount.
        minor :
            If given, increment the :attr:`Version.minor
            <packaging.version.Version.minor>` part.
        patch :
            If given, increment the :attr:`.Version.patch` part. The keyword argument
            `patch` may be used as an alias.
        ext :
            If given, increment the :attr:`.Version.ext` part. If this part is not
            present, add "dev{ext}". The keyword argument `local` may be used as an
            alias.
        """
        # Handle aliases
        if micro is not None:
            assert patch is None
            patch = micro
        if local is not None:
            assert ext is None
            ext = local

        # Apply defaults
        if major is minor is patch is ext is None:
            minor = ext = 1

        # Increment release parts
        release, incremented = [], False
        for current, arg in zip_longest(
            self.release, (major, minor, patch), fillvalue=0
        ):
            match arg:
                case None:
                    # If a superior part has been incremented, None → reset to 0
                    release.append(0 if incremented else current)
                case int() | bool():
                    release.append(current + int(arg))
                    incremented = True

        if ext is None:
            # Clear the local part
            _local = []
        else:
            # Increment extension/local part
            # Convert self.local into a mutable list, or supply a base value
            _local = list(self.local) or ["dev0"]

            if match := re.fullmatch("([^0-9]+)([0-9]+)", str(_local[0])):
                # Increment given and the first local part has an integer suffix
                _l, _n = match.group(1, 2)
                _local[0] = f"{_l}{int(_n) + int(ext)}"
            else:
                raise NotImplementedError(f"Increment SDMX version extension {_local}")

        # Return a new instance with modified release and local attributes
        return replace(self, release=tuple(release), local=tuple(_local))

    @cache
    def __str__(self) -> str:
        # Same as packaging.version.Version.__str__, except using the SDMX "-" separator
        # for the local part
        local_sep = "+" if self.kind == "py" else "-"
        parts = [
            f"{self.epoch}!" if self.epoch else None,
            ".".join(map(str, self.release)),
            "{}{}".format(*self.pre) if self.pre else None,
            ".{}{}".format(*self.post) if self.post else None,
            ".{}{}".format(*self.dev) if self.dev else None,
            local_sep + ".".join(map(str, self.local)) if self.local else None,
        ]
        return "".join(filter(None, parts))

    @cache
    def __repr__(self) -> str:
        return f"<Version('{self!s}')>"


def increment(value: packaging.version.Version | str, **kwargs) -> Version:
    """Increment the version `existing`.

    Identical to :py:`Version(str(value)).increment(**kwargs)`.

    See also
    --------
    Version.increment
    """
    return Version(str(value)).increment(**kwargs)


def parse(value: str) -> Version:
    """Parse the given version string.

    Identical to :py:`Version(value)`.

    See also
    --------
    Version
    """
    return Version(value)
