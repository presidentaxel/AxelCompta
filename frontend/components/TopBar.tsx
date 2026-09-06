/** Top bar 56px (DESIGN.md). Pas de recherche ⌘K ni de menu utilisateur —
 * hors scope pour 3 dossiers de démo (doc 17 §8, pas de self-signup).
 */
export function TopBar() {
  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-canvas px-6">
      <span className="text-sm font-semibold text-ink">Portefeuille — 3 dossiers de démo</span>
      <span className="text-xs text-subtle">Données synthétiques, calculs réels (doc 17 §4)</span>
    </header>
  );
}
