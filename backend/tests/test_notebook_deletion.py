import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.notebook_cleanup import delete_notebook_with_cleanup
from app.services.rag_utils import process_document_background
from tests import authenticated_api_user


class NotebookDeletionTests(unittest.TestCase):
    def test_delete_empty_notebook(self):
        file_remover = Mock()
        index_rebuilder = Mock()

        with patch(
            "app.services.notebook_cleanup.db.prepare_notebook_deletion",
            return_value={"ready_for_cleanup": True, "storage_paths": [], "notebook_id": "nb-1"},
        ), patch(
            "app.services.notebook_cleanup.db.finalize_notebook_deletion",
            return_value={"deleted": True},
        ):
            result = delete_notebook_with_cleanup(
                "nb-1",
                file_remover=file_remover,
                index_rebuilder=index_rebuilder,
            )

        self.assertTrue(result["deleted"])
        file_remover.assert_called_once_with([])
        index_rebuilder.assert_called_once()

    def test_delete_notebook_with_indexed_documents(self):
        file_remover = Mock()
        index_rebuilder = Mock()

        with patch(
            "app.services.notebook_cleanup.db.prepare_notebook_deletion",
            return_value={
                "ready_for_cleanup": True,
                "storage_paths": ["C:/tmp/doc-a.pdf", "C:/tmp/doc-b.pdf"],
                "notebook_id": "nb-2",
            },
        ), patch(
            "app.services.notebook_cleanup.db.finalize_notebook_deletion",
            return_value={"deleted": True},
        ):
            result = delete_notebook_with_cleanup(
                "nb-2",
                file_remover=file_remover,
                index_rebuilder=index_rebuilder,
            )

        self.assertTrue(result["deleted"])
        file_remover.assert_called_once_with(["C:/tmp/doc-a.pdf", "C:/tmp/doc-b.pdf"])
        index_rebuilder.assert_called_once()

    def test_deleting_notebook_during_processing_skips_background_work(self):
        fake_db = Mock()
        fake_db.get_notebook_lifecycle_status.side_effect = ["deleting"]

        with patch("app.services.rag_utils.get_db", return_value=fake_db):
            process_document_background("nb-3", "doc-3", "C:/tmp/missing.pdf", "processing.pdf", "job-3")

        fake_db.update_indexing_job.assert_not_called()
        fake_db.update_document_processing_status.assert_not_called()

    def test_retry_after_partial_cleanup_failure(self):
        file_remover = Mock(side_effect=[OSError("disk locked"), None])
        index_rebuilder = Mock()

        with patch(
            "app.services.notebook_cleanup.db.prepare_notebook_deletion",
            return_value={"ready_for_cleanup": True, "storage_paths": ["C:/tmp/doc-a.pdf"], "notebook_id": "nb-4"},
        ), patch(
            "app.services.notebook_cleanup.db.finalize_notebook_deletion",
            return_value={"deleted": True},
        ) as finalize_mock, patch(
            "app.services.notebook_cleanup.db.record_notebook_delete_failure",
            return_value=True,
        ) as record_failure_mock:
            first = delete_notebook_with_cleanup("nb-4", file_remover=file_remover, index_rebuilder=index_rebuilder)
            second = delete_notebook_with_cleanup("nb-4", file_remover=file_remover, index_rebuilder=index_rebuilder)

        self.assertFalse(first["deleted"])
        self.assertTrue(first["cleanup_failed"])
        self.assertTrue(second["deleted"])
        record_failure_mock.assert_called_once()
        finalize_mock.assert_called_once()
        self.assertEqual(file_remover.call_count, 2)
        index_rebuilder.assert_called_once()

    def test_delete_endpoint_returns_500_when_cleanup_fails(self):
        client = TestClient(app)

        with authenticated_api_user(), patch(
            "app.api.notebooks.delete_notebook_with_cleanup",
            return_value={"deleted": False, "not_found": False, "detail": "disk locked"},
        ):
            response = client.delete("/api/notebooks/nb-5")

        self.assertEqual(response.status_code, 500)
        self.assertIn("disk locked", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
