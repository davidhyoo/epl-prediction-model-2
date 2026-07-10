import type { Metadata } from "next";
import "flag-icons/css/flag-icons.min.css";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { TooltipProvider } from "@/components/ui/tooltip";
import { SiteNav } from "@/components/site-nav";
import { SiteFooter } from "@/components/site-footer";
import { CommandPalette } from "@/components/command-palette";

export const metadata: Metadata = {
  title: {
    default: "World Cup 2026 · Prediction & Analytics",
    template: "%s · World Cup 2026",
  },
  description:
    "A 2026 FIFA World Cup prediction and analytics dashboard powered by a reproducible machine-learning pipeline (Elo, Logistic Regression, Random Forest, XGBoost and a weighted ensemble).",
  applicationName: "World Cup 2026 Analytics",
  keywords: [
    "World Cup 2026",
    "football predictions",
    "machine learning",
    "analytics dashboard",
    "Elo",
    "XGBoost",
  ],
  authors: [{ name: "World Cup 2026 Analytics" }],
};

export const viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1220" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
          <TooltipProvider delayDuration={150}>
            <div className="flex min-h-screen flex-col">
              <SiteNav />
              <main className="flex-1">{children}</main>
              <SiteFooter />
            </div>
            <CommandPalette />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
