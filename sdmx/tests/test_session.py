import pytest

from sdmx.session import Session

from . import has_requests_cache


class TestSession:
    def test_init0(self, tmp_path):
        # requests_cache keyword argument, with invalid value
        # - TypeError if requests_cache is not installed
        # - ValueError from requests_cache if installed
        with pytest.raises(ValueError if has_requests_cache else TypeError):
            Session(backend="not_a_backend")

        # Keyword argument for a requests-cache backend, like fast_save, are accepted
        Session(
            cache_name=tmp_path.joinpath("TestSession_test_init0"),
            backend="sqlite",
            fast_save=True,
        )

        # Not an argument handled by sdmx1 or by requests_cache —no exception raised
        Session(foo="bar")


@pytest.mark.network
@pytest.mark.xfail(condition=not has_requests_cache, reason="Requires cache")
def test_init_cache(tmp_path):
    # Instantiate a REST object with cache
    cache_name = tmp_path.joinpath("test_init_cache")
    s = Session(cache_name=str(cache_name), backend="sqlite")

    # Get a resource
    s.get("https://registry.sdmx.org/ws/rest/dataflow")

    # Test for existence of cache file
    assert cache_name.with_suffix(".sqlite").exists()
