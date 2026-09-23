"""Identités légales **fictives** des 3 chauffeurs de démo (doc 17 §4), pour
remplir les en-têtes de la liasse fiscale (2065 cadre A, 2033-A à G) et le
nom du FEC.

Tout est inventé, comme les chauffeurs eux-mêmes : les SIREN respectent la
clé de contrôle (Luhn) pour passer les contrôles de format, et ont été
vérifiés **non attribués** dans l'annuaire des entreprises
(recherche-entreprises.api.gouv.fr, 2026-09-23). Courriels en
`example.com`, domaine réservé qui ne peut appartenir à personne.
"""

from __future__ import annotations

from datetime import date

from axelcompta.core.identite import Adresse, Associe, IdentiteEntreprise

CODE_APE_VTC = "4932Z"
ACTIVITE_VTC = "Transport de personnes par VTC"

IDENTITE_KARIM = IdentiteEntreprise(
    denomination="AMRANI VTC",
    siren="987142031",
    nic="00010",
    adresse_siege=Adresse("14", "rue de la Fontaine au Roi", "75011", "Paris"),
    code_ape=CODE_APE_VTC,
    activite=ACTIVITE_VTC,
    email="contact@amrani-vtc.example.com",
    capital_social_cts=1_000_00,
    associes=(
        Associe(
            civilite="M",
            nom="AMRANI",
            prenoms="Karim",
            date_naissance=date(1988, 3, 14),
            departement_naissance="93",
            commune_naissance="Saint-Denis",
            adresse=Adresse("14", "rue de la Fontaine au Roi", "75011", "Paris"),
            nb_titres=1_000,
            qualite="Président",
        ),
    ),
)

IDENTITE_SOPHIE = IdentiteEntreprise(
    denomination="SM CHAUFFEUR PRIVE",
    siren="987145778",
    nic="00013",
    adresse_siege=Adresse("6", "avenue Jean Jaurès", "92120", "Montrouge"),
    code_ape=CODE_APE_VTC,
    activite=ACTIVITE_VTC,
    email="sophie@sm-chauffeur.example.com",
    capital_social_cts=1_500_00,
    associes=(
        Associe(
            civilite="MME",
            nom="MARCHAND",
            prenoms="Sophie",
            date_naissance=date(1991, 9, 2),
            departement_naissance="69",
            commune_naissance="Lyon",
            adresse=Adresse("6", "avenue Jean Jaurès", "92120", "Montrouge"),
            nb_titres=150,
            qualite="Gérante",
        ),
    ),
)

IDENTITE_YANIS = IdentiteEntreprise(
    denomination="YH TRANSPORT",
    siren="987150315",
    nic="00016",
    adresse_siege=Adresse("27", "boulevard de la Libération", "94300", "Vincennes"),
    code_ape=CODE_APE_VTC,
    activite=ACTIVITE_VTC,
    email="yanis@yh-transport.example.com",
    capital_social_cts=500_00,
    associes=(
        Associe(
            civilite="M",
            nom="HADDAD",
            prenoms="Yanis",
            date_naissance=date(1996, 11, 21),
            departement_naissance="94",
            commune_naissance="Créteil",
            adresse=Adresse("27", "boulevard de la Libération", "94300", "Vincennes"),
            nb_titres=500,
            qualite="Président",
        ),
    ),
)

IDENTITES_DEMO: dict[str, IdentiteEntreprise] = {
    "DEMO_karim": IDENTITE_KARIM,
    "DEMO_sophie": IDENTITE_SOPHIE,
    "DEMO_yanis": IDENTITE_YANIS,
}
