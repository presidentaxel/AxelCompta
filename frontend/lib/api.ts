import type { DocumentCloture, DossierResume, TransactionVue } from "./types";

// axelcompta.demo_api, lancé à part : `uvicorn axelcompta.demo_api:app
// --reload --port 8000` depuis backend/ (voir frontend/README.md).
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function getJSON<T>(path: string): Promise<T> {
  const reponse = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!reponse.ok) {
    throw new Error(`API démo (${path}) : HTTP ${reponse.status}`);
  }
  return (await reponse.json()) as T;
}

// Erreur typée plutôt qu'un message générique : le composant appelant
// affiche `detail` tel quel (400 catégorie inconnue, 409 déjà tranchée,
// doc 17 §9 bloc C) au lieu d'un "une erreur est survenue" muet.
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export async function inviterChauffeur(
  dossierId: string,
  email: string,
): Promise<{ dossier_id: string; email: string; statut: string }> {
  const reponse = await fetch(`${API_BASE_URL}/dossiers/${dossierId}/inviter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const corps = await reponse.json();
  if (!reponse.ok) {
    throw new ApiError(corps.detail ?? `HTTP ${reponse.status}`, reponse.status);
  }
  return corps;
}

export async function trancherTransaction(
  dossierId: string,
  ecritureId: string,
  categorie: string,
): Promise<TransactionVue> {
  const reponse = await fetch(
    `${API_BASE_URL}/dossiers/${dossierId}/transactions/${ecritureId}/decision`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ categorie }),
    },
  );
  const corps = await reponse.json();
  if (!reponse.ok) {
    throw new ApiError(corps.detail ?? `HTTP ${reponse.status}`, reponse.status);
  }
  return corps as TransactionVue;
}

export function listerDossiers(): Promise<DossierResume[]> {
  return getJSON<DossierResume[]>("/dossiers");
}

export function obtenirDossier(dossierId: string): Promise<DossierResume> {
  return getJSON<DossierResume>(`/dossiers/${dossierId}`);
}

export function listerTransactions(dossierId: string): Promise<TransactionVue[]> {
  return getJSON<TransactionVue[]>(`/dossiers/${dossierId}/transactions`);
}

// doc 17 §9 Semaine 4 : un lien direct, pas un fetch — le navigateur gère
// le téléchargement (Content-Disposition côté demo_api.py), pas besoin de
// passer par React pour un fichier statique par requête.
export function urlTelechargementCloture(dossierId: string, document: DocumentCloture): string {
  return `${API_BASE_URL}/dossiers/${dossierId}/${document}`;
}
