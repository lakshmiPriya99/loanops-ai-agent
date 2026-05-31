import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "LoanOps AI Agent",
  description: "Forward deployed mortgage AI agent demo"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
