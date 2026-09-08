"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { deconnecter, obtenirSession } from "@/lib/auth-chauffeur";

/** Habillage chauffeur (mobile/webapp) — doc 19 §7 : même socle Next.js/
 * Tailwind que le gestionnaire, habillage différent, pas de Sidebar/TopBar
 * portefeuille (DESIGN.md « Comportement responsive » : la démo mobile est
 * une page publique autonome, comme la signature). Vocabulaire simple
 * (doc 19 §5.5), un seul niveau de navigation (déconnexion).
 */
export default function ChauffeurLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [connecte, setConnecte] = useState(false);

  useEffect(() => {
    setConnecte(obtenirSession() !== null);
  }, []);

  function seDeconnecter() {
    deconnecter();
    router.push("/chauffeur/login");
  }

  return (
    <div className="min-h-screen bg-canvas-app">
      <header className="flex items-center justify-between border-b border-border bg-canvas px-4 py-3">
        <span className="text-base font-semibold text-ink">AxeLCompta</span>
        {connecte && (
          <button
            type="button"
            onClick={seDeconnecter}
            className="text-xs font-medium text-subtle hover:text-ink"
          >
            Déconnexion
          </button>
        )}
      </header>
      <main className="mx-auto max-w-md px-4 py-6">{children}</main>
    </div>
  );
}
