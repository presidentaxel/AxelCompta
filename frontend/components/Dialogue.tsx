"use client";

import { useEffect, type ReactNode } from "react";

/** Feuille du bas, au-dessus de la barre. Échap et le fond ferment. */
export function Dialogue({
  titre,
  titreId,
  onFermer,
  children,
}: {
  titre: string;
  titreId: string;
  onFermer: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    function onTouche(event: KeyboardEvent) {
      if (event.key === "Escape") onFermer();
    }
    document.addEventListener("keydown", onTouche);
    return () => document.removeEventListener("keydown", onTouche);
  }, [onFermer]);

  return (
    <div
      className="fixed inset-0 z-20 flex items-end justify-center bg-ink/35"
      onClick={onFermer}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titreId}
        className="w-full max-w-md rounded-t-xl border-t border-border bg-canvas px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-3"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-border-strong" aria-hidden />
        <h2 id={titreId} className="text-base font-medium text-ink">
          {titre}
        </h2>
        {children}
      </div>
    </div>
  );
}
