"""Génère un tableau Excel de suivi des statuts fiscaux par chauffeur, avec
liens cliquables vers les documents sources, pour compléter la collecte
demandée en priorité #2 (README racine / doc 01 §9 / doc 06 §7).

⚠️ Ce script travaille sur des identités réelles (noms de chauffeurs) — PAS de
pseudonymisation ici, contrairement à extraire_fec.py : c'est un outil de
travail interne, pas un dataset d'entraînement. Le fichier produit ne doit
jamais être commité (il tombe sous sortie/, déjà gitignoré) ni envoyé à un
tiers sans anonymisation.

Ce que le script détecte automatiquement (colonnes bleutées, à VÉRIFIER) :
- Forme juridique (SASU/EURL) par mention dans les noms de fichiers Statuts/Kbis
- SIRET/SIREN extrait du nom des fichiers FEC (souvent préfixé)
- Indice de régime TVA : présence de docs "Acompte TVA" (indice réel simplifié
  historique) ou mention explicite "franchise"
- Statut apparent du dossier (actif / clôturé / résilié / repris) d'après les
  noms de sous-dossiers (Clôture, Fin contrat, Résilié, Reprise...)
- Présence de FEC / Grand Livre / Balance exploitables

Ce qu'il NE fait PAS : lire le contenu des PDF (pas d'OCR ici). Les colonnes
jaunes sont à remplir à la main après ouverture du document via le lien.

Usage:
    python generer_tableau_suivi.py --racine "/chemin/vers/Dossier Chauffeurs" \
        --sortie sortie/suivi_statuts_fiscaux.xlsx

Dépendances : openpyxl (pip install openpyxl)
"""
import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

FEC_RE = re.compile(r"FEC\d*\.(csv|txt)$", re.IGNORECASE)
SIRET_IN_FEC_RE = re.compile(r"(\d{9,14})FEC")
STATUT_APPARENT_MOTS = {
    "résilié / fin de contrat": ["fin contrat", "fin ct", "resilie", "résilié", "annule", "annulé"],
    "repris (ancien dossier)": ["reprise"],
    "clôturé (au moins un exercice)": ["cloture", "clôture"],
}

BLEU_DETECTE = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
JAUNE_A_REMPLIR = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
GRIS_HEADER = PatternFill(start_color="404040", end_color="404040", fill_type="solid")
BLANC_GRAS = Font(bold=True, color="FFFFFF")
LIEN_FONT = Font(color="0563C1", underline="single")


def to_file_uri(p: Path) -> str:
    try:
        return "file://" + quote(str(p))
    except Exception:
        return ""


def classifier_fichier(nom: str) -> set:
    low = nom.lower()
    tags = set()
    if "statut" in low:
        tags.add("statuts")
    if "kbis" in low or "k-bis" in low:
        tags.add("kbis")
    if "franchise" in low:
        tags.add("franchise")
    if "acompte" in low and "tva" in low:
        tags.add("acompte_tva")
    elif "tva" in low:
        tags.add("tva")
    if "grand livre" in low or "grandlivre" in low:
        tags.add("grand_livre")
    if "balance" in low:
        tags.add("balance")
    if FEC_RE.search(nom):
        tags.add("fec")
    if "sasu" in low:
        tags.add("mention_sasu")
    if "eurl" in low:
        tags.add("mention_eurl")
    return tags


def analyser_dossier(chemin_chauffeur: Path):
    matches = {k: [] for k in (
        "statuts", "kbis", "tva", "franchise", "acompte_tva",
        "grand_livre", "balance", "fec", "mention_sasu", "mention_eurl",
    )}
    statut_hits = []
    for root, dirs, files in os.walk(chemin_chauffeur):
        rel = Path(root).relative_to(chemin_chauffeur)
        for part in rel.parts:
            low = part.lower()
            for libelle, mots in STATUT_APPARENT_MOTS.items():
                if any(m in low for m in mots):
                    statut_hits.append(libelle)
        for f in files:
            tags = classifier_fichier(f)
            full = Path(root) / f
            for t in tags:
                if len(matches[t]) < 3:
                    matches[t].append(full)

    if matches["mention_sasu"] and matches["mention_eurl"]:
        forme_detectee = "Ambigu (SASU + EURL mentionnés)"
    elif matches["mention_sasu"]:
        forme_detectee = "SASU (détecté)"
    elif matches["mention_eurl"]:
        forme_detectee = "EURL (détecté)"
    else:
        forme_detectee = "Non détecté"

    if matches["franchise"]:
        tva_detectee = "Franchise (mention trouvée)"
    elif matches["acompte_tva"]:
        tva_detectee = "Acomptes trouvés -> historiquement réel simplifié"
    elif matches["tva"]:
        tva_detectee = "Doc TVA présent, à vérifier"
    else:
        tva_detectee = "Aucun doc TVA trouvé"

    siret = ""
    for f in matches["fec"]:
        m = SIRET_IN_FEC_RE.search(f.name)
        if m:
            siret = m.group(1)
            break

    if statut_hits:
        # priorité : résilié > repris > clôturé
        for libelle in STATUT_APPARENT_MOTS:
            if libelle in statut_hits:
                statut_apparent = libelle
                break
    else:
        statut_apparent = "Actif (probable, aucun indice de clôture)"

    return {
        "matches": matches,
        "forme_detectee": forme_detectee,
        "tva_detectee": tva_detectee,
        "siret": siret,
        "statut_apparent": statut_apparent,
    }


