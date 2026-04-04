"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { fetchAuthSession, signOutOfSession } from "@/features/auth/api";
import { useTheme } from "@/features/theme/ThemeProvider";
import { AuthUser } from "@/lib/types";

interface UseAuthSessionOptions {
  required?: boolean;
  redirectIfAuthenticated?: boolean;
  authenticatedRedirectTo?: string;
}

export function useAuthSession(options: UseAuthSessionOptions = {}) {
  const {
    required = false,
    redirectIfAuthenticated = false,
    authenticatedRedirectTo = "/",
  } = options;
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { theme, setTheme } = useTheme();
  const themeRef = useRef(theme);

  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);

  const currentPath = useMemo(() => {
    const queryString = searchParams.toString();
    return queryString ? `${pathname}?${queryString}` : pathname;
  }, [pathname, searchParams]);

  const refreshSession = useCallback(async () => {
    setIsLoading(true);
    try {
      const session = await fetchAuthSession();
      setUser(session.user);
      if (session.user?.themePreference && session.user.themePreference !== themeRef.current) {
        setTheme(session.user.themePreference);
      }
      return session.user;
    } catch (error) {
      console.error("Failed to load auth session", error);
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [setTheme]);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  useEffect(() => {
    if (isLoading) {
      return;
    }

    if (required && !user) {
      router.replace(`/sign-in?next=${encodeURIComponent(currentPath)}`);
      return;
    }

    if (redirectIfAuthenticated && user) {
      router.replace(authenticatedRedirectTo);
    }
  }, [authenticatedRedirectTo, currentPath, isLoading, redirectIfAuthenticated, required, router, user]);

  const signOut = useCallback(async () => {
    await signOutOfSession();
    setUser(null);
    router.replace("/sign-in");
  }, [router]);

  return {
    user,
    isLoading,
    refreshSession,
    signOut,
  };
}
