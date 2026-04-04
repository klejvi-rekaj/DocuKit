import test from "node:test";
import assert from "node:assert/strict";

function normalizeNotebook(raw, index) {
  return {
    id: raw.id,
    title: raw.title,
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
    })) ?? [],
  };
}

function removeNotebookFromState(notebooks, notebookId) {
  return notebooks.filter((notebook) => notebook.id !== notebookId);
}

test("backend notebook payload drives readiness state", () => {
  const notebook = normalizeNotebook(
    {
      id: "nb-1",
      title: "Backend truth",
      documents: [
        {
          id: "doc-1",
          notebook_id: "nb-1",
          original_filename: "paper.pdf",
          display_title: "Paper",
          processing_status: "processing",
        },
        {
          id: "doc-2",
          notebook_id: "nb-1",
          original_filename: "appendix.pdf",
          display_title: "Appendix",
          processing_status: "indexed",
        },
      ],
    },
    0,
  );

  assert.equal(notebook.readyForQuery, true);
  assert.equal(notebook.indexedDocumentCount, 1);
  assert.equal(notebook.pendingDocumentCount, 1);
  assert.equal(notebook.fileIds.length, 2);
});

test("deleted backend notebook is removed from UI state", () => {
  const notebooks = [
    { id: "nb-a", title: "A" },
    { id: "nb-b", title: "B" },
  ];

  assert.deepEqual(removeNotebookFromState(notebooks, "nb-a"), [{ id: "nb-b", title: "B" }]);
});
