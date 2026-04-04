import json
import logging
import os
import re
import time
from collections import Counter
from math import log
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from google import generativeai as genai
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.models.db_models import DocumentProcessingStatus, EmbeddingStatus, IndexingJobStatus
from app.models.schemas import SourceChunk
from app.services.pdf_utils import extract_text_from_pdf_bytes, fast_extract_metadata


def get_ai_utils():
    from app.services import ai_utils

    return ai_utils


def get_db():
    from app import db

    return db


logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "models/text-embedding-004"
LOCAL_FALLBACK_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 768 if settings.gemini_api_key else 384

_embedding_model = None


class FAISSIndexManager:
    def __init__(self, index_path: str = settings.faiss_index_path):
        self.index_path = index_path
        self.metadata_path = self.index_path.replace(".bin", "_meta.json")
        self.index = None
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self._load_index()

    def _fresh_index(self):
        return faiss.IndexFlatL2(EMBEDDING_DIM)

    def _load_index(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        try:
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
                if self.index.d != EMBEDDING_DIM:
                    logger.warning("Index dimension mismatch. Resetting FAISS index.")
                    self.index = self._fresh_index()
                    self.metadata = {}
            else:
                self.index = self._fresh_index()

            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                self.metadata = {int(k): v for k, v in loaded.items()}
            else:
                self.metadata = {}
        except Exception as exc:
            logger.error(f"Error loading FAISS index: {exc}")
            self.index = self._fresh_index()
            self.metadata = {}

    def save_index(self):
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.metadata_path, "w", encoding="utf-8") as handle:
                json.dump(self.metadata, handle)
        except Exception as exc:
            logger.error(f"Error saving FAISS index: {exc}")

    def add_embeddings(self, embeddings: np.ndarray, metadata_list: List[Dict[str, Any]]):
        if embeddings.shape[0] == 0:
            return
        start_id = self.index.ntotal
        self.index.add(embeddings)
        for offset, meta in enumerate(metadata_list):
            self.metadata[start_id + offset] = meta
        self.save_index()

    def rebuild(self, chunk_rows: List[Dict[str, Any]]):
        self.index = self._fresh_index()
        self.metadata = {}
        if not chunk_rows:
            self.save_index()
            return

        vectors = []
        for idx, row in enumerate(chunk_rows):
            vector = row.get("embedding_vector")
            if not vector:
                continue
            vectors.append(vector)
            self.metadata[len(vectors) - 1] = {
                "chunk_id": row["id"],
                "document_id": row["document_id"],
                "notebook_id": row["notebook_id"],
                "file_id": row["document_id"],
                "page": row.get("page_number") or 0,
                "text_snippet": row["content"],
            }
        if vectors:
            self.index.add(np.array(vectors, dtype="float32"))
        self.save_index()

    def search(
        self,
        query: str,
        *,
        notebook_id: str,
        file_ids: Optional[List[str]] = None,
        top_k: int = 10,
    ) -> List[SourceChunk]:
        if not notebook_id:
            raise ValueError("notebook_id is required for vector search.")
        if self.index is None or self.index.ntotal == 0:
            return []

        try:
            query_embedding = generate_embeddings([query])
            if query_embedding.shape[0] == 0:
                return []

            search_k = min(self.index.ntotal, max(top_k * 8, top_k))
            results: List[SourceChunk] = []
            seen: set[tuple[str, int, str]] = set()

            while True:
                distances, indices = self.index.search(query_embedding, search_k)

                for dist, idx in zip(distances[0], indices[0]):
                    if idx == -1 or idx not in self.metadata:
                        continue
                    meta = self.metadata[idx]
                    if meta.get("notebook_id") != notebook_id:
                        continue
                    if file_ids and meta.get("file_id") not in file_ids:
                        continue
                    key = (meta["file_id"], meta.get("page", 0), meta["text_snippet"])
                    if key in seen:
                        continue
                    seen.add(key)
                    score = 1.0 / (1.0 + float(dist))
                    results.append(
                        SourceChunk(
                            file_id=meta["file_id"],
                            page=meta.get("page", 0),
                            text_snippet=meta["text_snippet"],
                            score=score,
                        )
                    )

                if len(results) >= top_k or search_k >= self.index.ntotal:
                    break
                search_k = min(self.index.ntotal, max(search_k * 2, search_k + top_k))

            return results[:top_k]
        except Exception as exc:
            logger.error(f"Vector search failed: {exc}")
            return []


