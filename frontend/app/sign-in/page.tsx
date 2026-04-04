"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { AuthPageFrame } from "@/features/auth/AuthPageFrame";
import { sanitizeRedirectPath, signInWithPassword } from "@/features/auth/api";
import { useAuthSession } from "@/features/auth/useAuthSession";

export default function SignInPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { isLoading } = useAuthSession({ redirectIfAuthenticated: true });
  const trimmedEmail = email.trim();
  const canSubmit = trimmedEmail.length > 0 && password.length > 0 && !isSubmitting;
  const fieldClassName =
    "h-13 w-full rounded-[12px] border border-border bg-[color:var(--theme-surface)] px-3.5 text-[16px] text-ink outline-none transition-colors placeholder:text-[color:var(--theme-placeholder)] hover:border-[color:var(--theme-border-strong)] focus:border-[color:var(--theme-border-strong)]";

  const nextPath = useMemo(() => sanitizeRedirectPath(searchParams.get("next")), [searchParams]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await signInWithPassword(email.trim(), password);
      router.replace(nextPath);
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Sign in failed.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-paper text-sm text-[color:var(--theme-text-secondary)]">Loading...</div>;
  }

  return (
    <AuthPageFrame
      title="Welcome back"
      description="Continue to your notebooks, chats, and saved notes."
      footer={
        <p>
          New to DokuKit?{" "}
          <Link href="/sign-up" className="font-medium text-ink underline-offset-4 hover:underline">
            Create an account
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="email" className="mb-2 block text-[13px] font-medium text-[color:var(--theme-assistant-text)]">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className={fieldClassName}
            placeholder="you@example.com"
            inputMode="email"
            required
          />
        </div>

        <div>
          <label htmlFor="password" className="mb-2 block text-[13px] font-medium text-[color:var(--theme-assistant-text)]">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={fieldClassName}
            placeholder="Enter your password"
            minLength={8}
            required
          />
        </div>

        {password.length > 0 && password.length < 8 ? (
          <p className="text-[13px] leading-[1.6] text-[color:var(--theme-danger)]">Passwords must be at least 8 characters.</p>
        ) : null}

        {error ? <p className="text-[14px] leading-[1.6] text-[color:var(--theme-danger)]">{error}</p> : null}

        <button
          type="submit"
          disabled={!canSubmit || password.length < 8}
          className="inline-flex h-13 w-full items-center justify-center rounded-[12px] bg-[#111111] px-4 text-[16px] font-semibold text-white transition-opacity hover:opacity-93 disabled:cursor-not-allowed disabled:bg-[#111111] disabled:text-white disabled:opacity-100"
        >
          {isSubmitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </AuthPageFrame>
  );
}
