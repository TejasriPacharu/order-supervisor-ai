import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = { title: "Order Supervisor" };

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">
        <nav className="bg-white border-b px-6 py-3 flex gap-6 items-center">
          <Link href="/" className="font-bold text-lg">
            Order Supervisor
          </Link>
          <Link
            href="/supervisors"
            className="text-gray-600 hover:text-black text-sm"
          >
            Supervisors
          </Link>
          <Link href="/runs" className="text-gray-600 hover:text-black text-sm">
            Runs
          </Link>
        </nav>
        <main className="max-w-5xl mx-auto p-6">{children}</main>
      </body>
    </html>
  );
}
