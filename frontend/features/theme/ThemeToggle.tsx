"use client";

import { LaptopMinimal, Moon, SunMedium } from "lucide-react";

import { ThemePreference, useTheme } from "@/features/theme/ThemeProvider";
import { cn } from "@/lib/utils";

const OPTIONS: Array<{
  value: ThemePreference;
  label: string;
  icon: typeof SunMedium;
}> = [
  { value: "light", label: "Light", icon: SunMedium },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: LaptopMinimal },
];

interface ThemeToggleProps {
  className?: string;
  compact?: boolean;
}

export function ThemeToggle({ className, compact = false }: ThemeToggleProps) {
  const { theme, setTheme } = useTheme();

  return (
    <div
      className={cn(
        "theme-toggle-shell inline-flex items-center gap-1 rounded-full p-1",
        compact ? "scale-[0.96]" : "",
        className,
      )}
      role="group"
      aria-label="Theme switcher"
    >
      {OPTIONS.map((option) => {
        const Icon = option.icon;
        const selected = theme === option.value;

        return (
          <button
            key={option.value}
            type="button"
            onClick={() => setTheme(option.value)}
            className={cn("theme-toggle-button", selected && "theme-toggle-button-active")}
            aria-pressed={selected}
            aria-label={`Use ${option.label.toLowerCase()} theme`}
            title={option.label}
          >
            <Icon className="h-3.5 w-3.5" />
            {!compact ? <span>{option.label}</span> : null}
          </button>
        );
      })}
    </div>
  );
}
