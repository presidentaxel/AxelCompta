"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, trancherTransaction } from "@/lib/api";

/** doc 17 §9 bloc C : la décision humaine, pour de vrai — le clic appelle
 * `workflow` via l'API (doc 05 §5), pas un simple changement de badge côté
 * React. `router.refresh()` re-tire les données du serveur après succès :
 * pas d'état local qui pourrait diverger de ce que Postgres a vraiment
 * enregistré. */
export function TrancherActions({
  dossierId,
  ecritureId,
}: {
  dossierId: string;
  ecritureId: string;
}) {
  const router = useRouter();
  const [autreCategorie, setAutreCategorie] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function trancher(categorie: string) {
    if (!categorie.trim()) return;
    setEnCours(true);
    setErreur(null);
    try {
      await trancherTransaction(dossierId, ecritureId, categorie.trim());
      router.refresh();
    } catch (exception) {
      setErreur(exception instanceof ApiError ? exception.message : "Échec de la décision.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={enCours}
          onClick={() => trancher("usage_personnel")}
          className="rounded-md border border-warning/40 bg-pending-subtle px-2 py-1 text-xs font-semibold text-pending hover:bg-pending-subtle/70 disabled:opacity-50"
        >
          Usage personnel
        </button>
        <form
          className="flex items-center gap-1"
          onSubmit={(evenement) => {
            evenement.preventDefault();
            void trancher(autreCategorie);
          }}
        >
          <input
            type="text"
            value={autreCategorie}
            onChange={(evenement) => setAutreCategorie(evenement.target.value)}
            placeholder="autre catégorie…"
            disabled={enCours}
            className="w-32 rounded-md border border-border px-2 py-1 text-xs"
          />
          <button
            type="submit"
            disabled={enCours || !autreCategorie.trim()}
            className="rounded-md border border-border px-2 py-1 text-xs font-semibold text-ink hover:bg-canvas-app disabled:opacity-50"
          >
            Reclasser
          </button>
        </form>
      </div>
      {erreur && <p className="text-xs text-danger">{erreur}</p>}
    </div>
  );
}
