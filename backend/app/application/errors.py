"""Application-level errors raised by use cases and translated by the API layer."""


class EmailAlreadyRegisteredError(Exception):
    pass


class DuplicateEntryError(Exception):
    """A unique constraint rejected a staged row: a concurrent write won the race.

    The surrounding unit of work must roll back; the use case translates this into the
    domain conflict that fits its context.
    """


class InvalidCredentialsError(Exception):
    """Unknown email, wrong password or disabled account (deliberately indistinguishable)."""


class InvalidTokenError(Exception):
    """The access token is malformed, tampered with or expired."""


class PermissionDeniedError(Exception):
    """The actor is not allowed to perform the operation."""


class UserNotFoundError(Exception):
    pass


class SelfLockoutError(Exception):
    """An admin tried to demote or deactivate their own account."""


class EventNotFoundError(Exception):
    pass


class SpeakerNotFoundError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


class SpeakerEmailTakenError(Exception):
    pass


class SpeakerInUseError(Exception):
    """The speaker still has sessions assigned and cannot be deleted."""