def poser_lien(ws, cell_ref, path: Path, texte: str):
    cell = ws[cell_ref]
    if not path:
        cell.value = "—"
        return
    uri = to_file_uri(path)
    cell.value = texte
    try:
        cell.hyperlink = uri
        cell.font = LIEN_FONT
    except Exception:
        pass  # chemin trop long ou caractère invalide pour un hyperlien OOXML — on garde juste le texte


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--racine", required=True)
    parser.add_argument("--sortie", default="sortie/suivi_statuts_fiscaux.xlsx")
    args = parser.parse_args()

    racine = Path(args.racine)
    if not racine.is_dir():
        sys.exit(f"Dossier introuvable : {racine}")

    dossiers = sorted((p for p in racine.iterdir() if p.is_dir()), key=lambda p: p.name)
    print(f"{len(dossiers)} dossiers chauffeurs à analyser...")

    wb = Workbook()
    ws = wb.active
    ws.title = "Suivi statuts fiscaux"

    entetes = [
        "Nom dossier", "Lien dossier", "Statut apparent (détecté)",
        "SIRET (détecté)", "Forme juridique (détectée)", "Statuts/Kbis (lien)",
        "Indice régime TVA (détecté)", "Doc TVA (lien)", "FEC (lien)",
        "Grand livre / Balance (lien)",
        "--- À REMPLIR ---",
        "Forme juridique (validée)", "Régime imposition (validé)",
        "Date début option IR (si applicable)", "Régime TVA achats (validé)",
        "Régime TVA recettes (validé)", "Statut dossier (validé)",
        "Vérifié par / le", "Notes",
    ]
    ws.append(entetes)
    for col_idx in range(1, len(entetes) + 1):
        c = ws.cell(row=1, column=col_idx)
        c.fill = GRIS_HEADER
        c.font = BLANC_GRAS
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(entetes))}1"

    for i, d in enumerate(dossiers, start=2):
        info = analyser_dossier(d)
        m = info["matches"]

        ws.cell(row=i, column=1, value=d.name)
        poser_lien(ws, f"B{i}", d, "Ouvrir le dossier")
        ws.cell(row=i, column=3, value=info["statut_apparent"])
        ws.cell(row=i, column=4, value=info["siret"])
        ws.cell(row=i, column=5, value=info["forme_detectee"]).fill = BLEU_DETECTE

        statuts_ou_kbis = (m["statuts"] + m["kbis"])
        poser_lien(ws, f"F{i}", statuts_ou_kbis[0] if statuts_ou_kbis else None,
                   statuts_ou_kbis[0].name if statuts_ou_kbis else "—")

        ws.cell(row=i, column=7, value=info["tva_detectee"]).fill = BLEU_DETECTE
        docs_tva = m["franchise"] + m["acompte_tva"] + m["tva"]
        poser_lien(ws, f"H{i}", docs_tva[0] if docs_tva else None,
                   docs_tva[0].name if docs_tva else "—")

        poser_lien(ws, f"I{i}", m["fec"][0] if m["fec"] else None,
                   m["fec"][0].name if m["fec"] else "—")

        gl_bal = m["grand_livre"] + m["balance"]
        poser_lien(ws, f"J{i}", gl_bal[0] if gl_bal else None,
                   gl_bal[0].name if gl_bal else "—")

        for col_idx in range(12, len(entetes) + 1):
            ws.cell(row=i, column=col_idx).fill = JAUNE_A_REMPLIR

        if i % 500 == 0:
            print(f"  {i - 1} dossiers traités...")

    largeurs = [28, 16, 26, 16, 26, 26, 32, 26, 26, 26, 4, 20, 20, 22, 22, 22, 18, 30]
    for idx, larg in enumerate(largeurs, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = larg

    # Listes déroulantes sur les colonnes "À remplir"
    dv_forme = DataValidation(type="list", formula1='"SASU,EURL,Autre,Inconnu"', allow_blank=True)
    dv_regime = DataValidation(type="list", formula1='"IS,Option IR,Inconnu"', allow_blank=True)
    dv_tva_achats = DataValidation(type="list", formula1='"Réel normal,Réel simplifié (historique),Franchise,Inconnu"', allow_blank=True)
    dv_tva_recettes = DataValidation(type="list", formula1='"Assujetti taux réduit 10%,Franchise,Inconnu"', allow_blank=True)
    dv_statut = DataValidation(type="list", formula1='"Actif,Clôturé,Résilié,Inconnu"', allow_blank=True)

    for dv in (dv_forme, dv_regime, dv_tva_achats, dv_tva_recettes, dv_statut):
        ws.add_data_validation(dv)

    n = len(dossiers) + 1
    dv_forme.add(f"L2:L{n}")
    dv_regime.add(f"M2:M{n}")
    dv_tva_achats.add(f"O2:O{n}")
    dv_tva_recettes.add(f"P2:P{n}")
    dv_statut.add(f"Q2:Q{n}")

    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    wb.save(sortie)
    print(f"\n{len(dossiers)} dossiers écrits dans {sortie}")
    print("Colonnes bleues = détecté automatiquement (à vérifier), colonnes jaunes = à remplir.")
    print("Les liens 'file://' ne fonctionnent que si le disque est monté au même chemin.")


if __name__ == "__main__":
    main()
