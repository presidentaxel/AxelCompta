/** Connexion et session gestionnaire (doc 03 §7, doc 19 §2.1).
 *
 * Même mécanisme que le chauffeur (`auth-chauffeur.ts`, Supabase Auth en
 * REST direct) : ce qui change, c'est le lien porté par le compte. Ici
 * `app_metadata.tenant_id` (posé côté serveur, jamais modifiable par
 * l'utilisateur), là `app_metadata.dossier_id` (même emplacement). Le décodage du jeton plus
 * bas ne sert qu'à refuser tôt un compte sans lien gestionnaire ; la
 * vérification réelle est côté serveur (`demo_auth.verifier_jwt`) à chaque
 * appel.
 *
 * Session en `localStorage`, clé distincte de celle du chauffeur : un même
 * navigateur peut avoir les deux sessions sans qu'elles s'écrasent.
 */

import { ApiError } from "./api";
import {
  decoderChargeUtileJwt,
  enTetesSupabase,
  ErreurAuthChauffeur,
  extraireErreurSupabase,
  URL_SUPABASE,
} from "./auth-chauffeur";
import type { DossierAgregat } from "./types";

const CLE_SESSION = "axelcompta_session_gestionnaire";

export type SessionGestionnaire = {
  accessToken: string;
  refreshToken: string;
  tenantId: string;
  email: string;
};

export class ErreurAuthGestionnaire extends Error {}

function baseUrlApi(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

function tenantIdDepuisJeton(accessToken: string): string {
  const charge = decoderChargeUtileJwt(accessToken);
  const metadata = charge.app_metadata as { tenant_id?: string } | undefined;
  const tenantId = metadata?.tenant_id;
  if (!tenantId) {
    throw new ErreurAuthGestionnaire("Ce compte n'est lié à aucun portefeuille.");
  }
  return tenantId;
}

export function obtenirSessionGestionnaire(): SessionGestionnaire | null {
  try {
    const brut = window.localStorage.getItem(CLE_SESSION);
    return brut ? (JSON.parse(brut) as SessionGestionnaire) : null;
  } catch {
    return null;
  }
}

export function deconnecterGestionnaire(): void {
  try {
    window.localStorage.removeItem(CLE_SESSION);
  } catch {
    // Stockage indisponible : rien à effacer, pas une erreur.
  }
}

export async function connexionGestionnaire(
  email: string,
  motDePasse: string,
): Promise<SessionGestionnaire> {
  const reponse = await fetch(`${URL_SUPABASE}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: enTetesSupabase(),
    body: JSON.stringify({ email, password: motDePasse }),
  });
  if (!reponse.ok) {
    try {
      await extraireErreurSupabase(reponse);
    } catch (exception) {
      // Même erreur Supabase, réémise sous le type gestionnaire.
      throw new ErreurAuthGestionnaire(
        exception instanceof ErreurAuthChauffeur ? exception.message : "Échec de la connexion.",
      );
    }
  }
  const corps = (await reponse.json()) as { access_token: string; refresh_token: string };
  const session: SessionGestionnaire = {
    accessToken: corps.access_token,
    refreshToken: corps.refresh_token,
    tenantId: tenantIdDepuisJeton(corps.access_token),
    email,
  };
  try {
    window.localStorage.setItem(CLE_SESSION, JSON.stringify(session));
  } catch {
    // Session utilisable pour cette page, simplement pas persistée.
  }
  return session;
}

/** Requête authentifiée vers `demo_api`. Sur 401/403, la session est
 * effacée (jeton expiré ou compte sans droit) : l'appelant redirige alors
 * vers la connexion via `ErreurAuthGestionnaire`. */
async function requeteGestionnaire(path: string, init: RequestInit = {}): Promise<Response> {
  const session = obtenirSessionGestionnaire();
  if (!session) {
    throw new ErreurAuthGestionnaire("Aucune session active.");
  }
  const reponse = await fetch(`${baseUrlApi()}${path}`, {
    ...init,
    headers: { ...init.headers, Authorization: `Bearer ${session.accessToken}` },
    cache: "no-store",
  });
  if (reponse.status === 401 || reponse.status === 403) {
    deconnecterGestionnaire();
    throw new ErreurAuthGestionnaire("Session expirée ou accès refusé.");
  }
  return reponse;
}

/** doc 19 §2.1 : la liste agrégée, tout ce que voit le gestionnaire. */
export async function listerDossiers(): Promise<DossierAgregat[]> {
  const reponse = await requeteGestionnaire("/dossiers");
  if (!reponse.ok) {
    throw new ApiError(`API démo (/dossiers) : HTTP ${reponse.status}`, reponse.status);
  }
  return (await reponse.json()) as DossierAgregat[];
}

export async function inviterChauffeur(
  dossierId: string,
  email: string,
): Promise<{ dossier_id: string; email: string; statut: string }> {
  const reponse = await requeteGestionnaire(`/dossiers/${dossierId}/inviter`, {
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

export type ResultatInvitation =
  | "invité"
  | "deja_invite"
  | "dossier_inconnu"
  | "email_invalide"
  | "doublon_dans_le_lot"
  | "erreur";

export type InvitationsMasse = {
  lignes: { dossier_id: string; email: string; resultat: ResultatInvitation }[];
  nb_invitees: number;
};

/** doc 19 §3.1 : invitation en masse depuis une base clients (500 lignes au
 * plus par envoi, résultat ligne par ligne). */
export async function inviterEnMasse(
  lignes: { dossier_id: string; email: string }[],
): Promise<InvitationsMasse> {
  const reponse = await requeteGestionnaire("/invitations/en-masse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ invitations: lignes }),
  });
  const corps = await reponse.json();
  if (!reponse.ok) {
    throw new ApiError(
      typeof corps.detail === "string" ? corps.detail : `HTTP ${reponse.status}`,
      reponse.status,
    );
  }
  return corps as InvitationsMasse;
}
