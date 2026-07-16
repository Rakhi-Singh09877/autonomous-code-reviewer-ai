import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import {
  QueryProvider,
  ThemeProvider,
  SessionProvider,
  ShortcutProvider,
  PaletteProvider,
  NotificationProvider,
} from "../providers";
import { WorkspaceShell } from "../shared/layout/WorkspaceShell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Autonomous Code Reviewer AI",
  description: "Enterprise-grade automated code review dashboard powered by RAG and LLM agents.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <QueryProvider>
          <ThemeProvider>
            <SessionProvider>
              <ShortcutProvider>
                <PaletteProvider>
                  <NotificationProvider>
                    <WorkspaceShell>{children}</WorkspaceShell>
                  </NotificationProvider>
                </PaletteProvider>
              </ShortcutProvider>
            </SessionProvider>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
