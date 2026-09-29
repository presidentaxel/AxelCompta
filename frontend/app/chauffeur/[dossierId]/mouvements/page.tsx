"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { use, useState } from "react";

import { DetailOperation } from "@/components/DetailOperation";
import { LigneOperation } from "@/components/LigneOperation";
import { Segments } from "@/components/Segments";
import { useDossierChauffeur } from "@/app/chauffeur/use-dossier";
import { formatMontant } from "@/lib/format";
import { grouperParJour, libelleJour, libelleMois } from "@/lib/operations-chauffeur";
import type { TransactionVue } from "@/lib/types";

/** Mouvements : les opérations, mois par mois comme un relevé, sorties ou
 * entrées. Chaque ligne s'ouvre pour voir le détail et ajouter un ticket. */
export default function MouvementsChauffeurPage({
  params,
}: {
  params: Promise<{ dossierId: string }>;
}) {
  const { dossierId } = use(params);
  const { charge, remplacer } = useDossierChauffeur(dossierId);
  const [moisChoisi, setMoisChoisi] = useState<string | null>(null);
  const [sens, setSens] = useState<"sorties" | "entrees">("sorties");
  const [ouverte, setOuverte] = useState<TransactionVue | null>(null);

  if (charge.statut === "en_cours") {
    return <p className="text-sm text-subtle">Chargement…</p>;
  }
  if (charge.statut === "erreur") {
    return <p className="text-sm text-danger">{charge.message}</p>;
  }

  const { transactions } = charge;
  const moisDispo = [
    ...new Set(transactions.map((transaction) => transaction.date.slice(0, 7))),
  ].sort();
  const mois = moisChoisi && moisDispo.includes(moisChoisi) ? moisChoisi : moisDispo.at(-1);
  const indexMois = mois ? moisDispo.indexOf(mois) : -1;
  const retenues = transactions.filter(
    (transaction) =>
      transaction.date.startsWith(mois ?? "") &&
      (sens === "sorties" ? transaction.montant_cts < 0 : transaction.montant_cts > 0),
  );
  const total = retenues.reduce((somme, transaction) => somme + transaction.montant_cts, 0);
  const jours = grouperParJour(retenues);
  const ouverteAJour = ouverte
    ? (transactions.find((transaction) => transaction.ecriture_id === ouverte.ecriture_id) ??
      ouverte)
    : null;

  return (
    <div>
      <h1 className="text-[22px] font-medium tracking-tight text-ink">Mouvements</h1>
      <div className="mt-4 flex items-center justify-between">
        <button
          type="button"
          aria-label="Mois précédent"
          disabled={indexMois <= 0}
          onClick={() => setMoisChoisi(moisDispo[indexMois - 1] ?? null)}
          className="-ml-2 flex h-10 w-10 items-center justify-center text-ink disabled:text-faint"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <p className="text-[15px] font-medium capitalize text-ink">
          {mois ? libelleMois(mois) : "Aucun mois"}
        </p>
        <button
          type="button"
          aria-label="Mois suivant"
          disabled={indexMois < 0 || indexMois >= moisDispo.length - 1}
          onClick={() => setMoisChoisi(moisDispo[indexMois + 1] ?? null)}
          className="-mr-2 flex h-10 w-10 items-center justify-center text-ink disabled:text-faint"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
      <div className="mt-2">
        <Segments
          valeur={sens}
          onChange={setSens}
          options={[
            { valeur: "sorties", libelle: "Sorties" },
            { valeur: "entrees", libelle: "Entrées" },
          ]}
        />
      </div>
      {jours.length > 0 && (
        <p className="mt-5 flex items-baseline justify-between text-xs text-muted">
          Total du mois
          <span
            className={`text-lg font-medium tabular-nums ${
              total < 0 ? "text-amount-negative" : "text-amount-positive"
            }`}
          >
            {formatMontant(total)}
          </span>
        </p>
      )}
      {jours.length === 0 ? (
        <p className="mt-6 text-sm text-subtle">
          {sens === "sorties" ? "Aucune sortie ce mois-ci." : "Aucune entrée ce mois-ci."}
        </p>
      ) : (
        jours.map(([jour, lignes]) => (
          <section key={jour} className="mt-5">
            <h2 className="text-[11px] font-semibold uppercase tracking-wider text-muted">
              {libelleJour(jour)}
            </h2>
            <div className="mt-1">
              {lignes.map((transaction) => (
                <LigneOperation
                  key={transaction.ecriture_id}
                  transaction={transaction}
                  onOuvrir={setOuverte}
                />
              ))}
            </div>
          </section>
        ))
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
