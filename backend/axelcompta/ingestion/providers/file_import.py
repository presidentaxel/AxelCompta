"""FileImportProvider — CSV/XLSX/ODS/OFX/QIF (doc 04 §3).

Chemin C (doc 17 §4) : rejoue `_AUDIT_DONNEES/resultats/fec_ml_taxonomie.csv`
(36 152 lignes réelles labellisées — pas committé, gitignored, présent
seulement sur les postes qui ont fait tourner l'audit) comme filet
d'ingestion bancaire.

Ce CSV est un **export FEC déjà comptabilisé**, pas un relevé bancaire brut :
son `montant` suit la convention débit-crédit (`extraire_fec.py` :
`montant = debit - credit`). Pour obtenir le sens « relevé bancaire »
(positif = argent reçu, doc 13 §4.1), il faut l'**inverser** — vérifié sur
deux exemples réels : un virement reçu (compte 7060, produit) a un montant
FEC négatif, un paiement (compte 6278, charge) a un montant FEC positif ;
dans les deux cas l'inverse redonne le sens attendu d'un relevé bancaire.

Les écritures composites (une même transaction bancaire ventilée sur
plusieurs comptes, `piece_ref` du type `PAI-185#0`, `PAI-185#1`...) sont
regroupées par piece_ref de base et sommées pour reconstituer une seule
transaction par mouvement bancaire réel — vérifié : la somme des lignes
d'un groupe composite redonne un montant cohérent avec son libellé unique.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from axelcompta.core.ids import DossierId, TenantId

from .base import DataProvider, NormalizedTransaction, PlatformSettlement, ProviderHealth

# backend/axelcompta/ingestion/providers/file_import.py -> racine du repo
CSV_AUDIT_PAR_DEFAUT = (
    Path(__file__).resolve().parents[4] / "_AUDIT_DONNEES" / "resultats" / "fec_ml_taxonomie.csv"
)


def _vers_centimes(montant: str) -> int:
    return int((Decimal(montant) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _cle_transaction(ligne: dict[str, str]) -> tuple[str, str, str]:
    """Une transaction bancaire = un piece_ref de base (avant le `#` des
    composites) + sa date, dans un dossier donné (doc 13 §2.1)."""
    return (ligne["dossier_id"], ligne["piece_ref"].split("#")[0], ligne["date"])


def _regrouper(
    chemin: Path, dossier_id: DossierId, depuis: date, jusqua: date
) -> dict[tuple[str, str, str], list[dict[str, str]]]:
    groupes: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    with chemin.open(newline="", encoding="utf-8") as fichier:
        for ligne in csv.DictReader(fichier):
            if ligne["dossier_id"] != dossier_id:
                continue
            date_operation = datetime.strptime(ligne["date"], "%Y-%m-%d").date()
            if depuis <= date_operation <= jusqua:
                groupes[_cle_transaction(ligne)].append(ligne)
    return groupes


def charger_transactions_csv(
    chemin: Path, dossier_id: DossierId, depuis: date, jusqua: date
) -> list[NormalizedTransaction]:
    groupes = _regrouper(chemin, dossier_id, depuis, jusqua)
    resultat = [
        NormalizedTransaction(
            dossier_id=dossier_id,
            date=datetime.strptime(cle[2], "%Y-%m-%d").date(),
            montant_cts=-sum(_vers_centimes(ligne["montant"]) for ligne in lignes),
            libelle=lignes[0]["libelle_bancaire"],
            source_provider="file_import",
            raw_payload={"lignes_fec": lignes},
        )
        for cle, lignes in groupes.items()
    ]
    return sorted(resultat, key=lambda t: t.date)


class FileImportProvider(DataProvider):
    """doc 04 §3. Chemin C de la démo (doc 17 §4) avec le CSV audit par défaut."""

    def __init__(self, chemin_csv: Path | None = None) -> None:
        self._chemin_csv = chemin_csv or CSV_AUDIT_PAR_DEFAUT

    async def fetch_transactions(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[NormalizedTransaction]:
        return charger_transactions_csv(self._chemin_csv, dossier_id, since, until)

    async def fetch_platform_settlements(
        self, tenant_id: TenantId, dossier_id: DossierId, since: date, until: date
    ) -> list[PlatformSettlement]:
        return []  # les fichiers importés ne portent pas de settlements plateforme

    async def health(self) -> ProviderHealth:
        existe = self._chemin_csv.is_file()
        message = str(self._chemin_csv) if existe else f"fichier introuvable : {self._chemin_csv}"
        return ProviderHealth(ok=existe, message=message)
