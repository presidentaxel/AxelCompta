// doc 17 §9 Semaine 4 : compte de résultat + bilan simplifié + liens de
// téléchargement des exports de clôture. **Déplacé le 2026-09-11** (doc 19
// §2.1/§5.3) : sur la fiche dossier indiv, pas gestionnaire — le
// gestionnaire n'a plus de fiche dossier détaillée du tout, seulement
// l'agrégat du dashboard.
import { urlTelechargementCloture } from "@/lib/api";
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
              <a
                href={urlTelechargementCloture(dossier.dossier_id, document)}
                className="text-primary hover:underline"
              >
                {label}
              </a>
            </li>
          ))}
        </ul>
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
