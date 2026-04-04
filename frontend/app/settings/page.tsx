"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";

import { updatePasswordSettings, updateProfileSettings, updateThemePreference } from "@/features/auth/api";
import { useAuthSession } from "@/features/auth/useAuthSession";
import { ThemePreference, useTheme } from "@/features/theme/ThemeProvider";

const THEME_OPTIONS: Array<{ value: ThemePreference; label: string; description: string }> = [
  { value: "light", label: "Light", description: "Bright, clean, and paper-like." },
  { value: "dark", label: "Dark", description: "Soft contrast for focused reading." },
  { value: "system", label: "System", description: "Match your device preference." },
];

export default function SettingsPage() {
  const { user, isLoading, refreshSession, signOut } = useAuthSession({ required: true });
  const { theme, setTheme } = useTheme();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [profileError, setProfileError] = useState<string | null>(null);
  const [profileSuccess, setProfileSuccess] = useState<string | null>(null);
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState<string | null>(null);
  const [isSavingPassword, setIsSavingPassword] = useState(false);

  const [themeError, setThemeError] = useState<string | null>(null);
  const [themeSuccess, setThemeSuccess] = useState<string | null>(null);
  const [isSavingTheme, setIsSavingTheme] = useState(false);

  useEffect(() => {
    if (user) {
      setDisplayName(user.displayName ?? "");
      setEmail(user.email);
    }
  }, [user]);

  const selectedTheme = (user?.themePreference ?? theme) as ThemePreference;
  const canSaveProfile =
    user &&
    displayName.trim().length >= 2 &&
    email.trim().length > 0 &&
    (displayName.trim() !== (user.displayName ?? "") || email.trim() !== user.email) &&
    !isSavingProfile;
  const canSavePassword =
    (user?.hasPassword ?? true) &&
    currentPassword.length > 0 &&
    newPassword.length >= 8 &&
    confirmPassword.length >= 8 &&
    !isSavingPassword;

  const handleProfileSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!user || !canSaveProfile) {
      return;
    }

    setProfileError(null);
    setProfileSuccess(null);
    setIsSavingProfile(true);

    try {
      await updateProfileSettings(displayName.trim(), email.trim());
      await refreshSession();
      setProfileSuccess("Profile updated.");
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Profile update failed.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handlePasswordSave = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSavePassword) {
      return;
    }

    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword !== confirmPassword) {
      setPasswordError("New password confirmation does not match.");
      return;
    }

    setIsSavingPassword(true);

    try {
      await updatePasswordSettings(currentPassword, newPassword, confirmPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordSuccess("Password updated.");
    } catch (error) {
      setPasswordError(error instanceof Error ? error.message : "Password update failed.");
    } finally {
      setIsSavingPassword(false);
    }
  };

  const handleThemeChange = async (nextTheme: ThemePreference) => {
    const previousTheme = theme;
    setThemeError(null);
    setThemeSuccess(null);
    setIsSavingTheme(true);
    setTheme(nextTheme);

    try {
      await updateThemePreference(nextTheme);
      await refreshSession();
      setThemeSuccess("Theme updated.");
    } catch (error) {
      setTheme(previousTheme);
      setThemeError(error instanceof Error ? error.message : "Theme update failed.");
    } finally {
      setIsSavingTheme(false);
    }
  };

  const fieldClassName =
    "h-11 w-full border-0 border-b border-border bg-transparent px-0 text-[15px] leading-[1.4] text-ink outline-none transition-colors placeholder:text-[color:var(--theme-placeholder)] hover:border-[color:var(--theme-border-strong)] focus:border-[color:var(--theme-accent)]";

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper text-sm text-[color:var(--theme-text-secondary)]">
        Loading settings...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-paper px-5 py-8 text-ink sm:px-8 lg:px-10 lg:py-10">
      <div className="mr-auto max-w-[1180px]">
        <div className="grid gap-14 lg:grid-cols-[210px_minmax(0,720px)] lg:gap-16">
          <aside className="lg:sticky lg:top-10 lg:self-start">
            <Link
              href="/"
              className="inline-flex items-center gap-2 text-[14px] font-medium text-[color:var(--theme-text-secondary)] transition-colors hover:text-ink"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to library
            </Link>

            <div className="mt-10">
              <h1 className="text-[38px] font-semibold leading-[0.98] tracking-[-0.05em] text-ink">Settings</h1>
              <p className="mt-4 max-w-[190px] text-[14px] leading-[1.7] text-[color:var(--theme-text-secondary)]">
                Account, security, and appearance for your DokuKit workspace.
              </p>
            </div>

            <nav className="mt-12 space-y-4">
              {[
                { href: "#profile", label: "Profile" },
                { href: "#security", label: "Security" },
                { href: "#personalization", label: "Appearance" },
              ].map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="block text-[14px] text-[color:var(--theme-text-secondary)] transition-colors hover:text-ink"
                >
                  {item.label}
                </a>
              ))}
            </nav>

            <div className="mt-12 border-t border-border pt-6">
              <p className="text-[12px] font-medium uppercase tracking-[0.12em] text-[color:var(--theme-text-secondary)]">Signed in as</p>
              <p className="mt-3 text-[14px] leading-[1.6] text-ink">{user.email}</p>
              <button
                type="button"
                onClick={() => void signOut()}
                className="mt-6 inline-flex items-center rounded-[8px] bg-[#111111] px-4 py-2.5 text-[14px] font-medium text-white transition-opacity hover:opacity-93"
              >
                Sign out
              </button>
            </div>
          </aside>

          <main className="pb-12 lg:pt-3">
            <section id="profile" className="grid gap-8 border-t border-border pt-10 lg:grid-cols-[170px_minmax(0,1fr)] lg:gap-12">
              <div>
                <p className="text-[12px] font-medium uppercase tracking-[0.12em] text-[color:var(--theme-text-secondary)]">Profile</p>
              </div>

              <div>
                <h2 className="text-[30px] font-semibold leading-[1.02] tracking-[-0.04em] text-ink">Keep the basics current.</h2>
                <p className="mt-4 max-w-xl text-[15px] leading-[1.78] text-[color:var(--theme-text-secondary)]">
                  Your display name and email appear across the workspace and help keep everything easy to recognize.
                </p>

                <form onSubmit={handleProfileSave} className="mt-14">
                  <div className="grid gap-y-8 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:gap-x-10">
                    <div>
                      <label htmlFor="display-name" className="ds-label">
                        Display name
                      </label>
                      <input
                        id="display-name"
                        type="text"
                        autoComplete="name"
                        value={displayName}
                        onChange={(event) => setDisplayName(event.target.value)}
                        className={fieldClassName}
                        placeholder="Your name"
                        minLength={2}
                        required
                      />
                    </div>

                    <div>
                      <label htmlFor="email" className="ds-label">
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
                  </div>

                  <div className="mt-12 flex flex-wrap items-center gap-x-5 gap-y-3">
                    <button
                      type="submit"
                      disabled={!canSaveProfile}
                      className="inline-flex items-center rounded-[8px] bg-[#111111] px-4 py-2.5 text-[14px] font-medium text-white transition-opacity hover:opacity-93 disabled:cursor-not-allowed disabled:bg-[#111111] disabled:text-white disabled:opacity-100"
                    >
                      {isSavingProfile ? "Saving..." : "Save changes"}
                    </button>

                    {profileError ? <p className="text-[13px] leading-[1.6] text-[color:var(--theme-danger)]">{profileError}</p> : null}
                    {!profileError && profileSuccess ? (
                      <p className="text-[13px] leading-[1.6] text-[color:var(--theme-success)]">{profileSuccess}</p>
                    ) : null}
                  </div>
                </form>
              </div>
            </section>

            <section id="security" className="mt-16 grid gap-8 border-t border-border pt-10 lg:grid-cols-[170px_minmax(0,1fr)] lg:gap-12">
              <div>
                <p className="text-[12px] font-medium uppercase tracking-[0.12em] text-[color:var(--theme-text-secondary)]">Security</p>
              </div>

              <div>
                <h2 className="text-[30px] font-semibold leading-[1.02] tracking-[-0.04em] text-ink">Change your password.</h2>
                <p className="mt-4 max-w-xl text-[15px] leading-[1.78] text-[color:var(--theme-text-secondary)]">
                  Confirm your current password first, then choose a new one that feels safe and easy to remember.
                </p>

                {user.hasPassword === false ? (
                  <div className="mt-12 max-w-xl text-[15px] leading-[1.78] text-[color:var(--theme-text-secondary)]">
                    This account does not currently have a local password to update.
                  </div>
                ) : (
                  <form onSubmit={handlePasswordSave} className="mt-14">
                    <div className="space-y-8">
                      <div className="max-w-[480px]">
                        <label htmlFor="current-password" className="ds-label">
                          Current password
                        </label>
                        <input
                          id="current-password"
                          type="password"
                          autoComplete="current-password"
                          value={currentPassword}
                          onChange={(event) => setCurrentPassword(event.target.value)}
                          className={fieldClassName}
                          placeholder="Enter your current password"
                          required
                        />
                      </div>

                      <div className="grid gap-y-8 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] sm:gap-x-10">
                        <div>
                          <label htmlFor="new-password" className="ds-label">
                            New password
                          </label>
                          <input
                            id="new-password"
                            type="password"
                            autoComplete="new-password"
                            value={newPassword}
                            onChange={(event) => setNewPassword(event.target.value)}
                            className={fieldClassName}
                            placeholder="At least 8 characters"
                            minLength={8}
                            required
                          />
                        </div>

                        <div>
                          <label htmlFor="confirm-password" className="ds-label">
                            Confirm new password
                          </label>
                          <input
                            id="confirm-password"
                            type="password"
                            autoComplete="new-password"
                            value={confirmPassword}
                            onChange={(event) => setConfirmPassword(event.target.value)}
                            className={fieldClassName}
                            placeholder="Repeat your new password"
                            minLength={8}
                            required
                          />
                        </div>
                      </div>
                    </div>

                    <div className="mt-12 flex flex-wrap items-center gap-x-5 gap-y-3">
                      <button
                        type="submit"
                        disabled={!canSavePassword}
                        className="inline-flex items-center rounded-[8px] bg-[#111111] px-4 py-2.5 text-[14px] font-medium text-white transition-opacity hover:opacity-93 disabled:cursor-not-allowed disabled:bg-[#111111] disabled:text-white disabled:opacity-100"
                      >
                        {isSavingPassword ? "Updating..." : "Update password"}
                      </button>

                      {passwordError ? <p className="text-[13px] leading-[1.6] text-[color:var(--theme-danger)]">{passwordError}</p> : null}
                      {!passwordError && passwordSuccess ? (
                        <p className="text-[13px] leading-[1.6] text-[color:var(--theme-success)]">{passwordSuccess}</p>
                      ) : null}
                    </div>
                  </form>
                )}
              </div>
            </section>

            <section
              id="personalization"
              className="mt-16 grid gap-8 border-t border-border pt-10 lg:grid-cols-[170px_minmax(0,1fr)] lg:gap-12"
            >
              <div>
                <p className="text-[12px] font-medium uppercase tracking-[0.12em] text-[color:var(--theme-text-secondary)]">Appearance</p>
              </div>

              <div>
                <div className="max-w-[360px]">
                  <p className="text-[18px] font-medium text-ink">Theme</p>
                  <div
                    role="radiogroup"
                    aria-label="Theme"
                    className="mt-4 inline-flex rounded-[12px] border border-border bg-[color:var(--theme-surface)] p-1"
                  >
                    {THEME_OPTIONS.map((option) => {
                      const active = selectedTheme === option.value;
                      return (
                        <button
                          key={option.value}
                          type="button"
                          role="radio"
                          aria-checked={active}
                          onClick={() => void handleThemeChange(option.value)}
                          disabled={isSavingTheme}
                          className={`min-w-[92px] rounded-[9px] px-4 py-2.5 text-[14px] font-medium transition-colors disabled:opacity-60 ${
                            active
                              ? "bg-[color:var(--theme-ink)] text-[color:var(--theme-paper)]"
                              : "text-[color:var(--theme-text-secondary)] hover:bg-[color:var(--theme-surface-muted)] hover:text-ink"
                          }`}
                        >
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-3 text-[14px] leading-[1.68] text-[color:var(--theme-text-secondary)]">
                    Choose how DokuKit looks.
                  </p>
                </div>

                <div className="mt-6 min-h-[20px]">
                  {themeError ? <p className="text-[13px] leading-[1.6] text-[color:var(--theme-danger)]">{themeError}</p> : null}
                  {!themeError && themeSuccess ? <p className="text-[13px] leading-[1.6] text-[color:var(--theme-success)]">{themeSuccess}</p> : null}
                </div>
              </div>
            </section>
          </main>
        </div>
      </div>
    </div>
  );
}
