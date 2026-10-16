import type { Metadata } from "next";
import "../globals.css";

export const metadata: Metadata = {
  title: "SentinelGrid | Developer source preview",
  description:
    "Experimental product interfaces accompanying the SentinelGrid developer source preview.",
};

export default function MarketingLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return children;
}
