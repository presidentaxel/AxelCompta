"""Export FEC — Fichier des Écritures Comptables (LPF art. L.47 A-I et
A.47 A-1, BOI-CF-IOR-60-40-20). **Le format légal exigé en cas de
contrôle fiscal** — le détail derrière un chiffre de liasse, pas juste le
chiffre (2026-09-05, suite à « s'il est faux, on ne sait pas »).

Règles appliquées à la lettre (texte de l'article A.47 A-1, vérifié le
2026-09-23) :
- fichier à plat, 18 zones séparées par une tabulation, première ligne =
  noms des zones exactement comme dans l'arrêté ;
- jeu de caractères UTF-8 (l'un des trois autorisés avec ASCII et
  ISO 8859-15), enregistrements séparés par CR+LF ;
- montants en base décimale, **virgule** comme séparateur décimal, sans
  séparateur de milliers ; présentation Debit/Credit (pas Montant/Sens) ;
- dates au format AAAAMMJJ sans séparateur ;
- `EcritureNum` : séquence **continue** et chronologique, sans rupture ni
  inversion (BOI §40), commune à toutes les lignes d'une même écriture ;
- zones obligatoires toujours renseignées (`CompteLib`, `PieceRef`,
  `PieceDate`, `EcritureLib`, `ValidDate`) ; seules les zones facultatives
  (auxiliaire, lettrage, devise) restent vides ;
- aucune zone ne contient de tabulation ni de retour à la ligne ;
- nom du fichier `<SIREN>FEC<AAAAMMJJ>.txt`, date = clôture de l'exercice.

**Limite assumée** : conforme au texte, mais pas encore passé dans « Test
Compta Demat » (l'outil de validation DGFiP, Windows uniquement).
"""

from __future__ import annotations

import re
from datetime import date

from axelcompta.ledger.models import Ecriture, Journal, LigneEcriture, Sens

COLONNES_FEC = (
    "JournalCode",
    "JournalLib",
    "EcritureNum",
    "EcritureDate",
    "CompteNum",
    "CompteLib",
    "CompAuxNum",
    "CompAuxLib",
    "PieceRef",
    "PieceDate",
    "EcritureLib",
    "Debit",
    "Credit",
    "EcritureLet",
    "DateLet",
    "ValidDate",
    "Montantdevise",
    "Idevise",
)
SEPARATEUR_ZONE = "\t"
SEPARATEUR_ENREGISTREMENT = "\r\n"

LIBELLE_JOURNAL = {
    Journal.BQ: "Banque",
    Journal.AC: "Achats",
    Journal.VE: "Ventes",
    Journal.OD: "Opérations diverses",
    Journal.AN: "À-nouveaux",
}

# Libellés PCG des comptes que la démo peut émettre. Pour un compte absent,
# `libelle_compte` remonte au préfixe connu le plus long (compte, puis
# sous-classe, puis classe) : `CompteLib` n'est jamais vide.
LIBELLE_COMPTE = {
    "101": "Capital",
    "1013": "Capital souscrit, appelé, versé",
    "218": "Autres immobilisations corporelles",
    "444": "État, impôts sur les bénéfices",
    "455": "Associés, comptes courants",
    "457": "Associés, dividendes à payer",
    "471": "Compte d'attente",
    "512": "Banques",
    "602": "Achats stockés, autres approvisionnements",
    "604": "Achats d'études et prestations de services",
    "6061": "Fournitures non stockables (eau, énergie, carburant)",
    "612": "Redevances de crédit-bail",
    "613": "Locations",
    "6135": "Locations mobilières",
    "6155": "Entretien et réparations sur biens mobiliers",
    "6160": "Primes d'assurances",
    "618": "Divers (documentation, abonnements)",
    "622": "Rémunérations d'intermédiaires et honoraires",
    "6226": "Honoraires",
    "6251": "Voyages et déplacements",
    "6256": "Missions",
    "626": "Frais postaux et de télécommunications",
    "627": "Services bancaires et assimilés",
    "641": "Rémunérations du personnel",
    "645": "Charges de sécurité sociale et de prévoyance",
    "6450": "Charges de sécurité sociale et de prévoyance",
    "6475": "Médecine du travail, pharmacie",
    "661": "Charges d'intérêts",
    "671": "Charges exceptionnelles sur opérations de gestion",
    "6712": "Pénalités, amendes fiscales et pénales",
    "681": "Dotations aux amortissements et provisions",
    "695": "Impôts sur les bénéfices",
    "706": "Prestations de services",
    "741": "Subventions d'exploitation",
    "758": "Produits divers de gestion courante",
    "44551": "TVA à décaisser",
    "44566": "TVA déductible sur autres biens et services",
    "44567": "Crédit de TVA à reporter",
    "44571": "TVA collectée",
    # Sous-classes et classes du PCG : repli pour tout autre compte.
    "10": "Capital et réserves",
    "12": "Résultat de l'exercice",
    "16": "Emprunts et dettes assimilées",
    "20": "Immobilisations incorporelles",
    "21": "Immobilisations corporelles",
    "28": "Amortissements des immobilisations",
    "40": "Fournisseurs et comptes rattachés",
    "41": "Clients et comptes rattachés",
    "42": "Personnel et comptes rattachés",
    "43": "Sécurité sociale et autres organismes sociaux",
    "44": "État et autres collectivités publiques",
    "45": "Groupe et associés",
    "46": "Débiteurs divers et créditeurs divers",
    "47": "Comptes transitoires ou d'attente",
    "51": "Banques, établissements financiers et assimilés",
    "53": "Caisse",
    "60": "Achats",
    "61": "Services extérieurs",
    "62": "Autres services extérieurs",
    "63": "Impôts, taxes et versements assimilés",
    "64": "Charges de personnel",
    "65": "Autres charges de gestion courante",
    "66": "Charges financières",
    "67": "Charges exceptionnelles",
    "68": "Dotations aux amortissements, dépréciations et provisions",
    "69": "Participation des salariés, impôts sur les bénéfices",
    "70": "Ventes de produits fabriqués, prestations de services",
    "74": "Subventions d'exploitation",
    "75": "Autres produits de gestion courante",
    "76": "Produits financiers",
    "77": "Produits exceptionnels",
    "78": "Reprises sur amortissements, dépréciations et provisions",
    "1": "Comptes de capitaux",
    "2": "Comptes d'immobilisations",
    "3": "Comptes de stocks et en-cours",
    "4": "Comptes de tiers",
    "5": "Comptes financiers",
    "6": "Comptes de charges",
    "7": "Comptes de produits",
}

