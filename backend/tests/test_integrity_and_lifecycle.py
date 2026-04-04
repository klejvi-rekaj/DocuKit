import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, func, inspect, select
from sqlalchemy.orm import sessionmaker

from app import db
from app.database import Base
from app.models.db_models import ChatMessage, Conversation, Document, DocumentChunk, IndexingJob, Notebook
from app.services.rag_utils import process_document_background


@contextmanager
def temporary_db_session():
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}", future=True, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
        Base.metadata.create_all(bind=engine)

        with patch("app.db.SessionLocal", TestingSessionLocal):
            yield TestingSessionLocal

        engine.dispose()


class IntegrityAndLifecycleTests(unittest.TestCase):
    def test_uploaded_processing_indexed_lifecycle(self):
        fake_db = unittest.mock.Mock()
        fake_db.get_notebook_lifecycle_status.side_effect = ["active", "active", "active"]

        with patch("app.services.rag_utils.get_db", return_value=fake_db), patch(
            "app.services.rag_utils.extract_text_from_pdf_bytes",
            return_value={"status": "success", "content": [{"page_number": 1, "text": "hello world"}]},
        ), patch(
            "app.services.rag_utils.process_and_index_document", return_value=1
        ), patch(
            "app.services.rag_utils.fast_extract_metadata", return_value={"title": "Processed title"}
        ), patch(
            "app.services.rag_utils.get_ai_utils"
        ) as get_ai_utils:
            get_ai_utils.return_value.generate_document_summary.return_value = "summary"

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
                handle.write(b"%PDF-1.4")
                pdf_path = handle.name

            try:
                process_document_background("nb-1", "doc-1", pdf_path, "paper.pdf", "job-1")
            finally:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

        fake_db.update_indexing_job.assert_any_call("job-1", status=unittest.mock.ANY, started=True)
        fake_db.update_document_processing_status.assert_any_call("doc-1", unittest.mock.ANY)
        fake_db.save_document_summary.assert_called_once()
        fake_db.update_indexing_job.assert_any_call("job-1", status=unittest.mock.ANY, finished=True)

    def test_uploaded_processing_failed_lifecycle(self):
        fake_db = unittest.mock.Mock()
        fake_db.get_notebook_lifecycle_status.return_value = "active"

        with patch("app.services.rag_utils.get_db", return_value=fake_db), patch(
            "app.services.rag_utils.extract_text_from_pdf_bytes",
            return_value={"status": "error", "error": "broken pdf"},
        ):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
                handle.write(b"%PDF-1.4")
                pdf_path = handle.name

            try:
                process_document_background("nb-2", "doc-2", pdf_path, "broken.pdf", "job-2")
            finally:
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

        fake_db.update_document_processing_status.assert_any_call(
            "doc-2",
            unittest.mock.ANY,
            processing_error="broken pdf",
        )
        fake_db.update_indexing_job.assert_any_call(
            "job-2",
            status=unittest.mock.ANY,
            error_message="broken pdf",
            finished=True,
        )

    def test_notebook_cascade_deletion_removes_dependent_records(self):
        with temporary_db_session() as TestingSessionLocal:
            notebook = db.create_notebook("Cascade test")
            document = db.create_document(
                notebook_id=notebook["id"],
                original_filename="paper.pdf",
                display_title="Paper",
                storage_path="C:/tmp/paper.pdf",
                mime_type="application/pdf",
                file_size=123,
                page_count=2,
            )
            db.replace_document_chunks(
                document["id"],
                notebook["id"],
                [
                    {
                        "chunk_index": 0,
                        "content": "chunk one",
                        "page_number": 1,
                        "token_count": 2,
                    }
                ],
            )
            db.create_indexing_job(notebook["id"], document["id"])
            db.save_conversation(
                notebook["id"],
                [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "world"},
                ],
                "summary",
            )
            prepared = db.prepare_notebook_deletion(notebook["id"])
            self.assertTrue(prepared["ready_for_cleanup"])
            finalized = db.finalize_notebook_deletion(notebook["id"])
            self.assertTrue(finalized["deleted"])

            with TestingSessionLocal() as session:
                self.assertEqual(session.scalar(select(func.count(Notebook.id))), 0)
                self.assertEqual(session.scalar(select(func.count(Document.id))), 0)
                self.assertEqual(session.scalar(select(func.count(DocumentChunk.id))), 0)
                self.assertEqual(session.scalar(select(func.count(Conversation.id))), 0)
                self.assertEqual(session.scalar(select(func.count(ChatMessage.id))), 0)
                self.assertEqual(session.scalar(select(func.count(IndexingJob.id))), 0)

    def test_migrations_create_required_tables_and_constraints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "migration.db"
            db_url = f"sqlite:///{db_path}"
            alembic_cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))

            from app.config import settings

            with patch.object(settings, "database_url", db_url):
                command.upgrade(alembic_cfg, "head")

            engine = create_engine(db_url, future=True)
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            required_tables = {
                "users",
                "user_sessions",
                "notebooks",
                "documents",
                "document_chunks",
                "conversations",
                "chat_messages",
                "indexing_jobs",
                "alembic_version",
            }
            self.assertTrue(required_tables.issubset(tables))

            document_fks = {fk["referred_table"] for fk in inspector.get_foreign_keys("documents")}
            chunk_fks = {fk["referred_table"] for fk in inspector.get_foreign_keys("document_chunks")}
            message_fks = {fk["referred_table"] for fk in inspector.get_foreign_keys("chat_messages")}
            self.assertIn("notebooks", document_fks)
            self.assertTrue({"documents", "notebooks"}.issubset(chunk_fks))
            self.assertTrue({"conversations", "notebooks"}.issubset(message_fks))
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
