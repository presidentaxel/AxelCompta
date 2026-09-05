"""Squelette de structure — aucune validation, aucune persistance.

La matrice complète statut × régime (doc 06 §7) et son modèle Pydantic
Settings-validé restent à écrire ; ceci ne fixe que la forme des objets.
"""

from __future__ import annotations

from dataclasses import dataclass

from axelcompta.core.ids import DossierId, TenantId


@dataclass(frozen=True, slots=True)
class Tenant:
    """Mode portefeuille (1 → N dossiers) ou mono-entreprise (1 → 1), doc 01 §1."""

    id: TenantId


@dataclass(frozen=True, slots=True)
class Dossier:
    """Un dossier comptable indépendant : sa config ne s'hérite jamais du tenant
    au-delà du pré-remplissage à la création (doc 03 §3bis).
    """

    id: DossierId
    tenant_id: TenantId
    forme_juridique: str  # ex. "SASU", "EURL" — à typer en enum (doc 06 §7)
    regime_imposition: str  # "IS" ou "option_IR" — option IR bornée à 5 exercices
    regime_tva: str  # "reel_normal" | "reel_simplifie" | "franchise"
