from fastapi import APIRouter, Depends, HTTPException, status

from app import db
from app.auth import RequestUserContext, require_request_user_context, verify_csrf_request
from app.config import settings
from app.models.schemas import NoteCreateRequest, NoteResponse

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    request: NoteCreateRequest,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Note content cannot be empty.")
    if len(content) > settings.max_note_length:
        raise HTTPException(status_code=400, detail="Note is too long.")

    try:
        note = db.create_note(
            request.notebook_id,
            content,
            source_message_id=request.source_message_id,
            user_id=user.user_id,
        )
    except ValueError as exc:
        detail = str(exc)
        if "Notebook not found" in detail:
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=400, detail=detail)

    return note


@router.get("/{notebook_id}", response_model=list[NoteResponse])
async def list_notes(
    notebook_id: str,
    user: RequestUserContext = Depends(require_request_user_context),
):
    if not db.notebook_exists(notebook_id, user_id=user.user_id):
        raise HTTPException(status_code=404, detail="Notebook not found.")
    return db.list_notes_for_notebook(notebook_id, user_id=user.user_id)


@router.delete("/{notebook_id}/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    notebook_id: str,
    note_id: str,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    try:
        deleted = db.delete_note(note_id, notebook_id, user_id=user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found.")
