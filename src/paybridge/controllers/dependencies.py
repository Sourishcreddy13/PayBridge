from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header

from paybridge.domain.enums import Role
from paybridge.domain.exceptions import AuthenticationError, AuthorizationError
from paybridge.infrastructure.settings import Settings


class AuthContext:
    def __init__(self, actor: str, role: Role) -> None:
        self.actor = actor
        self.role = role


def current_auth(authorization: Annotated[str | None, Header()] = None) -> AuthContext:
    settings = Settings()
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    roles = settings.token_roles()
    role_value = roles.get(token)
    if role_value is None:
        raise AuthenticationError("Invalid bearer token")
    return AuthContext(actor=f"demo-{role_value.lower()}", role=Role(role_value))


def require_roles(*allowed: Role) -> Callable[[AuthContext], AuthContext]:
    def dependency(auth: Annotated[AuthContext, Depends(current_auth)]) -> AuthContext:
        if auth.role not in allowed:
            raise AuthorizationError("Insufficient role")
        return auth

    return dependency
