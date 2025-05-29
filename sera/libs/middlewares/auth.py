from __future__ import annotations

from datetime import datetime, timezone
from typing import Awaitable, Callable, Generic, Sequence

from litestar import Request
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from litestar.types import ASGIApp, Method, Scopes

from sera.typing import T


class AuthMiddleware(AbstractAuthenticationMiddleware, Generic[T]):
    """
    Middleware to handle authentication for the API.

    This middleware checks if the user is authenticated to access
    the requested resource. If not, it raises an HTTPException with a 401 status code.
    """

    def __init__(
        self,
        app: ASGIApp,
        user_handler: Callable[[str], Awaitable[T]],
        exclude: str | list[str] | None = None,
        exclude_from_auth_key: str = "exclude_from_auth",
        exclude_http_methods: Sequence[Method] | None = None,
        scopes: Scopes | None = None,
    ) -> None:
        super().__init__(
            app=app,
            exclude=exclude,
            exclude_from_auth_key=exclude_from_auth_key,
            exclude_http_methods=exclude_http_methods,
            scopes=scopes,
        )
        self.user_handler = user_handler

    async def authenticate_request(
        self, connection: ASGIConnection
    ) -> AuthenticationResult:
        # do something here.
        if "userid" not in connection.session:
            raise NotAuthorizedException(
                detail="Invalid credentials",
            )

        userid: str = connection.session["userid"]
        expired_at = datetime.fromtimestamp(
            connection.session.get("exp", 0), timezone.utc
        )
        if expired_at < datetime.now(timezone.utc):
            raise NotAuthorizedException(
                detail="Credentials expired",
            )

        user = await self.user_handler(userid)
        if user is None:
            raise NotAuthorizedException(
                detail="User not found",
            )

        return AuthenticationResult(user, None)

    @staticmethod
    def save(req: Request, user: T, expired_at: datetime) -> None:
        req.session["userid"] = user.id
        req.session["exp"] = expired_at.timestamp()
