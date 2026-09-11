// Miroir des modèles Pydantic de axelcompta/demo_api.py — garder les deux
// synchronisés à la main (pas de génération OpenAPI pour la démo, doc 17 §8).

export type DossierResume = {
  dossier_id: string;
  nom: string;
  tva_recettes_regime: string;
  plateformes: string[];
  exercice_debut: string | null;
  exercice_fin: string | null;
  ca_ht_cts: number;
  charges_cts: number;
  resultat_cts: number;
  tresorerie_cts: number;
  tva_a_payer_cts: number;
  nb_transactions: number;
  nb_a_trancher: number;
  statut_invitation: "invité" | "actif" | null; // null = "non_invité" (doc 19 §3.2)
  mode_acces_bancaire: "gestionnaire" | "chauffeur_direct"; // doc 19 §4
  greffe_inpi_signe: boolean; // doc 20 : dossier de dépôt signé (démo, jamais qualifié RGS)
};

// doc 17 §9 Semaine 4 : les 5 exports de clôture, servis en téléchargement
// direct par demo_api.py (mêmes renderers que demo_chauffeurs_type.py).
export type DocumentCloture =
  | "liasse.pdf"
  | "cerfa-2065.pdf"
  | "fec.txt"
  | "grand-livre.csv"
  | "balance.csv";

// doc 20 §4 : réponse de la signature greffe/INPI — déplacé ici le
// 2026-09-11 (doc 19) car appelé depuis lib/api.ts (type) et
// lib/auth-chauffeur.ts (l'appel authentifié réel, côté indiv).
export type SignatureGreffeVue = {
  dossier_id: string;
  signe: boolean;
  signe_le: string;
  qualifie: boolean; // toujours false en démo
};

export type StatutTransaction = "validé" | "à trancher";

export type TransactionVue = {
  ecriture_id: string;
  date: string;
  libelle: string;
  montant_cts: number;
  compte: string;
  statut: StatutTransaction;
  a_justificatif: boolean; // doc 17 §9 Semaine 3 : photo jointe (contenu non lu)
};
