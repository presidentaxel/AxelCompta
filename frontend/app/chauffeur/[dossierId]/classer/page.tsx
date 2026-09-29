"use client";

import { Check, ChevronLeft } from "lucide-react";
import Link from "next/link";
import { use, useState } from "react";

import { Button } from "@/components/ui/button";
import { ConfirmationGroupee } from "@/components/ConfirmationGroupee";
import { QuestionCategorisation } from "@/components/QuestionCategorisation";
import { useDossierChauffeur } from "@/app/chauffeur/use-dossier";
import { formatMontant } from "@/lib/format";
import {
  aTrancher,
  confirmable,
  groupesSemblables,
  libelleCategorie,
  libelleJour,
  presenter,
} from "@/lib/operations-chauffeur";

/** Classement : une opération à la fois, avec sa progression. « Passer » la
 * repousse à la fin de la file ; la barre du bas est masquée par le layout. */
export default function ClasserChauffeurPage({
  params,
}: {
  params: Promise<{ dossierId: string }>;
}) {
  const { dossierId } = use(params);
  const { charge, remplacer, recharger } = useDossierChauffeur(dossierId);
  const [passees, setPassees] = useState<string[]>([]);

  if (charge.statut === "en_cours") {
    return <p className="text-sm text-subtle">Chargement…</p>;
  }
  if (charge.statut === "erreur") {
    return <p className="text-sm text-danger">{charge.message}</p>;
  }

  const restantes = aTrancher(charge.transactions);
  // Le résumé du dossier n'est pas relu après une décision : son compteur est
  // le nombre de départ, le dénominateur de la progression.
  const depart = Math.max(charge.dossier.nb_a_trancher, restantes.length);
  const file = [
    ...restantes.filter((operation) => !passees.includes(operation.ecriture_id)),
    ...restantes.filter((operation) => passees.includes(operation.ecriture_id)),
  ];
  const courante = file[0];
  const faites = depart - restantes.length;
  const groupes = groupesSemblables(restantes);

  const entete = (
    <div className="flex items-center justify-between">
      <Link
        href={`/chauffeur/${dossierId}`}
        className="-ml-1 flex min-h-11 items-center text-sm font-medium text-ink"
      >
        <ChevronLeft className="h-4 w-4" aria-hidden />
        Quitter
      </Link>
      {courante && (
        <p className="text-sm tabular-nums text-subtle">
          {faites + 1} sur {depart}
        </p>
      )}
      <span className="w-14" aria-hidden />
    </div>
  );

  if (!courante) {
    return (
      <div className="flex min-h-[70vh] flex-col justify-center">
        <div className="flex flex-col items-center text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-validated-subtle text-validated">
            <Check className="h-6 w-6" strokeWidth={2} aria-hidden />
          </span>
          <h1 className="mt-4 text-[22px] font-medium tracking-tight text-ink">C&apos;est à jour.</h1>
          <p className="mt-2 max-w-64 text-sm text-subtle">
            {depart > 0
              ? `Vos ${depart} ${depart === 1 ? "opération est classée" : "opérations sont classées"}.`
              : "Aucune opération n'attend de classement."}
          </p>
        </div>
        <Button asChild className="mt-8 w-full">
          <Link href={`/chauffeur/${dossierId}`}>Retour à l&apos;accueil</Link>
        </Button>
      </div>
    );
  }

  const { nom } = presenter(courante.libelle);
  const negatif = courante.montant_cts < 0;
  const proposition = courante.proposition
    ? { code: courante.proposition, libelle: libelleCategorie(courante.proposition) }
    : null;

  return (
    <div>
      {entete}
      <div className="mt-3 h-[3px] bg-surface-soft" role="progressbar" aria-label="Progression du classement" aria-valuemin={0} aria-valuemax={depart} aria-valuenow={faites}>
        <div className="h-full bg-ink transition-all duration-200" style={{ width: `${(faites / depart) * 100}%` }} />
      </div>

      {groupes.map(([categorie, operations]) => (
        <div key={categorie} className="mt-5">
          <ConfirmationGroupee
            dossierId={dossierId}
            categorie={categorie}
            libelle={libelleCategorie(categorie)}
            operations={operations.map((operation) => ({
              ecritureId: operation.ecriture_id,
              nom: presenter(operation.libelle).nom,
              montantCts: operation.montant_cts,
            }))}
            onConfirme={recharger}
          />
        </div>
      ))}

      <section key={courante.ecriture_id} className="mt-6 rounded-lg border border-border bg-canvas p-5">
        <span className="inline-flex rounded-sm border border-dashed border-border-strong px-1.5 py-px text-xs text-muted">
          {negatif ? "Sortie" : "Entrée"}
        </span>
        <p
          className={`mt-4 text-[36px] font-normal leading-none tabular-nums tracking-tight ${
            negatif ? "text-amount-negative" : "text-amount-positive"
          }`}
        >
          {formatMontant(courante.montant_cts)}
        </p>
        <p className="mt-3 text-[15px] font-medium text-ink">{nom}</p>
        <p className="mt-0.5 text-xs text-muted">{libelleJour(courante.date.slice(0, 10))}</p>
      </section>

      <div className="mt-5">
        <QuestionCategorisation
          key={courante.ecriture_id}
          dossierId={dossierId}
          ecritureId={courante.ecriture_id}
          proposition={
            proposition && confirmable(proposition.code, courante.origine_proposition)
              ? proposition
              : null
          }
          origine={courante.origine_proposition}
          confiance={courante.confiance_proposition}
          sansProposition={proposition === null}
          onResolu={(transaction) => {
            remplacer(transaction);
            recharger();
          }}
        />
      </div>

      {restantes.length > 1 && (
        <Button
          type="button"
          variant="ghost"
          className="mt-3 w-full"
          onClick={() => setPassees((liste) => [...liste, courante.ecriture_id])}
        >
          Passer pour l&apos;instant
        </Button>
      )}
    </div>
  );
}
