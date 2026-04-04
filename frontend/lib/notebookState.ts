import { Notebook } from "@/lib/types";

export interface NotebookApiDocument {
  id: string;
  notebook_id: string;
  original_filename: string;
  display_title: string;
  processing_status: string;
  processing_error?: string | null;
  page_count?: number;
  summary?: string;
  latest_indexing_job?: {
    id: string;
    notebook_id: string;
    document_id: string;
    status: string;
    error_message?: string | null;
    queued_at?: string;
    started_at?: string | null;
    finished_at?: string | null;
  } | null;
}

export interface NotebookApiResponse {
  id: string;
  title: string;
  share_id?: string | null;
  icon_key?: string;
  created_at?: string;
  source_count?: number;
  indexed_document_count?: number;
  pending_document_count?: number;
  failed_document_count?: number;
  ready_for_query?: boolean;
  file_ids?: string[];
  filenames?: string[];
  documents?: NotebookApiDocument[];
}

export function normalizeNotebook(raw: NotebookApiResponse, index: number): Notebook {
  const createdAt = raw.created_at ? new Date(raw.created_at) : new Date();
  return {
    id: raw.id,
    title: raw.title,
    shareId: raw.share_id ?? null,
    iconKey: raw.icon_key ?? "folder",
    dateLabel: new Intl.DateTimeFormat("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(createdAt),
    sourceCount: raw.source_count ?? raw.documents?.length ?? 0,
    pastelIndex: index % 4,
    fileIds: raw.file_ids ?? raw.documents?.map((document) => document.id) ?? [],
    filenames: raw.filenames ?? raw.documents?.map((document) => document.original_filename) ?? [],
    indexedDocumentCount: raw.indexed_document_count ?? raw.documents?.filter((document) => document.processing_status === "indexed").length ?? 0,
    pendingDocumentCount: raw.pending_document_count ?? raw.documents?.filter((document) => ["uploaded", "processing"].includes(document.processing_status)).length ?? 0,
    failedDocumentCount: raw.failed_document_count ?? raw.documents?.filter((document) => document.processing_status === "failed").length ?? 0,
    readyForQuery: raw.ready_for_query ?? Boolean(raw.documents?.some((document) => document.processing_status === "indexed")),
    documents: raw.documents?.map((document) => ({
      id: document.id,
      notebookId: document.notebook_id,
      originalFilename: document.original_filename,
      displayTitle: document.display_title,
      processingStatus: document.processing_status,
      processingError: document.processing_error ?? null,
      pageCount: document.page_count ?? 0,
      summary: document.summary ?? "",
      latestIndexingJob: document.latest_indexing_job
        ? {
            id: document.latest_indexing_job.id,
            notebookId: document.latest_indexing_job.notebook_id,
            documentId: document.latest_indexing_job.document_id,
            status: document.latest_indexing_job.status,
            errorMessage: document.latest_indexing_job.error_message ?? null,
            queuedAt: document.latest_indexing_job.queued_at ?? "",
            startedAt: document.latest_indexing_job.started_at ?? null,
            finishedAt: document.latest_indexing_job.finished_at ?? null,
          }
        : null,
    })) ?? [],
  };
}

export function removeNotebookFromState(notebooks: Notebook[], notebookId: string): Notebook[] {
  return notebooks.filter((notebook) => notebook.id !== notebookId);
}
