import type { Metadata, Viewport } from "next";
import { Noto_Sans, Noto_Sans_Devanagari, Noto_Sans_Telugu } from "next/font/google";
import "./globals.css";
import { AppProvider } from "@/lib/app-context";
import AppShell from "@/components/AppShell";
import { SourceProvider } from "@/components/SourceViewer";

const noto = Noto_Sans({ subsets: ["latin"], variable: "--font-noto", display: "swap", weight: ["400", "500", "600", "700", "800"] });
const deva = Noto_Sans_Devanagari({ subsets: ["devanagari"], variable: "--font-noto-deva", display: "swap", weight: ["400", "500", "600", "700", "800"] });
const telugu = Noto_Sans_Telugu({ subsets: ["telugu"], variable: "--font-noto-telugu", display: "swap", weight: ["400", "500", "600", "700", "800"] });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "Haathi – Find Government Schemes",
  description: "Ask in Telugu, Hindi or English. Haathi finds government schemes you may be eligible for, proves it with exact citations, and tells you how to apply.",
  applicationName: "Haathi",
  appleWebApp: { capable: true, title: "Haathi", statusBarStyle: "default" },
  icons: {
    icon: [{ url: "/icons/icon.svg", type: "image/svg+xml" }, { url: "/icons/favicon.ico", sizes: "32x32" }],
    apple: "/icons/apple-touch-icon.png",
  },
  openGraph: { title: "Haathi – Find Government Schemes", description: "Multilingual scheme finder with proof from official rules.", images: ["/icons/og-image.png"] },
};

export const viewport: Viewport = {
  themeColor: "#0b6e84",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="te" suppressHydrationWarning className={`${noto.variable} ${deva.variable} ${telugu.variable}`}>
      <body>
        <AppProvider>
          <SourceProvider>
            <AppShell>{children}</AppShell>
          </SourceProvider>
        </AppProvider>
      </body>
    </html>
  );
}
