from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from fastapi import Cookie, Depends, HTTPException, Request, Response, status

from app.config import settings
from app.services.auth_service import get_session_user


@dataclass(frozen=True)
class RequestUserContext:
    user_id: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    theme_preference: Optional[str] = None
    has_password: bool = False
    session_id: Optional[str] = None
    authenticated: bool = False


def set_auth_cookie(response: Response, raw_session_token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_session_token,
        httponly=True,
        secure=settings.resolved_session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_max_age_seconds,
        path="/",
        domain=settings.session_cookie_domain,
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        domain=settings.session_cookie_domain,
    )


def _request_origin_is_trusted(request: Request) -> bool:
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    candidate = origin

    if not candidate and referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            candidate = f"{parsed.scheme}://{parsed.netloc}"

    if not candidate:
        return True

    return candidate in settings.trusted_frontend_origins


async def verify_csrf_request(request: Request) -> None:
    if request.method.upper() not in {"POST", "PATCH", "PUT", "DELETE"}:
        return

    if not _request_origin_is_trusted(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Request origin is not allowed.")


async def get_optional_request_user_context(
    request: Request,
    response: Response,
    session_token: Optional[str] = Cookie(default=None, alias=settings.session_cookie_name),
) -> RequestUserContext:
    if not session_token:
        return RequestUserContext()

    session_result = get_session_user(session_token)
    if not session_result:
        clear_auth_cookie(response)
        return RequestUserContext()

    return RequestUserContext(
        user_id=session_result.user.id,
        email=session_result.user.email,
        display_name=session_result.user.display_name,
        theme_preference=session_result.user.theme_preference,
        has_password=session_result.user.has_password,
        session_id=session_result.session_id,
        authenticated=True,
    )


async def require_request_user_context(
    user: RequestUserContext = Depends(get_optional_request_user_context),
) -> RequestUserContext:
    if not user.authenticated or not user.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user
