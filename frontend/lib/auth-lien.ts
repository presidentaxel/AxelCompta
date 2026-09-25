/** Ouvre la session qui correspond au jeton reçu dans un lien Supabase.
 * Un compte chauffeur porte `dossier_id`, un compte gestionnaire `tenant_id`.
 */

import {
  decoderChargeUtileJwt,
  enregistrerSessionChauffeur,
  ErreurAuthChauffeur,
} from "./auth-chauffeur";
import { ErreurAuthGestionnaire, ouvrirSessionGestionnaire } from "./auth-gestionnaire";

export type FragmentAuth = {
  accessToken: string;
  refreshToken: string;
  type: string;
};

export function estLienInvitation(fragment: string): boolean {
  return new URLSearchParams(fragment.replace(/^#/, "")).get("type") === "invite";
}

export function lireFragmentAuth(fragment: string): FragmentAuth {
  const parametres = new URLSearchParams(fragment.replace(/^#/, ""));
  const accessToken = parametres.get("access_token");
  const refreshToken = parametres.get("refresh_token");
  if (!accessToken || !refreshToken) {
    throw new ErreurAuthChauffeur("Lien invalide ou expiré.");
  }
  return { accessToken, refreshToken, type: parametres.get("type") ?? "" };
}

export function ouvrirSessionDepuisJetons(accessToken: string, refreshToken: string): string {
  const charge = decoderChargeUtileJwt(accessToken);
  const meta = (charge.app_metadata ?? {}) as { dossier_id?: string; tenant_id?: string };
  const email = typeof charge.email === "string" ? charge.email : "";
  if (meta.dossier_id) {
    enregistrerSessionChauffeur({
      accessToken,
      refreshToken,
      dossierId: meta.dossier_id,
      email,
    });
    return `/chauffeur/${meta.dossier_id}`;
  }
  if (meta.tenant_id) {
    try {
      ouvrirSessionGestionnaire(accessToken, refreshToken, email);
    } catch (exception) {
      throw new ErreurAuthGestionnaire(
        exception instanceof Error ? exception.message : "Lien invalide.",
      );
    }
    return "/";
  }
  throw new ErreurAuthChauffeur("Ce compte n'est lié ni à un dossier ni à un portefeuille.");
}
