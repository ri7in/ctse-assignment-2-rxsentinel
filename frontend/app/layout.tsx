import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "RxSentinel — AI agents on watch for medication harm",
  description:
    "A locally-hosted multi-agent system that performs medication safety reviews, drug-interaction analysis, and plain-English patient explanations. Free, private, offline.",
  keywords: [
    "medication safety",
    "drug interaction checker",
    "multi-agent system",
    "LangGraph",
    "Ollama",
    "RxNorm",
    "openFDA",
  ],
  authors: [
    { name: "Rivin Sandeepa" },
    { name: "Thusala" },
    { name: "Shehan" },
    { name: "Sachila Wandya" },
  ],
  openGraph: {
    title: "RxSentinel",
    description: "AI agents on watch for medication harm.",
    type: "website",
  },
  icons: {
    icon: "/favicon.svg",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0e1a",
  colorScheme: "dark",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="min-h-screen mesh-bg antialiased">
        {children}
        <Toaster
          theme="dark"
          position="top-right"
          toastOptions={{
            style: {
              background: "rgba(15, 23, 41, 0.85)",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "#f8fafc",
              backdropFilter: "blur(20px)",
            },
          }}
        />
      </body>
    </html>
  );
}
