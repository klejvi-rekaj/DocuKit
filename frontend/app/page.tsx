"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";

import { CreateNotebookModal } from "@/components/CreateNotebookModal";
import { NotebookFolderCard } from "@/components/NotebookFolderCard";
import { PixelIconPicker } from "@/components/PixelIconPicker";
import { AppButton } from "@/components/ui/AppButton";
import { useAuthSession } from "@/features/auth/useAuthSession";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useNotebooks } from "@/hooks/useNotebooks";
import { studyPixelIconOptions } from "@/lib/pixelAssetRegistry";
import { Notebook } from "@/lib/types";
import { AuthUser } from "@/lib/types";

function getTimeWelcome(date = new Date()) {
  const hour = date.getHours();

  if (hour < 12) {
    return {
      heading: "Good morning,",
      message: "Upload a PDF or ask a question to get started.",
    };
  }

  if (hour < 18) {
    return {
      heading: "Good afternoon,",
      message: "Drop in a PDF or continue a notebook from earlier today.",
    };
  }

  return {
    heading: "Good evening,",
    message: "Upload a PDF or ask a question to keep your research moving.",
  };
}

function getFirstName(user: AuthUser) {
  const trimmedName = user.displayName?.trim();
  if (trimmedName) {
    return trimmedName.split(/\s+/)[0];
  }

  const emailName = user.email.split("@")[0]?.trim();
  if (emailName) {
    return emailName;
  }

  return "there";
}

export default function Home() {
  const { user, isLoading: authLoading, signOut } = useAuthSession({ required: true });

  if (authLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-paper text-sm text-[color:var(--theme-text-secondary)]">Loading...</div>;
  }

  if (!user) {
    return null;
  }

  return <AuthenticatedHome user={user} onSignOut={signOut} />;
}

