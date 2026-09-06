import Link from "next/link";

import { Badge } from "@/components/Badge";
import { listerDossiers } from "@/lib/api";
import { formatMontant } from "@/lib/format";
import type { DossierResume } from "@/lib/types";

export default async function DashboardPage() {
  const dossiers = await listerDossiers();

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-1 text-2xl font-bold text-ink">Tableau de bord</h1>
      <p className="mb-6 text-sm text-subtle">
        3 dossiers de démo (doc 17 §4) — données synthétiques mais réalistes, calculs réels.
      </p>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {dossiers.map((dossier) => (
          <DossierCard key={dossier.dossier_id} dossier={dossier} />
        ))}
      </div>
    </div>
  );
}

function DossierCard({ dossier }: { dossier: DossierResume }) {
  return (
    <Link
      href={`/dossiers/${dossier.dossier_id}`}
      className="block rounded-lg border border-border bg-canvas p-5 shadow-sm transition-shadow hover:shadow-md"
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-base font-semibold text-ink">{dossier.nom}</span>
        {dossier.nb_a_trancher > 0 && (
          <Badge variant="pending">{dossier.nb_a_trancher} à trancher</Badge>
        )}
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge variant="neutral">{dossier.tva_recettes_regime}</Badge>
        {dossier.plateformes.map((plateforme) => (
          <Badge key={plateforme} variant="neutral">
            {plateforme}
          </Badge>
        ))}
      </div>
      <dl className="space-y-1.5 text-sm">
        <AmountRow label="CA HT" cents={dossier.ca_ht_cts} />
        <AmountRow label="Charges" cents={dossier.charges_cts} />
        <AmountRow label="Résultat" cents={dossier.resultat_cts} emphasise />
      </dl>
    </Link>
  );
}

function AmountRow({
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
