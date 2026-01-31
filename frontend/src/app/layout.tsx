import type { Metadata } from "next";
import { Outfit, Nunito } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";
import { ChatWidget } from "@/components/ChatWidget";
import { BackendOfflineBanner } from "@/components/BackendOfflineBanner";
import { Providers } from "./providers";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-heading",
  display: "swap",
});

const nunito = Nunito({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AuraShop – AI-Powered Shopping Assistant",
  description: "Personalized product recommendations and real-time AI assistant for e-commerce.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning className={`${outfit.variable} ${nunito.variable}`}>
      <body className="min-h-screen antialiased font-sans text-foreground">
        <Providers>
          <BackendOfflineBanner />
          <Header />
          <main className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl pb-28 sm:pb-24">
            {children}
          </main>
          <ChatWidget />
        </Providers>
      </body>
    </html>
  );
}
