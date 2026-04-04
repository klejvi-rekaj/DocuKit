"use client";

import { Trash2 } from "lucide-react";

import { getPixelAsset } from "@/lib/pixelAssetRegistry";
import { Notebook } from "@/lib/types";

interface NotebookFolderCardProps {
  notebook: Notebook;
  onOpen: () => void;
  onDelete: () => void;
  onChangeIcon: () => void;
}

export function NotebookFolderCard({ notebook, onOpen, onDelete, onChangeIcon }: NotebookFolderCardProps) {
  const asset = getPixelAsset(notebook.iconKey) ?? {
    key: "fallback",
    label: "Notebook",
    src: "/notebook-icons/robot.png",
  };

  return (
    <article
      className="group cursor-pointer select-none transition-transform duration-200 ease-out hover:-translate-y-[5px] hover:scale-[1.015] active:translate-y-0 active:scale-[1.005]"
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(event) => event.key === "Enter" && onOpen()}
    >
      <div className="folder-tab mb-1 ml-5 h-[18px] w-24" />
      <div className="folder-body flex h-[232px] flex-col overflow-hidden rounded-[18px] px-6 pb-6 pt-5 transition-[transform,box-shadow,background-color,border-color,filter] duration-200 group-hover:[filter:brightness(1.04)]">
        <div className="mb-4 flex items-start justify-between gap-3">
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onChangeIcon();
            }}
            className="shrink-0 cursor-pointer p-0 transition-transform duration-200 hover:scale-[1.04]"
            aria-label={`Change icon for ${notebook.title}`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={asset.src}
              alt={asset.label}
              width={88}
              height={88}
              className="pixel-icon block h-[88px] w-[88px] object-contain"
            />
          </button>

          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation();
              onDelete();
            }}
            className="relative z-10 cursor-pointer rounded-full p-2 text-[color:var(--theme-text-secondary)] transition-colors duration-200 hover:bg-[color:var(--theme-accent-soft)] hover:text-ink"
            aria-label={`Delete ${notebook.title}`}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>

        <h3 className="min-h-[3.3rem] overflow-hidden break-words text-[23px] font-semibold leading-[1.18] tracking-[-0.03em] text-ink">
          {notebook.title}
        </h3>

        <p className="mt-auto overflow-hidden text-ellipsis whitespace-nowrap text-[12px] font-medium text-[color:var(--theme-text-secondary)]">
          {notebook.sourceCount} sources
          {notebook.dateLabel ? ` / ${notebook.dateLabel}` : ""}
        </p>
      </div>
    </article>
  );
}
