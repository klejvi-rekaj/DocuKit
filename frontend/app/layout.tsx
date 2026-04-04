import type { Metadata } from "next";
import { Inter, Schoolbell, Source_Serif_4 } from "next/font/google";
import { ThemeProvider } from "@/features/theme/ThemeProvider";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-ui",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-reading",
  weight: ["400", "600"],
});

const schoolbell = Schoolbell({
  subsets: ["latin"],
  variable: "--font-logo",
  weight: "400",
});

export const metadata: Metadata = {
  title: "DokuKit",
  description: "Document research assistant.",
  icons: {
    icon: "/staryellow.png",
    shortcut: "/staryellow.png",
    apple: "/staryellow.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const themeScript = `
    (() => {
      const storageKey = 'dokukit-theme';
      const stored = window.localStorage.getItem(storageKey);
      const preference = stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'system';
      const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const resolved = preference === 'system' ? (systemDark ? 'dark' : 'light') : preference;
      document.documentElement.dataset.themeChoice = preference;
      document.documentElement.dataset.theme = resolved;
      document.documentElement.style.colorScheme = resolved;
    })();
  `;

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body
        className={`${inter.variable} ${sourceSerif.variable} ${schoolbell.variable} antialiased font-sans text-ink bg-paper selection:bg-ink selection:text-paper min-h-screen overflow-y-auto overflow-x-hidden`}
        style={{ cursor: "default" }}
        suppressHydrationWarning
      >
        <ThemeProvider>
          <div className="paper-texture"></div>
          <main className="relative z-10 w-full min-h-screen overflow-x-hidden">
            {children}
          </main>
        </ThemeProvider>
      </body>
    </html>
  );
}
