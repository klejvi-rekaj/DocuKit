"use client";

import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { FileText, MessageSquareText, NotebookPen, Palette, Search } from "lucide-react";

interface AuthPageFrameProps {
  title: string;
  description: string;
  children: React.ReactNode;
  footer: React.ReactNode;
}

const FOLDER_FLOATS: Array<{
  y: number[];
  x: number[];
  rotate: number[];
  scale: number[];
  duration: number;
  delay: number;
}> = [
  {
    y: [0, -8, 0],
    x: [0, 3, 0],
    rotate: [0, -0.8, 0],
    scale: [1, 1.015, 1],
    duration: 8.4,
    delay: 0,
  },
  {
    y: [0, -10, 0],
    x: [0, -4, 0],
    rotate: [0, 0.9, 0],
    scale: [1, 1.02, 1],
    duration: 9.3,
    delay: 0.8,
  },
  {
    y: [0, -7, 0],
    x: [0, 2, 0],
    rotate: [0, -0.6, 0],
    scale: [1, 1.012, 1],
    duration: 7.9,
    delay: 1.3,
  },
  {
    y: [0, -11, 0],
    x: [0, -3, 0],
    rotate: [0, 0.7, 0],
    scale: [1, 1.018, 1],
    duration: 9.8,
    delay: 0.4,
  },
];

const LOOP_DURATION = 14;
const LOOP_TIMES = [0, 0.18, 0.38, 0.6, 0.82, 1];

const WORKSPACE_ITEMS = [
  { label: "Files", icon: FileText },
  { label: "Answers", icon: MessageSquareText },
  { label: "Saved notes", icon: NotebookPen },
  { label: "Themes", icon: Palette },
];

function getStepPulse(index: number) {
  const emphasisStarts = [0.16, 0.29, 0.42, 0.55, 0.68];
  const start = emphasisStarts[index] ?? 0.16;
  const settle = Math.min(start + 0.08, 1);
  return {
    x: [0, 0, 10, 4, 0],
    scale: [1, 1, 1.022, 1.01, 1],
    opacity: [0.72, 0.72, 1, 0.92, 0.78],
    times: [0, Math.max(0, start - 0.04), start, settle, 1],
  };
}

