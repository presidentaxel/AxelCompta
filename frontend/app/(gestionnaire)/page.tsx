import { Badge } from "@/components/Badge";
import { InvitationActions } from "@/components/InvitationActions";
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

// doc 19 §2.1/§6 (révision 2026-09-11) : cette carte EST l'état des lieux
// gestionnaire, pas une porte d'entrée vers un détail — il n'y a plus de
// fiche dossier gestionnaire à ouvrir (le détail est exclusivement indiv,
// doc 19 §5). D'où l'absence de `Link` ici, retiré le 2026-09-11 (avant :
// toute la carte menait à `/dossiers/{id}`).
function DossierCard({ dossier }: { dossier: DossierResume }) {
  return (
    <div className="rounded-lg border border-border bg-canvas p-5 shadow-sm">
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
        {/* doc 19 §4 : les deux modes doivent être visibles à l'écran,
         * pas cachés dans un réglage — même logique que les autres badges. */}
        <Badge variant="neutral">
          {dossier.mode_acces_bancaire === "chauffeur_direct"
            ? "Banque : chauffeur"
            : "Banque : gestionnaire"}
        </Badge>
      </div>
      <dl className="space-y-1.5 text-sm">
        <AmountRow label="CA HT" cents={dossier.ca_ht_cts} />
        <AmountRow label="Charges" cents={dossier.charges_cts} />
        <AmountRow label="Résultat" cents={dossier.resultat_cts} emphasise />
      </dl>
      {/* Onboarding chauffeur : premier rang, pas caché dans un écran de
       * paramètres (doc 19 §3.2). */}
      <div className="mt-4 border-t border-border pt-3">
        <InvitationActions dossier={dossier} />
      </div>
    </div>
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
