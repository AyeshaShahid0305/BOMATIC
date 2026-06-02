import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "BOMATIC",
  description: "Multi-vendor pre-sales deliverable generation platform for Systems Integrators",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <nav className="flex items-center justify-between border-b border-gray-200 bg-white px-6 py-3">
          <a href="/opportunities" className="text-sm font-semibold text-gray-800 hover:text-blue-600">
            BOMATIC
          </a>
          <form action="/api/auth/logout" method="POST">
            <button
              type="submit"
              className="text-xs text-gray-400 hover:text-gray-700"
            >
              Sign out
            </button>
          </form>
        </nav>
        {children}
      </body>
    </html>
  );
}
