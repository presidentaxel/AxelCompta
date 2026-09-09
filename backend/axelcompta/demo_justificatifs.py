"""Justificatifs joints par le chauffeur (doc 17 §9 Semaine 3, doc 19 §5.7).

Portée démo assumée (doc 17 §8) : « la photo s'attache à la transaction,
le contenu n'est pas lu » — aucun OCR ici, ça reste V1 (doc 04 §3, module
`documents/`). Composition root de démo comme `demo_comptes.py`/
`demo_auth.py` (doc 18) : le futur module `documents/` accueillera le
stockage WORM réel et la cascade d'extraction (OCR/Vision), pas ce
fichier — celui-ci ne fait que constater « une photo a été jointe à cette
écriture », rien de plus.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class JustificatifRepository(Protocol):
    """Frontière (doc 18) — deux implémentations : `InMemory...` pour la
    suite rapide, `Fichier...` pour la démo réelle."""

    def enregistrer(
        self, dossier_id: str, ecriture_id: str, contenu: bytes, extension: str
    ) -> None: ...

    def a_un_justificatif(self, dossier_id: str, ecriture_id: str) -> bool: ...


class InMemoryJustificatifRepository:
    """Pour la suite de tests rapide — ne touche jamais le disque."""

    def __init__(self) -> None:
        self._stockage: dict[tuple[str, str], bytes] = {}

    def enregistrer(
        self, dossier_id: str, ecriture_id: str, contenu: bytes, extension: str
    ) -> None:
        self._stockage[(dossier_id, ecriture_id)] = contenu

    def a_un_justificatif(self, dossier_id: str, ecriture_id: str) -> bool:
        return (dossier_id, ecriture_id) in self._stockage


class FichierJustificatifRepository:
    """Stockage réel pour la démo : un fichier par écriture sous
    `<racine>/<dossier_id>/<ecriture_id><extension>`. Pas de WORM, pas de
    hash/horodatage d'archivage (doc 04 §1 : ça reste V1) — suffisant pour
    prouver que « la photo s'attache à la transaction », rien de plus."""

    def __init__(self, racine: Path) -> None:
        self._racine = racine

    def enregistrer(
        self, dossier_id: str, ecriture_id: str, contenu: bytes, extension: str
    ) -> None:
        dossier = self._racine / dossier_id
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / f"{ecriture_id}{extension}").write_bytes(contenu)

    def a_un_justificatif(self, dossier_id: str, ecriture_id: str) -> bool:
        dossier = self._racine / dossier_id
        if not dossier.exists():
            return False
        return any(chemin.stem == ecriture_id for chemin in dossier.iterdir())
