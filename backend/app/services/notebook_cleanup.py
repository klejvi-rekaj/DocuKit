import logging
from typing import Any, Callable, Dict, Optional

from app import db
from app.services.rag_utils import rebuild_vector_store_from_db

logger = logging.getLogger(__name__)


def delete_notebook_with_cleanup(
    notebook_id: str,
    *,
    user_id: Optional[str] = None,
    file_remover: Optional[Callable[[list[str]], None]] = None,
    index_rebuilder: Optional[Callable[[], None]] = None,
) -> Dict[str, Any]:
    file_remover = file_remover or db.delete_files_strict
    index_rebuilder = index_rebuilder or rebuild_vector_store_from_db

    prepared = db.prepare_notebook_deletion(notebook_id, user_id=user_id)
    if not prepared.get("ready_for_cleanup"):
        return {"deleted": False, "not_found": True}

    try:
        file_remover(prepared.get("storage_paths", []))
    except Exception as exc:
        logger.error("Notebook file cleanup failed for %s: %s", notebook_id, exc, exc_info=True)
        db.record_notebook_delete_failure(notebook_id, str(exc), user_id=user_id)
        return {"deleted": False, "not_found": False, "cleanup_failed": True, "detail": str(exc)}

    try:
        finalized = db.finalize_notebook_deletion(notebook_id, user_id=user_id)
    except Exception as exc:
        logger.error("Notebook DB deletion failed for %s: %s", notebook_id, exc, exc_info=True)
        db.record_notebook_delete_failure(notebook_id, str(exc), user_id=user_id)
        return {"deleted": False, "not_found": False, "cleanup_failed": True, "detail": str(exc)}

    if not finalized.get("deleted"):
        return {"deleted": False, "not_found": True}

    try:
        index_rebuilder()
    except Exception as exc:
        # The deleted notebook is already hidden and removed from the DB, so stale vectors are no
        # longer addressable through notebook-scoped retrieval. We still log aggressively here.
        logger.error("Vector store rebuild failed after deleting notebook %s: %s", notebook_id, exc, exc_info=True)
        return {"deleted": True, "vector_cleanup_failed": True, "detail": str(exc)}

    return {"deleted": True}
