from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated


ShortId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
NotebookTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
IconKey = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$")]
EmailValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=254)]
PasswordValue = Annotated[str, StringConstraints(min_length=8, max_length=128)]
CurrentPasswordValue = Annotated[str, StringConstraints(min_length=1, max_length=128)]
DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
ThemePreferenceValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=4, max_length=6, pattern=r"^(light|dark|system)$")]
QuestionValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
NoteContentValue = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class AuthUserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    theme_preference: Optional[str] = None
    has_password: bool = False


class AuthSessionResponse(BaseModel):
    authenticated: bool
    user: Optional[AuthUserResponse] = None


class SignUpRequest(BaseModel):
    name: DisplayName
    email: EmailValue
    password: PasswordValue


class SignInRequest(BaseModel):
    email: EmailValue
    password: PasswordValue


class ProfileUpdateRequest(BaseModel):
    display_name: DisplayName
    email: EmailValue


class PasswordChangeRequest(BaseModel):
    current_password: CurrentPasswordValue
    new_password: PasswordValue
    confirm_password: PasswordValue


class ThemePreferenceUpdateRequest(BaseModel):
    theme_preference: ThemePreferenceValue

class IndexingJobResponse(BaseModel):
    id: str
    notebook_id: str
    document_id: str
    status: str
    error_message: Optional[str] = None
    queued_at: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class DocumentResponse(BaseModel):
    id: str
    notebook_id: str
    original_filename: str
    display_title: str
    processing_status: str
    page_count: int = 0
    summary: str = ""
    processing_error: Optional[str] = None
    latest_indexing_job: Optional[IndexingJobResponse] = None


class UploadResponse(BaseModel):
    status: str
    file_id: str
    notebook_id: str
    pages: Optional[int] = 0
    text_summary: Optional[str] = None
    title: Optional[str] = None
    processing_status: str
    document: DocumentResponse
    indexing_job: Optional[IndexingJobResponse] = None

class Chunk(BaseModel):
    file_id: str
    page: int
    text_snippet: str
    
class SourceChunk(BaseModel):
    file_id: str
    page: int
    text_snippet: str
    score: float

class QueryRequest(BaseModel):
    file_ids: List[ShortId] = Field(default_factory=list, max_length=50)
    question: QuestionValue
    top_k: int = Field(default=3, ge=1, le=20)
    notebook_id: Optional[ShortId] = None

class QueryResponse(BaseModel):
    answer: str
    source_chunks: List[SourceChunk]

class ChatMessage(BaseModel):
    role: str
    content: str
    retrieval_metadata: Optional[Dict[str, Any]] = None

class ConversationStateResponse(BaseModel):
    notebook_id: str
    summary: str = ""
    messages: List[ChatMessage] = Field(default_factory=list)


class NotebookCreateRequest(BaseModel):
    title: NotebookTitle
    icon_key: IconKey = "folder"


class NotebookUpdateRequest(BaseModel):
    title: Optional[NotebookTitle] = None
    icon_key: Optional[IconKey] = None


class NoteCreateRequest(BaseModel):
    notebook_id: ShortId
    content: NoteContentValue
    source_message_id: Optional[ShortId] = None


class NoteResponse(BaseModel):
    id: str
    notebook_id: str
    content: str
    source_message_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class NotebookShareResponse(BaseModel):
    share_url: str


class SharedNotebookDocumentResponse(BaseModel):
    display_title: str
    page_count: int = 0
    summary: str = ""
    processing_status: str


class SharedNotebookResponse(BaseModel):
    title: str
    source_count: int = 0
    indexed_document_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    documents: List[SharedNotebookDocumentResponse] = Field(default_factory=list)


class NotebookResponse(BaseModel):
    id: str
    title: str
    icon_key: str = "folder"
    user_id: Optional[str] = None
    share_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    source_count: int = 0
    indexed_document_count: int = 0
    pending_document_count: int = 0
    failed_document_count: int = 0
    ready_for_query: bool = False
    file_ids: List[str] = Field(default_factory=list)
    filenames: List[str] = Field(default_factory=list)
    documents: List[DocumentResponse] = Field(default_factory=list)
