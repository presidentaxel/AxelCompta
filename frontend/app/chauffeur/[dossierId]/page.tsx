"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchAvecAuthChauffeur, obtenirSession } from "@/lib/auth-chauffeur";
import { formatMontant } from "@/lib/format";
import type { DossierResume, TransactionVue } from "@/lib/types";

type Chargement =
  | { statut: "en_cours" }
  | { statut: "pret"; dossier: DossierResume; transactions: TransactionVue[] }
  | { statut: "erreur"; message: string };

/** Vue chauffeur minimale (doc 19 §5.5 : « vocabulaire simple, pas le
 * vocabulaire comptable pro de la file de revue gestionnaire ») — lecture
 * seule. Répondre à une question de catégorisation, prendre une photo de
 * justificatif et signer restent la Semaine 3 du doc 17, pas cette page.
 */
export default function DossierChauffeurPage({ params }: { params: { dossierId: string } }) {
  const router = useRouter();
  const [chargement, setChargement] = useState<Chargement>({ statut: "en_cours" });

  useEffect(() => {
    const session = obtenirSession();
    if (session === null) {
      router.push("/chauffeur/login");
      return;
    }
    if (session.dossierId !== params.dossierId) {
      // Pas une 403 muette : on renvoie vers le seul dossier auquel ce
      // compte a effectivement accès (doc 19 §4).
      router.replace(`/chauffeur/${session.dossierId}`);
      return;
    }
    Promise.all([
      fetchAvecAuthChauffeur<DossierResume>(`/dossiers/${params.dossierId}`),
      fetchAvecAuthChauffeur<TransactionVue[]>(`/dossiers/${params.dossierId}/transactions`),
    ])
      .then(([dossier, transactions]) => setChargement({ statut: "pret", dossier, transactions }))
      .catch(() => setChargement({ statut: "erreur", message: "Impossible de charger vos données." }));
  }, [params.dossierId, router]);

  if (chargement.statut === "en_cours") {
    return <p className="text-sm text-subtle">Chargement…</p>;
  }
  if (chargement.statut === "erreur") {
    return <p className="text-sm text-danger">{chargement.message}</p>;
  }

  return (
    <div>
      <h1 className="mb-1 text-xl font-bold text-ink">Bonjour {chargement.dossier.nom}</h1>
      <p className="mb-6 text-sm text-subtle">Voici vos dernières transactions.</p>
      <ul className="space-y-2">
        {chargement.transactions.map((transaction) => (
          <TransactionLigne key={transaction.ecriture_id} transaction={transaction} />
        ))}
      </ul>
    </div>
  );
}

function TransactionLigne({ transaction }: { transaction: TransactionVue }) {
  const negatif = transaction.montant_cts < 0;
  const aVerifier = transaction.statut === "à trancher";
  return (
    <li className="flex items-center justify-between rounded-md border border-border bg-canvas px-3 py-2">
      <div>
        <p className="text-sm text-ink">{transaction.libelle}</p>
        <p className="text-xs text-subtle">
          {transaction.date} · {aVerifier ? "à vérifier" : "traité"}
        </p>
      </div>
      <span
        className={`tabular-nums text-sm font-medium ${
          negatif ? "text-amount-negative" : "text-amount-positive"
        }`}
      >
        {formatMontant(transaction.montant_cts)}
      </span>
    </li>
  );
}
