"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { trancherEnGroupeChauffeur } from "@/lib/auth-chauffeur";
import { formatMontant } from "@/lib/format";

/** « Tout confirmer » : des opérations qui ressemblent à ce que le chauffeur a
 * déjà classé lui-même. Il voit la liste avant de confirmer ; l'API écrit
 * toutes les décisions ou aucune. */
export function ConfirmationGroupee({
  dossierId,
  categorie,
  libelle,
  operations,
  onConfirme,
}: {
  dossierId: string;
  categorie: string;
  libelle: string;
  operations: { ecritureId: string; nom: string; montantCts: number }[];
  onConfirme: () => void;
}) {
  const [ouvert, setOuvert] = useState(false);
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  async function confirmer() {
    setEnCours(true);
    setErreur(null);
    try {
      await trancherEnGroupeChauffeur(
        dossierId,
        operations.map((operation) => operation.ecritureId),
        categorie,
      );
      onConfirme();
    } catch (exception) {
      setErreur(exception instanceof ApiError ? exception.message : "Échec de l'envoi.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="rounded-lg border border-primary/20 bg-primary-subtle p-4">
      <p className="text-sm font-medium text-ink">On a repéré un motif</p>
      <p className="mt-2 text-sm text-ink">
        <b className="font-semibold">{operations.length} opérations</b> ressemblent à celles que
        vous avez classées en « {libelle} ». Les classer aussi ?
      </p>
      {ouvert && (
        <ul className="mt-3 max-h-64 overflow-y-auto text-xs text-subtle">
          {operations.map((operation) => (
            <li key={operation.ecritureId} className="flex justify-between gap-3 py-1">
              <span className="min-w-0 truncate">{operation.nom}</span>
              <span className="shrink-0 tabular-nums">{formatMontant(operation.montantCts)}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-4 flex flex-col gap-1.5">
        <Button
          type="button"
          className="h-auto min-h-10 w-full px-3 whitespace-normal!"
          disabled={enCours}
          onClick={() => void confirmer()}
        >
          {enCours ? "Envoi…" : `Tout classer (${operations.length})`}
        </Button>
        <Button
          type="button"
          variant="ghost"
          className="w-full"
          disabled={enCours}
          onClick={() => setOuvert(!ouvert)}
        >
          {ouvert ? "Masquer la liste" : "Voir la liste d'abord"}
        </Button>
      </div>
      {erreur && <p className="mt-1 text-xs text-danger">{erreur}</p>}
    </div>
  );
}
