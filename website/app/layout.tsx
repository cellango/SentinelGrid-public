import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/providers/AuthProvider";

export const metadata: Metadata = {
  title: "SentinelGrid | Archived website prototype",
  description:
    "Archived website reference. The canonical frontend and current source-preview scope live in the main repository.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <aside className="border-b p-3 text-center text-sm">
          Archived website prototype. Its offers and capability claims are historical; review the main repository scope.
        </aside>
        <AuthProvider>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
