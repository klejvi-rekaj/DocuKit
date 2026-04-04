import atexit
from contextlib import contextmanager

from app.auth import RequestUserContext, require_request_user_context
from app.main import app
from app.database import engine


@atexit.register
def _dispose_shared_engine() -> None:
    engine.dispose()


@contextmanager
def authenticated_api_user(
    user_id: str = "user-test",
    email: str = "user@example.com",
    display_name: str = "Test User",
):
    app.dependency_overrides[require_request_user_context] = lambda: RequestUserContext(
        user_id=user_id,
        email=email,
        display_name=display_name,
        session_id="session-test",
        authenticated=True,
    )
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_request_user_context, None)
