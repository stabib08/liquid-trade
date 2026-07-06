import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "liquid-trade — deep-tech thesis baskets",
  description:
    "Public-equity proxy baskets for private deep-tech theses, each with a " +
    "falsifiable prediction, an explicit kill-criterion, and a point-in-time dataset.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
