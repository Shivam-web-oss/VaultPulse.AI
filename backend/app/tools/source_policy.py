"""Source access policy (doc §15).

Only permitted sources may be accessed, respecting terms, access
restrictions, and rate limits. Phase D will extend this with real
robots/ToS checks and rate limiting.
"""

_PERMITTED_SOURCES = {
    "example-product-directory",
    "example-marketplace-feed",
    "example-jobs-board",
    "example-events-calendar",
    "example-web-index",
}


def is_permitted(source: str) -> bool:
    return source in _PERMITTED_SOURCES
