"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialogue } from "@/components/Dialogue";
import { ApiError } from "@/lib/api";
import { joindreJustificatifChauffeur } from "@/lib/auth-chauffeur";
import { formatMontant } from "@/lib/format";
import { libelleJour, presenter } from "@/lib/operations-chauffeur";
import type { TransactionVue } from "@/lib/types";

/** Détail d'une opération, en feuille par-dessus la liste. Une sortie sans
 * ticket propose la photo ; le contenu n'est jamais lu, seule la présence
 * compte. */
export function DetailOperation({
  dossierId,
  transaction,
  onFermer,
  onJointe,
}: {
  dossierId: string;
  transaction: TransactionVue;
  onFermer: () => void;
  onJointe: (transaction: TransactionVue) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const { nom, detail } = presenter(transaction.libelle);
  const negatif = transaction.montant_cts < 0;

  async function envoyer(fichier: File) {
    setEnvoi(true);
    setErreur(null);
    try {
      onJointe(await joindreJustificatifChauffeur(dossierId, transaction.ecriture_id, fichier));
    } catch (exception) {
      setErreur(exception instanceof ApiError ? exception.message : "Échec de l'envoi de la photo.");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <Dialogue titre={nom} titreId="detail-operation" onFermer={onFermer}>
      <p className="mt-1 text-xs text-muted">
        {libelleJour(transaction.date.slice(0, 10))} - {negatif ? "Sortie" : "Entrée"}
      </p>
      <p
        className={`mt-2 text-[32px] font-normal tabular-nums tracking-tight ${
          negatif ? "text-amount-negative" : "text-amount-positive"
        }`}
      >
        {formatMontant(transaction.montant_cts)}
      </p>
      <dl className="mt-5 divide-y divide-hairline rounded-lg bg-surface-soft px-4 text-sm">
        <div className="flex justify-between py-2.5">
          <dt className="text-subtle">Catégorie</dt>
          <dd className="font-medium text-ink">
            {transaction.statut === "à trancher" ? "À classer" : (detail ?? "Classée")}
          </dd>
        </div>
        {negatif && (
          <div className="flex justify-between py-2.5">
            <dt className="text-subtle">Ticket</dt>
            <dd className="font-medium text-ink">
              {transaction.a_justificatif ? "Joint" : "Manquant"}
            </dd>
          </div>
        )}
      </dl>
      {negatif && !transaction.a_justificatif && (
        <>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(evenement) => {
              const fichier = evenement.target.files?.[0];
              if (fichier) void envoyer(fichier);
              evenement.target.value = "";
            }}
          />
          <Button
            type="button"
            className="cta mt-5 w-full"
            disabled={envoi}
            onClick={() => inputRef.current?.click()}
          >
            {envoi ? "Envoi…" : "Ajouter le ticket"}
          </Button>
        </>
      )}
      {erreur && <p className="mt-2 text-xs text-danger">{erreur}</p>}
      <Button type="button" variant="ghost" className="mt-2 w-full" onClick={onFermer}>
        Fermer
      </Button>
    </Dialogue>
  );
}
