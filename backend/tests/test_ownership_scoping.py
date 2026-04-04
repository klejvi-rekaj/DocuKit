import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app import db
from app.database import Base
from app.models.db_models import User


@contextmanager
def temporary_db_session():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "ownership.db"
        engine = create_engine(f"sqlite:///{db_path}", future=True, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(bind=engine)

        try:
            with patch("app.db.SessionLocal", TestingSessionLocal):
                yield TestingSessionLocal
        finally:
            engine.dispose()


class OwnershipScopingTests(unittest.TestCase):
    def test_unowned_notebooks_are_the_only_public_notebooks_without_user_context(self):
        with temporary_db_session() as TestingSessionLocal:
            with TestingSessionLocal() as session:
                session.add(User(id="user-123", email="owner@example.com", display_name="Owner"))
                session.commit()

            public_notebook = db.create_notebook("Public notebook", user_id=None)
            private_notebook = db.create_notebook("Private notebook", user_id="user-123")

            visible = db.list_notebooks()
            self.assertEqual([notebook["id"] for notebook in visible], [public_notebook["id"]])

            self.assertIsNotNone(db.get_notebook(public_notebook["id"]))
            self.assertIsNone(db.get_notebook(private_notebook["id"]))

    def test_user_scoped_queries_include_owned_and_legacy_unowned_notebooks(self):
        with temporary_db_session() as TestingSessionLocal:
            with TestingSessionLocal() as session:
                session.add_all(
                    [
                        User(id="user-123", email="mine@example.com", display_name="Mine"),
                        User(id="user-999", email="other@example.com", display_name="Other"),
                    ]
                )
                session.commit()

            public_notebook = db.create_notebook("Public notebook", user_id=None)
            mine = db.create_notebook("Mine", user_id="user-123")
            db.create_notebook("Someone else's", user_id="user-999")

            visible = db.list_notebooks(user_id="user-123")
            visible_ids = {notebook["id"] for notebook in visible}

            self.assertIn(public_notebook["id"], visible_ids)
            self.assertIn(mine["id"], visible_ids)
            self.assertEqual(db.get_notebook(mine["id"], user_id="user-123")["id"], mine["id"])
            self.assertIsNone(db.get_notebook(mine["id"], user_id="user-999"))


if __name__ == "__main__":
    unittest.main()
