"use client";

import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { AlertCircle, ArrowUp, Bookmark, Copy, Loader2, Square } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { NotebookDocument } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  retrieval_metadata?: {
    status?: "streaming" | "complete" | string;
    [key: string]: unknown;
  } | null;
}

interface NoteSaveState {
  status: "idle" | "saving" | "saved" | "error";
  error?: string;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Unknown error";
}

function getEmptyGreeting(date = new Date()) {
  const hour = date.getHours();

  if (hour >= 5 && hour < 12) {
    return "It's a quiet morning";
  }

  if (hour >= 12 && hour < 18) {
    return "Good afternoon";
  }

  if (hour >= 18 && hour < 23) {
    return "Good evening";
  }

  return "Still up?";
}

interface ChatStreamProps {
  fileIds: string[];
  notebookId?: string;
  documents?: NotebookDocument[];
  onNoteSaved?: () => void | Promise<void>;
}

export default function ChatStream({ fileIds, notebookId, documents = [], onNoteSaved }: ChatStreamProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [copiedMessageIndex, setCopiedMessageIndex] = useState<number | null>(null);
  const [noteSaveStates, setNoteSaveStates] = useState<Record<number, NoteSaveState>>({});
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const stopRequestedRef = useRef(false);
  const hasInitialScrollRef = useRef(false);
  const shouldStickToBottomRef = useRef(true);
  const copyResetTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const noteResetTimeoutsRef = useRef<Record<number, ReturnType<typeof setTimeout>>>({});
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const indexedDocuments = documents.filter((document) => document.processingStatus === "indexed");
  const pendingDocuments = documents.filter((document) => ["uploaded", "processing"].includes(document.processingStatus));
  const failedDocuments = documents.filter((document) => document.processingStatus === "failed");
  const hasReadyDocuments = indexedDocuments.length > 0;
  const isEmptyState = messages.length === 0;
  const greeting = getEmptyGreeting();
  const latestMessage = messages[messages.length - 1];
  const hasRemoteStreamingMessage =
    !isLoading &&
    latestMessage?.role === "assistant" &&
    latestMessage.retrieval_metadata?.status === "streaming";
  const isGenerating = isLoading || hasRemoteStreamingMessage;

  const isNearBottom = (container: HTMLDivElement) => {
    const threshold = 120;
    return container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;
  };

  const loadHistoryFromServer = useCallback(async () => {
    if (!notebookId) {
      setMessages([]);
      return;
    }

    const response = await fetch(`${apiBaseUrl}/api/query/history/${notebookId}`, {
      cache: "no-store",
      credentials: "include",
    });
    if (!response.ok) {
      throw new Error(`History request failed: ${response.status}`);
    }

    const data = await response.json();
    if (Array.isArray(data.messages)) {
      setMessages(data.messages);
      return;
    }

    setMessages([]);
  }, [apiBaseUrl, notebookId]);

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTo({
        top: messagesContainerRef.current.scrollHeight,
        behavior,
      });
      return;
    }

    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    if (!shouldStickToBottomRef.current) {
      return;
    }
    scrollToBottom();
  }, [messages, isLoading]);

  useLayoutEffect(() => {
    if (messages.length === 0) {
      hasInitialScrollRef.current = false;
      return;
    }

    if (hasInitialScrollRef.current) {
      return;
    }

    let cancelled = false;
    const timeoutIds: number[] = [];

    const forceInitialBottom = () => {
      if (cancelled) {
        return;
      }
      shouldStickToBottomRef.current = true;
      scrollToBottom("auto");
    };

    forceInitialBottom();

    const frameId = window.requestAnimationFrame(() => {
      forceInitialBottom();
      window.requestAnimationFrame(() => {
        forceInitialBottom();
      });
    });

    timeoutIds.push(window.setTimeout(forceInitialBottom, 80));
    timeoutIds.push(window.setTimeout(() => {
      forceInitialBottom();
      hasInitialScrollRef.current = true;
    }, 180));

    return () => {
      cancelled = true;
      window.cancelAnimationFrame(frameId);
      timeoutIds.forEach((timeoutId) => window.clearTimeout(timeoutId));
    };
  }, [messages]);

  useEffect(() => {
    hasInitialScrollRef.current = false;
    shouldStickToBottomRef.current = true;
  }, [notebookId]);

  const handleMessagesScroll = () => {
    const container = messagesContainerRef.current;
    if (!container) {
      return;
    }

    shouldStickToBottomRef.current = isNearBottom(container);
  };

  useEffect(() => {
    const noteResetTimeouts = noteResetTimeoutsRef.current;
    return () => {
      if (copyResetTimeoutRef.current) {
        clearTimeout(copyResetTimeoutRef.current);
      }
      Object.values(noteResetTimeouts).forEach((timeoutId) => clearTimeout(timeoutId));
    };
  }, []);

  useEffect(() => {
    loadHistoryFromServer().catch((error) => {
      console.error("Failed to load chat history from our server", error);
      setMessages([]);
    });
  }, [loadHistoryFromServer]);

  useEffect(() => {
    if (!hasRemoteStreamingMessage) {
      return;
    }

    const intervalId = window.setInterval(() => {
      loadHistoryFromServer().catch((error) => {
        console.error("Failed to refresh streaming chat history", error);
      });
    }, 1500);

    return () => window.clearInterval(intervalId);
  }, [hasRemoteStreamingMessage, loadHistoryFromServer]);

  const handleStop = async () => {
    if (!notebookId) {
      return;
    }

    stopRequestedRef.current = true;

    try {
      await fetch(`${apiBaseUrl}/api/query/stop/${notebookId}`, {
        method: "POST",
        credentials: "include",
      });
    } catch (error) {
      console.error("Failed to stop generation", error);
    } finally {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      setIsLoading(false);
      window.setTimeout(() => {
        loadHistoryFromServer().catch((error) => {
          console.error("Failed to reload chat history after stop", error);
        });
      }, 250);
    }
  };

  const handleCopy = async (messageContent: string, messageIndex: number) => {
    try {
      await navigator.clipboard.writeText(messageContent);
      setCopiedMessageIndex(messageIndex);
      if (copyResetTimeoutRef.current) {
        clearTimeout(copyResetTimeoutRef.current);
      }
      copyResetTimeoutRef.current = setTimeout(() => {
        setCopiedMessageIndex(null);
      }, 1500);
    } catch (error) {
      console.error("Copy failed", error);
    }
  };

  const handleSaveNote = async (messageContent: string, messageIndex: number) => {
    if (!notebookId) {
      setNoteSaveStates((prev) => ({
        ...prev,
        [messageIndex]: { status: "error", error: "Notebook unavailable" },
      }));
      return;
    }

    setNoteSaveStates((prev) => ({
      ...prev,
      [messageIndex]: { status: "saving" },
    }));

    try {
      const response = await fetch(`${apiBaseUrl}/api/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          notebook_id: notebookId,
          content: messageContent,
          source_message_id: null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        throw new Error(errorData.detail || "Failed to save note");
      }

      await onNoteSaved?.();

      setNoteSaveStates((prev) => ({
        ...prev,
        [messageIndex]: { status: "saved" },
      }));

      if (noteResetTimeoutsRef.current[messageIndex]) {
        clearTimeout(noteResetTimeoutsRef.current[messageIndex]);
      }
      noteResetTimeoutsRef.current[messageIndex] = setTimeout(() => {
        setNoteSaveStates((prev) => ({
          ...prev,
          [messageIndex]: { status: "idle" },
        }));
      }, 1500);
    } catch (error) {
      console.error("Save note failed", error);
      setNoteSaveStates((prev) => ({
        ...prev,
        [messageIndex]: {
          status: "error",
          error: getErrorMessage(error),
        },
      }));

      if (noteResetTimeoutsRef.current[messageIndex]) {
        clearTimeout(noteResetTimeoutsRef.current[messageIndex]);
      }
      noteResetTimeoutsRef.current[messageIndex] = setTimeout(() => {
        setNoteSaveStates((prev) => ({
          ...prev,
          [messageIndex]: { status: "idle" },
        }));
      }, 2500);
    }
  };

  const buildNotReadyMessage = () => {
    if (documents.length === 0) {
      return "Upload a PDF to get started. Once it's ready, you can ask questions about it.";
    }

    if (pendingDocuments.length > 0) {
      return "Your PDF is still being prepared. You'll be able to ask questions in a moment.";
    }

    if (failedDocuments.length > 0) {
      return "Something went wrong while preparing your PDF. Try uploading it again.";
    }

    return "This notebook isn't ready yet. Try adding or re-uploading a PDF.";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;

    if (!hasReadyDocuments) {
      const statusMessage = buildNotReadyMessage();
      setMessages((prev) => [
        ...prev,
        { role: "user", content: input },
        { role: "assistant", content: statusMessage, retrieval_metadata: { status: "complete" } },
      ]);
      setInput("");
      return;
    }

    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);
    stopRequestedRef.current = false;
    shouldStickToBottomRef.current = true;
    let shouldReconcileFromServer = false;

    abortControllerRef.current = new AbortController();

    try {
      const timeoutId = setTimeout(() => abortControllerRef.current?.abort(), 30000);
      const response = await fetch(`${apiBaseUrl}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          question: input,
          file_ids: fileIds,
          top_k: 8,
          notebook_id: notebookId,
        }),
        signal: abortControllerRef.current.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }
      shouldReconcileFromServer = true;

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No reader available");

      let assistantMsgContent = "";
      setMessages((prev) => [...prev, { role: "assistant", content: "", retrieval_metadata: { status: "streaming" } }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = new TextDecoder().decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (!line.trim().startsWith("data: ")) {
            continue;
          }

          const dataStr = line.replace("data: ", "").trim();
          if (dataStr === "[DONE]") break;

          try {
            const data = JSON.parse(dataStr);
            if (data.type === "message" && data.content) {
              assistantMsgContent += data.content;
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last && last.role === "assistant") {
                  return [
                    ...prev.slice(0, -1),
                    { ...last, content: assistantMsgContent, retrieval_metadata: { status: "streaming" } },
                  ];
                }
                return prev;
              });
            } else if (data.type === "error") {
              assistantMsgContent = `ERROR: ${data.content}`;
              setMessages((prev) => {
                const last = prev[prev.length - 1];
                if (last && last.role === "assistant") {
                  return [
                    ...prev.slice(0, -1),
                    { ...last, content: assistantMsgContent, retrieval_metadata: { status: "complete" } },
                  ];
                }
                return prev;
              });
              break;
            }
          } catch {
            // Ignore partial JSON and keep-alives.
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        if (!stopRequestedRef.current) {
          setMessages((prev) => [
            ...prev,
            { role: "assistant", content: "The request timed out. Please try again or check your backend.", retrieval_metadata: { status: "complete" } },
          ]);
        }
      } else {
        console.error("Chat error:", err);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Failed to connect: ${getErrorMessage(err)}`, retrieval_metadata: { status: "complete" } },
        ]);
      }
    } finally {
      if (shouldReconcileFromServer) {
        try {
          await loadHistoryFromServer();
        } catch (error) {
          console.error("Failed to reconcile chat history with backend", error);
        }
      }
      setIsLoading(false);
      abortControllerRef.current = null;
      stopRequestedRef.current = false;
    }
  };

  const formatContent = (content: string) => {
    return content.split(/(\[\d+\])/g).map((part, i) => {
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        return (
          <sup key={i} className="ml-0.5 cursor-pointer font-semibold text-[color:var(--theme-text-muted)] hover:text-ink">
            {match[1]}
          </sup>
        );
      }
      return part;
    });
  };

  const renderAssistantBody = (content: string) => {
    const blocks = content
      .split(/\n{2,}/)
      .map((block) => block.trim())
      .filter(Boolean);

    return blocks.map((block, blockIndex) => {
      const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
      const bulletLines = lines.filter((line) => /^[-*]\s+/.test(line));
      const numberedLines = lines.filter((line) => /^\d+\.\s+/.test(line));
      const isBulletList = bulletLines.length === lines.length && lines.length > 0;
      const isNumberedList = numberedLines.length === lines.length && lines.length > 0;

      if (isBulletList) {
        return (
          <ul key={`assistant-bullets-${blockIndex}`} className="ml-5 list-disc space-y-2.5 text-[16px] leading-[1.72] text-[color:var(--theme-assistant-text)]">
            {lines.map((line, lineIndex) => (
              <li key={`assistant-bullet-${blockIndex}-${lineIndex}`}>{formatContent(line.replace(/^[-*]\s+/, ""))}</li>
            ))}
          </ul>
        );
      }

      if (isNumberedList) {
        return (
          <ol key={`assistant-numbered-${blockIndex}`} className="ml-5 list-decimal space-y-2.5 text-[16px] leading-[1.72] text-[color:var(--theme-assistant-text)]">
            {lines.map((line, lineIndex) => (
              <li key={`assistant-number-${blockIndex}-${lineIndex}`}>{formatContent(line.replace(/^\d+\.\s+/, ""))}</li>
            ))}
          </ol>
        );
      }

      return (
        <p key={`assistant-paragraph-${blockIndex}`} className="text-[16px] leading-[1.72] text-[color:var(--theme-assistant-text)]">
          {formatContent(lines.join(" "))}
        </p>
      );
    });
  };

  const thinkingAnimation = {
    scale: [1, 1.05, 1],
    y: [0, -2, 0],
    opacity: [0.72, 1, 0.72],
    filter: [
      "drop-shadow(0 0 0 rgba(255, 190, 92, 0))",
      "drop-shadow(0 0 8px rgba(91, 141, 239, 0.16))",
      "drop-shadow(0 0 0 rgba(255, 190, 92, 0))",
    ],
  };

  const renderComposer = (mode: "empty" | "chat") => (
    <form onSubmit={handleSubmit} className={cn("mx-auto w-full", mode === "empty" ? "max-w-3xl" : "max-w-4xl")}>
      <div className="ds-panel rounded-[14px] bg-surface px-4 py-3">
        <div className="flex items-center gap-3">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="How can I help you today?"
            className="flex-1 bg-transparent py-2 text-[15px] text-ink placeholder:text-[color:var(--theme-placeholder)] outline-none"
            disabled={isGenerating}
          />

          <div className="flex items-center gap-3">
            {!isEmptyState ? (
              <div className="text-[12px] font-medium text-[color:var(--theme-text-muted)]">
                {indexedDocuments.length}/{documents.length || fileIds.length} ready
              </div>
            ) : null}

            {isGenerating ? (
              <button
                type="button"
                onClick={handleStop}
                className="flex h-10 w-10 items-center justify-center rounded-[10px] border border-border text-ink transition-colors hover:bg-[color:var(--theme-surface-muted)]"
              >
                <Square className="h-4 w-4 fill-current" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!input.trim()}
                className="flex h-10 w-10 items-center justify-center rounded-[10px] bg-accent text-white transition-colors hover:bg-[color:var(--theme-accent-hover)] disabled:opacity-35"
              >
                <ArrowUp className="h-5 w-5" strokeWidth={2.4} />
              </button>
            )}
          </div>
        </div>
      </div>
      {mode === "chat" ? (
        <p className="mt-3 text-center text-[11px] text-[color:var(--theme-text-muted)]">
          DokuKit may be imperfect. Double-check important details.
        </p>
      ) : null}
    </form>
  );

  return (
    <div className="flex h-full min-h-0 flex-col bg-transparent text-ink">
      {!hasReadyDocuments && (
        <div className="mx-6 mt-6 rounded-[14px] border border-border bg-[color:var(--theme-surface-raised)] px-4 py-4 text-sm text-[color:var(--theme-text-secondary)] shadow-[var(--theme-card-shadow)] lg:mx-8">
          <div className="flex items-start gap-3">
            {failedDocuments.length > 0 ? (
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--theme-danger)]" />
            ) : (
              <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-[color:var(--theme-text-secondary)]" />
            )}
            <div>
              <p className="text-[14px] font-medium text-ink">
                {documents.length === 0
                  ? "No documents uploaded yet"
                  : pendingDocuments.length > 0
                    ? "Indexing in progress"
                    : "No query-ready documents"}
              </p>
              <p className="mt-1 text-[14px] leading-[1.55] text-[color:var(--theme-text-secondary)]">
                {documents.length === 0
                  ? "Add a PDF to this notebook and I'll ground answers in it."
                  : pendingDocuments.length > 0
                    ? `${pendingDocuments.length} document${pendingDocuments.length === 1 ? "" : "s"} still processing. You can start chatting once at least one source is indexed.`
                    : failedDocuments[0]?.processingError || "Document processing failed for this notebook."}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="min-h-0 flex-1">
        <AnimatePresence mode="wait">
          {isEmptyState ? (
            <motion.div
              key="empty-state"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -14 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
              className="flex h-full min-h-0 items-center justify-center px-6 py-8 lg:px-8"
            >
              <div className="w-full max-w-3xl text-center">
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.24, delay: 0.03, ease: "easeOut" }}
                >
                  <h3 className="reading-serif text-[36px] font-normal leading-[1.08] tracking-[-0.03em] text-ink">
                    {greeting}
                  </h3>
                  <p className="mt-4 text-[16px] leading-[1.7] text-[color:var(--theme-text-secondary)]">
                    What are you working on today?
                  </p>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.24, delay: 0.08, ease: "easeOut" }}
                  className="mt-8"
                >
                  {renderComposer("empty")}
                </motion.div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="chat-state"
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
              className="flex h-full min-h-0 flex-col"
            >
              <div
                ref={messagesContainerRef}
                onScroll={handleMessagesScroll}
                className="h-[calc(100vh-210px)] min-h-0 space-y-8 overflow-y-auto overflow-x-hidden px-6 py-8 scroll-smooth lg:px-8"
              >
                {messages.map((message, index) => (
                  <motion.div key={message.id ?? `${message.role}-${index}-${message.content.slice(0, 24)}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="w-full">
                    <div className={cn("flex w-full", message.role === "user" ? "justify-end" : "justify-start")}>
                      <div className={cn("max-w-[70%]", message.role === "assistant" ? "max-w-3xl" : "max-w-[70%]")}>
                        {(() => {
                          const isStreamingAssistant =
                            message.role === "assistant" &&
                            ((isLoading && index === messages.length - 1) || message.retrieval_metadata?.status === "streaming");
                          const hasStartedStreaming = isStreamingAssistant && message.content.trim().length > 0;
                          const showAssistantActions =
                            message.role === "assistant" && !isStreamingAssistant && message.content.trim().length > 0;

                          return (
                            <>
                              {message.role === "user" ? (
                                <div className="mb-3 text-right text-[12px] font-medium text-[color:var(--theme-text-muted)]">You</div>
                              ) : null}

                              {message.role === "user" ? (
                                <div className="rounded-[16px] bg-[color:var(--theme-user-bubble)] px-4 py-3 text-[16px] leading-[1.65] text-[color:var(--theme-user-bubble-text)]">
                                  {formatContent(message.content)}
                                </div>
                              ) : (
                                <div className="reading-serif whitespace-pre-wrap text-[16px] font-normal leading-[1.72] text-[color:var(--theme-assistant-text)]">
                                  {message.content.includes("\n") ? (
                                    <>
                                      <span className="mb-3 block text-[21px] font-semibold leading-[1.28] tracking-[-0.02em] text-ink">
                                        {message.content.split("\n")[0] || ""}
                                      </span>
                                      <div className="space-y-4">{renderAssistantBody(message.content.split("\n").slice(1).join("\n"))}</div>
                                    </>
                                  ) : (
                                    <div className="space-y-4">{renderAssistantBody(message.content)}</div>
                                  )}
                                </div>
                              )}

                              {message.role === "assistant" ? (
                                <div className="mt-3 flex items-center gap-2 text-[12px] font-medium text-[color:var(--theme-text-muted)]">
                                  {isStreamingAssistant ? (
                                    <motion.img
                                      src="/staryellow.png"
                                      alt="Assistant is thinking"
                                      width={28}
                                      height={28}
                                      className="pixel-icon h-7 w-7 object-contain"
                                      animate={thinkingAnimation}
                                      transition={{
                                        duration: 1.4,
                                        repeat: Infinity,
                                        ease: "easeInOut",
                                      }}
                                    />
                                  ) : (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src="/staryellow.png" alt="DokuKit" width={28} height={28} className="pixel-icon h-7 w-7 object-contain opacity-95" />
                                  )}
                                  {isStreamingAssistant && !hasStartedStreaming ? <span>Thinking</span> : null}
                                </div>
                              ) : null}

                              {showAssistantActions && (
                                <div className="flex items-center gap-2 pt-4">
                                  <button
                                    type="button"
                                    onClick={() => handleSaveNote(message.content, index)}
                                    disabled={noteSaveStates[index]?.status === "saving"}
                                    className="relative z-10 rounded-[10px] px-2.5 py-1.5 text-[12px] font-medium text-[color:var(--theme-text-secondary)] transition-colors hover:bg-[color:var(--theme-surface-muted)] hover:text-ink disabled:opacity-50 cursor-pointer"
                                  >
                                    <span className="inline-flex items-center gap-2">
                                      <Bookmark className="h-3 w-3" />
                                      {noteSaveStates[index]?.status === "saving"
                                        ? "Saving"
                                        : noteSaveStates[index]?.status === "saved"
                                          ? "Saved"
                                          : noteSaveStates[index]?.status === "error"
                                            ? "Failed"
                                            : "Save to note"}
                                    </span>
                                  </button>
                                    <button
                                      type="button"
                                      onClick={() => handleCopy(message.content, index)}
                                      className="relative z-10 rounded-[10px] px-2.5 py-1.5 text-[12px] font-medium text-[color:var(--theme-text-secondary)] transition-colors hover:bg-[color:var(--theme-surface-muted)] hover:text-ink cursor-pointer"
                                    >
                                      {copiedMessageIndex === index ? (
                                      <span className="text-[12px] font-medium text-ink">Copied</span>
                                    ) : (
                                      <span className="inline-flex items-center gap-2">
                                        <Copy className="h-3 w-3" />
                                        Copy
                                      </span>
                                    )}
                                  </button>
                                  {noteSaveStates[index]?.status === "error" && noteSaveStates[index]?.error && (
                                    <span className="text-[11px] text-[color:var(--theme-danger)]">{noteSaveStates[index]?.error}</span>
                                  )}
                                </div>
                              )}
                            </>
                          );
                        })()}
                      </div>
                    </div>
                  </motion.div>
                ))}
                <div ref={messagesEndRef} />
              </div>

              <div className="sticky bottom-0 z-10 bg-paper px-6 pb-6 pt-3 backdrop-blur-sm lg:px-8">
                {renderComposer("chat")}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
