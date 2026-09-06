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
};

export type StatutTransaction = "validé" | "à trancher";

export type TransactionVue = {
  ecriture_id: string;
  date: string;
  libelle: string;
  montant_cts: number;
  compte: string;
  statut: StatutTransaction;
};
