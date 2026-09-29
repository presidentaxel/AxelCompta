import type { TransactionVue } from "@/lib/types";

const MOIS = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" });
const JOUR = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long" });
const JOUR_COURT = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" });

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
  remuneration_dirigeant: "Ma rémunération",
  compte_courant_associe: "Compte courant d'associé",
  virement_interne: "Virement entre mes comptes",
  salaires_personnel: "Salaire d'un salarié",
  frais_bancaires: "Frais bancaires",
  abonnements_logiciels: "Abonnement",
  fournitures_administratives: "Fournitures",
  amendes_infractions: "Amende",
  subventions: "Aide publique",
  a_verifier_location_materiel: "Location de matériel",
  immobilisation_vehicule: "Achat de véhicule",
  non_categorise_a_verifier: "À vérifier",
  interets_emprunts: "Intérêts d'emprunt",
  sous_traitance_chauffeurs: "Sous-traitance",
  visite_medicale_vtc: "Visite médicale",
};

export function libelleCategorie(code: string): string {
  return DETAILS[code] ?? "Autre";
}

/** Une proposition se confirme en un geste, sauf quand la réponse est déjà
 * l'un des boutons ou que la catégorie elle-même demande de vérifier. Une
 * proposition tirée des choix du chauffeur se confirme toujours. */
export function confirmable(code: string, origine: TransactionVue["origine_proposition"]): boolean {
  if (origine === "appris") return true;
  return !(
    code === "non_categorise_a_verifier" ||
    code === "usage_personnel" ||
    code === "usage_personnel_suspect" ||
    code === "remuneration_dirigeant" ||
    code.startsWith("a_verifier")
  );
}

/** Le libellé bancaire porte parfois sa catégorie entre parenthèses. */
export function presenter(libelle: string): { nom: string; detail: string | null } {
  const trouve = libelle.match(/^(.*)\s+\(([a-z0-9_]+)\)$/);
  if (!trouve?.[1] || !trouve[2]) return { nom: libelle, detail: null };
  return { nom: trouve[1], detail: libelleCategorie(trouve[2]) };
}

/** Opérations à trancher qui ressemblent à une opération déjà classée, par
 * catégorie. Un groupe d'une seule opération n'a pas besoin de raccourci. */
export function groupesSemblables(aVerifier: TransactionVue[]): [string, TransactionVue[]][] {
  const groupes = new Map<string, TransactionVue[]>();
  for (const transaction of aVerifier) {
    if (transaction.origine_proposition !== "appris" || !transaction.proposition) continue;
    groupes.set(transaction.proposition, [
      ...(groupes.get(transaction.proposition) ?? []),
      transaction,
    ]);
  }
  return [...groupes.entries()].filter(([, operations]) => operations.length >= 2);
}

export function aTrancher(transactions: TransactionVue[]): TransactionVue[] {
  return transactions
    .filter((transaction) => transaction.statut === "à trancher")
    .sort((a, b) => b.date.localeCompare(a.date));
}

export function grouperParJour(transactions: TransactionVue[]): [string, TransactionVue[]][] {
  const groupes = new Map<string, TransactionVue[]>();
  for (const transaction of [...transactions].sort((a, b) => b.date.localeCompare(a.date))) {
    const jour = transaction.date.slice(0, 10);
    groupes.set(jour, [...(groupes.get(jour) ?? []), transaction]);
  }
  return [...groupes.entries()];
}

export function libelleMois(mois: string): string {
  return MOIS.format(new Date(`${mois}-01T12:00:00`));
}

export function libelleJour(jour: string): string {
  return JOUR.format(new Date(`${jour}T12:00:00`));
}

export function libelleJourCourt(date: string): string {
  return JOUR_COURT.format(new Date(`${date.slice(0, 10)}T12:00:00`));
}
