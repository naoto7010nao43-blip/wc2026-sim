import pytest

from app import rate_limit


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """The rate limiter's bucket store is process-global, so without this,
    unrelated tests sharing pytest's single process would leak request
    counts into each other."""
    rate_limit.reset()
    yield
    rate_limit.reset()
