import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.rag_utils import EMBEDDING_DIM, FAISSIndexManager, build_document_summary_fallback, keyword_search
from tests import authenticated_api_user


class NotebookIsolationTests(unittest.TestCase):
    def test_vector_search_refills_within_active_notebook(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = str(Path(temp_dir) / "index.bin")
            manager = FAISSIndexManager(index_path=index_path)

            embeddings = np.zeros((4, EMBEDDING_DIM), dtype="float32")
            embeddings[1, 0] = 0.01
            embeddings[1, 1] = 0.01
            embeddings[2, 0] = 0.02
            embeddings[2, 1] = 0.02
            embeddings[3, 0] = 9.0
            embeddings[3, 1] = 9.0
            manager.add_embeddings(
                embeddings,
                [
                    {
                        "notebook_id": "notebook-b",
                        "document_id": "doc-b1",
                        "file_id": "doc-b1",
                        "page": 1,
                        "text_snippet": "foreign chunk",
                    },
                    {
                        "notebook_id": "notebook-a",
                        "document_id": "doc-a1",
                        "file_id": "doc-a1",
                        "page": 1,
                        "text_snippet": "local chunk one",
                    },
                    {
                        "notebook_id": "notebook-a",
                        "document_id": "doc-a2",
                        "file_id": "doc-a2",
                        "page": 2,
                        "text_snippet": "local chunk two",
                    },
                    {
                        "notebook_id": "notebook-c",
                        "document_id": "doc-c1",
                        "file_id": "doc-c1",
                        "page": 1,
                        "text_snippet": "other chunk",
                    },
                ],
            )

            query_embedding = np.zeros((1, EMBEDDING_DIM), dtype="float32")
            with patch("app.services.rag_utils.generate_embeddings", return_value=query_embedding):
                results = manager.search("query", notebook_id="notebook-a", top_k=2)

            self.assertEqual(len(results), 2)
            self.assertTrue(all(result.file_id in {"doc-a1", "doc-a2"} for result in results))

    def test_keyword_search_only_uses_active_notebook_records(self):
        class FakeDb:
            def list_chunk_search_records(self, notebook_id, file_ids=None):
                self.called_with = (notebook_id, file_ids)
                if notebook_id != "notebook-a":
                    return []
                return [
                    {
                        "document_id": "doc-a1",
                        "page_number": 1,
                        "content": "photosynthesis happens in chloroplasts",
                    },
                    {
                        "document_id": "doc-a2",
                        "page_number": 2,
                        "content": "calvin cycle fixes carbon dioxide",
                    },
                ]

        fake_db = FakeDb()
        with patch("app.services.rag_utils.get_db", return_value=fake_db):
            results = keyword_search("chloroplasts", notebook_id="notebook-a", top_k=5)

        self.assertEqual(fake_db.called_with, ("notebook-a", None))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].file_id, "doc-a1")

    def test_summary_fallback_requires_and_respects_notebook_id(self):
        class FakeDb:
            def __init__(self):
                self.calls = []

            def get_document_records(self, file_ids, notebook_id=None):
                self.calls.append(("records", tuple(file_ids), notebook_id))
                return [{"summary": "Notebook A summary", "display_title": "Doc A"}]

            def list_documents_for_notebook(self, notebook_id):
                self.calls.append(("list", notebook_id))
                return [{"summary": "Notebook list summary", "display_title": "Doc"}]

        fake_db = FakeDb()
        with patch("app.services.rag_utils.get_db", return_value=fake_db):
            summary = build_document_summary_fallback(["doc-a1"], notebook_id="notebook-a")

        self.assertEqual(summary, "Notebook A summary")
        self.assertEqual(fake_db.calls, [("records", ("doc-a1",), "notebook-a")])

        with self.assertRaises(ValueError):
            build_document_summary_fallback(["doc-a1"], notebook_id=None)

    def test_query_endpoint_rejects_notebook_document_mismatch(self):
        client = TestClient(app)

        with authenticated_api_user(), patch("app.api.query.db.notebook_exists", return_value=True), patch(
            "app.api.query.db.validate_notebook_documents", return_value=False
        ):
            response = client.post(
                "/api/query",
                json={
                    "notebook_id": "notebook-a",
                    "file_ids": ["doc-from-b"],
                    "question": "summarize",
                    "top_k": 3,
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("do not belong to the notebook", response.json()["detail"])

    def test_history_endpoint_rejects_unknown_notebook(self):
        client = TestClient(app)

        with authenticated_api_user(), patch("app.api.query.db.notebook_exists", return_value=False):
            response = client.get("/api/query/history/missing-notebook")

        self.assertEqual(response.status_code, 404)

    def test_query_returns_status_message_when_notebook_has_no_indexed_documents(self):
        client = TestClient(app)

        with authenticated_api_user(), patch("app.api.query.db.notebook_exists", return_value=True), patch(
            "app.api.query.db.validate_notebook_documents", return_value=True
        ), patch(
            "app.api.query.db.list_documents_for_notebook",
            return_value=[
                {
                    "id": "doc-a1",
                    "display_title": "Pending doc",
                    "original_filename": "pending.pdf",
                    "processing_status": "processing",
                    "processing_error": None,
                }
            ],
        ), patch(
            "app.api.query.db.get_conversation",
            return_value={"messages": [], "summary": ""},
        ), patch(
            "app.api.query.classify_intent", return_value="vague_query"
        ), patch(
            "app.api.query.db.save_conversation"
        ) as save_conversation:
            response = client.post(
                "/api/query",
                json={
                    "notebook_id": "notebook-a",
                    "file_ids": [],
                    "question": "what is this?",
                    "top_k": 3,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("still being processed", response.text)
        save_conversation.assert_called_once()


if __name__ == "__main__":
    unittest.main()
