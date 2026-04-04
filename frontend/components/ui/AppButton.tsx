"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

type AppButtonVariant = "primary" | "secondary";

export interface AppButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: AppButtonVariant;
}

export const AppButton = React.forwardRef<HTMLButtonElement, AppButtonProps>(function AppButton(
  { className, variant = "secondary", type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "ds-button disabled:pointer-events-none disabled:opacity-45",
        variant === "primary" ? "ds-button-primary" : "ds-button-secondary",
        className,
      )}
      {...props}
    />
  );
});
