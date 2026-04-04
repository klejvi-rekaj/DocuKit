export interface IndexingJob {
  id: string;
  notebookId: string;
  documentId: string;
  status: string;
  errorMessage?: string | null;
  queuedAt: string;
  startedAt?: string | null;
  finishedAt?: string | null;
}

export interface NotebookDocument {
  id: string;
  notebookId: string;
  originalFilename: string;
  displayTitle: string;
  processingStatus: string;
  processingError?: string | null;
  pageCount: number;
  summary: string;
  latestIndexingJob?: IndexingJob | null;
}

export interface Note {
  id: string;
  notebookId: string;
  content: string;
  sourceMessageId?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AuthUser {
  id: string;
  email: string;
  displayName?: string | null;
  themePreference?: "system" | "light" | "dark" | null;
  hasPassword?: boolean;
}

export interface AuthSession {
  authenticated: boolean;
  user: AuthUser | null;
}

export interface Notebook {
  id: string;
  title: string;
  shareId?: string | null;
  iconKey: string;
  dateLabel: string;
  sourceCount: number;
  pastelIndex: number;
  fileIds: string[];
  filenames: string[];
  documents: NotebookDocument[];
  indexedDocumentCount: number;
  pendingDocumentCount: number;
  failedDocumentCount: number;
  readyForQuery: boolean;
}

export interface SharedNotebookDocument {
  displayTitle: string;
  pageCount: number;
  summary: string;
  processingStatus: string;
}

export interface SharedNotebook {
  title: string;
  sourceCount: number;
  indexedDocumentCount: number;
  createdAt: string;
  updatedAt: string;
  documents: SharedNotebookDocument[];
}