vector_store = FAISSIndexManager()


def rebuild_vector_store_from_db() -> None:
    db = get_db()
    vector_store.rebuild(db.list_chunks_with_embeddings())


def split_text_into_chunks(
    content: List[Dict[str, Any]],
    chunk_size: int = 700,
    overlap: int = 100,
) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    chunk_index = 0
    for page_data in content:
        page_num = page_data["page_number"]
        text = (page_data.get("text") or "").strip()
        if not text:
            continue

        cursor = 0
        text_length = len(text)
        while cursor < text_length:
            end = min(cursor + chunk_size, text_length)
            chunk_text = text[cursor:end]
            if end < text_length:
                last_space = chunk_text.rfind(" ")
                if last_space != -1 and last_space > chunk_size * 0.75:
                    end = cursor + last_space
                    chunk_text = text[cursor:end]

            cleaned = chunk_text.strip()
            if cleaned:
                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "content": cleaned,
                        "page_number": page_num,
                        "token_count": max(1, len(cleaned.split())),
                    }
                )
                chunk_index += 1

            if end >= text_length:
                break
            cursor = max(end - overlap, cursor + 1)
    return chunks


def generate_embeddings(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.array([], dtype="float32")

    if settings.gemini_api_key:
        try:
            genai.configure(api_key=settings.gemini_api_key)
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=EMBEDDING_MODEL_NAME,
                    content=text,
                    task_type="retrieval_document",
                )
                embeddings.append(result["embedding"])
            return np.array(embeddings, dtype="float32")
        except Exception as exc:
            logger.error(f"Gemini embedding failed, falling back locally: {exc}")

    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(LOCAL_FALLBACK_MODEL)
    return _embedding_model.encode(texts).astype("float32")


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", (text or "").lower())


def keyword_search(
    query: str,
    *,
    notebook_id: str,
    file_ids: Optional[List[str]] = None,
    top_k: int = 10,
) -> List[SourceChunk]:
    if not notebook_id:
        raise ValueError("notebook_id is required for keyword search.")
    query_terms = _tokenize(query)
    if not query_terms:
        return []

    db = get_db()
    candidate_meta = [
        {
            "file_id": row["document_id"],
            "page": row.get("page_number") or 0,
            "text_snippet": row["content"],
        }
        for row in db.list_chunk_search_records(notebook_id, file_ids=file_ids)
    ]
    if not candidate_meta:
        return []

    doc_tokens: List[List[str]] = [_tokenize(meta.get("text_snippet", "")) for meta in candidate_meta]
    doc_freq = Counter()
    for tokens in doc_tokens:
        for token in set(tokens):
            doc_freq[token] += 1

    avg_len = sum(len(tokens) for tokens in doc_tokens) / max(len(doc_tokens), 1)
    scores = []
    for meta, tokens in zip(candidate_meta, doc_tokens):
        if not tokens:
            continue
        token_counts = Counter(tokens)
        score = 0.0
        for term in query_terms:
            tf = token_counts.get(term, 0)
            if tf == 0:
                continue
            df = doc_freq.get(term, 0)
            idf = log(1 + (len(doc_tokens) - df + 0.5) / (df + 0.5))
            numerator = tf * 2.2
            denominator = tf + 1.2 * (1 - 0.75 + 0.75 * (len(tokens) / max(avg_len, 1)))
            score += idf * (numerator / max(denominator, 1e-6))

        if score > 0:
            scores.append(
                SourceChunk(
                    file_id=meta["file_id"],
                    page=meta.get("page", 0),
                    text_snippet=meta["text_snippet"],
                    score=float(score),
                )
            )

    return sorted(scores, key=lambda chunk: chunk.score, reverse=True)[:top_k]


