import type { Metadata } from "next";
import { Darker_Grotesque, IBM_Plex_Mono } from "next/font/google";
import { Toaster } from "sonner";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const darkerGrotesque = Darker_Grotesque({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["700", "800", "900"],
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "AdForge",
  description: "AI-powered creative infrastructure for eCommerce ads",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${darkerGrotesque.variable} ${ibmPlexMono.variable} font-mono antialiased`}>
        <ThemeProvider>
          {children}
          <Toaster
            position="bottom-right"
            toastOptions={{
              unstyled: true,
              classNames: {
                toast: "bg-[#1A1A1A] text-[#F2F0ED] font-mono text-xs uppercase tracking-wider p-4 border border-[#333] flex items-center gap-3",
                title: "font-medium",
                description: "text-[#9B9590]",
              },
            }}
          />
        </ThemeProvider>
      </body>
    </html>
  );
}
