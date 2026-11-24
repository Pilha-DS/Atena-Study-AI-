import type { Metadata } from "next";
import { Fraunces, Manrope } from "next/font/google";
import { Sidebar } from "@/components/sidebar";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const sans = Manrope({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Atena Study AI",
  description: "Plataforma pessoal de estudos com organização hierárquica",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className={`${display.variable} ${sans.variable} antialiased`}>
        <ThemeProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 px-4 pb-10 pt-20 sm:px-8 lg:px-10 lg:py-10">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
