import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app


@contextmanager
def temporary_db_session():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "auth.db"
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
                yield
        finally:
            engine.dispose()


class AuthTests(unittest.TestCase):
    def test_sign_up_sign_in_session_and_sign_out_flow(self):
        with temporary_db_session():
            client = TestClient(app)

            sign_up_response = client.post(
                "/api/auth/sign-up",
                json={
                    "name": "Klejvi",
                    "email": "klejvi@example.com",
                    "password": "supersecure123",
                },
            )

            self.assertEqual(sign_up_response.status_code, 201)
            self.assertTrue(sign_up_response.json()["authenticated"])
            self.assertEqual(sign_up_response.json()["user"]["email"], "klejvi@example.com")

            session_response = client.get("/api/auth/session")
            self.assertEqual(session_response.status_code, 200)
            self.assertTrue(session_response.json()["authenticated"])

            protected_response = client.get("/api/notebooks")
            self.assertEqual(protected_response.status_code, 200)

            sign_out_response = client.post("/api/auth/sign-out")
            self.assertEqual(sign_out_response.status_code, 200)
            self.assertFalse(sign_out_response.json()["authenticated"])

            session_after_sign_out = client.get("/api/auth/session")
            self.assertEqual(session_after_sign_out.status_code, 200)
            self.assertFalse(session_after_sign_out.json()["authenticated"])

            sign_in_response = client.post(
                "/api/auth/sign-in",
                json={
                    "email": "klejvi@example.com",
                    "password": "supersecure123",
                },
            )
            self.assertEqual(sign_in_response.status_code, 200)
            self.assertTrue(sign_in_response.json()["authenticated"])

    def test_protected_route_rejects_unauthenticated_request(self):
        client = TestClient(app)

        response = client.get("/api/notebooks")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Authentication required.")

    def test_invalid_session_cookie_is_cleared_and_treated_as_logged_out(self):
        client = TestClient(app)
        client.cookies.set("dokukit_session", "invalid-token")

        response = client.get("/api/auth/session")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])
        self.assertIn("dokukit_session=", response.headers.get("set-cookie", ""))

    def test_sign_out_with_stale_cookie_still_succeeds(self):
        client = TestClient(app)
        client.cookies.set("dokukit_session", "stale-token")

        response = client.post("/api/auth/sign-out")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["authenticated"])


if __name__ == "__main__":
    unittest.main()
