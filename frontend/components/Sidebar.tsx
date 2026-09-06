import Link from "next/link";

/** Sidebar sombre 240px (DESIGN.md — le seul endroit sombre de l'app en V1).
 * Pas de liste de dossiers ici : la démo n'a que 3 dossiers, tous sur le
 * tableau de bord — la vraie navigation portefeuille (doc 11 §2) viendra
 * quand ça sera nécessaire, pas avant.
 */
export function Sidebar() {
  return (
    <aside className="w-60 shrink-0 bg-surface-dark px-2 py-3 text-white">
      <div className="border-b border-white/10 px-3 pb-2 pt-1 text-sm font-semibold">
        AxeLCompta
      </div>
      <nav className="mt-3 flex flex-col gap-1">
        <Link
          href="/"
          className="rounded-md px-3 py-2 text-sm font-medium text-white/80 transition-colors hover:bg-white/10 hover:text-white"
        >
          Tableau de bord
        </Link>
      </nav>
      <div className="mt-4 px-3 text-[11px] uppercase tracking-wide text-white/40">
        Démo — doc 17 / doc 19
      </div>
    </aside>
  );
}
