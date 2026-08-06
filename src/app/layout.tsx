import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import "flag-icons/css/flag-icons.min.css";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SiteNav } from "@/components/site-nav";
import { SiteFooter } from "@/components/site-footer";
import { getIndex } from "@/lib/data";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

function refreshEnabled(): boolean {
  return process.env.NODE_ENV !== "production" || process.env.ALLOW_DATA_REFRESH === "1";
}

export const metadata: Metadata = {
  title: {
    default: "Soccer Agent · EPL & La Liga Prediction Analytics",
    template: "%s · Soccer Agent",
  },
  description:
    "A live Premier League & La Liga prediction and analytics dashboard powered by a reproducible machine-learning pipeline (Elo, Logistic Regression, Random Forest, XGBoost, a market baseline and a weighted ensemble) with Monte-Carlo season simulation.",
  applicationName: "Soccer Agent",
  keywords: [
    "Premier League",
    "La Liga",
    "football predictions",
    "machine learning",
    "analytics dashboard",
    "Elo",
    "XGBoost",
    "Monte Carlo",
  ],
  authors: [{ name: "Soccer Agent" }],
};

export const viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0b14" },
  ],
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const index = await getIndex();
  return (
    <html lang="en" suppressHydrationWarning className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="min-h-screen antialiased">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <TooltipProvider delayDuration={150}>
            <div className="flex min-h-screen flex-col">
              <Suspense fallback={<div className="h-16 border-b border-border" />}>
                <SiteNav index={index} refreshEnabled={refreshEnabled()} />
              </Suspense>
              <main className="flex-1">{children}</main>
              <SiteFooter />
            </div>
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
