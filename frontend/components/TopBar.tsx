"use client";

import { useRouter } from "next/navigation";

import { deconnecterGestionnaire } from "@/lib/auth-gestionnaire";

/** Top bar 56px (DESIGN.md). Pas de recherche ⌘K — hors scope pour 3
 * dossiers de démo (doc 17 §8). Bouton de déconnexion ajouté le 2026-09-21
 * avec l'auth gestionnaire (doc 03 §7).
 */
export function TopBar() {
  const router = useRouter();

  function seDeconnecter() {
    deconnecterGestionnaire();
    router.push("/connexion");
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-canvas px-6">
      <span className="text-sm font-semibold text-ink">Portefeuille — 3 dossiers de démo</span>
      <div className="flex items-center gap-4">
        <span className="text-xs text-subtle">Données synthétiques, calculs réels (doc 17 §4)</span>
        <button
          type="button"
          onClick={seDeconnecter}
          className="rounded-md border border-border px-2 py-1 text-xs font-semibold text-ink hover:bg-canvas-app"
        >
          Se déconnecter
        </button>
      </div>
    </header>
  );
}
