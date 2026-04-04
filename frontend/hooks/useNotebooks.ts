"use client";

import { useCallback, useEffect, useState } from "react";
import { Notebook } from "@/lib/types";
import { normalizeNotebook, NotebookApiResponse, removeNotebookFromState } from "@/lib/notebookState";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error";
}

export function useNotebooks() {
  const [notebooks, setNotebooks] = useState<Notebook[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const refreshNotebooks = useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) {
      setIsLoading(true);
    }
    try {
      const response = await fetch(`${apiBaseUrl}/api/notebooks`, {
        cache: "no-store",
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(`Failed to load notebooks: ${response.status}`);
      }
      const data: unknown = await response.json();
      setNotebooks(Array.isArray(data) ? data.map((item, index) => normalizeNotebook(item as NotebookApiResponse, index)) : []);
    } catch (error) {
      console.error("Failed to load notebooks", error);
      setNotebooks([]);
    } finally {
      if (!options?.silent) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void refreshNotebooks();
  }, [refreshNotebooks]);

  useEffect(() => {
    const hasPendingDocuments = notebooks.some((notebook) => notebook.pendingDocumentCount > 0);
    if (!hasPendingDocuments) {
      return;
    }

    const intervalId = window.setInterval(() => {
      refreshNotebooks({ silent: true }).catch((error) => {
        console.error("Failed to refresh notebooks during background indexing", error);
      });
    }, 2500);

    return () => window.clearInterval(intervalId);
  }, [notebooks, refreshNotebooks]);

  useEffect(() => {
    const handleFocusRefresh = () => {
      if (document.visibilityState === "hidden") {
        return;
      }
      refreshNotebooks({ silent: true }).catch((error) => {
        console.error("Failed to refresh notebooks on focus", error);
      });
    };

    window.addEventListener("focus", handleFocusRefresh);
    document.addEventListener("visibilitychange", handleFocusRefresh);
    return () => {
      window.removeEventListener("focus", handleFocusRefresh);
      document.removeEventListener("visibilitychange", handleFocusRefresh);
    };
  }, [refreshNotebooks]);

  const createNotebook = async (files: File[], iconKey: string) => {
    setIsCreating(true);
    let notebookId: string | null = null;
    try {
      const notebookResponse = await fetch(`${apiBaseUrl}/api/notebooks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ title: "Untitled notebook", icon_key: iconKey }),
      });

      if (!notebookResponse.ok) {
        const errorData = await notebookResponse.json().catch(() => ({ detail: `HTTP ${notebookResponse.status}` }));
        throw new Error(errorData.detail || "Failed to create notebook");
      }

      const notebookData: NotebookApiResponse = await notebookResponse.json();
      notebookId = notebookData.id;
      const createdNotebookId = notebookData.id;

      const uploadPromises = files.map(async (file) => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("notebook_id", createdNotebookId);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5m timeout

        try {
          const response = await fetch(`${apiBaseUrl}/api/upload`, {
            method: "POST",
            body: formData,
            credentials: "include",
            signal: controller.signal,
          });

          clearTimeout(timeoutId);

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
            throw new Error(errorData.detail || `Failed to upload ${file.name}`);
          }

          return response.json();
        } catch (err: unknown) {
          clearTimeout(timeoutId);
          if (err instanceof DOMException && err.name === "AbortError") {
            throw new Error(`Upload timed out for ${file.name}. The server might be busy.`);
          }
          throw err;
        }
      });

      await Promise.all(uploadPromises);

      const detailsResponse = await fetch(`${apiBaseUrl}/api/notebooks/${createdNotebookId}`, {
        cache: "no-store",
        credentials: "include",
      });
      if (!detailsResponse.ok) {
        throw new Error("Notebook created but failed to load notebook details.");
      }

      const notebookDetailsData: NotebookApiResponse = await detailsResponse.json();
      const notebookDetails = normalizeNotebook(notebookDetailsData, notebooks.length);
      setNotebooks((prev) => [notebookDetails, ...prev]);
      return notebookDetails;
    } catch (error) {
      if (notebookId) {
        fetch(`${apiBaseUrl}/api/notebooks/${notebookId}`, {
          method: "DELETE",
          credentials: "include",
        }).catch(() => undefined);
      }
      console.error("Error creating notebook:", error);
      throw new Error(getErrorMessage(error));
    } finally {
      setIsCreating(false);
    }
  };

  const deleteNotebook = async (notebookId: string) => {
    const response = await fetch(`${apiBaseUrl}/api/notebooks/${notebookId}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      throw new Error(errorData.detail || "Failed to delete notebook");
    }
    setNotebooks((prev) => removeNotebookFromState(prev, notebookId));
  };

  const updateNotebookIcon = async (notebookId: string, iconKey: string) => {
    const response = await fetch(`${apiBaseUrl}/api/notebooks/${notebookId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ icon_key: iconKey }),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
      throw new Error(errorData.detail || "Failed to update notebook icon");
    }
    const notebookData: NotebookApiResponse = await response.json();
    setNotebooks((prev) =>
      prev.map((notebook, index) => (notebook.id === notebookId ? normalizeNotebook(notebookData, index) : notebook)),
    );
  };

  return {
    notebooks,
    createNotebook,
    deleteNotebook,
    updateNotebookIcon,
    isCreating,
    isLoading,
    refreshNotebooks,
  };
}
