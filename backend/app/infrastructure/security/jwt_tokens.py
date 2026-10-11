from datetime import timedelta

import jwt

from app.application.clock import Clock, utc_now
from app.application.errors import InvalidTokenError


class JwtTokenService:
    """Signed, expiring JWT access tokens (implements the TokenService port)."""

    def __init__(
        self, secret: str, algorithm: str, expire_minutes: int, clock: Clock = utc_now
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expire = timedelta(minutes=expire_minutes)
        self._clock = clock

    def create_access_token(self, user_id: int) -> str:
        now = self._clock()
        claims = {"sub": str(user_id), "iat": now, "exp": now + self._expire}
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)

    def read_subject(self, token: str) -> int:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["exp", "sub"]},
            )
            return int(claims["sub"])
        except (jwt.PyJWTError, ValueError) as exc:
            raise InvalidTokenError from exc
