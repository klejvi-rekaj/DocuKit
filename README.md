# DokuKit

DokuKit is a document-grounded study workspace built around notebooks, PDF ingestion, retrieval-augmented chat, saved notes, sharing, account-based sessions, and user-level personalization.

This README is based on the code currently present in this repository. It avoids describing features that were not found in the inspected codebase.

## What the app currently does

- Creates notebook-scoped study workspaces
- Uploads PDF files into notebooks
- Extracts PDF text, chunks it, embeds it, and indexes it for retrieval
- Answers notebook questions through a retrieval-augmented chat flow
- Streams assistant responses over Server-Sent Events
- Persists chat history in the backend database
- Lets users save assistant messages as notebook notes
- Supports notebook sharing through public share links
- Supports email/password sign up, sign in, sign out, and cookie-based sessions
- Supports user profile updates, password changes, and saved theme preference
- Supports light, dark, and system theme modes

## Repository layout

```text
DocuMind/
|-- backend/
|   |-- alembic/
|   |-- app/
|   |   |-- api/
|   |   |-- models/
|   |   `-- services/
|   |-- requirements.txt
|   `-- tests/
|-- frontend/
|   |-- app/
|   |-- components/
|   |-- features/
|   |-- hooks/
|   |-- lib/
|   |-- public/
|   `-- package.json
|-- scripts/
|-- .gitignore
`-- README.md
```

## Frontend

The frontend is a Next.js App Router application.

- Framework: `next@16.1.6`
- UI runtime: `react@19.2.3`, `react-dom@19.2.3`
- Language: TypeScript
- Styling: Tailwind CSS v4 plus custom CSS variables and component tokens in `frontend/app/globals.css`
- Animation: Framer Motion plus CSS transitions and keyframes
- Dialog UI: `@radix-ui/react-dialog`
- Icons: `lucide-react` plus local PNG assets in `frontend/public/`

Verified from:

- `frontend/package.json`
- `frontend/app/layout.tsx`
- `frontend/app/globals.css`
- `frontend/components/ui/dialog.tsx`
- `frontend/features/theme/ThemeProvider.tsx`

### Frontend routes present in the app

- `/` - notebook library
- `/notebook/[id]` - notebook workspace and chat
- `/settings` - account settings
- `/sign-in` - sign-in page
- `/sign-up` - sign-up page
- `/share/[shareId]` - public shared notebook view

Verified from:

- `frontend/app/page.tsx`
- `frontend/app/notebook/[id]/page.tsx`
- `frontend/app/settings/page.tsx`
- `frontend/app/sign-in/page.tsx`
- `frontend/app/sign-up/page.tsx`
- `frontend/app/share/[shareId]/page.tsx`

## Backend

The backend is a FastAPI application with SQLAlchemy models, Alembic migrations, and a database-backed document, chat, notes, share, and auth layer.

- Framework: FastAPI
- ASGI server: Uvicorn
- ORM: SQLAlchemy 2.x
- Migrations: Alembic
- Database driver: `psycopg[binary]`
- Validation and config: Pydantic v2 plus `pydantic-settings`
- File upload handling: `python-multipart`
- Streaming support: `sse-starlette`

Verified from:

- `backend/requirements.txt`
- `backend/app/main.py`
- `backend/app/database.py`
- `backend/alembic/`

### Backend API routers present in the app

- `/api/auth`
- `/api/notebooks`
- `/api/upload`
- `/api/query`
- `/api/notes`
- `/api/share`
- `/health`

Verified from:

- `backend/app/main.py`
- `backend/app/api/auth.py`
- `backend/app/api/notebooks.py`
- `backend/app/api/upload.py`
- `backend/app/api/query.py`
- `backend/app/api/notes.py`
- `backend/app/api/share.py`

## Database model summary

The current SQLAlchemy model layer includes:

- `User`
- `UserSession`
- `Notebook`
- `Document`
- `DocumentChunk`
- `Conversation`
- `ChatMessage`
- `IndexingJob`
- `Note`

Verified from:

- `backend/app/models/db_models.py`

### Current user and account fields

The inspected `User` model currently includes:

- `email`
- `display_name`
- `password_hash`
- `theme_preference`

The current session model stores:

- `token_hash`
- `expires_at`
- `last_seen_at`
- `user_agent`

Verified from:

- `backend/app/models/db_models.py`

## Authentication

The current authentication flow is email/password only.

Implemented:

- sign up
- sign in
- sign out
- server-side session lookup
- cookie-based auth
- profile update
- password change
- saved theme preference

Not found in the inspected auth routes:

- Google sign-in
- password reset
- email verification
- magic links

Verified from:

- `backend/app/api/auth.py`
- `backend/app/services/auth_service.py`
- `frontend/app/sign-in/page.tsx`
- `frontend/app/sign-up/page.tsx`
- `frontend/app/settings/page.tsx`

### Auth and session details

