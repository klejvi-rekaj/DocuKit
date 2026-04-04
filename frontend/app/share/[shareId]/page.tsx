"use client";

import { use, useEffect, useState } from "react";
import { FileText, Link2, Loader2 } from "lucide-react";

import { SharedNotebook } from "@/lib/types";

interface SharedNotebookApiResponse {
  title: string;
  source_count: number;
  indexed_document_count: number;
  created_at?: string;
  updated_at?: string;
  documents?: Array<{
    display_title: string;
    page_count?: number;
    summary?: string;
    processing_status: string;
  }>;
}

function normalizeSharedNotebook(raw: SharedNotebookApiResponse): SharedNotebook {
  return {
    title: raw.title,
    sourceCount: raw.source_count ?? 0,
    indexedDocumentCount: raw.indexed_document_count ?? 0,
    createdAt: raw.created_at ?? "",
    updatedAt: raw.updated_at ?? "",
    documents:
      raw.documents?.map((document) => ({
        displayTitle: document.display_title,
        pageCount: document.page_count ?? 0,
        summary: document.summary ?? "",
        processingStatus: document.processing_status,
      })) ?? [],
  };
}

export default function SharedNotebookPage({ params }: { params: Promise<{ shareId: string }> }) {
  const { shareId } = use(params);
  const [notebook, setNotebook] = useState<SharedNotebook | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState("");
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const loadSharedNotebook = async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/api/share/${shareId}`, { cache: "no-store" });
        if (!response.ok) {
          if (response.status === 404) {
            setNotFound(true);
            setNotebook(null);
            return;
          }
          throw new Error(`Failed to load shared notebook (${response.status})`);
        }

        const data = (await response.json()) as SharedNotebookApiResponse;
        setNotebook(normalizeSharedNotebook(data));
        setNotFound(false);
        setError("");
      } catch (loadError) {
        console.error("Failed to load shared notebook", loadError);
        setNotebook(null);
        setError("This shared notebook could not be loaded right now.");
      } finally {
        setLoading(false);
      }
    };

    void loadSharedNotebook();
  }, [apiBaseUrl, shareId]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-paper text-white/50">
        <div className="inline-flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading shared notebook...
        </div>
      </div>
    );
  }

  if (!notebook) {
    return (
      <div className="flex h-screen flex-col items-center justify-center bg-paper px-4 text-center">
        <h1 className="text-4xl font-black uppercase tracking-tighter text-ink/20 mb-4">{notFound ? "404" : "Share"}</h1>
        <p className="font-mono text-[10px] uppercase tracking-widest text-ink/50">
          {notFound ? "Shared notebook not found." : error || "Shared notebook could not be loaded."}
        </p>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-paper text-ink px-4 py-4">
      <div className="app-shell-glow" />
      <div className="relative mx-auto max-w-5xl">
        <header className="surface-card rounded-[28px] px-6 py-5 mb-4">
          <div className="flex items-center gap-4">
            <div className="w-11 h-11 rounded-2xl bg-white/[0.04] border border-white/10 flex items-center justify-center">
              <Link2 className="w-5 h-5 text-white" strokeWidth={2.2} />
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.28em] text-white/35 font-medium">Shared notebook</p>
              <h1 className="text-2xl font-semibold tracking-tight text-white">{notebook.title}</h1>
            </div>
          </div>
        </header>

        <section className="surface-card rounded-[28px] p-6">
          <div className="mb-6 flex flex-wrap gap-3">
            <div className="rounded-2xl border border-white/8 bg-white/[0.02] px-4 py-3">
              <div className="text-lg font-semibold tracking-tight text-white">{notebook.sourceCount}</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-white/35">Sources</div>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/[0.02] px-4 py-3">
              <div className="text-lg font-semibold tracking-tight text-white">{notebook.indexedDocumentCount}</div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-white/35">Indexed</div>
            </div>
          </div>

          <div className="space-y-3">
            {notebook.documents.map((document, index) => (
              <article key={`${document.displayTitle}-${index}`} className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-xl bg-white/[0.04] border border-white/10 flex items-center justify-center shrink-0">
                    <FileText className="w-4 h-4 text-white/60" />
                  </div>
                  <div className="min-w-0">
                    <h2 className="text-[14px] font-semibold tracking-tight text-white">{document.displayTitle}</h2>
                    <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-white/35">
                      {document.pageCount > 0 ? `${document.pageCount} pages` : "Document"} · {document.processingStatus}
                    </p>
                    <p className="mt-3 whitespace-pre-wrap text-[13px] leading-6 text-white/75">
                      {document.summary || "No public summary is available for this document yet."}
                    </p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