export function AuthPageFrame({ title, description, children, footer }: AuthPageFrameProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="min-h-screen overflow-hidden bg-paper px-6 py-6 text-ink lg:px-10 lg:py-7">
      <div className="mx-auto max-w-[1320px]">
        <div className="mb-6 lg:mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-3 transition duration-150 hover:scale-[1.02] hover:opacity-90"
            aria-label="DokuKit"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/staryellow.png" alt="DokuKit" className="h-[54px] w-auto object-contain" />
            <span className="text-[32px] leading-none text-[color:var(--theme-logo)] [font-family:var(--font-logo)]">
              DokuKit
            </span>
          </Link>
        </div>

        <div className="grid items-start gap-10 lg:grid-cols-[minmax(400px,500px)_minmax(420px,1fr)] lg:gap-14 xl:gap-16">
          <section className="pt-2 lg:pt-8">
            <div className="max-w-[470px]">
              <h1 className="reading-serif text-[52px] font-normal leading-[0.95] tracking-[-0.045em] text-ink sm:text-[64px]">
                {title}
              </h1>
              <p className="mt-4 max-w-[430px] text-[17px] leading-[1.5] text-[color:var(--theme-assistant-text)]">
                {description}
              </p>
            </div>

            <div className="mt-8 max-w-[430px] rounded-[18px] border border-border bg-[color:var(--theme-surface-raised)] px-7 py-7 shadow-[0_6px_18px_rgba(0,0,0,0.035)]">
              {children}
              <div className="mt-6 text-[14px] leading-[1.55] text-[color:var(--theme-text-secondary)]">
                {footer}
              </div>
            </div>
          </section>

          <aside className="relative hidden min-h-[680px] overflow-hidden rounded-[22px] border border-border bg-[color:var(--theme-surface-raised)] lg:block">
            <div
              className="absolute inset-0 opacity-100"
              style={{
                backgroundImage:
                  "linear-gradient(to right, color-mix(in srgb, var(--theme-border) 86%, transparent) 1px, transparent 1px), linear-gradient(to bottom, color-mix(in srgb, var(--theme-border) 86%, transparent) 1px, transparent 1px)",
                backgroundSize: "56px 56px",
              }}
            />

            <div className="absolute left-1/2 top-14 z-10 -translate-x-1/2">
              <motion.div
                className="relative flex items-center gap-2 rounded-[14px] border border-border bg-[color:var(--theme-surface)] p-1 shadow-[0_10px_24px_rgba(0,0,0,0.07)]"
                animate={
                  reduceMotion
                    ? undefined
                    : {
                        y: [0, -4, -1, -5, 0, 0],
                        x: [0, 2, -2, 1, 0, 0],
                        rotate: [0, -0.25, 0.15, -0.2, 0, 0],
                        scale: [1, 1.01, 1.008, 1.012, 1, 1],
                      }
                }
                transition={
                  reduceMotion
                    ? undefined
                    : {
                        duration: LOOP_DURATION,
                        times: LOOP_TIMES,
                        repeat: Number.POSITIVE_INFINITY,
                        ease: "easeInOut",
                      }
                }
              >
                <motion.div
                  className="absolute top-1 bottom-1 w-[132px] rounded-[10px] border border-border bg-[color:var(--theme-surface)] shadow-[0_6px_14px_rgba(0,0,0,0.06)]"
                  animate={
                    reduceMotion
                      ? undefined
                      : {
                          x: [0, 0, 140, 140, 0, 0],
                        }
                  }
                  transition={
                    reduceMotion
                      ? undefined
                      : {
                          duration: LOOP_DURATION,
                          times: LOOP_TIMES,
                          repeat: Number.POSITIVE_INFINITY,
                          ease: "easeInOut",
                        }
                  }
                />
                <motion.div
                  className="relative z-10 rounded-[10px] px-14 py-2.5 text-[16px] font-medium"
                  animate={
                    reduceMotion
                      ? undefined
                      : {
                          color: [
                            "var(--theme-ink)",
                            "var(--theme-ink)",
                            "var(--theme-text-secondary)",
                            "var(--theme-text-secondary)",
                            "var(--theme-ink)",
                            "var(--theme-ink)",
                          ],
                        }
                  }
                  transition={
                    reduceMotion
                      ? undefined
                      : {
                        duration: LOOP_DURATION,
                        times: LOOP_TIMES,
                        repeat: Number.POSITIVE_INFINITY,
                        ease: "easeInOut",
                      }
                  }
                >
                  Study
                </motion.div>
                <motion.div
                  className="relative z-10 rounded-[10px] px-14 py-2.5 text-[16px] font-medium"
                  animate={
                    reduceMotion
                      ? undefined
                      : {
                          color: [
                            "var(--theme-text-secondary)",
                            "var(--theme-text-secondary)",
                            "var(--theme-ink)",
                            "var(--theme-ink)",
                            "var(--theme-text-secondary)",
                            "var(--theme-text-secondary)",
                          ],
                        }
                  }
                  transition={
                    reduceMotion
                      ? undefined
                      : {
                        duration: LOOP_DURATION,
                        times: LOOP_TIMES,
                        repeat: Number.POSITIVE_INFINITY,
                        ease: "easeInOut",
                      }
                  }
                >
                  Organize
                </motion.div>
              </motion.div>
            </div>

            <motion.div
              className="absolute left-8 top-36 z-10 w-[245px] rounded-[16px] border border-border bg-[color:var(--theme-surface)] p-4 shadow-[0_12px_28px_rgba(0,0,0,0.085)]"
              animate={
                reduceMotion
                  ? undefined
                  : {
                      x: [0, -3, 7, 4, -2, 0],
                      y: [0, -5, -10, -4, -7, 0],
                      rotate: [0, -0.45, 0.55, 0.15, -0.2, 0],
                      scale: [1, 1.008, 1.018, 1.012, 1.006, 1],
                    }
              }
              transition={
                reduceMotion
                  ? undefined
                  : {
                      duration: LOOP_DURATION,
                      times: LOOP_TIMES,
                      repeat: Number.POSITIVE_INFINITY,
                      ease: "easeInOut",
                    }
              }
              style={{ transformOrigin: "50% 85%" }}
            >
              <div className="flex h-9 items-center gap-3 rounded-[10px] bg-[color:var(--theme-surface-muted)] px-4 text-[15px] text-[color:var(--theme-text-secondary)]">
                <Search className="h-4 w-4" />
                <span>Search</span>
              </div>
              <div className="mt-6 grid grid-cols-2 gap-6">
                {["Lecture notes", "Meeting", "Research", "Exams"].map((label, index) => (
                  <motion.div
                    key={label}
                    animate={
                      reduceMotion
                        ? undefined
                        : {
                            y: [0, ...FOLDER_FLOATS[index].y, -3, 0],
                            x: [0, ...FOLDER_FLOATS[index].x, index % 2 === 0 ? 5 : -4, 0],
                            rotate: [0, ...FOLDER_FLOATS[index].rotate, index % 2 === 0 ? 0.6 : -0.5, 0],
                            scale: [1, ...FOLDER_FLOATS[index].scale, index === 1 ? 1.03 : 1.018, 1],
                            opacity: [0.94, 0.98, 1, 1, 0.98, 0.96],
                          }
                    }
                    transition={
                      reduceMotion
                        ? undefined
                        : {
                            duration: LOOP_DURATION + index * 0.35,
                            delay: FOLDER_FLOATS[index].delay,
                            repeat: Number.POSITIVE_INFINITY,
                            ease: "easeInOut",
                          }
                    }
                    style={{ transformOrigin: "50% 80%" }}
                  >
                    <div className="folder-tab mb-1 ml-3 h-[12px] w-14" />
                    <div className="folder-body rounded-[10px] px-3 py-4">
                      <p className="text-[13px] leading-[1.35] text-ink">{label}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
              <div className="mt-5 flex items-center justify-between border-t border-border pt-4 text-[13px]">
                <span className="text-[color:var(--theme-text-secondary)]">Keep everything together</span>
                <span className="rounded-[8px] bg-[color:var(--theme-ink)] px-4 py-1.5 text-[color:var(--theme-paper)]">Open</span>
              </div>
            </motion.div>

            <div className="absolute bottom-20 left-1/2 z-10 -translate-x-1/2">
              <motion.div
                className="w-[330px] rounded-[16px] border border-border bg-[color:var(--theme-surface)] p-5 shadow-[0_14px_30px_rgba(0,0,0,0.085)]"
                animate={
                  reduceMotion
                    ? undefined
                    : {
                        x: [0, 5, -2, 3, 0, 0],
                        y: [0, -4, -9, -6, -2, 0],
                        rotate: [0, 0.2, -0.35, 0.15, -0.1, 0],
                        scale: [1, 1.006, 1.014, 1.01, 1.004, 1],
                      }
                }
                transition={
                  reduceMotion
                    ? undefined
                    : {
                        duration: LOOP_DURATION,
                        times: LOOP_TIMES,
                        repeat: Number.POSITIVE_INFINITY,
                        ease: "easeInOut",
                      }
                }
                style={{ transformOrigin: "50% 90%" }}
              >
                <div className="flex items-center justify-between">
                  <p className="text-[16px] font-medium text-ink">Progress</p>
                  <motion.p
                    className="text-[13px] text-[color:var(--theme-text-secondary)]"
                    animate={reduceMotion ? undefined : { opacity: [0.75, 1, 0.82, 1, 0.75] }}
                    transition={
                      reduceMotion
                        ? undefined
                        : { duration: LOOP_DURATION, times: [0, 0.25, 0.5, 0.75, 1], repeat: Number.POSITIVE_INFINITY, ease: "easeInOut" }
                    }
                  >
                    5 steps
                  </motion.p>
                </div>
                <div className="mt-4 space-y-3">
                  {["Upload your PDFs", "Ask a question", "Save useful notes", "Return later", "Keep studying"].map((step, index) => {
                    const pulse = getStepPulse(index);
                    return (
                      <motion.div
                        key={step}
                        className="flex items-center gap-4 text-[15px] text-ink"
                        animate={
                          reduceMotion
                            ? undefined
                            : {
                                x: pulse.x,
                                scale: pulse.scale,
                                opacity: pulse.opacity,
                              }
                        }
                        transition={
                          reduceMotion
                            ? undefined
                            : {
                                duration: LOOP_DURATION,
                                times: pulse.times,
                                repeat: Number.POSITIVE_INFINITY,
                                ease: "easeInOut",
                              }
                        }
                      >
                        <motion.span
                          className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-[color:var(--theme-surface-muted)] text-[13px] text-[color:var(--theme-text-secondary)]"
                          animate={
                            reduceMotion
                              ? undefined
                              : {
                                  scale: pulse.scale,
                                }
                          }
                          transition={
                            reduceMotion
                              ? undefined
                              : {
                                  duration: LOOP_DURATION,
                                  times: pulse.times,
                                  repeat: Number.POSITIVE_INFINITY,
                                  ease: "easeInOut",
                                }
                          }
                        >
                          {index + 1}
                        </motion.span>
                        <span>{step}</span>
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            </div>

            <motion.div
              className="absolute right-8 top-34 z-10 w-[236px] rounded-[16px] border border-border bg-[color:var(--theme-surface)] p-5 shadow-[0_12px_28px_rgba(0,0,0,0.085)]"
              animate={
                reduceMotion
                  ? undefined
                  : {
                      x: [0, 4, -3, 5, 1, 0],
                      y: [0, -6, -2, -8, -3, 0],
                      rotate: [0, -0.3, 0.4, -0.2, 0.15, 0],
                      scale: [1, 1.008, 1.015, 1.012, 1.006, 1],
                    }
              }
              transition={
                reduceMotion
                  ? undefined
                  : {
                      duration: LOOP_DURATION,
                      times: LOOP_TIMES,
                      repeat: Number.POSITIVE_INFINITY,
                      ease: "easeInOut",
                    }
              }
              style={{ transformOrigin: "50% 85%" }}
            >
              <div className="flex items-center justify-between">
                <p className="text-[16px] font-medium text-ink">Workspace</p>
                <span className="h-3 w-3 rounded-full bg-[color:var(--theme-accent)]" />
              </div>
              <div className="mt-5 space-y-4">
                {WORKSPACE_ITEMS.map((item, index) => {
                  const Icon = item.icon;
                  return (
                    <motion.div
                      key={item.label}
                      className="flex items-center gap-3 text-[15px] text-ink"
                      animate={
                        reduceMotion
                          ? undefined
                          : {
                              x: [0, 0, index === 1 ? 8 : index === 2 ? 5 : 0, 2, 0],
                              scale: [1, 1, index === 1 ? 1.018 : 1.01, 1.006, 1],
                              opacity: [0.86, 0.9, 1, 0.94, 0.88],
                            }
                      }
                      transition={
                        reduceMotion
                          ? undefined
                          : {
                              duration: LOOP_DURATION,
                              times: [0, 0.32 + index * 0.04, 0.44 + index * 0.04, 0.58 + index * 0.04, 1],
                              repeat: Number.POSITIVE_INFINITY,
                              ease: "easeInOut",
                            }
                      }
                    >
                      <span className="inline-flex h-10 w-10 items-center justify-center rounded-[10px] border border-border bg-[color:var(--theme-surface-muted)] text-[color:var(--theme-text-secondary)]">
                        <Icon className="h-4.5 w-4.5" strokeWidth={1.8} />
                      </span>
                      <span>{item.label}</span>
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          </aside>
        </div>
      </div>
    </div>
  );
}
