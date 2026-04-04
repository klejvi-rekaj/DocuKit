"use client";

import { AuthSession } from "@/lib/types";
import { ThemePreference } from "@/features/theme/ThemeProvider";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface AuthSessionResponse {
  authenticated: boolean;
  user?: {
    id: string;
    email: string;
    display_name?: string | null;
    theme_preference?: ThemePreference | null;
    has_password?: boolean;
  } | null;
}

function mapSession(data: AuthSessionResponse): AuthSession {
  return {
    authenticated: data.authenticated,
    user: data.user
      ? {
          id: data.user.id,
          email: data.user.email,
          displayName: data.user.display_name ?? null,
          themePreference: data.user.theme_preference ?? null,
          hasPassword: data.user.has_password ?? false,
        }
      : null,
  };
}

async function parseError(response: Response, fallback: string, options?: { unauthorizedMessage?: string }): Promise<Error> {
  const errorData = await response.json().catch(() => ({ detail: fallback }));

  if (response.status >= 500) {
    return new Error("Something went wrong on our side. Please try again in a moment.");
  }

  if (response.status === 401) {
    return new Error(options?.unauthorizedMessage || "That email and password combination didn't match.");
  }

  if (response.status === 409) {
    return new Error("An account with that email already exists.");
  }

  return new Error(errorData.detail || fallback);
}

function normalizeFetchError(error: unknown): never {
  if (error instanceof Error && error.name === "TypeError") {
    throw new Error("Could not reach the server. Make sure the backend is running and try again.");
  }

  if (error instanceof Error) {
    throw error;
  }

  throw new Error("Something unexpected happened. Please try again.");
}

export function sanitizeRedirectPath(input: string | null | undefined): string {
  if (!input) {
    return "/";
  }

  if (!input.startsWith("/") || input.startsWith("//")) {
    return "/";
  }

  return input;
}

export async function fetchAuthSession(): Promise<AuthSession> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/auth/session`, {
      cache: "no-store",
      credentials: "include",
    });

    if (!response.ok) {
      throw await parseError(response, `Failed to load session (${response.status})`, {
        unauthorizedMessage: "Your session has expired. Please sign in again.",
      });
    }

    return mapSession((await response.json()) as AuthSessionResponse);
  } catch (error) {
    normalizeFetchError(error);
  }
}

export async function signInWithPassword(email: string, password: string): Promise<AuthSession> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/auth/sign-in`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      throw await parseError(response, "Sign in failed.");
    }

    return mapSession((await response.json()) as AuthSessionResponse);
  } catch (error) {
    normalizeFetchError(error);
  }
}

export async function signUpWithPassword(name: string, email: string, password: string): Promise<AuthSession> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/auth/sign-up`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name, email, password }),
    });

    if (!response.ok) {
      throw await parseError(response, "Sign up failed.");
    }

    return mapSession((await response.json()) as AuthSessionResponse);
  } catch (error) {
    normalizeFetchError(error);
  }
}

export async function signOutOfSession(): Promise<void> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/auth/sign-out`, {
      method: "POST",
      credentials: "include",
    });

    if (!response.ok) {
      throw await parseError(response, "Sign out failed.");
    }
  } catch (error) {
    normalizeFetchError(error);
  }
}

export async function updateProfileSettings(displayName: string, email: string): Promise<AuthSession> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/auth/profile`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ display_name: displayName, email }),
    });

    if (!response.ok) {
      throw await parseError(response, "Profile update failed.", {
        unauthorizedMessage: "Your session has expired. Please sign in again.",
      });
    }

    return mapSession((await response.json()) as AuthSessionResponse);
  } catch (error) {
    normalizeFetchError(error);
  }
}

export async function updatePasswordSettings(currentPassword: string, newPassword: string, confirmPassword: string): Promise<void> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/auth/change-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });

    if (!response.ok) {
      throw await parseError(response, "Password update failed.", {
        unauthorizedMessage: "Your session has expired. Please sign in again.",
      });
    }
  } catch (error) {
    normalizeFetchError(error);
  }
}

export async function updateThemePreference(themePreference: ThemePreference): Promise<AuthSession> {
  try {
    const response = await fetch(`${apiBaseUrl}/api/auth/preferences/theme`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ theme_preference: themePreference }),
    });

    if (!response.ok) {
      throw await parseError(response, "Theme update failed.", {
        unauthorizedMessage: "Your session has expired. Please sign in again.",
      });
    }

    return mapSession((await response.json()) as AuthSessionResponse);
  } catch (error) {
    normalizeFetchError(error);
  }
}
