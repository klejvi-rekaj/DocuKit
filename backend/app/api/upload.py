import logging
import os
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request, status
from app.auth import RequestUserContext, require_request_user_context, verify_csrf_request
from app import db
from app.models.db_models import DocumentProcessingStatus
from app.models.schemas import UploadResponse
from app.services.pdf_utils import fast_extract_metadata
from app.services.rag_utils import process_document_background
from app.config import settings
from app.services.rate_limit import rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Ensure upload directory exists
os.makedirs(settings.pdf_upload_dir, exist_ok=True)

@router.post("", response_model=UploadResponse)
async def upload_pdf(
    request: Request,
    notebook_id: str = Form(...),
    file: UploadFile = File(...),
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    if not db.notebook_exists(notebook_id, user_id=user.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found.")

    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.hit(
        f"upload:{user.user_id}:{client_ip}",
        settings.upload_rate_limit_attempts,
        settings.upload_rate_limit_window_seconds,
    )

    original_filename = os.path.basename((file.filename or "upload.pdf").replace("\x00", "")).strip()[:255]
    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed.",
        )

    if file.content_type not in {"application/pdf", "application/x-pdf"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are allowed."
        )
        
    # Read file into memory
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read file.")
        
    # Check payload size
    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large.")

    if not file_bytes.lstrip().startswith(b"%PDF-"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid PDF.")

    page_count = 0
    title = original_filename or "Uploaded document"
    try:
        extracted_meta = fast_extract_metadata(file_bytes)
        if isinstance(extracted_meta, dict):
            title = extracted_meta.get("title") or title
            page_count = int(extracted_meta.get("pages") or 0)
    except Exception as e:
        logger.warning(f"Metadata extraction failed for {original_filename}: {e}")

    title = str(title).strip()[: settings.max_notebook_title_length] or "Uploaded document"

    document = db.create_document(
        notebook_id=notebook_id,
        original_filename=original_filename or "upload.pdf",
        display_title=title,
        storage_path=os.path.join(settings.pdf_upload_dir, "__pending__.pdf"),
        mime_type=file.content_type or "application/pdf",
        file_size=len(file_bytes),
        page_count=page_count,
    )
    file_id = document["id"]
    save_path = os.path.join(settings.pdf_upload_dir, f"{file_id}.pdf")
    try:
        with open(save_path, "wb") as f:
            f.write(file_bytes)
    except Exception as e:
        db.delete_document(file_id)
        logger.error(f"Critical Upload Error for {original_filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed. Please try again."
        )
    db.update_document_processing_status(
        file_id,
        status=DocumentProcessingStatus.uploaded,
        page_count=page_count,
        display_title=title,
    )
    db.update_document_storage_path(file_id, save_path)

    # 2. Offload FULL extraction and indexing to an independent task
    import asyncio
    indexing_job = db.create_indexing_job(notebook_id, file_id)
    asyncio.create_task(
        asyncio.to_thread(
            process_document_background,
            notebook_id,
            file_id,
            save_path,
            original_filename or title,
            indexing_job["id"],
        )
    )
    logger.info(f"Background processing task scheduled for file {file_id}")

    document_record = db.get_document(file_id)
    return UploadResponse(
        status="ok",
        file_id=file_id,
        notebook_id=notebook_id,
        pages=page_count,
        title=title,
        processing_status=document_record["processing_status"] if document_record else DocumentProcessingStatus.uploaded.value,
        document=document_record,
        indexing_job=indexing_job,
    )
