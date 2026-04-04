"use client";

import { useRef, useState } from "react";
import { File as FileIcon, Loader2, Upload, X } from "lucide-react";

import { PixelIconPicker } from "@/components/PixelIconPicker";
import { AppButton } from "@/components/ui/AppButton";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { getPixelAsset, studyPixelIconOptions } from "@/lib/pixelAssetRegistry";
import { Notebook } from "@/lib/types";

const DEFAULT_ICON_KEY = "pixel_heart";

interface CreateNotebookModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (files: File[], iconKey: string) => Promise<Notebook | void>;
  isCreating: boolean;
}

export function CreateNotebookModal({
  isOpen,
  onClose,
  onCreate,
  isCreating,
}: CreateNotebookModalProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [iconKey, setIconKey] = useState(DEFAULT_ICON_KEY);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const selectedIcon = getPixelAsset(iconKey) ?? {
    key: "fallback",
    label: "Notebook",
    src: "/notebook-icons/pixel-heart.png",
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setIsDragging(true);
    } else if (e.type === "dragleave") {
      setIsDragging(false);
    }
  };

  const addIncomingFiles = (incoming: FileList | null) => {
    if (!incoming) return;
    const newFiles = Array.from(incoming).filter((file) => file.type === "application/pdf");
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    addIncomingFiles(e.dataTransfer.files);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    addIncomingFiles(e.target.files);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  const resetAndClose = () => {
    setFiles([]);
    setIconKey(DEFAULT_ICON_KEY);
    setIsDragging(false);
    onClose();
  };

  const handleCreate = async () => {
    if (files.length === 0) return;
    try {
      await onCreate(files, iconKey);
      resetAndClose();
    } catch (error) {
      console.error("Failed to create notebook", error);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && resetAndClose()}>
      <DialogContent
        className="w-[min(96vw,1040px)] max-w-[1040px] overflow-hidden p-0"
        onCloseAutoFocus={(event) => event.preventDefault()}
      >
        <div className="grid max-h-[88vh] min-h-0 lg:grid-cols-[260px_minmax(0,1fr)]">
          <aside className="hidden min-h-full border-r border-border bg-[color:var(--theme-surface-tint)] px-7 py-7 lg:flex lg:flex-col">

            <div className="mt-8">
              <div className="folder-tab mb-1 ml-4 h-[18px] w-24" />
              <div className="folder-body rounded-[18px] px-6 py-6">
                <div className="flex h-[68px] w-[68px] items-center justify-center">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={selectedIcon.src} alt={selectedIcon.label} width={52} height={52} className="pixel-icon h-[52px] w-[52px] object-contain" />
                </div>
                <h3 className="mt-5 text-[26px] font-semibold leading-[1.02] tracking-[-0.04em] text-ink">
                  Untitled notebook
                </h3>
                <p className="mt-3 text-sm leading-[1.6] text-[color:var(--theme-text-secondary)]">
                  Drop in your course material and start a clean notebook right away.
                </p>
              </div>
            </div>
          </aside>

          <div className="flex min-h-0 flex-col bg-surface">
            <DialogHeader className="border-b border-border px-8 pb-5 pt-7">
              <DialogTitle className="text-[34px] font-semibold tracking-[-0.05em]">Create new notebook</DialogTitle>
              <DialogDescription className="max-w-2xl text-[16px] leading-[1.6]">
                Upload your sources, then choose an icon to represent it in your library.
              </DialogDescription>
            </DialogHeader>

            <div className="min-h-0 flex-1 overflow-y-auto px-8 py-8">
              <div className="mx-auto max-w-[720px]">
                <section>
                  <div
                    className={`relative overflow-hidden rounded-[18px] px-8 py-10 transition-all duration-200 ${
                      isDragging
                        ? "bg-[color:var(--theme-accent-soft)] shadow-[inset_0_0_0_1px_var(--theme-accent)]"
                        : "bg-[color:var(--theme-surface-blue)] shadow-[inset_0_0_0_1px_var(--theme-border)]"
                    }`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                  >
                    <input
                      ref={fileInputRef}
                      id="create-notebook-files"
                      type="file"
                      multiple
                      accept=".pdf"
                      className="hidden"
                      onChange={handleFileChange}
                      disabled={isCreating}
                    />

                    <div className="text-center">
                      <p className="text-[24px] font-semibold tracking-[-0.03em] text-ink">drop your files</p>
                      <p className="mt-2 text-sm leading-[1.6] text-[color:var(--theme-text-secondary)]">PDF only for now. Everything you add becomes part of this notebook.</p>

                      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                        <button
                          type="button"
                          onClick={openFilePicker}
                          disabled={isCreating}
                          className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2.5 text-[14px] font-medium text-ink transition-colors hover:bg-[color:var(--theme-surface-muted)] disabled:opacity-50"
                        >
                          <Upload className="h-4 w-4" />
                          Upload files
                        </button>
                      </div>

                      {files.length > 0 ? (
                        <p className="mt-5 text-[13px] font-medium text-[color:var(--theme-success)]">
                          {files.length} PDF{files.length === 1 ? "" : "s"} added
                        </p>
                      ) : null}
                    </div>
                  </div>

                  {files.length > 0 ? (
                    <div className="mt-5 space-y-2">
                      {files.map((file, index) => (
                        <div key={`${file.name}-${index}`} className="theme-soft-row flex items-center justify-between rounded-[12px] px-3 py-3">
                          <div className="min-w-0 flex items-center gap-3">
                            <div className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-surface">
                              <FileIcon className="h-4 w-4 text-[color:var(--theme-text-secondary)]" strokeWidth={1.75} />
                            </div>
                            <span className="truncate text-[14px] font-medium text-ink">{file.name}</span>
                          </div>
                          <button
                            onClick={() => removeFile(index)}
                            className="rounded-[10px] p-2 text-[color:var(--theme-text-muted)] transition-colors hover:bg-[color:var(--theme-accent-soft)] hover:text-ink"
                            disabled={isCreating}
                            type="button"
                            aria-label={`Remove ${file.name}`}
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </section>

                <section className="mt-8">
                  <div>
                    <div>
                      <p className="ds-section-title">Choose an icon</p>
                      <p className="mt-2 text-sm leading-[1.6] text-[color:var(--theme-text-secondary)]">
                        Pick one clean icon for the folder.
                      </p>
                    </div>
                  </div>

                  <div className="mt-5">
                    <PixelIconPicker
                      selectedKey={iconKey}
                      onSelect={setIconKey}
                      options={studyPixelIconOptions}
                      showLabels={false}
                      className="grid-cols-4 gap-x-4 gap-y-3 sm:grid-cols-6"
                    />
                  </div>
                </section>
              </div>
            </div>

            <DialogFooter className="border-t border-border px-8 py-5 sm:justify-between">
              <AppButton onClick={resetAndClose} variant="secondary" disabled={isCreating}>
                Cancel
              </AppButton>
              <AppButton onClick={handleCreate} disabled={files.length === 0 || isCreating} variant="primary">
                {isCreating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Loading notebook...</span>
                  </>
                ) : (
                  "Create notebook"
                )}
              </AppButton>
            </DialogFooter>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