_CARACTERES_INTERDITS = re.compile(r"[\t\r\n]+")


def libelle_compte(compte: str) -> str:
    """Libellé du préfixe connu le plus long : jamais vide pour un numéro
    de compte PCG (classes 1 à 7), jamais inventé au-delà de la table."""
    for longueur in range(len(compte), 0, -1):
        libelle = LIBELLE_COMPTE.get(compte[:longueur])
        if libelle is not None:
            return libelle
    return ""


def nom_fichier_fec(siren: str, cloture: date) -> str:
    """`SirenFECAAAAMMJJ` (A.47 A-1), extension .txt pour un fichier à plat."""
    return f"{siren}FEC{cloture.strftime('%Y%m%d')}.txt"


def _zone(valeur: str) -> str:
    return _CARACTERES_INTERDITS.sub(" ", valeur).strip()


def _montant(centimes: int) -> str:
    """848,00 : virgule décimale, pas de séparateur de milliers."""
    return f"{centimes // 100},{centimes % 100:02d}"


def _ligne_fec(ecriture: Ecriture, numero: int, ligne: LigneEcriture) -> tuple[str, ...]:
    date_str = ecriture.date.strftime("%Y%m%d")
    debit = _montant(ligne.montant.centimes) if ligne.sens is Sens.DEBIT else "0,00"
    credit = _montant(ligne.montant.centimes) if ligne.sens is Sens.CREDIT else "0,00"
    return (
        ecriture.journal.name,
        LIBELLE_JOURNAL[ecriture.journal],
        str(numero),
        date_str,
        ligne.compte,
        libelle_compte(ligne.compte),
        "",  # CompAuxNum — pas de compte auxiliaire modélisé (facultatif)
        "",  # CompAuxLib
        _zone(ecriture.reference_piece or ecriture.id),
        date_str,  # PieceDate — pas distincte de la date d'écriture (démo)
        _zone(ecriture.libelle),
        debit,
        credit,
        "",  # EcritureLet — pas de lettrage modélisé (facultatif)
        "",  # DateLet
        date_str,  # ValidDate — tout est validé immédiatement (doc 17 §3)
        "",  # Montantdevise — toujours en EUR, zone facultative
        "",  # Idevise
    )


def exporter_fec(ecritures: tuple[Ecriture, ...]) -> str:
    """Écritures triées par date (les à-nouveaux d'abord le même jour), puis
    numérotées 1, 2, 3... dans cet ordre : la séquence continue et
    chronologique qu'exige le BOI, quelle que soit la numérotation interne."""
    ordre_journal = {Journal.AN: 0}
    triees = sorted(ecritures, key=lambda e: (e.date, ordre_journal.get(e.journal, 1), e.id))
    lignes_texte = [SEPARATEUR_ZONE.join(COLONNES_FEC)]
    for numero, ecriture in enumerate(triees, start=1):
        lignes_texte += [
            SEPARATEUR_ZONE.join(_ligne_fec(ecriture, numero, ligne)) for ligne in ecriture.lignes
        ]
    return SEPARATEUR_ENREGISTREMENT.join(lignes_texte) + SEPARATEUR_ENREGISTREMENT
