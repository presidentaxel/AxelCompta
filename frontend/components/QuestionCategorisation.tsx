"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { trancherTransactionChauffeur } from "@/lib/auth-chauffeur";
import type { TransactionVue } from "@/lib/types";

const RACCOURCIS = [
  ["dividendes", "Mes dividendes"],
  ["impots_dividendes", "Impôts sur mes dividendes"],
  ["cotisations_dirigeant", "Mes cotisations sociales"],
  ["prelevement_source_paie", "Impôt prélevé sur ma paie"],
] as const;

/** doc 19 §5.6 : « petites questions de catégorisation ... présentée
 * simplement » — même mécanisme de revue que doc 17 §9 bloc C (désormais
 * exclusivement indiv, doc 19 §2.1) mais sans le vocabulaire comptable
 * ("471", "reclasser") : trois réponses fermées d'abord (personnelle, sa
 * rémunération, autre chose), un champ libre seulement pour « autre chose ». */
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
      <p className="mb-2 text-sm font-medium text-ink">À quoi correspond cette dépense ?</p>
      {!afficherAutre ? (
        <div className="flex gap-2">
          <Button
            type="button"
            variant="secondary"
            className="h-11 flex-1"
            disabled={enCours}
            onClick={() => repondre("usage_personnel")}
          >
            Personnelle
          </Button>
          {/* Louis, 2026-09-26 : le chauffeur se paie et catégorise sa paie
              lui-même ; le compte (641, 644, 108) dépend de sa forme. */}
          <Button
            type="button"
            variant="secondary"
            className="h-11 flex-1"
            disabled={enCours}
            onClick={() => repondre("remuneration_dirigeant")}
          >
            Ma rémunération
          </Button>
          <Button
            type="button"
            variant="secondary"
            className="h-11 flex-1"
            disabled={enCours}
            onClick={() => setAfficherAutre(true)}
          >
            Autre chose
          </Button>
        </div>
      ) : (
        <div>
          {/* Catégories dont le compte dépend du statut : l'API répond
              clairement si elle ne s'applique pas à ce dossier. */}
          <div className="mb-2 flex flex-wrap gap-1.5">
            {RACCOURCIS.map(([categorie, libelle]) => (
              <Button
                key={categorie}
                type="button"
                variant="secondary"
                size="sm"
                disabled={enCours}
                onClick={() => repondre(categorie)}
              >
                {libelle}
              </Button>
            ))}
          </div>
          <form
            className="flex items-center gap-2"
            onSubmit={(evenement) => {
              evenement.preventDefault();
              void repondre(autreCategorie);
            }}
          >
            <Input
              type="text"
              value={autreCategorie}
              onChange={(evenement) => setAutreCategorie(evenement.target.value)}
              placeholder="à quoi correspond-elle ?"
              autoFocus
              disabled={enCours}
              className="h-7 min-w-0 flex-1 text-xs"
            />
            <Button
              type="submit"
              variant="secondary"
              size="sm"
              disabled={enCours || !autreCategorie.trim()}
              className="shrink-0"
            >
              Envoyer
            </Button>
          </form>
        </div>
      )}
      {erreur && <p className="mt-1 text-xs text-danger">{erreur}</p>}
    </div>
  );
}
