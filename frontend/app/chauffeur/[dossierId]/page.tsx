"use client";

import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { use, useState } from "react";

import { Button } from "@/components/ui/button";
import { DetailOperation } from "@/components/DetailOperation";
import { LigneOperation } from "@/components/LigneOperation";
import { StationTickets } from "@/components/StationTickets";
import { useDossierChauffeur } from "@/app/chauffeur/use-dossier";
import { aTrancher } from "@/lib/operations-chauffeur";
import type { TransactionVue } from "@/lib/types";

const RECENTES = 5;

/** Accueil : ce qu'il reste à faire, en une phrase et une action. Le détail
 * des opérations vit dans Mouvements ; le résultat, dans Exercice. */
export default function AccueilChauffeurPage({
  params,
}: {
  params: Promise<{ dossierId: string }>;
}) {
  const { dossierId } = use(params);
  const { charge, remplacer } = useDossierChauffeur(dossierId);
  const [ouverte, setOuverte] = useState<TransactionVue | null>(null);

  if (charge.statut === "en_cours") {
    return <p className="text-sm text-subtle">Chargement…</p>;
  }
  if (charge.statut === "erreur") {
    return <p className="text-sm text-danger">{charge.message}</p>;
  }

  const { dossier, transactions } = charge;
  const nbATrier = aTrancher(transactions).length;
  const dernierMois = transactions
    .map((transaction) => transaction.date.slice(0, 7))
    .sort()
    .at(-1);
  const depenses = dernierMois
    ? transactions.filter(
        (transaction) => transaction.montant_cts < 0 && transaction.date.startsWith(dernierMois),
      )
    : [];
  const ticketsManquants = depenses.some((depense) => !depense.a_justificatif);
  const recentes = [...transactions]
    .sort((a, b) => b.date.localeCompare(a.date))
    .slice(0, RECENTES);
  // La feuille suit la version à jour de l'opération (photo jointe).
  const ouverteAJour = ouverte
    ? (transactions.find((transaction) => transaction.ecriture_id === ouverte.ecriture_id) ??
      ouverte)
    : null;

  return (
    <div>
      <p className="text-xs text-muted">
        {dossier.forme_juridique} - {dossier.regime_libelle}
      </p>
      <h1 className="mt-1 text-[22px] font-medium tracking-tight text-ink">{dossier.nom}</h1>

      <ConnexionBancaire
        peutConnecter={dossier.peut_connecter_sa_banque}
        aDesTransactions={transactions.length > 0}
      />

      <section className="mt-8">
        {nbATrier > 0 ? (
          <>
            <p className="text-xs text-muted">Il reste à classer</p>
            <p className="mt-1 text-[38px] font-normal leading-none tabular-nums tracking-tight text-ink">
              {nbATrier}
            </p>
            <p className="mt-2 text-sm text-subtle">
              {nbATrier === 1 ? "opération" : "opérations"} pour finir l&apos;exercice. On vous les
              présente une par une.
            </p>
            <Button asChild className="cta mt-4">
              <Link href={`/chauffeur/${dossierId}/classer`}>Commencer le classement</Link>
            </Button>
          </>
        ) : (
          <>
            <p className="text-[22px] font-medium tracking-tight text-ink">Tout est à jour.</p>
            <p className="mt-1 text-sm text-subtle">Aucune opération n&apos;attend de classement.</p>
          </>
        )}
      </section>

      {dernierMois && ticketsManquants && (
        <div className="mt-8 rounded-lg bg-surface-soft px-4 pb-4">
          <StationTickets
            dossierId={dossierId}
            mois={dernierMois}
            depenses={depenses}
            onJointe={remplacer}
          />
        </div>
      )}

      {recentes.length > 0 && (
        <section className="mt-8">
          <div className="flex items-center justify-between">
            <h2 className="text-[15px] font-medium text-ink">Dernières opérations</h2>
            <Link
              href={`/chauffeur/${dossierId}/mouvements`}
              className="flex min-h-11 items-center text-sm font-medium text-primary"
            >
              Tout voir
              <ChevronRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
          <div className="mt-1">
            {recentes.map((transaction) => (
              <LigneOperation
                key={transaction.ecriture_id}
                transaction={transaction}
                avecDate
                onOuvrir={setOuverte}
              />
            ))}
          </div>
        </section>
      )}

      {ouverteAJour && (
        <DetailOperation
          dossierId={dossierId}
          transaction={ouverteAJour}
          onFermer={() => setOuverte(null)}
          onJointe={remplacer}
        />
      )}
    </div>
  );
}

function ConnexionBancaire({
  peutConnecter,
  aDesTransactions,
}: {
  peutConnecter: boolean;
  aDesTransactions: boolean;
}) {
  if (peutConnecter) {
    return (
      <Button
        type="button"
        variant="secondary"
        className="mt-5 w-full"
        disabled
        title="Bientôt disponible"
      >
        Connecter ma banque
      </Button>
    );
  }
  if (!aDesTransactions) {
    return <p className="mt-5 text-sm text-subtle">Vos transactions arrivent bientôt.</p>;
  }
  return null;
}
