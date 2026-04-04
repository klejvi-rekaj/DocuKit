import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import RequestUserContext, require_request_user_context, verify_csrf_request
from app import db
from app.config import settings
from app.models.schemas import NotebookCreateRequest, NotebookResponse, NotebookShareResponse, NotebookUpdateRequest
from app.services.notebook_cleanup import delete_notebook_with_cleanup

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])
PIXEL_ICON_KEYS = {
    "atom",
    "balance_scale",
    "address_book",
    "brain",
    "calculator",
    "chemical",
    "connect",
    "computer",
    "dna",
    "fashion",
    "finance",
    "function",
    "hello_kitty",
    "info",
    "law",
    "loss",
    "mail",
    "money",
    "musical_note",
    "pixel_cat",
    "pixel_heart",
    "pixels",
    "pride",
    "profit",
    "rain",
    "react",
    "robot",
    "robotic",
    "robots",
    "spring",
    "stock",
    "team",
    "team_alt",
    "teddy_bear",
    "tooth",
    # Legacy keys kept valid for older notebooks.
    "folder",
    "book",
    "robot",
    "leaf",
    "coin",
    "badge",
    "gavel",
    "briefcase",
    "pencil",
    "cell",
    "chart",
    "chip",
}


@router.get("", response_model=list[NotebookResponse])
async def list_notebooks(user: RequestUserContext = Depends(require_request_user_context)):
    return db.list_notebooks(user_id=user.user_id)


@router.post("", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    request: NotebookCreateRequest,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    title = request.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Notebook title cannot be empty.")
    if request.icon_key not in PIXEL_ICON_KEYS:
        raise HTTPException(status_code=400, detail="Invalid icon_key.")
    return db.create_notebook(title, user_id=user.user_id, icon_key=request.icon_key)


@router.get("/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(
    notebook_id: str,
    user: RequestUserContext = Depends(require_request_user_context),
):
    notebook = db.get_notebook(notebook_id, user_id=user.user_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found.")
    return notebook


@router.patch("/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    request: NotebookUpdateRequest,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    title = request.title.strip() if request.title is not None else None
    if title is not None and not title:
        raise HTTPException(status_code=400, detail="Notebook title cannot be empty.")
    if title is None and request.icon_key is None:
        raise HTTPException(status_code=400, detail="Provide a title and/or icon_key to update.")
    if request.icon_key is not None and request.icon_key not in PIXEL_ICON_KEYS:
        raise HTTPException(status_code=400, detail="Invalid icon_key.")
    notebook = db.update_notebook(notebook_id, title=title, icon_key=request.icon_key, user_id=user.user_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found.")
    return notebook


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(
    notebook_id: str,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    result = delete_notebook_with_cleanup(notebook_id, user_id=user.user_id)
    if result.get("not_found"):
        raise HTTPException(status_code=404, detail="Notebook not found.")
    if not result.get("deleted"):
        raise HTTPException(status_code=500, detail=result.get("detail") or "Notebook cleanup failed.")
    return None


@router.post("/{notebook_id}/share", response_model=NotebookShareResponse)
async def share_notebook(
    notebook_id: str,
    user: RequestUserContext = Depends(require_request_user_context),
    _: None = Depends(verify_csrf_request),
):
    share_id = db.ensure_notebook_share_id(notebook_id, user_id=user.user_id)
    if not share_id:
        raise HTTPException(status_code=404, detail="Notebook not found.")

    base_url = settings.frontend_base_url.rstrip("/")
    return {"share_url": f"{base_url}/share/{share_id}"}
