import type { DocumentCloture, DossierResume } from "./types";

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

// doc 19 §2.1/§6 (révision 2026-09-11) : c'est tout ce qui reste côté
// gestionnaire — la liste agrégée. Le détail d'un dossier (transactions,
// clôture, signature) n'existe plus que côté indiv, doc 19 §5 —
// `obtenirDossier`/`listerTransactions`/`trancherTransaction` ont été
// retirés d'ici avec la fiche dossier gestionnaire qui les utilisait ;
// leurs équivalents authentifiés vivent dans lib/auth-chauffeur.ts.
export function listerDossiers(): Promise<DossierResume[]> {
  return getJSON<DossierResume[]>("/dossiers");
}

// doc 19 §8bis (2026-09-11) : ces routes exigent désormais un jeton indiv
// (demo_api.py) — un `<a href>` ne peut porter d'en-tête `Authorization`,
// donc ce ne sont plus des URLs complètes à mettre directement dans un
// lien, seulement des **chemins** pour `telechargerAvecAuthChauffeur`
// (lib/auth-chauffeur.ts), qui fait le fetch authentifié puis déclenche
// l'enregistrement via une URL d'objet temporaire.
export function cheminTelechargementCloture(dossierId: string, document: DocumentCloture): string {
  return `/dossiers/${dossierId}/${document}`;
}

// doc 20 : dossier de dépôt greffe/INPI — même logique, le PDF reflète
// automatiquement l'état signé/non signé côté serveur (demo_api.py).
export function cheminGreffeInpi(dossierId: string): string {
  return `/dossiers/${dossierId}/greffe-inpi.pdf`;
}
