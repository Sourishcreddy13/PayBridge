from collections.abc import Callable
from typing import Annotated, Protocol

from fastapi import Depends, Header, Request

from paybridge.domain.enums import Role
from paybridge.domain.exceptions import AuthenticationError, AuthorizationError


class TokenDirectory(Protocol):
    def token_identities(self) -> dict[str, tuple[str, Role]]: ...


class AuthContext:
    """The authenticated principal: a unique subject (recorded in audit) plus a role."""

    def __init__(self, actor: str, role: Role) -> None:
        self.actor = actor
        self.role = role

    @property
    def owner_filter(self) -> str | None:
        """Customers are confined to their own payments; staff see everything."""
        return self.actor if self.role is Role.CUSTOMER else None


def current_auth(
    request: Request, authorization: Annotated[str | None, Header()] = None
) -> AuthContext:
    settings: TokenDirectory = request.app.state.settings
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    identity = settings.token_identities().get(token)
    if identity is None:
        raise AuthenticationError("Invalid bearer token")
    subject, role = identity
    return AuthContext(actor=subject, role=role)


def require_roles(*allowed: Role) -> Callable[[AuthContext], AuthContext]:
    def dependency(auth: Annotated[AuthContext, Depends(current_auth)]) -> AuthContext:
        if auth.role not in allowed:
            raise AuthorizationError("Insufficient role")
        return auth

    return dependency