From the inspected code:

- passwords are hashed with `passlib` using `pbkdf2_sha256`
- session tokens are generated server-side and stored as SHA-256 hashes in the database
- the browser receives a session cookie
- session cookies are configured through environment variables
- the frontend does not use localStorage as the source of truth for authentication

Verified from:

- `backend/app/services/auth_service.py`
- `backend/app/auth.py`
- `backend/app/config.py`
- `frontend/features/auth/useAuthSession.ts`

## Document processing and retrieval pipeline

The current backend pipeline works like this:

1. A PDF is uploaded to `/api/upload`
2. The file is validated as a PDF and saved under `backend/data/uploads/`
3. A background indexing task is started
4. PDF text is extracted page by page
5. The document is split into chunks
6. Embeddings are generated
7. Chunks and embeddings are persisted
8. The FAISS index is rebuilt from database-backed chunk rows
9. Notebook queries search the indexed content and stream a generated answer

Verified from:

- `backend/app/api/upload.py`
- `backend/app/services/pdf_utils.py`
- `backend/app/services/rag_utils.py`
- `backend/app/api/query.py`

### Current embedding and generation model path

The currently inspected backend uses:

- local generation model: `Qwen/Qwen2.5-0.5B-Instruct`
- optional Gemini embeddings when `GEMINI_API_KEY` is set
- local embedding fallback: `sentence-transformers/all-MiniLM-L6-v2`

Verified from:

- `backend/app/services/ai_utils.py`
- `backend/app/services/rag_utils.py`
- `backend/app/config.py`

Important note:

- `OPENAI_API_KEY` is present in `backend/.env.example`
- I did not find active OpenAI usage in the inspected backend service files listed above

## Theme system

The app has a custom theme system with:

- `light`
- `dark`
- `system`

Theme behavior currently includes:

- early theme application in `frontend/app/layout.tsx`
- a client-side theme provider
- localStorage persistence under `dokukit-theme`
- user-level theme preference in the database via `theme_preference`

Verified from:

- `frontend/app/layout.tsx`
- `frontend/features/theme/ThemeProvider.tsx`
- `frontend/app/settings/page.tsx`
- `backend/app/models/db_models.py`
- `backend/app/api/auth.py`

## Security features currently visible in code

The inspected code currently includes:

- cookie-based auth
- `HttpOnly` session cookies
- configurable `SameSite` cookie policy
- production-ready secure-cookie toggle through config
- CSRF-style request verification dependency on mutating auth, notebook, upload, query, and note routes
- in-memory rate limiting for auth, query, and upload endpoints
- backend security headers
- frontend security headers via Next.js config
- upload validation for PDF extension, MIME type, size, and PDF file signature
- ownership checks on notebook-scoped routes

Verified from:

- `backend/app/config.py`
- `backend/app/auth.py`
- `backend/app/api/auth.py`
- `backend/app/api/notebooks.py`
- `backend/app/api/upload.py`
- `backend/app/api/query.py`
- `backend/app/main.py`
- `frontend/next.config.ts`

## Migrations currently in the repo

The repository currently includes these Alembic revisions:

- `20260401_0001_notebook_first_postgres.py`
- `20260401_0002_notebook_deletion_lifecycle.py`
- `20260402_0003_notes_table.py`
- `20260402_0004_notebook_share_id.py`
- `20260403_0005_notebook_visual_identity.py`
- `20260403_0006_manual_notebook_icons.py`
- `20260403_0007_auth_sessions.py`
- `20260404_0008_chat_message_order.py`
- `20260404_0009_repair_chat_message_order.py`
- `20260404_0010_user_theme_preference.py`

Verified from:

- `backend/alembic/versions/`

## Local development

### Frontend scripts

Defined in `frontend/package.json`:

```bash
npm run dev
npm run build
npm run start
npm run lint
npm run test:state
```

### Backend prerequisites

The repository does not define a backend package manager wrapper or task runner. The inspected backend expects:

- a Python environment with the packages from `backend/requirements.txt`
- a database reachable through `DATABASE_URL`
- Alembic available through the backend environment

### Environment variables

The checked-in example file is:

- `backend/.env.example`

Variables currently present there:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `SESSION_COOKIE_NAME`
- `SESSION_MAX_AGE_DAYS`
- `SESSION_COOKIE_SECURE`
- `SESSION_COOKIE_SAMESITE`
- `AUTH_RATE_LIMIT_WINDOW_SECONDS`
- `AUTH_RATE_LIMIT_ATTEMPTS`
- `SIGN_UP_RATE_LIMIT_WINDOW_SECONDS`
- `SIGN_UP_RATE_LIMIT_ATTEMPTS`
- `QUERY_RATE_LIMIT_WINDOW_SECONDS`
- `QUERY_RATE_LIMIT_ATTEMPTS`
- `UPLOAD_RATE_LIMIT_WINDOW_SECONDS`
- `UPLOAD_RATE_LIMIT_ATTEMPTS`
- `MAX_UPLOAD_SIZE_BYTES`
- `MAX_QUESTION_LENGTH`
- `MAX_NOTE_LENGTH`
- `MAX_NOTEBOOK_TITLE_LENGTH`
- `ENVIRONMENT`
- `PORT`
- `DATABASE_URL`
- `FRONTEND_BASE_URL`
- `FAISS_INDEX_PATH`
- `PDF_UPLOAD_DIR`

