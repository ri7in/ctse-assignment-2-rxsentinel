import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "RxSentinel — Medication safety review",
  description:
    "Local multi-agent system for medication safety review. Drug interactions, severity ranking, and plain-English patient summaries — all running on your machine.",
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
    description: "Local agents for medication safety review.",
    type: "website",
  },
  icons: {
    icon: "/favicon.svg",
  },
};

export const viewport: Viewport = {
  themeColor: "#FAFAFA",
  colorScheme: "light",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable}`}>
      <body className="min-h-screen bg-mesh antialiased">
        {children}
        <Toaster
          theme="light"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#FFFFFF",
              border: "1px solid #E7E5E4",
              color: "#0A0E1A",
              fontSize: "13px",
            },
          }}
        />
      </body>
    </html>
  );
}
