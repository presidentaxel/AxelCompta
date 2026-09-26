"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { use, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { QuestionCategorisation } from "@/components/QuestionCategorisation";
import { StationTickets } from "@/components/StationTickets";
import { useDossierChauffeur } from "@/app/chauffeur/use-dossier";
import { ApiError } from "@/lib/api";
import { joindreJustificatifChauffeur } from "@/lib/auth-chauffeur";
import { formatMontant } from "@/lib/format";
import type { TransactionVue } from "@/lib/types";

const MOIS = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" });
const JOUR = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long" });

/** Activité : d'abord l'arriéré, qui se termine. Les mouvements déjà traités
 * se lisent mois par mois, comme un relevé, pas comme une file sans fin. */
export default function DossierChauffeurPage({
  params,
}: {
  params: Promise<{ dossierId: string }>;
}) {
  const { dossierId } = use(params);
  const { charge, remplacer } = useDossierChauffeur(dossierId);
  const [vue, setVue] = useState<"traiter" | "mouvements">("traiter");
  const [moisChoisi, setMoisChoisi] = useState<string | null>(null);

  if (charge.statut === "en_cours") {
    return <p className="text-sm text-subtle">Chargement…</p>;
  }
  if (charge.statut === "erreur") {
    return <p className="text-sm text-danger">{charge.message}</p>;
  }

  const { dossier, transactions } = charge;
  const aVerifier = transactions
    .filter((transaction) => transaction.statut === "à trancher")
    .sort((a, b) => b.date.localeCompare(a.date));
  const moisDispo = [
    ...new Set(transactions.map((transaction) => transaction.date.slice(0, 7))),
  ].sort();
  const dernierMois = moisDispo.at(-1);
  const mois = moisChoisi && moisDispo.includes(moisChoisi) ? moisChoisi : dernierMois;
  const indexMois = mois ? moisDispo.indexOf(mois) : -1;

  return (
    <div>
      <h1 className="text-[28px] font-bold tracking-tight text-ink">{dossier.nom}</h1>
      <p
        className={`mt-6 text-[28px] font-bold tabular-nums tracking-tight ${
          dossier.resultat_cts < 0 ? "text-amount-negative" : "text-amount-positive"
        }`}
      >
        {formatMontant(dossier.resultat_cts)}
      </p>
      <p className="text-sm text-subtle">Résultat de l&apos;exercice</p>
      <ConnexionBancaire
        peutConnecter={dossier.peut_connecter_sa_banque}
        aDesTransactions={transactions.length > 0}
      />
      <div className="mt-8 flex gap-2">
        <Onglet actif={vue === "traiter"} onClick={() => setVue("traiter")}>
          À traiter{aVerifier.length > 0 ? ` · ${aVerifier.length}` : ""}
        </Onglet>
        <Onglet actif={vue === "mouvements"} onClick={() => setVue("mouvements")}>
          Mouvements
        </Onglet>
      </div>
      {vue === "traiter" ? (
        <Arriere
          aVerifier={aVerifier}
          dossierId={dossierId}
          mois={dernierMois}
          depenses={
            dernierMois
              ? transactions.filter(
                  (transaction) =>
                    transaction.montant_cts < 0 && transaction.date.startsWith(dernierMois),
                )
              : []
          }
          onChange={remplacer}
        />
      ) : (
        <Mouvements
          dossierId={dossierId}
          onJointe={remplacer}
          transactions={transactions.filter((transaction) => transaction.date.startsWith(mois ?? ""))}
          mois={mois}
          peutReculer={indexMois > 0}
          peutAvancer={indexMois >= 0 && indexMois < moisDispo.length - 1}
          onReculer={() => setMoisChoisi(moisDispo[indexMois - 1] ?? null)}
          onAvancer={() => setMoisChoisi(moisDispo[indexMois + 1] ?? null)}
        />
      )}
    </div>
  );
}

function Onglet({
  actif,
  onClick,
  children,
}: {
  actif: boolean;
  onClick: () => void;
  children: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={actif}
      onClick={onClick}
      className={`h-9 rounded-full px-4 text-sm font-medium ${
        actif ? "bg-ink text-canvas" : "text-subtle"
      }`}
    >
      {children}
    </button>
  );
}