def hybrid_search(
    query: str,
    *,
    notebook_id: str,
    file_ids: Optional[List[str]] = None,
    top_k: int = 15,
) -> List[SourceChunk]:
    if not notebook_id:
        raise ValueError("notebook_id is required for hybrid search.")
    vector_results = vector_store.search(query, notebook_id=notebook_id, file_ids=file_ids, top_k=top_k)
    keyword_results = keyword_search(query, notebook_id=notebook_id, file_ids=file_ids, top_k=top_k)

    merged: Dict[tuple, SourceChunk] = {}
    for weight, results in ((0.65, vector_results), (0.35, keyword_results)):
        for chunk in results:
            key = (chunk.file_id, chunk.page, chunk.text_snippet)
            if key not in merged:
                merged[key] = SourceChunk(**chunk.model_dump())
                merged[key].score = 0.0
            merged[key].score += chunk.score * weight

    return sorted(merged.values(), key=lambda chunk: chunk.score, reverse=True)[: max(top_k, 1) * 2]


def rerank_chunks(query: str, chunks: List[SourceChunk], top_k: int = 10) -> List[SourceChunk]:
    if not chunks:
        return []
    query_terms = set(_tokenize(query))
    reranked: List[SourceChunk] = []
    for chunk in chunks:
        updated = SourceChunk(**chunk.model_dump())
        snippet_terms = set(_tokenize(chunk.text_snippet))
        overlap = len(query_terms.intersection(snippet_terms))
        density = overlap / max(len(query_terms), 1)
        updated.score = float(chunk.score + density * 0.35 + min(overlap, 6) * 0.03)
        reranked.append(updated)
    return sorted(reranked, key=lambda chunk: chunk.score, reverse=True)[:top_k]


def build_document_summary_fallback(file_ids: List[str], notebook_id: Optional[str] = None) -> str:
    if not notebook_id:
        raise ValueError("notebook_id is required for summary fallback.")
    db = get_db()
    records = db.get_document_records(file_ids, notebook_id=notebook_id) if file_ids else db.list_documents_for_notebook(notebook_id or "")
    summaries = [record["summary"] for record in records if record.get("summary")]
    if summaries:
        return " ".join(summaries[:3]).strip()
    return ""


def get_document_titles(file_ids: List[str], notebook_id: Optional[str] = None) -> List[str]:
    if not notebook_id:
        raise ValueError("notebook_id is required for document titles.")
    db = get_db()
    records = db.get_document_records(file_ids, notebook_id=notebook_id) if file_ids else db.list_documents_for_notebook(notebook_id or "")
    titles = [record["display_title"] for record in records if record.get("display_title")]
    return titles


def is_low_confidence(chunks: List[SourceChunk], threshold: float = 0.2) -> bool:
    if not chunks:
        return True
    top_score = chunks[0].score
    if top_score < threshold:
        return True
    strong_matches = [chunk for chunk in chunks if chunk.score >= threshold]
    return len(strong_matches) < 2