The current `Settings` object also defines:

- `gemini_api_key`

## One accurate local startup flow

The following steps match the structure and tooling currently in this repository:

### 1. Install frontend dependencies

```bash
cd frontend
npm install
```

### 2. Install backend dependencies

Create or activate your Python environment, then install:

```bash
pip install -r backend/requirements.txt
```

### 3. Configure backend environment

Copy:

```bash
backend/.env.example
```

to:

```bash
backend/.env
```

and fill in the required values for your environment.

### 4. Run database migrations

The repository uses Alembic migrations and also calls `Base.metadata.create_all()` on startup. The safer path is still to apply Alembic first:

```bash
cd backend
alembic upgrade head
```

### 5. Start the backend

From the backend directory:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6. Start the frontend

From the frontend directory:

```bash
npm run dev
```

If your backend is not running on `http://localhost:8000`, set:

```bash
NEXT_PUBLIC_API_URL
```

before starting the frontend.

The frontend code currently defaults to:

- `http://localhost:8000` in several client fetches
- `http://127.0.0.1:8000` is also allowed by backend CORS

Verified from:

- `frontend/hooks/useNotebooks.ts`
- `frontend/components/ChatStream.tsx`
- `backend/app/main.py`

## Testing

### Frontend

The frontend exposes one checked-in test command:

```bash
cd frontend
npm run test:state
```

That command runs Node's built-in test runner against:

- `frontend/tests/notebookState.test.mjs`

### Backend

The backend test suite is written with Python `unittest` under:

- `backend/tests/`

Inspected test files include:

- `test_auth.py`
- `test_integrity_and_lifecycle.py`
- `test_notebook_deletion.py`
- `test_notebook_isolation.py`
- `test_notes.py`
- `test_ownership_scoping.py`
- `test_security_hardening.py`
- `test_share.py`

The repository does not define a dedicated backend test runner script in source.

## Project structure details

### Frontend components of interest

- `frontend/components/ChatStream.tsx` - chat UI and SSE streaming client
- `frontend/components/CreateNotebookModal.tsx` - notebook creation modal
- `frontend/components/NotebookFolderCard.tsx` - notebook folder card UI
- `frontend/components/ResearchStudioShell.tsx` - notebook workspace shell
- `frontend/features/auth/` - auth page frame, API helpers, session hook
- `frontend/features/theme/` - theme provider and toggle logic

### Backend services of interest

- `backend/app/services/ai_utils.py` - local generation logic and streamed answer helpers
- `backend/app/services/rag_utils.py` - chunking, embeddings, hybrid search, FAISS management
- `backend/app/services/auth_service.py` - password and session logic
- `backend/app/services/generation_control.py` - server-side stop signal handling
- `backend/app/services/rate_limit.py` - in-memory rate limiting

## Current product limitations visible from inspected code

The following are true at the time of inspection:

- uploads are limited to PDF files
- there is no Google sign-in route in the backend auth API
- there is no password reset route in the backend auth API
- there is no email verification flow in the inspected auth code
- rate limiting is implemented in process memory, not in a shared external store
- the local generation model is a very small CPU-hosted Qwen model
- the backend currently allows CORS for local frontend origins only

## Versioned assets and storage

The repository ignores the following local and runtime data in `.gitignore`:

- `.env`
- `.venv`
- `node_modules`
- `.next`
- `backend/data/faiss/`
- `backend/data/uploads/`
- local SQLite and DB artifacts

This means uploaded PDFs and generated FAISS indexes are intended to stay out of Git.

## Notes for deployment

The codebase already contains some production-facing pieces:

- security headers
- configurable secure cookies
- ownership checks
- session expiration
- migrations
- public share route

Before deployment, the following code-backed settings should be reviewed:

- `SESSION_COOKIE_SECURE`
- `SESSION_COOKIE_SAMESITE`
- `FRONTEND_BASE_URL`
- `DATABASE_URL`
- `GEMINI_API_KEY` if Gemini embeddings are desired
- CORS origins in `backend/app/main.py`

## Summary

DokuKit currently ships as:

- a Next.js frontend with a notebook library, notebook workspace, auth pages, settings page, and share page
- a FastAPI backend with notebook, upload, query, notes, share, and auth APIs
- a SQLAlchemy and Alembic data model
- a PDF-to-RAG pipeline with database-backed chat history and notebook-scoped retrieval
