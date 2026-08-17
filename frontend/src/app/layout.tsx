import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

// ✅ SEO + App Identity
export const metadata: Metadata = {
  title: {
    default: "Saki AI",
    template: "%s | Saki AI",
  },
  description: "AI Close Companion powered by FastAPI + Next.js",
  applicationName: "Saki AI",
};

// ✅ Mobile responsiveness
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <body className="h-screen w-screen overflow-hidden bg-slate-50 text-slate-900 antialiased">
        <Providers>
          <div className="h-screen w-screen overflow-hidden flex flex-col">
            {children}
          </div>
        </Providers>
      </body>
    </html>
  );
}