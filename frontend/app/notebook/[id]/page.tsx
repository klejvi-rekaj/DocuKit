"use client";

import { use, useEffect, useState } from "react";
import { Notebook } from "@/lib/types";
import ResearchStudioShell from "@/components/ResearchStudioShell";
import { useAuthSession } from "@/features/auth/useAuthSession";
import { normalizeNotebook, NotebookApiResponse } from "@/lib/notebookState";

export default function NotebookPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { user, isLoading: authLoading, signOut } = useAuthSession({ required: true });
  const [notebook, setNotebook] = useState<Notebook | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState<string>("");
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (!user) {
      return;
    }

    let cancelled = false;
    let refreshTimeoutId: number | null = null;

    const fetchNotebook = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/notebooks/${id}`, {
          cache: "no-store",
          credentials: "include",
        });
        if (!response.ok) {
          if (response.status === 401) {
            window.location.href = "/sign-in";
            return;
          }
          if (response.status === 404) {
            setNotFound(true);
            setNotebook(null);
            setLoadError("");
            return;
          }
          throw new Error(`Failed to load notebook: ${response.status}`);
        }
        const data: NotebookApiResponse = await response.json();
        const normalized = normalizeNotebook(data, 0);
        if (cancelled) {
          return;
        }
        setNotebook(normalized);
        setNotFound(false);
        setLoadError("");

        const hasPendingDocuments = normalized.documents.some((document) =>
          ["uploaded", "processing"].includes(document.processingStatus),
        );
        if (hasPendingDocuments) {
          refreshTimeoutId = window.setTimeout(() => {
            void fetchNotebook();
          }, 2000);
        }
      } catch (e) {
        console.error("Failed to load notebook", e);
        if (cancelled) {
          return;
        }
        setNotebook(null);
        setLoadError("The notebook could not be loaded right now.");
      }
      if (!cancelled) {
        setLoading(false);
      }
    };

    void fetchNotebook();

    return () => {
      cancelled = true;
      if (refreshTimeoutId) {
        window.clearTimeout(refreshTimeoutId);
      }
    };
  }, [apiBaseUrl, id, user]);

  if (authLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-paper text-sm font-medium text-[color:var(--theme-text-muted)] animate-pulse">
        Opening notebook...
      </div>
    );
  }

  if (!user) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-paper text-sm font-medium text-[color:var(--theme-text-muted)] animate-pulse">
        Opening notebook...
      </div>
    );
  }

  if (!notebook) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-paper text-center px-4">
        <h1 className="mb-4 text-4xl font-semibold tracking-[-0.04em] text-ink">{notFound ? "Notebook missing" : "Something went wrong"}</h1>
        <p className="text-[14px] leading-[1.6] text-[color:var(--theme-text-secondary)]">
          {notFound ? "Notebook not found or has been deleted." : loadError || "Notebook could not be loaded."}
        </p>
        <button 
          onClick={() => window.location.href = "/"}
          className="mt-8 rounded-[10px] border border-border bg-surface px-4 py-2.5 text-[14px] font-medium text-ink transition-colors hover:bg-[color:var(--theme-surface-muted)]"
        >
          Return to Library
        </button>
      </div>
    );
  }

  return <ResearchStudioShell notebook={notebook} currentUser={user} onSignOut={signOut} />;
}
