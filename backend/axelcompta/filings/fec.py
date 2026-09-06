"""Export FEC — Fichier des Écritures Comptables (art. A.47 A-1 du LPF,
doc 06 §6). **Le format légal exigé en cas de contrôle fiscal** — le détail
derrière un chiffre de liasse, pas juste le chiffre (2026-09-05, suite à
« s'il est faux, on ne sait pas »).

18 colonnes normées, une ligne par ligne d'écriture — même schéma que
`_AUDIT_DONNEES/extraire_fec.py` (utilisé pour extraire l'historique réel),
pas réinventé.

**Limite assumée** : structurellement correct (18 colonnes, fichier texte
tabulé), mais pas passé dans « Test Compta Demat » (l'outil de validation
DGFiP) ni comparé octet à octet à un FEC de référence — la checklist
complète (doc 09 §3) reste V1, pas cette démo.
"""

from __future__ import annotations

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

LIBELLE_JOURNAL = {
    Journal.BQ: "Banque",
    Journal.AC: "Achats",
    Journal.VE: "Ventes",
    Journal.OD: "Opérations diverses",
    Journal.AN: "À-nouveaux",
}

# Libellés PCG usuels des comptes que la démo peut émettre — best-effort pour
# la lisibilité, pas un jugement comptable validé (même statut que le mapping
# compte par catégorie, doc 12 §0.2).
LIBELLE_COMPTE = {
    "101": "Capital",
    "218": "Autres immobilisations corporelles",
    "444": "État — Impôts et taxes",
    "457": "Associés — Dividendes à payer",
    "471": "Compte d'attente",
    "512": "Banques",
    "602": "Achats stockés — Autres approvisionnements",
    "604": "Achats d'études et prestations de services",
    "6061": "Achats non stockés — Carburant",
    "612": "Redevances de crédit-bail (mobilier)",
    "613": "Locations",
    "6135": "Locations mobilières",
    "6155": "Entretien et réparations sur biens mobiliers",
    "6160": "Assurances",
    "618": "Divers (documentation, abonnements)",
    "622": "Rémunérations d'intermédiaires et honoraires",
    "6226": "Honoraires",
    "6251": "Voyages et déplacements",
    "6256": "Missions et réceptions",
    "626": "Frais postaux et de télécommunications",
    "627": "Services bancaires et assimilés",
    "641": "Rémunérations du personnel",
    "645": "Charges de sécurité sociale et de prévoyance",
    "6450": "Charges de sécurité sociale et de prévoyance",
    "6475": "Autres charges sociales",
    "661": "Charges d'intérêts",
    "671": "Charges exceptionnelles sur opérations de gestion",
    "681": "Dotations aux amortissements et provisions",
    "706": "Prestations de services",
    "741": "Subventions d'exploitation",
    "758": "Produits divers de gestion courante",
    "44566": "TVA déductible sur autres biens et services",
    "44571": "TVA collectée",
}


def libelle_compte(compte: str) -> str:
    """Chaîne vide si le compte n'est pas dans la table — jamais un libellé
    inventé pour un compte inconnu."""
    return LIBELLE_COMPTE.get(compte, "")


def _montant(centimes: int) -> str:
    return f"{centimes / 100:.2f}"


def _ligne_fec(ecriture: Ecriture, ligne: LigneEcriture) -> tuple[str, ...]:
    date_str = ecriture.date.strftime("%Y%m%d")
    debit = _montant(ligne.montant.centimes) if ligne.sens is Sens.DEBIT else "0.00"
    credit = _montant(ligne.montant.centimes) if ligne.sens is Sens.CREDIT else "0.00"
    return (
        ecriture.journal.name,
        LIBELLE_JOURNAL[ecriture.journal],
        ecriture.id,
        date_str,
        ligne.compte,
        libelle_compte(ligne.compte),
        "",  # CompAuxNum — pas de compte auxiliaire modélisé (démo)
        "",  # CompAuxLib
        ecriture.reference_piece or ecriture.id,
        date_str,  # PieceDate — pas distincte de la date d'écriture (démo)
        ecriture.libelle,
        debit,
        credit,
        "",  # EcritureLet — pas de lettrage modélisé (démo)
        "",  # DateLet
        date_str,  # ValidDate — tout est validé immédiatement, pas de workflow (doc 17 §3)
        "",  # Montantdevise — toujours en EUR (démo)
        "",  # Idevise
    )


def exporter_fec(ecritures: tuple[Ecriture, ...]) -> str:
    """Une ligne par ligne d'écriture, triées par date — l'ordre
    chronologique attendu d'un FEC (art. A.47 A-1)."""
    paires = sorted(
        ((ecriture, ligne) for ecriture in ecritures for ligne in ecriture.lignes),
        key=lambda paire: (paire[0].date, paire[0].id),
    )
    lignes_texte = ["\t".join(COLONNES_FEC)]
    lignes_texte += ["\t".join(_ligne_fec(ecriture, ligne)) for ecriture, ligne in paires]
    return "\n".join(lignes_texte) + "\n"
