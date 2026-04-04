from fastapi import APIRouter, HTTPException

from app import db
from app.models.schemas import SharedNotebookResponse

router = APIRouter(prefix="/api/share", tags=["share"])


@router.get("/{share_id}", response_model=SharedNotebookResponse)
async def get_shared_notebook(share_id: str):
    notebook = db.get_shared_notebook_by_share_id(share_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Shared notebook not found.")
    return notebook
