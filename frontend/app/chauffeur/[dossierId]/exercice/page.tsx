"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { ClotureExerciceSection } from "@/components/ClotureExerciceSection";
import { ClotureSection } from "@/components/ClotureSection";
import { GreffeInpiSection } from "@/components/GreffeInpiSection";
import { useDossierChauffeur } from "@/app/chauffeur/use-dossier";
import { fetchAvecAuthChauffeur } from "@/lib/auth-chauffeur";
import { formatDate } from "@/lib/format";
import type { AffectationVue } from "@/lib/types";

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
      {[dossier.alerte_regime, dossier.alerte_tva]
        .filter((alerte): alerte is string => alerte !== null)
        .map((alerte) => (
          <p
            key={alerte}
            className="mt-4 rounded-md border border-border bg-canvas p-3 text-sm text-ink"
          >
            {alerte}
          </p>
        ))}
      {dossier.regimes_a_venir.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm text-subtle">
          {dossier.regimes_a_venir.map((changement) => (
            <li key={changement.exercice}>
              Exercice {changement.exercice} : {changement.regime} ({changement.motif})
            </li>
          ))}
        </ul>
      )}
      <div className="mt-8">
        <ClotureSection dossier={dossier} />
        {dossier.depot_greffe && <GreffeInpiSection dossier={dossier} />}
        <ClotureExerciceSection dossierId={dossierId} onClos={() => window.location.reload()} />
        <LienAffectation dossierId={dossierId} />
      </div>
    </div>
  );
}

/** Après la clôture : l'affectation du résultat se décide sur son propre
 * écran (Louis, 2026-09-26). Rien ne s'affiche tant qu'il n'y a rien à
 * décider. */
function LienAffectation({ dossierId }: { dossierId: string }) {
  const [vue, setVue] = useState<AffectationVue | null>(null);

  useEffect(() => {
    fetchAvecAuthChauffeur<AffectationVue>(`/dossiers/${dossierId}/affectation`)
      .then(setVue)
      .catch(() => setVue(null));
  }, [dossierId]);

  if (!vue?.applicable) {
    return null;
  }
  return (
    <Link
      href={`/chauffeur/${dossierId}/resultat`}
      className="mt-8 block rounded-md border border-border bg-canvas p-3 text-sm text-ink"
    >
      Décider de l&apos;affectation de mon résultat {vue.annee_exercice} →
    </Link>
  );
}
