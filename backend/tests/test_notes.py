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
from tests import authenticated_api_user


@contextmanager
def temporary_db_session():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "notes.db"
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
                yield
        finally:
            engine.dispose()


class NotesTests(unittest.TestCase):
    def test_notes_persist_and_stay_notebook_scoped(self):
        with temporary_db_session():
            notebook_a = db.create_notebook("Notebook A")
            notebook_b = db.create_notebook("Notebook B")
            db.create_note(notebook_a["id"], "First note")
            db.create_note(notebook_a["id"], "Second note")
            db.create_note(notebook_b["id"], "Notebook B note")

            notebook_a_notes = db.list_notes_for_notebook(notebook_a["id"])
            notebook_b_notes = db.list_notes_for_notebook(notebook_b["id"])

            self.assertEqual(len(notebook_a_notes), 2)
            self.assertTrue(all(note["notebook_id"] == notebook_a["id"] for note in notebook_a_notes))
            self.assertEqual(len(notebook_b_notes), 1)
            self.assertEqual(notebook_b_notes[0]["content"], "Notebook B note")

    def test_delete_note_requires_matching_notebook_scope(self):
        with temporary_db_session():
            notebook_a = db.create_notebook("Notebook A")
            notebook_b = db.create_notebook("Notebook B")
            note = db.create_note(notebook_a["id"], "Delete me")

            deleted_from_wrong_notebook = db.delete_note(note["id"], notebook_b["id"])
            self.assertFalse(deleted_from_wrong_notebook)

            deleted_from_correct_notebook = db.delete_note(note["id"], notebook_a["id"])
            self.assertTrue(deleted_from_correct_notebook)
            self.assertEqual(db.list_notes_for_notebook(notebook_a["id"]), [])

    def test_notes_endpoints_require_matching_notebook_scope(self):
        client = TestClient(app)

        with authenticated_api_user(), patch("app.api.notes.db.notebook_exists", return_value=True), patch(
            "app.api.notes.db.create_note",
            return_value={
                "id": "note-1",
                "notebook_id": "nb-1",
                "content": "Saved answer",
                "source_message_id": None,
                "created_at": "",
                "updated_at": "",
            },
        ):
            create_response = client.post(
                "/api/notes",
                json={
                    "notebook_id": "nb-1",
                    "content": "Saved answer",
                    "source_message_id": None,
                },
            )

        self.assertEqual(create_response.status_code, 201)

        with authenticated_api_user(), patch("app.api.notes.db.notebook_exists", return_value=False):
            list_response = client.get("/api/notes/missing-notebook")

        self.assertEqual(list_response.status_code, 404)

        with authenticated_api_user(), patch("app.api.notes.db.delete_note", return_value=True):
            delete_response = client.delete("/api/notes/nb-1/note-1")

        self.assertEqual(delete_response.status_code, 204)


if __name__ == "__main__":
    unittest.main()
