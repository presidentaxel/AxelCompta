const TVA_RECETTES: Record<string, string> = {
  assujetti_taux_reduit: "TVA à taux réduit",
  franchise: "Franchise en base de TVA",
};

const REGIME_TVA: Record<string, string> = {
  reel_normal: "Réel normal",
  reel_simplifie: "Réel simplifié",
  franchise: "Franchise en base",
};

const IMPOSITION: Record<string, string> = {
  IS: "Impôt sur les sociétés",
  option_IR: "Impôt sur le revenu",
};

export function libelleCompte(statut: "invité" | "actif" | null): string {
  if (statut === "actif") return "Compte ouvert";
  if (statut === "invité") return "Invitation envoyée";
  return "Sans compte";
}

export function libelleTvaRecettes(code: string): string {
  return TVA_RECETTES[code] ?? code;
}

export function libelleRegimeTva(code: string): string {
  return REGIME_TVA[code] ?? code;
}

export function libelleImposition(code: string): string {
  return IMPOSITION[code] ?? code;
}

export function libelleBanque(mode: "gestionnaire" | "chauffeur_direct"): string {
  return mode === "chauffeur_direct"
    ? "Banque reliée par le chauffeur"
    : "Banque reliée par le portefeuille";
}
