"""Identité légale d'une entreprise et de ses associés (doc 06 §6, doc 20) :
ce qu'exigent les en-têtes de la liasse fiscale (2065 cadre A, 2033-A à G)
et le FEC (nom de fichier `<SIREN>FEC<AAAAMMJJ>.txt`).

Dans `core` plutôt que `tenants` : `closing` et `filings` en ont besoin pour
remplir les formulaires sans dépendre du module qui persiste les dossiers.

Un dossier sans identité (`None`) reste valide — c'est le cas du dossier
historique pseudonymisé de l'audit (doc 07 §2.2) : on n'invente jamais une
identité réelle, les en-têtes restent alors blancs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Adresse:
    numero: str
    voie: str
    code_postal: str
    commune: str
    pays: str = "France"

    def sur_une_ligne(self) -> str:
        return f"{self.numero} {self.voie}, {self.code_postal} {self.commune}".strip()


@dataclass(frozen=True, slots=True)
class Associe:
    """Personne physique détenant des parts (2033-F cadre II). Le dirigeant
    d'une SASU/EURL est aussi son associé unique : un seul objet, pas deux."""

    civilite: str  # "M" ou "MME" (notice 2033-F, renvoi 2)
    nom: str
    prenoms: str
    date_naissance: date
    departement_naissance: str
    commune_naissance: str
    adresse: Adresse
    nb_titres: int
    qualite: str  # "Président" (SASU) ou "Gérant" (EURL)
    pays_naissance: str = "France"


@dataclass(frozen=True, slots=True)
class IdentiteEntreprise:
    denomination: str
    siren: str  # 9 chiffres
    nic: str  # 5 chiffres : SIRET = SIREN + NIC
    adresse_siege: Adresse
    code_ape: str
    activite: str
    email: str
    capital_social_cts: int
    associes: tuple[Associe, ...]

    @property
    def siret(self) -> str:
        return self.siren + self.nic

    @property
    def dirigeant(self) -> Associe:
        return self.associes[0]
