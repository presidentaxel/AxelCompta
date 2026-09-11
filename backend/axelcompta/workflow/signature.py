"""Signature électronique d'un document — doc 18 (`workflow` : « validation,
revue, signature électronique »), doc 20 §4/§5.

**Contrat pensé pour la prod, pas juste pour la démo** (Louis, 2026-09-11 :
« on fait la démo en pensant à la prod, ne fais pas un système qu'il
faudra entièrement refaire »). `SignatureProvider` est l'abstraction que
brancheront plus tard les vrais prestataires eIDAS (Universign, Yousign/
Youtrust…, comparatif doc 20 §7) une fois ADR-004 tranché — `signer()` ne
change pas de signature de méthode entre la démo et la prod, seule
l'implémentation change (même principe que `DataProvider`, doc 13 §2, ou
que `DigifactoryProvider` chemin B → chemin A, doc 16).

**Ce que la démo ne fait jamais** : produire une vraie signature qualifiée
RGS (impossible sans certificat + prestataire réel, doc 20 §4). Le
`qualifie=False` sur `DocumentSigne` est le signal explicite qu'aucun
document signé par ce provider ne doit jamais être déposé pour de vrai —
doctrine d'erreurs doc 08 §5 : un artefact de démo ne doit jamais pouvoir
se faire passer pour un vrai document officiel.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from axelcompta.core.ids import DossierId, UserId


@dataclass(frozen=True, slots=True)
class DocumentSigne:
    """Le résultat d'une signature — `qualifie` distingue une vraie
    signature électronique qualifiée RGS (V1, prestataire à choisir,
    ADR-004) d'un tampon de démo (toujours `False` ici)."""

    contenu_pdf: bytes
    signataire: UserId
    signe_le: datetime
    provider: str  # "demo" en démo ; nom du prestataire réel en V1
    qualifie: bool


class SignatureProvider(ABC):
    """Frontière : produit un `DocumentSigne` à partir d'un PDF non signé.
    Le prestataire réel (V1) fera probablement un aller-retour réseau
    (upload, redirection ou iframe selon le prestataire, doc 20 §7) —
    cette interface n'en présume rien, `signer()` reste une opération
    unique du point de vue de l'appelant."""

    @abstractmethod
    def signer(self, contenu_pdf: bytes, signataire: UserId) -> DocumentSigne:
        """Signe `contenu_pdf` au nom de `signataire`."""


class SignatureRepository(ABC):
    """Frontière de persistance — un document signé doit survivre entre
    deux requêtes (même principe que `DecisionRepository`, doc 17 §9 bloc
    A : « pas juste un changement d'état côté React »)."""

    @abstractmethod
    def enregistrer(
        self, dossier_id: DossierId, type_document: str, document: DocumentSigne
    ) -> None:
        """Enregistre la signature courante pour ce dossier/type de
        document — remplace la précédente s'il y en avait une (contrairement
        à `DecisionHumaine`, un document de dépôt n'a pas besoin d'historique
        de versions signées pour la démo)."""

    @abstractmethod
    def dernier(self, dossier_id: DossierId, type_document: str) -> DocumentSigne | None:
        """Le dernier document signé pour ce dossier/type, ou `None` si
        jamais signé."""
