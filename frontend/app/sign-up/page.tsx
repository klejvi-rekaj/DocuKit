"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AuthPageFrame } from "@/features/auth/AuthPageFrame";
import { signUpWithPassword } from "@/features/auth/api";
import { useAuthSession } from "@/features/auth/useAuthSession";

export default function SignUpPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { isLoading } = useAuthSession({ redirectIfAuthenticated: true });
  const trimmedName = name.trim();
  const trimmedEmail = email.trim();
  const canSubmit = trimmedName.length > 0 && trimmedEmail.length > 0 && password.length >= 8 && !isSubmitting;
  const fieldClassName =
    "h-13 w-full rounded-[12px] border border-border bg-[color:var(--theme-surface)] px-3.5 text-[16px] text-ink outline-none transition-colors placeholder:text-[color:var(--theme-placeholder)] hover:border-[color:var(--theme-border-strong)] focus:border-[color:var(--theme-border-strong)]";

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await signUpWithPassword(name.trim(), email.trim(), password);
      router.replace("/");
    } catch (submitError) {
      const message = submitError instanceof Error ? submitError.message : "Sign up failed.";
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
      title="Create your account"
      description="Start a private study space for your files, answers, and notes."
      footer={
        <p>
          Already have an account?{" "}
          <Link href="/sign-in" className="font-medium text-ink underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="name" className="mb-2 block text-[13px] font-medium text-[color:var(--theme-assistant-text)]">
            Name
          </label>
          <input
            id="name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            className={fieldClassName}
            placeholder="Your name"
            minLength={2}
            required
          />
        </div>

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
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className={fieldClassName}
            placeholder="At least 8 characters"
            minLength={8}
            required
          />
        </div>

        {password.length > 0 && password.length < 8 ? (
          <p className="text-[13px] leading-[1.6] text-[color:var(--theme-danger)]">Choose a password with at least 8 characters.</p>
        ) : null}

        {error ? <p className="text-[14px] leading-[1.6] text-[color:var(--theme-danger)]">{error}</p> : null}

        <button
          type="submit"
          disabled={!canSubmit}
          className="inline-flex h-13 w-full items-center justify-center rounded-[12px] bg-[#111111] px-4 text-[16px] font-semibold text-white transition-opacity hover:opacity-93 disabled:cursor-not-allowed disabled:bg-[#111111] disabled:text-white disabled:opacity-100"
        >
          {isSubmitting ? "Creating account..." : "Create account"}
        </button>
      </form>
    </AuthPageFrame>
  );
}
