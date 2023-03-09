from warnings import warn

from . import v21


def __getattr__(name):
    try:
        result = getattr(v21, name)
    except AttributeError:
        raise
    else:
        # TODO reduce number of warnings emitted
        warn(
            message=" ".join(
                [
                    f"Importing {name} from sdmx.model.",
                    f'Use "from sdmx.model.v21 import {name}" instead.',
                ]
            ),
            category=DeprecationWarning,
            stacklevel=-2,
        )
        return result
