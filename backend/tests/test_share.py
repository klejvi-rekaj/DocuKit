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
from app.models.db_models import DocumentProcessingStatus
from tests import authenticated_api_user


@contextmanager
def temporary_db_session():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "share.db"
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


class ShareNotebookTests(unittest.TestCase):
    def test_share_generation_and_public_payload(self):
        with temporary_db_session():
            notebook = db.create_notebook("Shared notebook")
            document = db.create_document(
                notebook_id=notebook["id"],
                original_filename="paper.pdf",
                display_title="Paper",
                storage_path="C:/tmp/paper.pdf",
                mime_type="application/pdf",
                file_size=100,
                page_count=3,
            )
            db.update_document_processing_status(
                document["id"],
                DocumentProcessingStatus.indexed,
                summary="Shared summary",
            )

            share_id = db.ensure_notebook_share_id(notebook["id"])
            self.assertIsNotNone(share_id)

            shared = db.get_shared_notebook_by_share_id(share_id)
            self.assertEqual(shared["title"], "Shared notebook")
            self.assertNotIn("id", shared)
            self.assertEqual(shared["documents"][0]["summary"], "Shared summary")

    def test_share_endpoints_return_public_safe_data(self):
        client = TestClient(app)

        with authenticated_api_user(), patch("app.api.notebooks.db.ensure_notebook_share_id", return_value="share-123"), patch(
            "app.api.notebooks.settings.frontend_base_url",
            "http://127.0.0.1:3000",
        ):
            create_response = client.post("/api/notebooks/notebook-1/share")

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["share_url"], "http://127.0.0.1:3000/share/share-123")

        with patch(
            "app.api.share.db.get_shared_notebook_by_share_id",
            return_value={
                "title": "Shared notebook",
                "source_count": 1,
                "indexed_document_count": 1,
                "created_at": "",
                "updated_at": "",
                "documents": [
                    {
                        "display_title": "Paper",
                        "page_count": 3,
                        "summary": "Summary",
                        "processing_status": "indexed",
                    }
                ],
            },
        ):
            read_response = client.get("/api/share/share-123")

        self.assertEqual(read_response.status_code, 200)
        self.assertNotIn("id", read_response.json())


if __name__ == "__main__":
    unittest.main()