function AuthenticatedHome({ user, onSignOut }: { user: AuthUser; onSignOut: () => Promise<void> }) {
  const router = useRouter();
  const { notebooks, createNotebook, deleteNotebook, updateNotebookIcon, isCreating } = useNotebooks();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Notebook | null>(null);
  const [iconEditingNotebook, setIconEditingNotebook] = useState<Notebook | null>(null);
  const welcome = getTimeWelcome();
  const firstName = getFirstName(user);

  const handleCreate = async (files: File[], iconKey: string) => {
    try {
      const notebook = await createNotebook(files, iconKey);
      router.push(`/notebook/${notebook.id}`);
    } catch (error) {
      console.error("Failed to create notebook:", error);
    }
  };

  const confirmDelete = () => {
    if (!pendingDelete) return;
    deleteNotebook(pendingDelete.id).catch((error) => {
      console.error("Failed to delete notebook", error);
    });
    setPendingDelete(null);
  };

  const handleChangeIcon = async (iconKey: string) => {
    if (!iconEditingNotebook) return;
    try {
      await updateNotebookIcon(iconEditingNotebook.id, iconKey);
      setIconEditingNotebook(null);
    } catch (error) {
      console.error("Failed to update notebook icon", error);
    }
  };

  return (
    <div className="relative min-h-screen overflow-y-auto overflow-x-hidden bg-paper text-ink">
      <div className="mx-auto max-w-[1280px] px-6 py-6 lg:px-10 lg:py-7">
        <header className="border-b border-border/80 pb-5">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div className="max-w-3xl">
              <Link
                href="/"
                className="inline-flex items-center gap-3 transition duration-150 hover:scale-[1.03] hover:opacity-85"
                aria-label="Go to notebook library"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/staryellow.png" alt="DokuKit" className="h-[58px] w-auto object-contain" />
                <span className="text-[34px] leading-none text-[color:var(--theme-logo)] [font-family:var(--font-logo)]">
                  DokuKit
                </span>
              </Link>

              <h1 className="mt-4 max-w-3xl text-[40px] leading-[0.95] tracking-[-0.06em] text-ink lg:text-[60px]">
                {welcome.heading} {firstName}.
              </h1>
              <p className="mt-4 max-w-2xl text-[18px] leading-[1.5] text-[color:var(--theme-text-secondary)] lg:text-[22px]">
                {welcome.message}
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => setIsModalOpen(true)}
                className="inline-flex items-center gap-2 rounded-[10px] bg-[color:var(--theme-surface-muted)] px-3.5 py-2.5 text-[14px] font-medium text-ink transition-colors hover:bg-[color:var(--theme-accent-soft)]"
              >
                New notebook
              </button>
              <Link href="/settings">
                <AppButton className="px-3 py-2.5" variant="secondary">
                  <span>Settings</span>
                </AppButton>
              </Link>
              <AppButton onClick={() => void onSignOut()} className="px-3 py-2.5" variant="secondary">
                <span>Sign out</span>
              </AppButton>
            </div>
          </div>
        </header>

        <section className="pt-10">
          <div className="mb-8">
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
              className="group w-full max-w-[360px] text-left"
            >
              <div className="folder-tab mb-1 ml-5 h-[18px] w-24" />
              <div className="folder-body flex h-[232px] flex-col overflow-hidden rounded-[18px] border-dashed px-6 pb-6 pt-5 transition-all duration-200 group-hover:-translate-y-[5px] group-hover:scale-[1.015] group-hover:[filter:brightness(1.035)]">
                <div className="mb-4 flex items-start justify-between">
                  <div className="flex h-[88px] w-[88px] items-center justify-center text-ink/76">
                    <Plus className="h-14 w-14" strokeWidth={1.8} />
                  </div>
                </div>
                <h2 className="overflow-hidden text-[23px] font-semibold leading-[1.08] tracking-[-0.03em] text-ink [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2]">
                  Create a new notebook
                </h2>
                <p className="mt-auto overflow-hidden text-ellipsis whitespace-nowrap text-[12px] font-medium text-[color:var(--theme-text-secondary)]">
                  Add PDFs and start studying
                </p>
              </div>
            </button>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {notebooks.map((notebook) => (
              <NotebookFolderCard
                key={notebook.id}
                notebook={notebook}
                onOpen={() => router.push(`/notebook/${notebook.id}`)}
                onDelete={() => setPendingDelete(notebook)}
                onChangeIcon={() => setIconEditingNotebook(notebook)}
              />
            ))}
          </div>
        </section>

        <footer className="mt-14 border-t border-border/70 pt-6 pb-8">
          <p className="mx-auto max-w-3xl text-center text-[13px] leading-[1.75] text-[color:var(--theme-text-secondary)]">
            Your data stays yours. We do not use your notebooks or documents to train our models. Only feedback you
            explicitly share may be used to improve the product.
          </p>
        </footer>
      </div>

      <CreateNotebookModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreate={handleCreate}
        isCreating={isCreating}
      />

      <Dialog open={Boolean(pendingDelete)} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader className="p-2">
            <DialogTitle className="text-2xl font-semibold tracking-tight">Delete notebook</DialogTitle>
            <DialogDescription>
              {pendingDelete ? `Delete "${pendingDelete.title}"? This removes the folder from your workspace.` : "Delete this notebook?"}
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-4 flex items-center gap-4 sm:justify-between">
            <AppButton onClick={() => setPendingDelete(null)} variant="secondary">
              Cancel
            </AppButton>
            <AppButton onClick={confirmDelete} className="bg-[color:var(--theme-ink)] text-[color:var(--theme-paper)] hover:opacity-92" variant="primary">
              Delete
            </AppButton>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(iconEditingNotebook)} onOpenChange={(open) => !open && setIconEditingNotebook(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader className="p-2">
            <DialogTitle className="text-2xl font-semibold tracking-tight">Choose icon</DialogTitle>
            <DialogDescription>
              Pick one pixel icon for {iconEditingNotebook ? `"${iconEditingNotebook.title}"` : "this notebook"}.
            </DialogDescription>
          </DialogHeader>
          <div className="px-2 py-3">
            <PixelIconPicker selectedKey={iconEditingNotebook?.iconKey ?? "folder"} onSelect={handleChangeIcon} options={studyPixelIconOptions} showLabels={false} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
