"""Crée un dossier et un compte de démo par contact Digifactory, puis synchronise.

Les e-mails sont fictifs (`demo-digi-<nr>@axelcompta.fr`). Le mot de passe
est celui des chauffeurs de démo déjà en place. Les transactions écrites en
base viennent de l'API au moment de l'exécution.

Usage, depuis backend/ :

    python scripts/ajouter_chauffeurs_digifactory.py

Idempotent : un contact déjà mappé et un e-mail déjà créé sont laissés tels
quels. La synchro, elle, rejoue (curseur, pas de doublon d'écriture).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

import httpx
from dotenv import load_dotenv

from axelcompta.core.db import engine_depuis_env
from axelcompta.demo_comptes import SupabaseConfig
from axelcompta.demo_digifactory import (
    MOT_DE_PASSE_COMMUN,
    TENANT_DEMO,
    corps_compte_demo,
    dossier_depuis_contact,
    email_demo,
    forme_depuis_nature_juridique,
    numero_contact,
    siren_contact,
)
from axelcompta.ingestion.providers.digifactory import DigifactoryHttpClient
from axelcompta.synchro_digifactory import synchroniser_portefeuille
from axelcompta.tenants.models import Dossier, Tenant
from axelcompta.tenants.postgres import PostgresDossierRepository

_DEJA_PRIS = ("already", "already been registered", "déjà")


def _assurer_dossier(depot: PostgresDossierRepository, voulu: Dossier) -> tuple[Dossier, str]:
    if voulu.contact_nr is None:
        raise RuntimeError(f"{voulu.id} sans contact")
    existant = depot.par_contact_nr(voulu.contact_nr)
    if existant is not None:
        return existant, "déjà en base"
    depot.enregistrer(voulu)
    enregistre = depot.obtenir(voulu.id)
    if enregistre is None:
        raise RuntimeError(f"{voulu.id} non relu après écriture")
    return enregistre, "créé"


def _creer_compte(client: httpx.Client, dossier: Dossier) -> str:
    email = email_demo(dossier.contact_nr or "")
    corps = corps_compte_demo(email, dossier.id, MOT_DE_PASSE_COMMUN)
    reponse = client.post("/admin/users", json=corps)
    if reponse.status_code < 400:
        return "compte créé"
    texte = reponse.text.lower()
    if reponse.status_code in (409, 422) and any(marque in texte for marque in _DEJA_PRIS):
        return "compte déjà là"
    raise RuntimeError(f"compte {email} refusé ({reponse.status_code})")


async def _contacts_bruts() -> dict[str, dict[str, object]]:
    client = DigifactoryHttpClient.depuis_env()
    try:
        brut = await client.contacts()
    finally:
        await client.aclose()
    return {str(nr): contact for nr, contact in brut.items() if isinstance(contact, dict)}


def _forme_sirene(siren: str) -> str | None:
    """Recherche d'entreprises (data.gouv, sans clé). On n'accepte que le
    résultat dont le SIREN est exactement celui demandé."""
    reponse = httpx.get(
        "https://recherche-entreprises.api.gouv.fr/search",
        params={"q": siren, "per_page": 1},
        headers={"accept": "application/json"},
        timeout=15.0,
    )
    reponse.raise_for_status()
    resultats = reponse.json().get("results") or []
    if not resultats or str(resultats[0].get("siren") or "") != siren:
        return None
    nature = resultats[0].get("nature_juridique")
    if not isinstance(nature, str):
        return None
    return forme_depuis_nature_juridique(nature)


def _aligner_formes(depot: PostgresDossierRepository) -> None:
    for contact in asyncio.run(_contacts_bruts()).values():
        dossier = depot.par_contact_nr(numero_contact(contact))
        if dossier is None:
            continue
        siren = siren_contact(contact)
        if siren is None:
            print(
                f"{dossier.id} : pas de SIREN, forme laissée {dossier.forme_juridique}", flush=True
            )
            continue
        forme = _forme_sirene(siren)
        if forme is None:
            print(f"{dossier.id} : nature juridique non reconnue", flush=True)
            continue
        if forme != dossier.forme_juridique:
            depot.poser_forme_juridique(dossier.id, forme)
        print(f"{dossier.id} : {forme}", flush=True)


def main() -> int:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    depot = PostgresDossierRepository(engine_depuis_env())
    if len(sys.argv) > 1 and sys.argv[1] == "--formes":
        _aligner_formes(depot)
        return 0
    depot.enregistrer_tenant(Tenant(id=TENANT_DEMO, nom="Portefeuille démo"))
    voulus = tuple(
        dossier_depuis_contact(contact, date.today())
        for contact in asyncio.run(_contacts_bruts()).values()
    )
    dossiers = tuple(_poser(depot, voulu) for voulu in voulus)
    _aligner_formes(depot)
    _comptes(dossiers)
    engine = engine_depuis_env()
    erreurs = 0
    for dossier in dossiers:
        print(f"Synchro {dossier.id}…", flush=True)
        resultats = synchroniser_portefeuille(engine, (dossier,))
        for resultat in resultats:
            if resultat.erreur:
                erreurs += 1
                print(f"  ECHEC {resultat.erreur}", flush=True)
            elif resultat.rapport:
                rapport = resultat.rapport
                print(
                    f"  {rapport.nouvelles} nouvelles, {rapport.deja_connues} déjà connues, "
                    f"{rapport.rejets} rejetées",
                    flush=True,
                )
    return 1 if erreurs else 0


def _poser(depot: PostgresDossierRepository, voulu: Dossier) -> Dossier:
    dossier, etat = _assurer_dossier(depot, voulu)
    print(f"{dossier.id} ({email_demo(dossier.contact_nr or '')}) : {etat}", flush=True)
    return dossier


def _comptes(dossiers: tuple[Dossier, ...]) -> None:
    config = SupabaseConfig.depuis_env()
    with httpx.Client(
        base_url=f"{config.url}/auth/v1",
        headers={
            "apikey": config.service_role_key,
            "Authorization": f"Bearer {config.service_role_key}",
        },
        timeout=15.0,
    ) as client:
        for dossier in dossiers:
            print(
                f"  {email_demo(dossier.contact_nr or '')} : {_creer_compte(client, dossier)}",
                flush=True,
            )


if __name__ == "__main__":
    sys.exit(main())
