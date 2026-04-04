import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app import db
from app.database import Base
from app.main import app
from app.models.db_models import User
from app.services.rate_limit import rate_limiter
from tests import authenticated_api_user


@contextmanager
def temporary_db_session():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "security.db"
        engine = create_engine(f"sqlite:///{db_path}", future=True, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(bind=engine)

        try:
            with patch("app.db.SessionLocal", TestingSessionLocal), patch(
                "app.services.auth_service.SessionLocal", TestingSessionLocal
            ):
                yield TestingSessionLocal
        finally:
            engine.dispose()


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self):
        rate_limiter.reset()

    def test_cross_user_notebook_access_returns_not_found(self):
        with temporary_db_session() as TestingSessionLocal:
            with TestingSessionLocal() as session:
                session.add_all(
                    [
                        User(id="owner-1", email="owner@example.com", display_name="Owner"),
                        User(id="user-2", email="other@example.com", display_name="Other"),
                    ]
                )
                session.commit()

            notebook = db.create_notebook("Private notebook", user_id="owner-1")
            client = TestClient(app)

            with authenticated_api_user(user_id="user-2", email="other@example.com", display_name="Other"):
                response = client.get(f"/api/notebooks/{notebook['id']}")

            self.assertEqual(response.status_code, 404)

    def test_upload_rejects_non_pdf_payload_even_with_pdf_content_type(self):
        client = TestClient(app)

        with authenticated_api_user():
            with patch("app.api.upload.db.notebook_exists", return_value=True):
                response = client.post(
                    "/api/upload",
                    data={"notebook_id": "nb-1"},
                    files={"file": ("notes.pdf", b"not really a pdf", "application/pdf")},
                )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Uploaded file is not a valid PDF.")

    def test_sign_in_is_rate_limited_after_repeated_failures(self):
        with temporary_db_session():
            client = TestClient(app)

            with patch("app.api.auth.settings.auth_rate_limit_attempts", 1), patch(
                "app.api.auth.settings.auth_rate_limit_window_seconds", 60
            ):
                first = client.post(
                    "/api/auth/sign-in",
                    json={"email": "user@example.com", "password": "wrongpass123"},
                )
                second = client.post(
                    "/api/auth/sign-in",
                    json={"email": "user@example.com", "password": "wrongpass123"},
                )

        self.assertEqual(first.status_code, 401)
        self.assertEqual(second.status_code, 429)

    def test_untrusted_origin_is_rejected_for_cookie_auth_mutations(self):
        client = TestClient(app)

        with authenticated_api_user():
            response = client.post(
                "/api/notebooks",
                json={"title": "Blocked notebook", "icon_key": "robot"},
                headers={"Origin": "https://evil.example.com"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Request origin is not allowed.")

    def test_security_headers_are_present(self):
        client = TestClient(app)

        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(response.headers.get("x-frame-options"), "DENY")
        self.assertEqual(response.headers.get("referrer-policy"), "strict-origin-when-cross-origin")


if __name__ == "__main__":
    unittest.main()
