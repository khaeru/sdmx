import importlib
from typing import Optional, Tuple

import pytest
from packaging.version import Version


# thanks to xarray
def _importorskip(
    modname: str, minversion: Optional[str] = None
) -> Tuple[bool, pytest.MarkDecorator]:
    try:
        mod = importlib.import_module(modname)
        has = True
        if minversion is not None:  # pragma: no cover
            if Version(mod.__version__) < Version(minversion):
                raise ImportError("Minimum version not satisfied")
    except ImportError:
        has = False
    func = pytest.mark.skipif(not has, reason=f"requires {modname}")
    return has, func


has_requests_cache, requires_requests_cache = _importorskip("requests_cache")
