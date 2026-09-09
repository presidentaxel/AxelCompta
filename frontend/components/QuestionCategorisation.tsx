"use client";

import { useState } from "react";

import { ApiError } from "@/lib/api";
import { trancherTransactionChauffeur } from "@/lib/auth-chauffeur";
import type { TransactionVue } from "@/lib/types";

/** doc 19 §5.6 : « petites questions de catégorisation ... présentée
 * simplement » — même mécanisme que la file de revue gestionnaire
 * (`TrancherActions.tsx`, doc 17 §9 bloc C) mais sans le vocabulaire
 * comptable ("471", "reclasser") : une question fermée d'abord, un champ
 * libre seulement si la réponse est non. */
export function QuestionCategorisation({
  dossierId,
  ecritureId,
  onResolu,
}: {
  dossierId: string;
  ecritureId: string;
  onResolu: (transaction: TransactionVue) => void;
}) {
  const [autreCategorie, setAutreCategorie] = useState("");
  const [afficherAutre, setAfficherAutre] = useState(false);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function repondre(categorie: string) {
    if (!categorie.trim()) return;
    setEnCours(true);
    setErreur(null);
    try {
      const transaction = await trancherTransactionChauffeur(
        dossierId,
        ecritureId,
        categorie.trim(),
      );
      onResolu(transaction);
    } catch (exception) {
      setErreur(exception instanceof ApiError ? exception.message : "Échec de l'envoi.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="rounded-md border border-warning/40 bg-pending-subtle p-3">
      <p className="mb-2 text-sm font-medium text-ink">Cette dépense est-elle personnelle ?</p>
      {!afficherAutre ? (
        <div className="flex gap-2">
          <button
            type="button"
            disabled={enCours}
            onClick={() => repondre("usage_personnel")}
            className="rounded-md border border-border bg-canvas px-3 py-1 text-xs font-semibold text-ink hover:bg-canvas-app disabled:opacity-50"
          >
            Oui
          </button>
          <button
            type="button"
            disabled={enCours}
            onClick={() => setAfficherAutre(true)}
            className="rounded-md border border-border bg-canvas px-3 py-1 text-xs font-semibold text-ink hover:bg-canvas-app disabled:opacity-50"
          >
            Non
          </button>
        </div>
      ) : (
        <form
          className="flex items-center gap-2"
          onSubmit={(evenement) => {
            evenement.preventDefault();
            void repondre(autreCategorie);
          }}
        >
          <input
            type="text"
            value={autreCategorie}
            onChange={(evenement) => setAutreCategorie(evenement.target.value)}
            placeholder="à quoi correspond-elle ?"
            autoFocus
            disabled={enCours}
            className="min-w-0 flex-1 rounded-md border border-border px-2 py-1 text-xs"
          />
          <button
            type="submit"
            disabled={enCours || !autreCategorie.trim()}
            className="shrink-0 rounded-md border border-border bg-canvas px-2 py-1 text-xs font-semibold text-ink hover:bg-canvas-app disabled:opacity-50"
          >
            Envoyer
          </button>
        </form>
      )}
      {erreur && <p className="mt-1 text-xs text-danger">{erreur}</p>}
    </div>
  );
}
