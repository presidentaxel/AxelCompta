"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchAvecAuthChauffeur, obtenirSession } from "@/lib/auth-chauffeur";
import type { DossierResume, TransactionVue } from "@/lib/types";

export type DossierCharge =
  | { statut: "en_cours" }
  | { statut: "pret"; dossier: DossierResume; transactions: TransactionVue[] }
  | { statut: "erreur"; message: string };

/** Charge le dossier du chauffeur connecté. Une autre adresse que la sienne
 * renvoie vers son dossier, pas une page d'erreur. `remplacer` met à jour
 * une opération déjà affichée (photo, réponse) sans recharger la page. */
export function useDossierChauffeur(dossierId: string): {
  charge: DossierCharge;
  remplacer: (transaction: TransactionVue) => void;
} {
  const router = useRouter();
  const [charge, setCharge] = useState<DossierCharge>({ statut: "en_cours" });

  useEffect(() => {
    const session = obtenirSession();
    if (session === null) {
      router.push("/chauffeur/login");
      return;
    }
    if (session.dossierId !== dossierId) {
      router.replace(`/chauffeur/${session.dossierId}`);
      return;
    }
    Promise.all([
      fetchAvecAuthChauffeur<DossierResume>(`/dossiers/${dossierId}`),
      fetchAvecAuthChauffeur<TransactionVue[]>(`/dossiers/${dossierId}/transactions`),
    ])
      .then(([dossier, transactions]) => setCharge({ statut: "pret", dossier, transactions }))
      .catch(() => setCharge({ statut: "erreur", message: "Impossible de charger vos données." }));
  }, [dossierId, router]);

  function remplacer(transaction: TransactionVue) {
    setCharge((etat) =>
      etat.statut === "pret"
        ? {
            ...etat,
            transactions: etat.transactions.map((ligne) =>
              ligne.ecriture_id === transaction.ecriture_id ? transaction : ligne,
            ),
          }
        : etat,
    );
  }

  return { charge, remplacer };
}