def process_and_index_document(document_id: str, notebook_id: str, content: List[Dict[str, Any]]) -> int:
    db = get_db()
    chunks = split_text_into_chunks(content)
    if not chunks:
        db.replace_document_chunks(document_id, notebook_id, [])
        return 0

    texts = [chunk["content"] for chunk in chunks]
    processed_chunks: List[Dict[str, Any]] = []

    processed_count = 0
    batch_size = 20
    for index in range(0, len(texts), batch_size):
        batch_chunks = chunks[index:index + batch_size]
        batch_texts = texts[index:index + batch_size]
        try:
            embeddings = generate_embeddings(batch_texts)
            if embeddings.shape[0] > 0:
                for offset, chunk in enumerate(batch_chunks):
                    processed_chunks.append(
                        {
                            **chunk,
                            "embedding_status": EmbeddingStatus.embedded,
                            "embedding_model": EMBEDDING_MODEL_NAME if settings.gemini_api_key else LOCAL_FALLBACK_MODEL,
                            "embedding_vector": embeddings[offset].tolist(),
                        }
                    )
                processed_count += len(batch_texts)
            time.sleep(0.2)
        except Exception as exc:
            logger.error(f"Batch indexing failed for {document_id}: {exc}")
            for chunk in batch_chunks:
                processed_chunks.append(
                    {
                        **chunk,
                        "embedding_status": EmbeddingStatus.failed,
                        "embedding_model": EMBEDDING_MODEL_NAME if settings.gemini_api_key else LOCAL_FALLBACK_MODEL,
                        "embedding_vector": None,
                    }
                )

    db.replace_document_chunks(document_id, notebook_id, processed_chunks)
    rebuild_vector_store_from_db()
    return processed_count


def process_document_background(
    notebook_id: str,
    document_id: str,
    pdf_path: str,
    original_filename: str = "",
    job_id: Optional[str] = None,
):
    db = get_db()
    if db.get_notebook_lifecycle_status(notebook_id) != "active":
        logger.info(f"Skipping background processing for {document_id}; notebook {notebook_id} is being deleted.")
        return
    if job_id:
        db.update_indexing_job(job_id, status=IndexingJobStatus.processing, started=True)
    db.update_document_processing_status(document_id, DocumentProcessingStatus.processing)

    try:
        if not os.path.exists(pdf_path):
            logger.error(f"PDF path missing for background processing: {pdf_path}")
            raise FileNotFoundError(pdf_path)

        with open(pdf_path, "rb") as handle:
            pdf_bytes = handle.read()

        extraction = extract_text_from_pdf_bytes(pdf_bytes)
        if extraction["status"] != "success":
            raise RuntimeError(extraction.get("error") or "Extraction failed")

        if db.get_notebook_lifecycle_status(notebook_id) != "active":
            logger.info(f"Aborting background processing for {document_id}; notebook {notebook_id} moved to deletion.")
            return

        process_and_index_document(document_id, notebook_id, extraction["content"])

        title = original_filename
        try:
            metadata = fast_extract_metadata(pdf_bytes)
            extracted_title = (metadata or {}).get("title") if isinstance(metadata, dict) else None
            if extracted_title:
                title = extracted_title
        except Exception as exc:
            logger.warning(f"Metadata extraction failed for {document_id}: {exc}")

        full_text = "\n".join(page.get("text", "") for page in extraction["content"])
        ai_utils = get_ai_utils()
        summary = ai_utils.generate_document_summary(full_text, title=title)
        if db.get_notebook_lifecycle_status(notebook_id) != "active":
            logger.info(f"Discarding summary save for {document_id}; notebook {notebook_id} is deleting.")
            return
        db.save_document_summary(
            document_id,
            summary,
            title=title or original_filename,
            metadata={
                "pages": len(extraction["content"]),
                "filename": original_filename,
            },
        )
        if job_id:
            db.update_indexing_job(job_id, status=IndexingJobStatus.indexed, finished=True)
        logger.info(f"Finished background processing for {document_id}")
    except Exception as exc:
        db.update_document_processing_status(
            document_id,
            DocumentProcessingStatus.failed,
            processing_error=str(exc),
        )
        if job_id:
            db.update_indexing_job(job_id, status=IndexingJobStatus.failed, error_message=str(exc), finished=True)
        logger.error(f"Background processing error for {document_id}: {exc}", exc_info=True)
