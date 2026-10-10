"""Application-level errors raised by use cases and translated by the API layer."""


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    """Unknown email, wrong password or disabled account (deliberately indistinguishable)."""


class InvalidTokenError(Exception):
    """The access token is malformed, tampered with or expired."""
