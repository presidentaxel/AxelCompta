"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { FileText, House, List, UserRound } from "lucide-react";

import { Cloche } from "@/components/Cloche";
import { Marque } from "@/components/Marque";
import { obtenirSession, type SessionChauffeur } from "@/lib/auth-chauffeur";

/** Pages d'entrée : pas de navigation, même si une session traîne encore
 * dans le navigateur. */
const PAGES_PUBLIQUES = new Set(["/chauffeur/login", "/chauffeur/accepter-invitation"]);

/** Habillage chauffeur - webapp téléphone, lisible aussi sur un grand
 * écran (colonne centrée). Thème mobile (`.theme-mobile`) : marque, quatre
 * onglets en bas. Pas de Sidebar. */
export default function ChauffeurLayout({ children }: { children: React.ReactNode }) {
  const chemin = usePathname();
  const [session, setSession] = useState<SessionChauffeur | null>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSession(obtenirSession());
  }, [chemin]);

  const espace = session !== null && !PAGES_PUBLIQUES.has(chemin);
  // Le classement prend tout l'écran : pas de barre du bas pendant qu'on trie.
  const immersif = chemin.endsWith("/classer");

  return (
    <div className="theme-mobile min-h-screen bg-canvas-app">
      <header className="sticky top-0 z-10 border-b border-border bg-canvas-app/95 backdrop-blur">
        <div className="mx-auto flex h-12 max-w-md items-center px-5">
          <Marque />
          {espace && session && <Cloche dossierId={session.dossierId} chemin={chemin} />}
        </div>
      </header>
      <main className={`mx-auto min-w-0 max-w-md overflow-x-clip px-5 py-6 ${espace && !immersif ? "pb-24" : ""}`}>
        {children}
      </main>
      {espace && !immersif && session && <Barre dossierId={session.dossierId} chemin={chemin} />}
    </div>
  );
}

function Barre({ dossierId, chemin }: { dossierId: string; chemin: string }) {
  const accueil = `/chauffeur/${dossierId}`;
  const mouvements = `${accueil}/mouvements`;
  const exercice = `${accueil}/exercice`;
  const compte = "/chauffeur/compte";
  const liens = [
    { href: accueil, libelle: "Accueil", Icone: House, actif: chemin === accueil },
    { href: mouvements, libelle: "Mouvements", Icone: List, actif: chemin === mouvements },
    {
      href: exercice,
      libelle: "Exercice",
      Icone: FileText,
      actif: chemin === exercice || chemin === `${accueil}/resultat`,
    },
    { href: compte, libelle: "Compte", Icone: UserRound, actif: chemin === compte },
  ];

  return (
    <nav className="fixed bottom-0 left-1/2 z-10 w-full max-w-md -translate-x-1/2 border-t border-border bg-canvas/95 backdrop-blur">
      <div className="grid grid-cols-4 pb-[env(safe-area-inset-bottom)]">
        {liens.map(({ href, libelle, Icone, actif }) => (
          <Link
            key={href}
            href={href}
            aria-current={actif ? "page" : undefined}
            className={`flex h-14 flex-col items-center justify-center gap-0.5 text-[10.5px] font-medium ${
              actif ? "text-ink" : "text-muted"
            }`}
          >
            <Icone className="h-[22px] w-[22px]" strokeWidth={1.7} aria-hidden />
            {libelle}
          </Link>
        ))}
      </div>
    </nav>
  );
}