function Arriere({
  aVerifier,
  dossierId,
  mois,
  depenses,
  onChange,
}: {
  aVerifier: TransactionVue[];
  dossierId: string;
  mois: string | undefined;
  depenses: TransactionVue[];
  onChange: (transaction: TransactionVue) => void;
}) {
  const ticketsManquants = depenses.some((depense) => !depense.a_justificatif);
  if (aVerifier.length === 0 && !ticketsManquants) {
    return <p className="mt-10 text-sm text-subtle">Tout est à jour.</p>;
  }
  return (
    <div>
      {mois && ticketsManquants && (
        <StationTickets dossierId={dossierId} mois={mois} depenses={depenses} onJointe={onChange} />
      )}
      <ul className="mt-2">
        {aVerifier.map((transaction) => {
          const { nom, detail } = presenter(transaction.libelle);
          return (
            <li key={transaction.ecriture_id} className="border-b border-hairline py-4">
              <LigneMontant nom={nom} detail={detail} transaction={transaction} />
              <div className="mt-3">
                <QuestionCategorisation
                  dossierId={dossierId}
                  ecritureId={transaction.ecriture_id}
                  onResolu={onChange}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Mouvements({
  dossierId,
  onJointe,
  transactions,
  mois,
  peutReculer,
  peutAvancer,
  onReculer,
  onAvancer,
}: {
  dossierId: string;
  onJointe: (transaction: TransactionVue) => void;
  transactions: TransactionVue[];
  mois: string | undefined;
  peutReculer: boolean;
  peutAvancer: boolean;
  onReculer: () => void;
  onAvancer: () => void;
}) {
  const [sens, setSens] = useState<"sorties" | "entrees">("sorties");
  const retenues = transactions.filter((transaction) =>
    sens === "sorties" ? transaction.montant_cts < 0 : transaction.montant_cts > 0,
  );
  const total = retenues.reduce((somme, transaction) => somme + transaction.montant_cts, 0);
  const jours = grouperParJour(retenues);
  return (
    <div className="mt-6">
      <div className="flex items-center justify-between">
        <button
          type="button"
          aria-label="Mois précédent"
          disabled={!peutReculer}
          onClick={onReculer}
          className="flex h-11 w-11 items-center justify-center text-ink disabled:text-faint"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <p className="text-sm font-medium text-ink capitalize">{mois ? libelleMois(mois) : "Aucun mois"}</p>
        <button
          type="button"
          aria-label="Mois suivant"
          disabled={!peutAvancer}
          onClick={onAvancer}
          className="flex h-11 w-11 items-center justify-center text-ink disabled:text-faint"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
      <div className="mt-2 flex gap-2">
        <Onglet actif={sens === "sorties"} onClick={() => setSens("sorties")}>
          Sorties
        </Onglet>
        <Onglet actif={sens === "entrees"} onClick={() => setSens("entrees")}>
          Entrées
        </Onglet>
      </div>
      {jours.length > 0 && (
        <p
          className={`mt-4 text-lg font-semibold tabular-nums ${
            total < 0 ? "text-amount-negative" : "text-amount-positive"
          }`}
        >
          {formatMontant(total)}
        </p>
      )}
      {jours.length === 0 ? (
        <p className="mt-6 text-sm text-subtle">
          {sens === "sorties" ? "Aucune sortie ce mois-ci." : "Aucune entrée ce mois-ci."}
        </p>
      ) : (
        jours.map(([jour, lignes]) => (
          <section key={jour} className="mt-6">
            <h2 className="text-sm font-medium text-subtle">{libelleJour(jour)}</h2>
            <ul>
              {lignes.map((transaction) => {
                const { nom, detail } = presenter(transaction.libelle);
                return (
                  <li key={transaction.ecriture_id} className="border-b border-hairline py-3">
                    <LigneMontant nom={nom} detail={detail} transaction={transaction} />
                    {sens === "sorties" && (
                      <AjouterTicketSortie
                        dossierId={dossierId}
                        transaction={transaction}
                        onJointe={onJointe}
                      />
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}

function AjouterTicketSortie({
  dossierId,
  transaction,
  onJointe,
}: {
  dossierId: string;
  transaction: TransactionVue;
  onJointe: (transaction: TransactionVue) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [envoi, setEnvoi] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  if (transaction.a_justificatif) {
    return <p className="mt-1 text-sm text-validated">Ticket joint</p>;
  }

  async function envoyer(fichier: File) {
    setEnvoi(true);
    setErreur(null);
    try {
      onJointe(await joindreJustificatifChauffeur(dossierId, transaction.ecriture_id, fichier));
    } catch (exception) {
      setErreur(exception instanceof ApiError ? exception.message : "Échec de l'envoi de la photo.");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(evenement) => {
          const fichier = evenement.target.files?.[0];
          if (fichier) void envoyer(fichier);
          evenement.target.value = "";
        }}
      />
      <button
        type="button"
        disabled={envoi}
        onClick={() => inputRef.current?.click()}
        className="mt-1 py-1 text-sm font-medium text-primary disabled:opacity-50"
      >
        {envoi ? "Envoi…" : "Ajouter un ticket"}
      </button>
      {erreur && <p className="mt-1 text-xs text-danger">{erreur}</p>}
    </div>
  );
}

function LigneMontant({
  nom,
  detail,
  transaction,
}: {
  nom: string;
  detail: string | null;
  transaction: TransactionVue;
}) {
  const negatif = transaction.montant_cts < 0;
  return (
    <div className="flex items-baseline justify-between gap-4">
      <span className="min-w-0">
        <span className="block truncate text-base font-semibold text-ink">{nom}</span>
        {detail && <span className="mt-0.5 block text-sm text-subtle">{detail}</span>}
      </span>
      <span
        className={`shrink-0 text-base font-semibold tabular-nums ${
          negatif ? "text-amount-negative" : "text-amount-positive"
        }`}
      >
        {formatMontant(transaction.montant_cts)}
      </span>
    </div>
  );
}

function ConnexionBancaire({
  peutConnecter,
  aDesTransactions,
}: {
  peutConnecter: boolean;
  aDesTransactions: boolean;
}) {
  if (peutConnecter) {
    return (
      <Button type="button" variant="secondary" className="mt-6 w-full" disabled title="Bientôt disponible">
        Connecter ma banque
      </Button>
    );
  }
  if (!aDesTransactions) {
    return <p className="mt-6 text-sm text-subtle">Vos transactions arrivent bientôt.</p>;
  }
  return null;
}

const DETAILS: Record<string, string> = {
  usage_personnel_suspect: "À confirmer",
  usage_personnel: "Dépense personnelle",
  carburant: "Carburant",
  peage_stationnement: "Péage",
  repas_et_receptions: "Repas",
  assurance_vehicule: "Assurance",
  telecommunications: "Téléphone",
  entretien_reparation_vehicule: "Entretien",
  charges_sociales_impots: "Charges",
  honoraires_comptable_juridique: "Honoraires",
  recettes_plateformes: "Courses",
};

function presenter(libelle: string): { nom: string; detail: string | null } {
  const trouve = libelle.match(/^(.*)\s+\(([a-z0-9_]+)\)$/);
  if (!trouve?.[1] || !trouve[2]) return { nom: libelle, detail: null };
  const code = trouve[2];
  return { nom: trouve[1], detail: DETAILS[code] ?? code.replaceAll("_", " ") };
}

function grouperParJour(transactions: TransactionVue[]): [string, TransactionVue[]][] {
  const groupes = new Map<string, TransactionVue[]>();
  for (const transaction of [...transactions].sort((a, b) => b.date.localeCompare(a.date))) {
    const jour = transaction.date.slice(0, 10);
    groupes.set(jour, [...(groupes.get(jour) ?? []), transaction]);
  }
  return [...groupes.entries()];
}

function libelleMois(mois: string): string {
  return MOIS.format(new Date(`${mois}-01T12:00:00`));
}

function libelleJour(jour: string): string {
  return JOUR.format(new Date(`${jour}T12:00:00`));
}
