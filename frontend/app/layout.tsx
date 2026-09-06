import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";

import "./globals.css";

// DESIGN.md : une seule famille, Inter, partout — jamais mélangée à une
// autre police d'affichage.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "AxeLCompta — démo produit",
  description: "Démo produit AxeLCompta : 3 dossiers chauffeur, calculs réels (doc 17, doc 19).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={inter.variable}>
      <body className="min-h-screen bg-canvas-app font-sans text-ink">
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex flex-1 flex-col">
            <TopBar />
            <main className="flex-1 p-6">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
