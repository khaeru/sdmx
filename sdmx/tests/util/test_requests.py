import pytest


class TestOfflineAdapter:
    def test_raises(self, session_with_stored_responses):
        with pytest.raises(RuntimeError):
            session_with_stored_responses.get("https://example.com")
