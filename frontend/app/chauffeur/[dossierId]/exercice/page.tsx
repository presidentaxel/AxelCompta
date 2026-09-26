"use client";

import { use } from "react";

import { ClotureSection } from "@/components/ClotureSection";
import { GreffeInpiSection } from "@/components/GreffeInpiSection";
import { useDossierChauffeur } from "@/app/chauffeur/use-dossier";
import { formatDate } from "@/lib/format";

/** Exercice : le résultat, les documents, le dépôt et la signature.
 * Séparé de l'activité pour que le téléphone s'ouvre sur les opérations. */
export default function ExerciceChauffeurPage({
  params,
}: {
  params: Promise<{ dossierId: string }>;
}) {
  const { dossierId } = use(params);
  const { charge } = useDossierChauffeur(dossierId);

  if (charge.statut === "en_cours") {
    return <p className="text-sm text-subtle">Chargement…</p>;
  }
  if (charge.statut === "erreur") {
    return <p className="text-sm text-danger">{charge.message}</p>;
  }

  const { dossier } = charge;
  const periode =
    dossier.exercice_debut && dossier.exercice_fin
      ? `${formatDate(dossier.exercice_debut)} – ${formatDate(dossier.exercice_fin)}`
      : null;

  return (
    <div>
      <h1 className="text-[28px] font-bold tracking-tight text-ink">Exercice</h1>
      {periode && <p className="mt-2 text-sm text-subtle">{periode}</p>}
      <div className="mt-8">
        <ClotureSection dossier={dossier} />
        {dossier.depot_greffe && <GreffeInpiSection dossier={dossier} />}
      </div>
    </div>
  );
}
