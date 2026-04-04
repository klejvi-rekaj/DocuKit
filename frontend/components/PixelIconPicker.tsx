"use client";

import { PixelAssetDefinition, pixelIconOptions } from "@/lib/pixelAssetRegistry";
import { cn } from "@/lib/utils";

interface PixelIconPickerProps {
  selectedKey: string;
  onSelect: (iconKey: string) => void;
  className?: string;
  options?: PixelAssetDefinition[];
  showLabels?: boolean;
}

export function PixelIconPicker({
  selectedKey,
  onSelect,
  className,
  options = pixelIconOptions,
  showLabels = true,
}: PixelIconPickerProps) {
  return (
    <div className={cn("grid grid-cols-4 gap-3 sm:grid-cols-6", className)}>
      {options.map((icon) => {
        const isSelected = selectedKey === icon.key;

        return (
          <button
            key={icon.key}
            type="button"
            onClick={() => onSelect(icon.key)}
            aria-pressed={isSelected}
            className={cn(
              "flex min-w-0 flex-col items-center justify-start gap-2 rounded-[12px] px-2.5 py-2.5 text-center transition-all duration-150 ease-out",
              isSelected ? "scale-[1.04] bg-[color:var(--theme-accent-soft)]" : "hover:bg-[color:var(--theme-surface-muted)]",
            )}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={icon.src} alt={icon.label} width={32} height={32} className="pixel-icon h-8 w-8 object-contain" />
            {showLabels ? (
              <span className="truncate text-[12px] font-medium leading-[1.2] text-[color:var(--theme-text-secondary)]">{icon.label}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
