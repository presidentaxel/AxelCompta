/** Connexion et session chauffeur (doc 17 §9 bloc B, doc 19 §5.1-2).
 *
 * Appels REST directs à Supabase Auth — jamais le SDK
 * `@supabase/supabase-js`, même choix que le backend (`demo_comptes.py`,
 * appels `httpx` bruts) : cohérent avec la règle anti-lock-in d'ADR-003
 * (« n'utiliser que la connection string/API standard, jamais un SDK
 * propriétaire qui s'installe par défaut »). La clé anon est faite pour
 * être exposée côté client (contrairement à la service role key,
 * backend-only).
 *
 * Session stockée en `localStorage` — lectures/écritures protégées
 * (peut échouer en navigation privée ou si le viewer bloque le stockage
 * de site) : dans ce cas, on retombe simplement sur "pas de session",
 * jamais une exception qui casse la page.
 */

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";
const CLE_SESSION = "axelcompta_session_chauffeur";

export type SessionChauffeur = {
  accessToken: string;
  refreshToken: string;
  dossierId: string;
  email: string;
};

export class ErreurAuthChauffeur extends Error {}

function enTetesSupabase(accessToken?: string): Record<string, string> {
  return {
    apikey: SUPABASE_ANON_KEY,
    Authorization: `Bearer ${accessToken ?? SUPABASE_ANON_KEY}`,
    "Content-Type": "application/json",
  };
}

/** Décodage du payload d'un JWT — **aucune vérification de signature**,
 * uniquement pour peupler l'URL après connexion. La vérification réelle
 * est côté serveur (`demo_auth.verifier_jwt`) à chaque appel API. */
function decoderChargeUtileJwt(jeton: string): Record<string, unknown> {
  const partie = jeton.split(".")[1];
  const normalise = partie.replace(/-/g, "+").replace(/_/g, "/");
  return JSON.parse(atob(normalise)) as Record<string, unknown>;
}

function dossierIdDepuisJeton(accessToken: string): string {
  const charge = decoderChargeUtileJwt(accessToken);
  const metadata = charge.user_metadata as { dossier_id?: string } | undefined;
  const dossierId = metadata?.dossier_id;
  if (!dossierId) {
    throw new ErreurAuthChauffeur("Ce compte n'est lié à aucun dossier.");
  }
  return dossierId;
}

export function obtenirSession(): SessionChauffeur | null {
  try {
    const brut = window.localStorage.getItem(CLE_SESSION);
    return brut ? (JSON.parse(brut) as SessionChauffeur) : null;
  } catch {
    return null;
  }
}

function enregistrerSession(session: SessionChauffeur): void {
  try {
    window.localStorage.setItem(CLE_SESSION, JSON.stringify(session));
  } catch {
    // Stockage indisponible (navigation privée, réglages navigateur) — la
    // session reste utilisable pour la requête en cours, juste pas
    // persistée. Pas une erreur fatale (doc artefacts : dégrader, pas casser).
  }
}

export function deconnecter(): void {
  try {
    window.localStorage.removeItem(CLE_SESSION);
  } catch {
    // idem ci-dessus
  }
}

async function extraireErreurSupabase(reponse: Response): Promise<never> {
  const corps = (await reponse.json().catch(() => ({}))) as { error_description?: string };
  throw new ErreurAuthChauffeur(
    corps.error_description ?? `Échec de l'authentification (HTTP ${reponse.status}).`,
  );
}

export async function connexionParMotDePasse(
  email: string,
  motDePasse: string,
): Promise<SessionChauffeur> {
  const reponse = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=password`, {
    method: "POST",
    headers: enTetesSupabase(),
    body: JSON.stringify({ email, password: motDePasse }),
  });
  if (!reponse.ok) {
    await extraireErreurSupabase(reponse);
  }
  const corps = (await reponse.json()) as { access_token: string; refresh_token: string };
  const session: SessionChauffeur = {
    accessToken: corps.access_token,
    refreshToken: corps.refresh_token,
    dossierId: dossierIdDepuisJeton(corps.access_token),
    email,
  };
  enregistrerSession(session);
  return session;
}

/** Consomme le fragment d'URL du lien d'invitation Supabase
 * (`#access_token=...&refresh_token=...&type=invite`) — doc 19 §5.1-2. */
export async function accepterInvitation(fragmentUrl: string): Promise<SessionChauffeur> {
  const parametres = new URLSearchParams(fragmentUrl.replace(/^#/, ""));
  const accessToken = parametres.get("access_token");
  const refreshToken = parametres.get("refresh_token");
  if (!accessToken || !refreshToken) {
    throw new ErreurAuthChauffeur("Lien d'invitation invalide ou expiré.");
  }
  const reponse = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    headers: enTetesSupabase(accessToken),
  });
  if (!reponse.ok) {
    await extraireErreurSupabase(reponse);
  }
  const utilisateur = (await reponse.json()) as { email: string };
  const session: SessionChauffeur = {
    accessToken,
    refreshToken,
    dossierId: dossierIdDepuisJeton(accessToken),
    email: utilisateur.email,
  };
  enregistrerSession(session);
  return session;
}

export async function definirMotDePasse(motDePasse: string): Promise<void> {
  const session = obtenirSession();
  if (!session) {
    throw new ErreurAuthChauffeur("Aucune session active.");
  }
  const reponse = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
    method: "PUT",
    headers: enTetesSupabase(session.accessToken),
    body: JSON.stringify({ password: motDePasse }),
  });
  if (!reponse.ok) {
    await extraireErreurSupabase(reponse);
  }
}

/** Appel à `demo_api` avec le jeton chauffeur — pour toute route côté
 * chauffeur (doc 19 §4 : le serveur vérifie que le dossier appartient bien
 * à l'appelant, ceci ne fait qu'ajouter l'en-tête). */
export async function fetchAvecAuthChauffeur<T>(path: string): Promise<T> {
  const session = obtenirSession();
  if (!session) {
    throw new ErreurAuthChauffeur("Aucune session active.");
  }
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  const reponse = await fetch(`${baseUrl}${path}`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: "no-store",
  });
  if (!reponse.ok) {
    throw new ErreurAuthChauffeur(`API démo (${path}) : HTTP ${reponse.status}`);
  }
  return (await reponse.json()) as T;
}
