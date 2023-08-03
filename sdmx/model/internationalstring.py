from copy import copy
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

# TODO read this from the environment, or use any value set in the SDMX-ML spec.
#      Currently set to 'en' because test_dsd.py expects it.
#: Default locale for :class:`InternationalString`.
DEFAULT_LOCALE = "en"

# §3.2: Base structures


class InternationalString:
    """SDMX-IM InternationalString.

    SDMX-IM LocalisedString is not implemented. Instead, the 'localizations' is a
    mapping where:

    - keys correspond to the 'locale' property of LocalisedString.
    - values correspond to the 'label' property of LocalisedString.

    When used as a type hint with pydantic, InternationalString fields can be assigned
    to in one of four ways::

        @dataclass
        class Foo:
             name: InternationalStringDescriptor() = InternationalStringDescriptor()

        # Equivalent: no localizations
        f = Foo()
        f = Foo(name={})

        # Using an explicit locale
        f.name['en'] = "Foo's name in English"

        # Using a (locale, label) tuple
        f.name = ('fr', "Foo's name in French")

        # Using a dict
        f.name = {'en': "Replacement English name",
                  'fr': "Replacement French name"}

        # Using a bare string, implicitly for the DEFAULT_LOCALE
        f.name = "Name in DEFAULT_LOCALE language"

    Only the first method preserves existing localizations; the latter three replace
    them.

    """

    # Types that can be converted into InternationalString
    _CONVERTIBLE = Union[str, Sequence, Mapping, Iterable[Tuple[str, str]]]

    localizations: Dict[str, str] = {}

    def __init__(self, value: Optional[_CONVERTIBLE] = None, **kwargs):
        # Handle initial values according to type
        if value is None:
            # Keyword arguments → dict, possibly empty
            value = dict(kwargs)
        elif isinstance(value, str):
            # Bare string
            value = {DEFAULT_LOCALE: value}
        elif (
            isinstance(value, Sequence)
            and len(value) == 2
            and isinstance(value[0], str)
        ):
            # 2-tuple of str is (locale, label)
            value = {value[0]: value[1]}
        elif isinstance(value, Mapping):
            # dict; use directly
            value = dict(value)
        else:
            try:
                # Iterable of 2-tuples
                value = {  # type: ignore [misc]
                    locale: label for (locale, label) in value
                }
            except Exception:
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
            return self.__dict__["localizations"][name]
        except KeyError:
            raise AttributeError(name) from None

    def __add__(self, other):
        result = copy(self)
        result.localizations.update(other.localizations)
        return result

    def localized_default(self, locale=None) -> str:
        """Return the string in *locale*, or else the first defined."""
        try:
            return self.localizations[locale]
        except KeyError:
            if len(self.localizations):
                # No label in the default locale; use the first stored value
                return next(iter(self.localizations.values()))
            else:
                return ""

    def __str__(self):
        return self.localized_default(DEFAULT_LOCALE)

    def __repr__(self):
        return "\n".join(
            ["{}: {}".format(*kv) for kv in sorted(self.localizations.items())]
        )

    def __eq__(self, other):
        try:
            return self.localizations == other.localizations
        except AttributeError:
            return NotImplemented


_TInternationalString = Union[InternationalString, InternationalString._CONVERTIBLE]
_TInternationalStringInit = Union[_TInternationalString, None]


class InternationalStringDescriptor:
    def __set_name__(self, owner, name):
        self._name = "_" + name

    def __get__(self, obj, type) -> InternationalString:
        if obj is None:
            return None  # type: ignore [return-value]

        return obj.__dict__[self._name]

    def __set__(self, obj, value: _TInternationalStringInit):
        if not isinstance(value, InternationalString):
            value = InternationalString(value)
        setattr(obj, self._name, value)
