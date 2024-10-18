import operator
import re
from typing import Callable, Optional, Union

import packaging.version

#: Regular expressions (:class:`re.Pattern`) for version strings.
#:
#: - :py:`"2_1"` SDMX 2.1, e.g. "1.0"
#: - :py:`"3_0"` SDMX 3.0, e.g. "1.0.0-draft"
#: - :py:`"py"` Python-compatible versions, using :mod:`packaging.version`.
VERSION_PATTERNS = {
    "2_1": re.compile(r"^(?P<release>[0-9]+(?:\.[0-9]+){1})$"),
    "3_0": re.compile(r"^(?P<release>[0-9]+(?:\.[0-9]+){2})(-(?P<ext>.+))?$"),
    "py": re.compile(
        r"^\s*" + packaging.version.VERSION_PATTERN + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    ),
}


def _cmp_method(op: Callable) -> Callable:
    def cmp(self, other) -> bool:
        try:
            return op(self._key, other._key)
        except AttributeError:
            if isinstance(other, str):
                return op(self, Version(other))
            else:
                return NotImplemented

    return cmp


class Version(packaging.version.Version):
    """Class representing a version.

    The SDMX Information Model **does not** specify a Version class; instead,
    :attr:`.VersionableArtefact.version` is described as “a version **string** following
    SDMX versioning rules.”

    In order to simplify application of those ‘rules’, and to handle the differences
    between SDMX 2.1 and 3.0.0, this class extends :class:`packaging.version.Version`,
    which provides a complete interface for interacting with Python version specifiers.
    The extensions implement the particular form of versioning laid out by the SDMX
    standards. Specifically:

    - :attr:`kind` as added to identify whether a Version instance is an SDMX 2.1, SDMX
      3.0, or Python-style version string.
    - Attribute aliases for particular terms used in the SDMX 3.0 standards:
      :attr:`patch` and :attr:`ext`.
    - The :class:`str` representation of a Version uses the SDMX 3.0 style of separating
      the :attr:`ext` with a hyphen ("1.0.0-dev1"), which differs from the Python style
      of using no separator for a ‘post-release’ ("1.0.0dev1") or a plus symbol for a
      ‘local part’ ("1.0.0+dev1").
    - :meth:`increment`, an added convenience method.
    - The class is comparable and interchangeable with :class:`str` version expressions.

    Parameters
    ----------
    version : str
        String expression
    """

    #: Type of version expression; one of the keys of :data:`.VERSION_PATTERNS`.
    kind: str

    def __init__(self, version: str):
        for kind, pattern in VERSION_PATTERNS.items():
            match = pattern.fullmatch(version)
            if match:
                break

        if not match:
            raise packaging.version.InvalidVersion(version)

        self.kind = kind

        if kind == "py":
            tmp = packaging.version.Version(version)
            self._version = tmp._version
        else:
            # Store the parsed out pieces of the version
            try:
                ext = match.group("ext")
                local = None if ext is None else (ext,)
            except IndexError:
                local = None
            self._version = packaging.version._Version(
                epoch=0,
                release=tuple(int(i) for i in match.group("release").split(".")),
                pre=None,
                post=None,
                dev=None,
                local=local,
            )

        self._update_key()

    def _update_key(self):
        # Generate a key which will be used for sorting
        self._key = packaging.version._cmpkey(
            self._version.epoch,
            self._version.release,
            self._version.pre,
            self._version.post,
            self._version.dev,
            self._version.local,
        )

    def __str__(self):
        if self.kind == "3_0":
            parts = [".".join(str(x) for x in self.release)]
            if self.ext:
                parts.append(f"-{self.ext}")
            return "".join(parts)
        else:
            return super().__str__()

    __eq__ = _cmp_method(operator.eq)
    __ge__ = _cmp_method(operator.ge)
    __gt__ = _cmp_method(operator.gt)
    __le__ = _cmp_method(operator.le)
    __lt__ = _cmp_method(operator.lt)
    __ne__ = _cmp_method(operator.ne)

    @property
    def patch(self) -> int:
        """Alias for :any:`Version.micro <packaging.version.Version.micro>`."""
        return self.micro

    @property
    def ext(self) -> Optional[str]:
        """SDMX 3.0 version 'extension'.

        For :py:`kind="py"`, this is equivalent to :attr:`Version.local
        <packaging.version.Version.local>`.
        """
        if self._version.local is None:
            return None
        else:
            return "".join(map(str, self._version.local))

    def increment(self, **kwargs: Union[bool, int]) -> "Version":
        """Return a Version that is incrementally greater than the current Version.

        If no arguments are given, then by default :py:`minor=True` and :py:`ext=1`.

        Parameters
        ----------
        major : bool or int, optional
            If given, increment the :attr:`Version.major
            <packaging.version.Version.major>` part.
        minor : bool or int, optional
            If given, increment the :attr:`Version.minor
            <packaging.version.Version.minor>` part.
        patch : bool or int, optional
            If given, increment the :attr:`.Version.patch` part.
        micro : bool or int, optional
            Alias for `patch`.
        ext : bool or int, optional
            If given, increment the :attr:`.Version.ext` part. If this part is not
            present, add "dev1".
        local: bool or int, optional
            Alias for `ext`.
        """
        if not kwargs:
            # Apply defaults
            kwargs["minor"] = kwargs["ext"] = 1

        # Convert self._version.release into a mutable dict
        N_release = len(self._version.release)  # Number of parts in `release` tuple
        parts = dict(
            major=self._version.release[0] if N_release > 0 else 0,
            minor=self._version.release[1] if N_release > 1 else 0,
            patch=self._version.release[2] if N_release > 2 else 0,
        )
        # Convert self._version.local into a mutable list
        local = list(self._version.local) if self._version.local is not None else []

        # Increment parts according to kwargs
        for part, value in kwargs.items():
            # Recognize kwarg aliases
            part = {"local": "ext", "micro": "patch"}.get(part, part)

            # Update the extension/local part
            if part == "ext":
                if not len(local):
                    ext = "dev1"
                elif match := re.fullmatch("([^0-9]+)([0-9]+)", str(local[0])):
                    _l, _n = match.group(1, 2)
                    ext = f"{_l}{int(_n) + value}"
                else:
                    raise NotImplementedError(
                        f"Increment SDMX version extension {self.ext!r}"
                    )
                local = [ext]
                continue

            try:
                # Update the major/minor/patch parts
                parts[part] += int(value)
            except KeyError:
                raise ValueError(f"increment(..., {part}={value})")

        # Construct a new Version object
        result = type(self)(str(self))
        # Overwrite its private _version attribute and key
        result._version = packaging.version._Version(
            epoch=self._version.epoch,
            release=tuple(parts.values()),
            pre=self._version.pre,
            post=self._version.post,
            dev=self._version.dev,
            local=tuple(local) if len(local) else None,
        )
        result._update_key()

        return result


def increment(value: Union[packaging.version.Version, str], **kwargs) -> Version:
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
