from __future__ import annotations

from typing import Callable

from litestar.connection.base import UserT
from litestar.middleware import AbstractMiddleware
from litestar.types import ASGIApp, Message, Receive, Scope, Scopes, Send

SKIP_UPDATE_SYSTEM_CONTROLLED_PROPS_KEY = "skip_uscp_1157"


class USCPMiddleware(AbstractMiddleware):
    """
    Middleware to update system-controlled properties in the request.

    This middleware updates the `created_at`, `updated_at`, and `deleted_at` properties
    of the request with the current timestamp. It is intended to be used in a Litestar
    application.
    """

    def __init__(
        self,
        app: ASGIApp,
        skip_update_system_controlled_props: Callable[[UserT], bool],
        exclude: str | list[str] | None = None,
        exclude_opt_key: str | None = None,
        scopes: Scopes | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ``next`` ASGI app to call.
            exclude: A pattern or list of patterns to match against a request's path.
                If a match is found, the middleware will be skipped.
            exclude_opt_key: An identifier that is set in the route handler
                ``opt`` key which allows skipping the middleware.
            scopes: ASGI scope types, should be a set including
                either or both 'ScopeType.HTTP' and 'ScopeType.WEBSOCKET'.
        """
        super().__init__(app, exclude, exclude_opt_key, scopes)
        self.skip_update_system_controlled_props = skip_update_system_controlled_props

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        user = scope["user"]
        scope["state"][SKIP_UPDATE_SYSTEM_CONTROLLED_PROPS_KEY] = (
            self.skip_update_system_controlled_props(user)
        )
        await self.app(scope, receive, send)


def get_scp_from_user(user: UserT, fields: dict[str, str]) -> dict:
    """Get system-controlled properties from the user.

    Args:
        user: The user object.
        fields: A list of fields to include in the system-controlled properties.

    Returns:
        A dictionary containing the system-controlled properties.
    """
    return {
        data_field: getattr(user, db_field) for data_field, db_field in fields.items()
    }
