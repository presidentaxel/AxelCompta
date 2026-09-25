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
  changerEmailAvecJeton,
  decoderChargeUtileJwt,
  definirMotDePasseAvecJeton,
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

export function ouvrirSessionGestionnaire(
  accessToken: string,
  refreshToken: string,
  email: string,
): SessionGestionnaire {
  const session: SessionGestionnaire = {
    accessToken,
    refreshToken,
    tenantId: tenantIdDepuisJeton(accessToken),
    email,
  };
  try {
    window.localStorage.setItem(CLE_SESSION, JSON.stringify(session));
  } catch {
    // Session utilisable pour cette page, simplement pas persistée.
  }
  return session;
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
  return ouvrirSessionGestionnaire(corps.access_token, corps.refresh_token, email);
}

export async function changerMotDePasseGestionnaire(motDePasse: string): Promise<void> {
  const session = obtenirSessionGestionnaire();
  if (!session) {
    throw new ErreurAuthGestionnaire("Aucune session active.");
  }
  try {
    await definirMotDePasseAvecJeton(session.accessToken, motDePasse);
  } catch (exception) {
    throw new ErreurAuthGestionnaire(
      exception instanceof ErreurAuthChauffeur ? exception.message : "Échec du changement.",
    );
  }
}

export async function changerEmailGestionnaire(email: string): Promise<void> {
  const session = obtenirSessionGestionnaire();
  if (!session) {
    throw new ErreurAuthGestionnaire("Aucune session active.");
  }
  try {
    await changerEmailAvecJeton(session.accessToken, email);
  } catch (exception) {
    throw new ErreurAuthGestionnaire(
      exception instanceof ErreurAuthChauffeur ? exception.message : "Échec du changement.",
    );
  }
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

const CLE_PORTEFEUILLE = "axelcompta_portefeuille";

/** Dernière liste affichée, pour ne pas attendre le recalcul à chaque navigation. */
export function lirePortefeuilleSession(): DossierAgregat[] | null {
  try {
    const brut = window.sessionStorage.getItem(CLE_PORTEFEUILLE);
    if (!brut) return null;
    const valeur = JSON.parse(brut) as DossierAgregat[];
    return Array.isArray(valeur) ? valeur : null;
  } catch {
    return null;
  }
}

/** doc 19 §2.1 : la liste agrégée, tout ce que voit le gestionnaire. */
export async function listerDossiers(): Promise<DossierAgregat[]> {
  const reponse = await requeteGestionnaire("/dossiers");
  if (!reponse.ok) {
    throw new ApiError(`API démo (/dossiers) : HTTP ${reponse.status}`, reponse.status);
  }
  const dossiers = (await reponse.json()) as DossierAgregat[];
  try {
    window.sessionStorage.setItem(CLE_PORTEFEUILLE, JSON.stringify(dossiers));
  } catch {
    // Affichage quand même, simplement pas mémorisé pour la prochaine page.
  }
  return dossiers;
}

export type MembrePortefeuille = { email: string; acces: string };

export async function listerMembres(): Promise<MembrePortefeuille[]> {
  const reponse = await requeteGestionnaire("/portefeuille/membres");
  if (!reponse.ok) {
    throw new ApiError(`API (/portefeuille/membres) : HTTP ${reponse.status}`, reponse.status);
  }
  return (await reponse.json()) as MembrePortefeuille[];
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
