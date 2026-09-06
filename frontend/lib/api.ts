import type { DossierResume, TransactionVue } from "./types";

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

export function listerDossiers(): Promise<DossierResume[]> {
  return getJSON<DossierResume[]>("/dossiers");
}

export function obtenirDossier(dossierId: string): Promise<DossierResume> {
  return getJSON<DossierResume>(`/dossiers/${dossierId}`);
}

export function listerTransactions(dossierId: string): Promise<TransactionVue[]> {
  return getJSON<TransactionVue[]>(`/dossiers/${dossierId}/transactions`);
}
