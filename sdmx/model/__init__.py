from warnings import warn

from . import common, v21

WARNED = set()


def __dir__():
    return dir(common)


def __getattr__(name):
    # Common classes are available directly
    try:
        return getattr(common, name)
    except AttributeError:
        pass

    try:
        result = getattr(v21, name)
    except AttributeError:
        raise
    else:
        if name not in WARNED:
            WARNED.add(name)
            warn(
                message=f"Importing {name} from sdmx.model. "
                f'Use "from sdmx.model.v21 import {name}" instead.',
                category=DeprecationWarning,
                stacklevel=2,
            )
        return result
