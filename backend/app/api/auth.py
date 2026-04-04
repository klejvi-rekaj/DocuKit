import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth import RequestUserContext, clear_auth_cookie, get_optional_request_user_context, require_request_user_context, set_auth_cookie, verify_csrf_request
from app.config import settings
from app.models.schemas import (
    AuthSessionResponse,
    AuthUserResponse,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    SignInRequest,
    SignUpRequest,
    ThemePreferenceUpdateRequest,
)
from app.services import auth_service
from app.services.rate_limit import rate_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _build_session_response(user: RequestUserContext | auth_service.AuthenticatedUser | None) -> AuthSessionResponse:
    if not user:
        return AuthSessionResponse(authenticated=False, user=None)

    return AuthSessionResponse(
        authenticated=True,
        user=AuthUserResponse(
            id=user.user_id if isinstance(user, RequestUserContext) else user.id,
            email=user.email or "",
            display_name=user.display_name,
            theme_preference=user.theme_preference if isinstance(user, RequestUserContext) else user.theme_preference,
            has_password=user.has_password if isinstance(user, RequestUserContext) else user.has_password,
        ),
    )


@router.get("/session", response_model=AuthSessionResponse)
async def get_session(
    response: Response,
    user: RequestUserContext = Depends(get_optional_request_user_context),
):
    if not user.authenticated:
        return AuthSessionResponse(authenticated=False, user=None)
    return _build_session_response(user)


@router.post("/sign-up", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
async def sign_up(
    request: SignUpRequest,
    response: Response,
    http_request: Request,
    _: None = Depends(verify_csrf_request),
):
    name = request.name.strip()
    email = request.email.strip()
    password = request.password

    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")
    if not auth_service.validate_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if not auth_service.validate_password(password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    client_ip = http_request.client.host if http_request.client else "unknown"
    rate_limiter.hit(
        f"auth:sign-up:{client_ip}",
        settings.sign_up_rate_limit_attempts,
        settings.sign_up_rate_limit_window_seconds,
    )

    try:
        user = auth_service.create_user(email=email, display_name=name, password=password)
    except ValueError as exc:
        logger.warning("Sign-up rejected for email=%s ip=%s reason=%s", email, client_ip, str(exc))
        raise HTTPException(status_code=409, detail=str(exc))

    auth_service.claim_legacy_notebooks_for_user(user.id)
    session_token = auth_service.generate_session_token()
    auth_service.create_user_session(user.id, session_token, user_agent=http_request.headers.get("user-agent"))
    set_auth_cookie(response, session_token)
    logger.info("Sign-up succeeded for user_id=%s ip=%s", user.id, client_ip)
    return _build_session_response(user)


@router.post("/sign-in", response_model=AuthSessionResponse)
async def sign_in(
    request: SignInRequest,
    response: Response,
    http_request: Request,
    _: None = Depends(verify_csrf_request),
):
    email = request.email.strip()
    password = request.password

    if not auth_service.validate_email(email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")

    client_ip = http_request.client.host if http_request.client else "unknown"
    rate_limiter.hit(
        f"auth:sign-in:{client_ip}",
        settings.auth_rate_limit_attempts,
        settings.auth_rate_limit_window_seconds,
    )

    user = auth_service.authenticate_user(email=email, password=password)
    if not user:
        logger.warning("Sign-in failed for email=%s ip=%s", email, client_ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    auth_service.claim_legacy_notebooks_for_user(user.id)
    session_token = auth_service.generate_session_token()
    auth_service.create_user_session(user.id, session_token, user_agent=http_request.headers.get("user-agent"))
    set_auth_cookie(response, session_token)
    logger.info("Sign-in succeeded for user_id=%s ip=%s", user.id, client_ip)
    return _build_session_response(user)


@router.post("/sign-out", response_model=AuthSessionResponse)
async def sign_out(
    http_request: Request,
    response: Response,
    _: None = Depends(verify_csrf_request),
):
    raw_token = http_request.cookies.get(settings.session_cookie_name)
    if raw_token:
        auth_service.delete_user_session(raw_token)
    clear_auth_cookie(response)
    logger.info("Sign-out completed for ip=%s", http_request.client.host if http_request.client else "unknown")
    return AuthSessionResponse(authenticated=False, user=None)


@router.patch("/profile", response_model=AuthSessionResponse)
async def update_profile(
    request: ProfileUpdateRequest,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    if not auth_service.validate_email(request.email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")

    try:
        updated_user = auth_service.update_user_profile(
            user.user_id,
            display_name=request.display_name,
            email=request.email,
        )
    except ValueError as exc:
        detail = str(exc)
        if "already exists" in detail:
            raise HTTPException(status_code=409, detail=detail)
        raise HTTPException(status_code=400, detail=detail)

    logger.info("Profile updated for user_id=%s", user.user_id)
    return _build_session_response(updated_user)


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    http_request: Request,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    client_ip = http_request.client.host if http_request.client else "unknown"
    rate_limiter.hit(
        f"auth:change-password:{user.user_id}:{client_ip}",
        settings.auth_rate_limit_attempts,
        settings.auth_rate_limit_window_seconds,
    )

    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="New password confirmation does not match.")

    try:
        auth_service.change_user_password(
            user.user_id,
            current_password=request.current_password,
            new_password=request.new_password,
        )
    except ValueError as exc:
        detail = str(exc)
        if "incorrect" in detail:
            raise HTTPException(status_code=400, detail="Current password is incorrect.")
        raise HTTPException(status_code=400, detail=detail)

    logger.info("Password updated for user_id=%s", user.user_id)
    return {"success": True}


@router.patch("/preferences/theme", response_model=AuthSessionResponse)
async def update_theme_preference(
    request: ThemePreferenceUpdateRequest,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    try:
        updated_user = auth_service.update_user_theme_preference(user.user_id, request.theme_preference)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info("Theme preference updated for user_id=%s preference=%s", user.user_id, request.theme_preference)
    return _build_session_response(updated_user)
