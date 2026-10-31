class FestivalError(Exception):
    """Base of every deliberate error in this package."""


class NotFoundError(FestivalError):
    """Unknown venue, artist or performance id (HTTP 404)."""


class ConflictError(FestivalError):
    """Valid request that clashes with the schedule (HTTP 409)."""


class InvalidError(FestivalError):
    """Value outside the rules of the brief (HTTP 422)."""


class StorageError(FestivalError):
    """Data file missing, damaged or unwritable (HTTP 500)."""
