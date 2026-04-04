"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  Check,
  Loader2,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings2,
  Share2,
  Trash2,
} from "lucide-react";

import ChatStream from "@/components/ChatStream";
import { AppButton } from "@/components/ui/AppButton";
import { AuthUser, Note, Notebook } from "@/lib/types";

interface ResearchStudioShellProps {
  notebook: Notebook;
  currentUser: AuthUser;
  onSignOut: () => Promise<void>;
}

const SOURCES_PANEL_STORAGE_KEY = "documind_sources_panel_open";
const DESKTOP_MEDIA_QUERY = "(min-width: 1024px)";

export default function ResearchStudioShell({ notebook, currentUser, onSignOut }: ResearchStudioShellProps) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [notesLoading, setNotesLoading] = useState(true);
  const [notesError, setNotesError] = useState<string | null>(null);
  const [deletingNoteId, setDeletingNoteId] = useState<string | null>(null);
  const [isSourcesOpen, setIsSourcesOpen] = useState(true);
  const [hasHydratedSourcesState, setHasHydratedSourcesState] = useState(false);
  const [isSharing, setIsSharing] = useState(false);
  const [shareFeedback, setShareFeedback] = useState<"idle" | "copied" | "error">("idle");
  const [title, setTitle] = useState(notebook.title || "Untitled notebook");
  const [draftTitle, setDraftTitle] = useState(notebook.title || "Untitled notebook");
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [isSavingTitle, setIsSavingTitle] = useState(false);
  const [titleError, setTitleError] = useState<string | null>(null);
  const titleContainerRef = useRef<HTMLDivElement | null>(null);
  const titleInputRef = useRef<HTMLInputElement | null>(null);
  const previousNotebookIdRef = useRef(notebook.id);
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const hasDocuments = notebook.documents.length > 0;
  const readyDocuments = notebook.documents.filter((document) => document.processingStatus === "indexed").length;
  const hasNotes = notes.length > 0;

  useEffect(() => {
    if (previousNotebookIdRef.current === notebook.id) {
      return;
    }

    previousNotebookIdRef.current = notebook.id;
    const nextTitle = notebook.title || "Untitled notebook";
    setTitle(nextTitle);
    setDraftTitle(nextTitle);
    setIsEditingTitle(false);
    setTitleError(null);
  }, [notebook.id, notebook.title]);

  useEffect(() => {
    if (!isEditingTitle) {
      return;
    }

    titleInputRef.current?.focus();
    titleInputRef.current?.select();
  }, [isEditingTitle]);

  const loadNotes = useCallback(async () => {
    setNotesLoading(true);
    setNotesError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/notes/${notebook.id}`, {
        cache: "no-store",
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(`Failed to load notes (${response.status})`);
      }

      const data = (await response.json()) as Array<{
        id: string;
        notebook_id: string;
        content: string;
        source_message_id?: string | null;
        created_at: string;
        updated_at: string;
      }>;

      setNotes(
        data.map((note) => ({
          id: note.id,
          notebookId: note.notebook_id,
          content: note.content,
          sourceMessageId: note.source_message_id ?? null,
          createdAt: note.created_at,
          updatedAt: note.updated_at,
        })),
      );
    } catch (error) {
      console.error("Failed to load notes", error);
      setNotesError("Saved notes could not be loaded right now.");
    } finally {
      setNotesLoading(false);
    }
  }, [apiBaseUrl, notebook.id]);

  useEffect(() => {
    void loadNotes();
  }, [loadNotes]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const mediaQuery = window.matchMedia(DESKTOP_MEDIA_QUERY);
    const savedPreference = window.localStorage.getItem(SOURCES_PANEL_STORAGE_KEY);

    if (savedPreference === "true" || savedPreference === "false") {
      setIsSourcesOpen(savedPreference === "true");
    } else {
      setIsSourcesOpen(mediaQuery.matches);
    }

    setHasHydratedSourcesState(true);
  }, []);

  useEffect(() => {
    if (!hasHydratedSourcesState || typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(SOURCES_PANEL_STORAGE_KEY, String(isSourcesOpen));
  }, [hasHydratedSourcesState, isSourcesOpen]);

  const cancelTitleEdit = useCallback(() => {
    setDraftTitle(title);
    setTitleError(null);
    setIsEditingTitle(false);
  }, [title]);

  const saveTitle = useCallback(async () => {
    const nextTitle = draftTitle.trim() || "Untitled notebook";

    if (nextTitle === title) {
      setDraftTitle(nextTitle);
      setTitleError(null);
      setIsEditingTitle(false);
      return;
    }

    setIsSavingTitle(true);
    setTitleError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/api/notebooks/${notebook.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ title: nextTitle }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        throw new Error(errorData.detail || "Failed to rename notebook");
      }

      setTitle(nextTitle);
      setDraftTitle(nextTitle);
      setIsEditingTitle(false);
    } catch (error) {
      console.error("Failed to rename notebook", error);
      setTitleError("Could not save right now.");
    } finally {
      setIsSavingTitle(false);
    }
  }, [apiBaseUrl, draftTitle, notebook.id, title]);

  useEffect(() => {
    if (!isEditingTitle) {
      return;
    }

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node | null;
      if (!target) {
        return;
      }

      if (titleContainerRef.current?.contains(target)) {
        return;
      }

      void saveTitle();
    };

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [isEditingTitle, saveTitle]);

  const handleShare = useCallback(async () => {
    setIsSharing(true);
    setShareFeedback("idle");

    try {
      const response = await fetch(`${apiBaseUrl}/api/notebooks/${notebook.id}/share`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(`Failed to share notebook (${response.status})`);
      }

      const data = (await response.json()) as { share_url: string };
      await navigator.clipboard.writeText(data.share_url);
      setShareFeedback("copied");
      window.setTimeout(() => setShareFeedback("idle"), 1500);
    } catch (error) {
      console.error("Share failed", error);
      setShareFeedback("error");
      window.setTimeout(() => setShareFeedback("idle"), 2000);
    } finally {
      setIsSharing(false);
    }
  }, [apiBaseUrl, notebook.id]);

  const handleDeleteNote = useCallback(
    async (noteId: string) => {
      setDeletingNoteId(noteId);
      setNotesError(null);

      try {
        const response = await fetch(`${apiBaseUrl}/api/notes/${notebook.id}/${noteId}`, {
          method: "DELETE",
          credentials: "include",
        });

        if (!response.ok) {
          throw new Error(`Failed to delete note (${response.status})`);
        }

        await loadNotes();
      } catch (error) {
        console.error("Failed to delete note", error);
        setNotesError("That note could not be deleted right now.");
      } finally {
        setDeletingNoteId(null);
      }
    },
    [apiBaseUrl, loadNotes, notebook.id],
  );

  const statusBadge = (status: string) => {
    if (status === "indexed") {
      return (
        <span className="theme-success-badge inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium">
          <Check className="h-3 w-3" />
          Ready
        </span>
      );
    }

    if (status === "failed") {
      return (
        <span className="theme-danger-badge inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium">
          <AlertCircle className="h-3 w-3" />
          Failed
        </span>
      );
    }

    return (
      <span className="theme-muted-badge inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium">
        <Loader2 className="h-3 w-3 animate-spin" />
        Processing
      </span>
    );
  };

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-paper text-ink">
      <div className="relative h-screen overflow-hidden px-4 py-4">
        <div className="flex h-full flex-col overflow-hidden">
          <header className="mb-6 flex items-center justify-between border-b border-border px-2 pb-5">
            <div className="flex min-w-0 items-center gap-7">
              <Link
                href="/"
                className="inline-flex shrink-0 items-center justify-center transition duration-150 hover:scale-[1.03] hover:opacity-85"
                aria-label="Go to notebook library"
              >
                <span className="text-[38px] leading-none text-[color:var(--theme-logo)] [font-family:var(--font-logo)]">DokuKit</span>
              </Link>
              <div ref={titleContainerRef} className="min-w-0">
                <p className="text-[13px] font-medium text-[color:var(--theme-text-secondary)]">Notebook</p>
                {isEditingTitle ? (
                  <div className="mt-1">
                    <input
                      ref={titleInputRef}
                      value={draftTitle}
                      onChange={(event) => setDraftTitle(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          void saveTitle();
                        }

                        if (event.key === "Escape") {
                          event.preventDefault();
                          cancelTitleEdit();
                        }
                      }}
                      className="w-full bg-transparent pb-1 text-[32px] font-semibold leading-[1.12] tracking-[-0.035em] text-ink outline-none"
                      aria-label="Rename notebook"
                    />
                    <div className="mt-1 min-h-[18px] text-[12px] text-[color:var(--theme-text-secondary)]">
                      {isSavingTitle ? "Saving..." : titleError ?? ""}
                    </div>
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => {
                      setDraftTitle(title);
                      setTitleError(null);
                      setIsEditingTitle(true);
                    }}
                    className="mt-1 inline-flex max-w-full items-center bg-transparent text-left outline-none transition-opacity hover:opacity-80"
                    aria-label="Rename notebook"
                  >
                    <span className="block truncate pb-1 text-[32px] font-semibold leading-[1.12] tracking-[-0.035em] text-ink">
                      {title}
                    </span>
                  </button>
                )}
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <div className="hidden text-right lg:block">
                <p className="text-[12px] font-medium text-[color:var(--theme-text-muted)]">Signed in</p>
                <p className="text-[13px] text-ink">{currentUser.displayName || currentUser.email}</p>
              </div>
              <Link href="/settings">
                <AppButton type="button" variant="secondary" className="px-3.5 py-2.5">
                  <Settings2 className="h-4 w-4" />
                  <span>Settings</span>
                </AppButton>
              </Link>
              <AppButton
                type="button"
                onClick={() => void handleShare()}
                disabled={isSharing}
                variant="secondary"
                className="px-3.5 py-2.5"
              >
                {isSharing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Share2 className="h-4 w-4" />}
                <span>
                  {shareFeedback === "copied"
                    ? "Link copied"
                    : shareFeedback === "error"
                      ? "Share failed"
                      : isSharing
                        ? "Generating"
                        : "Share"}
                </span>
              </AppButton>
              <AppButton type="button" onClick={() => void onSignOut()} variant="secondary" className="px-3.5 py-2.5">
                <LogOut className="h-4 w-4" />
                <span>Sign out</span>
              </AppButton>
            </div>
          </header>

          <div className="min-h-0 flex-1 overflow-hidden">
            <div className="flex h-full min-h-0 gap-6">
              <div
                className={`relative h-full min-h-0 shrink-0 transition-all duration-300 ease-out ${
                  hasHydratedSourcesState && !isSourcesOpen ? "w-16" : "w-[320px]"
                }`}
              >
                <div className="ds-panel flex h-full min-h-0 flex-col overflow-hidden rounded-[18px] bg-[color:var(--theme-surface-raised)] shadow-none">
                  <div className="flex items-center border-b border-border p-5">
                    <div className="flex min-w-0 items-center gap-3">
                      <button
                        type="button"
                        onClick={() => setIsSourcesOpen((prev) => !prev)}
                        className="shrink-0 rounded-[10px] p-2 text-[color:var(--theme-text-secondary)] transition-colors hover:bg-[color:var(--theme-surface-muted)] hover:text-ink cursor-pointer"
                        aria-label={isSourcesOpen ? "Collapse sources panel" : "Expand sources panel"}
                        aria-expanded={isSourcesOpen}
                      >
                        <span className="relative z-10">
                          {isSourcesOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
                        </span>
                      </button>
                      {isSourcesOpen && <span className="text-[15px] font-medium text-ink">Sources</span>}
                    </div>
                  </div>

                  {isSourcesOpen ? (
                    <div className="flex flex-col gap-4 overflow-x-hidden overflow-y-auto p-4">
                      <div className="mt-2">
                        <div className="mb-4 px-1">
                          <span className="text-[13px] font-medium text-[color:var(--theme-text-secondary)]">Files</span>
                        </div>

                        <div className="space-y-2">
                          {!hasDocuments && (
                            <div className="rounded-[12px] bg-[color:var(--theme-surface-muted)] p-4 text-sm leading-[1.55] text-[color:var(--theme-text-secondary)]">
                              This notebook exists, but it does not have any uploaded documents yet.
                            </div>
                          )}

                          {notebook.documents.map((document, index) => (
                            <div
                              key={document.id}
                              className={`flex items-center justify-between gap-3 rounded-[12px] px-3 py-3 ${index !== 0 ? "border-t border-border" : ""}`}
                            >
                              <div className="min-w-0">
                                <span className="block truncate text-[14px] font-medium leading-tight text-ink">
                                  {document.displayTitle || document.originalFilename}
                                </span>
                                <span className="mt-1 block text-[12px] leading-[1.45] text-[color:var(--theme-text-secondary)]">
                                  {document.pageCount > 0 ? `${document.pageCount} pages` : "Document"}
                                </span>
                                {document.processingError && (
                                  <span className="mt-2 block text-[11px] leading-5 text-[color:var(--theme-danger)]">
                                    {document.processingError}
                                  </span>
                                )}
                              </div>
                              <div className="shrink-0">{statusBadge(document.processingStatus)}</div>
                            </div>
                          ))}
                        </div>

                        <div className="mt-6 border-t border-border pt-5">
                          <div className="mb-4 px-1">
                            <span className="text-[13px] font-medium text-[color:var(--theme-text-secondary)]">Saved notes</span>
                          </div>

                          {notesLoading ? (
                            <div className="px-4 py-4 text-sm text-[color:var(--theme-text-secondary)]">
                              <div className="flex items-center gap-2">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Loading saved notes...
                              </div>
                            </div>
                          ) : notesError ? (
                            <div className="px-4 py-4 text-sm text-[color:var(--theme-danger)]">{notesError}</div>
                          ) : !hasNotes ? (
                            <div className="rounded-[12px] bg-[color:var(--theme-surface-muted)] p-4 text-sm leading-[1.55] text-[color:var(--theme-text-secondary)]">
                              Save any assistant message to keep a notebook-scoped note here.
                            </div>
                          ) : (
                            <div className="space-y-2">
                              {notes.map((note, index) => (
                                <article
                                  key={note.id}
                                  className={`px-4 py-4 ${index !== 0 ? "border-t border-border" : ""}`}
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <p className="min-w-0 flex-1 whitespace-pre-wrap text-[14px] leading-[1.65] text-ink">
                                      {note.content}
                                    </p>
                                    <button
                                      type="button"
                                      onClick={() => void handleDeleteNote(note.id)}
                                      disabled={deletingNoteId === note.id}
                                      className="shrink-0 rounded-[10px] px-2 py-1 text-[12px] font-medium text-[color:var(--theme-text-secondary)] transition-colors hover:bg-[color:var(--theme-surface-muted)] hover:text-ink disabled:opacity-50 cursor-pointer"
                                    >
                                      <span className="inline-flex items-center gap-2">
                                        {deletingNoteId === note.id ? (
                                          <>
                                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                            Deleting
                                          </>
                                        ) : (
                                          <>
                                            <Trash2 className="h-3 w-3" />
                                            Delete
                                          </>
                                        )}
                                      </span>
                                    </button>
                                  </div>
                                  <p className="mt-3 text-[11px] text-[color:var(--theme-text-muted)]">
                                    Saved {new Date(note.createdAt).toLocaleString()}
                                  </p>
                                </article>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex h-full flex-col items-center gap-3 overflow-hidden px-3 py-4">
                      <button
                        type="button"
                        onClick={() => setIsSourcesOpen(true)}
                        className="rounded-[10px] border border-border bg-[color:var(--theme-surface)] px-2.5 py-2 text-[12px] font-medium text-[color:var(--theme-text-secondary)]"
                      >
                        {readyDocuments}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="h-full min-h-0 min-w-0 flex-1 transition-all duration-300 ease-out">
                <div className="relative flex h-full min-h-0 flex-col overflow-hidden">
                  <div className="relative min-h-0 flex-1 overflow-hidden bg-transparent pl-2">
                    <ChatStream
                      fileIds={notebook.fileIds || []}
                      notebookId={notebook.id}
                      documents={notebook.documents}
                      onNoteSaved={loadNotes}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
