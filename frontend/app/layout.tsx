import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

// DESIGN.md : une seule famille, Inter, partout — jamais mélangée à une
// autre police d'affichage.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "AxeLCompta — démo produit",
  description: "Démo produit AxeLCompta : 3 dossiers chauffeur, calculs réels (doc 17, doc 19).",
};

// Habillage volontairement neutre ici (doc 19 §7 : « même socle, deux
// habillages ») — la Sidebar/TopBar gestionnaire vit dans
// `app/(gestionnaire)/layout.tsx`, l'habillage chauffeur dans
// `app/chauffeur/layout.tsx`. Rien de commun aux deux rôles à part la
// police et le fond.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={inter.variable}>
      <body className="min-h-screen bg-canvas-app font-sans text-ink">{children}</body>
    </html>
  );
}
