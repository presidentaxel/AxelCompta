"use client";

// doc 17 §9 Semaine 4 : compte de résultat + bilan simplifié + exports de
// clôture. **Déplacé le 2026-09-11** (doc 19 §2.1/§5.3) : sur la fiche
// dossier indiv, pas gestionnaire — le gestionnaire n'a plus de fiche
// dossier détaillée du tout, seulement l'agrégat du dashboard.
//
// **Boutons plutôt que `<a href>` depuis le 2026-09-11** (doc 19 §8bis) :
// ces routes exigent maintenant un jeton indiv — un lien direct ne peut
// pas porter l'en-tête `Authorization` et échouerait en 401.
// `telechargerAvecAuthChauffeur` fait le fetch authentifié puis déclenche
// l'enregistrement.
import { useState } from "react";

import { cheminTelechargementCloture } from "@/lib/api";
import { ErreurAuthChauffeur, telechargerAvecAuthChauffeur } from "@/lib/auth-chauffeur";
import { formatMontant } from "@/lib/format";
import type { DocumentCloture, DossierResume } from "@/lib/types";

const DOCUMENTS: Array<{ document: DocumentCloture; label: string }> = [
  { document: "liasse.pdf", label: "Liasse (PDF)" },
  { document: "cerfa-2065.pdf", label: "CERFA 2065 (PDF)" },
  { document: "fec.txt", label: "FEC" },
  { document: "grand-livre.csv", label: "Grand livre (CSV)" },
  { document: "balance.csv", label: "Balance (CSV)" },
];

export function ClotureSection({ dossier }: { dossier: DossierResume }) {
  const [erreur, setErreur] = useState<string | null>(null);

  async function telecharger(document: DocumentCloture) {
    setErreur(null);
    // Même schéma de nom que le Content-Disposition côté serveur
    // (demo_api.py : "liasse-{dossier_id}.pdf" etc.) — utile dès qu'on
    // télécharge plusieurs dossiers dans le même dossier de téléchargements.
    const [nom, extension] = document.split(/\.(?=[^.]+$)/);
    const nomFichier = `${nom}-${dossier.dossier_id}.${extension}`;
    try {
      await telechargerAvecAuthChauffeur(
        cheminTelechargementCloture(dossier.dossier_id, document),
        nomFichier,
      );
    } catch (exception) {
      setErreur(
        exception instanceof ErreurAuthChauffeur
          ? exception.message
          : "Échec du téléchargement.",
      );
    }
  }

  return (
    <div className="mb-6 grid grid-cols-1 gap-6 rounded-lg border border-border bg-canvas p-5 shadow-sm md:grid-cols-2">
      <div>
        <SousTitre>Compte de résultat</SousTitre>
        <dl className="space-y-1.5 text-sm">
          <Ligne label="CA HT" cents={dossier.ca_ht_cts} />
          <Ligne label="Charges" cents={dossier.charges_cts} />
          <Ligne label="Résultat" cents={dossier.resultat_cts} emphasise />
        </dl>
        <div className="mt-5">
          <SousTitre>Bilan (simplifié)</SousTitre>
          <dl className="space-y-1.5 text-sm">
            <Ligne label="Trésorerie" cents={dossier.tresorerie_cts} />
            <Ligne label="TVA à payer" cents={dossier.tva_a_payer_cts} />
          </dl>
        </div>
      </div>
      <div>
        <SousTitre>Documents de clôture</SousTitre>
        <ul className="space-y-2 text-sm">
          {DOCUMENTS.map(({ document, label }) => (
            <li key={document}>
              <button
                type="button"
                onClick={() => void telecharger(document)}
                className="text-primary hover:underline"
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
        {erreur && <p className="mt-2 text-xs text-danger">{erreur}</p>}
        <p className="mt-3 text-xs text-subtle">
          Démo — liasse simplifiée, pas conforme CERFA/DGFiP (doc 17 §3).
        </p>
      </div>
    </div>
  );
}

function SousTitre({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-subtle">{children}</h2>
  );
}

function Ligne({
  label,
  cents,
  emphasise,
}: {
  label: string;
  cents: number;
  emphasise?: boolean;
}) {
  const negatif = cents < 0;
  return (
    <div className="flex items-baseline justify-between">
      <dt className="text-subtle">{label}</dt>
      <dd
        className={`tabular-nums text-right ${emphasise ? "font-semibold" : ""} ${
          negatif ? "text-amount-negative" : emphasise ? "text-amount-positive" : "text-ink"
        }`}
      >
        {formatMontant(cents)}
      </dd>
    </div>
  );
}
