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

Liens : formules =HYPERLIEN()/=HYPERLINK() (plus portables entre Excel et
LibreOffice Calc que l'attribut hyperlink OOXML). Dans LibreOffice Calc, un
simple clic peut ne rien faire selon la config : utiliser Ctrl+clic. La
colonne "Chemin dossier (texte)" donne en plus le chemin brut, copiable-
collable dans un gestionnaire de fichiers si le lien ne s'ouvre toujours pas.

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

try:
    import pdfplumber
except ImportError:
    sys.exit("pdfplumber requis : pip install pdfplumber")

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

FEC_RE = re.compile(r"FEC\d*\.(csv|txt)$", re.IGNORECASE)
SIRET_IN_FEC_RE = re.compile(r"(\d{9,14})FEC")
FORME_KBIS_RE = re.compile(r"Forme juridique\s+([^\n]+)", re.IGNORECASE)
CATEGORIE_AVIS_RE = re.compile(r"Cat[ée]gorie juridique\s+([^\n]+)", re.IGNORECASE)
SIREN_AVIS_RE = re.compile(r"Identifiant SIREN\s+([\d ]{9,15})", re.IGNORECASE)


def lire_premiere_page(path: Path) -> str:
    """Texte natif de la 1re page d'un PDF — vide si le PDF est scanné (pas
    de couche texte) ou illisible. Pas d'OCR ici (voir ADR-005 pour le
    pipeline complet si besoin plus tard)."""
    try:
        with pdfplumber.open(path) as pdf:
            return pdf.pages[0].extract_text() or ""
    except Exception:
        return ""


def deduire_forme_depuis_texte(texte: str) -> str | None:
    """Classe le texte extrait (Forme juridique du Kbis, ou Catégorie
    juridique de l'avis de situation INSEE) dans les catégories du produit
    (doc 06 §7). Retourne None si le texte ne contient aucun motif reconnu."""
    t = texte.lower()
    unique = "associé unique" in t or "associée unique" in t or "à associé unique" in t
    if "responsabilité limitée" in t:
        return "EURL" if unique else "SARL"
    if "actions simplifiée" in t:
        return "SASU" if unique else "SAS (pluripersonnelle, hors scope V1)"
    if "entrepreneur individuel" in t:
        return "Entrepreneur individuel"
    return None
STATUT_APPARENT_MOTS = {
    "résilié / fin de contrat": ["fin contrat", "fin ct", "resilie", "résilié", "annule", "annulé"],
    "repris (ancien dossier)": ["reprise"],
    "clôturé (au moins un exercice)": ["cloture", "clôture"],
}

BLEU_DETECTE = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")
JAUNE_A_REMPLIR = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
GRIS_HEADER = PatternFill(start_color="404040", end_color="404040", fill_type="solid")
BLANC_GRAS = Font(bold=True, color="FFFFFF")


def to_file_uri(p: Path) -> str:
    return "file://" + quote(str(p))


def formule_hyperlien(path, texte: str) -> str:
    """=HYPERLINK() : plus portable entre Excel/LibreOffice que l'attribut
    hyperlink OOXML seul. Les guillemets internes sont doublés (échappement
    des formules xlsx)."""
    if not path:
        return None
    uri = to_file_uri(path).replace('"', '""')
    texte_echappe = texte.replace('"', '""')
    return f'=HYPERLINK("{uri}","{texte_echappe}")'


def classifier_fichier(nom: str) -> set:
    low = nom.lower()
    tags = set()
    if "statut" in low:
        tags.add("statuts")
    if "kbis" in low or "k-bis" in low:
        tags.add("kbis")
    if "avis" in low and "situation" in low:
        tags.add("avis_situation")
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
        "statuts", "kbis", "avis_situation", "tva", "franchise", "acompte_tva",
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

    forme_detectee = None
    source_forme = ""

    if matches["kbis"]:
        texte = lire_premiere_page(matches["kbis"][0])
        m = FORME_KBIS_RE.search(texte)
        forme_lue = deduire_forme_depuis_texte(m.group(1)) if m else None
        if forme_lue:
            forme_detectee = forme_lue
            source_forme = f"Lu dans {matches['kbis'][0].name}"

    if forme_detectee is None and matches["avis_situation"]:
        texte = lire_premiere_page(matches["avis_situation"][0])
        m = CATEGORIE_AVIS_RE.search(texte)
        forme_lue = deduire_forme_depuis_texte(m.group(1)) if m else None
        if forme_lue:
            forme_detectee = forme_lue
            source_forme = f"Lu dans {matches['avis_situation'][0].name}"

    if forme_detectee is None:
        if matches["mention_sasu"] and matches["mention_eurl"]:
            forme_detectee = "Ambigu (SASU + EURL mentionnés dans des noms de fichiers)"
            source_forme = "Nom de fichier (ambigu)"
        elif matches["mention_sasu"]:
            forme_detectee = "SASU (détecté par nom de fichier)"
            source_forme = "Nom de fichier"
        elif matches["mention_eurl"]:
            forme_detectee = "EURL (détecté par nom de fichier)"
            source_forme = "Nom de fichier"
        else:
            forme_detectee = "Non détecté"
            source_forme = "Aucun Kbis/avis de situation/nom de fichier exploitable"

    if matches["franchise"]:
        tva_detectee = "Franchise (mention trouvée)"
    elif matches["acompte_tva"]:
        tva_detectee = "Acomptes trouvés -> historiquement réel simplifié"
    elif matches["tva"]:
        tva_detectee = "Doc TVA présent, à vérifier"
    else:
        tva_detectee = "Aucun doc TVA trouvé"

    siret = ""
    if matches["avis_situation"]:
        texte = lire_premiere_page(matches["avis_situation"][0])
        m = SIREN_AVIS_RE.search(texte)
        if m:
            siret = m.group(1).replace(" ", "")
    if not siret:
        for f in matches["fec"]:
            m = SIRET_IN_FEC_RE.search(f.name)
            if m:
                siret = m.group(1)
                break

    statut_apparent = "Actif (probable, aucun indice de clôture)"
    if statut_hits:
        for libelle in STATUT_APPARENT_MOTS:
            if libelle in statut_hits:
                statut_apparent = libelle
                break

    return {
        "matches": matches,
        "forme_detectee": forme_detectee,
        "source_forme": source_forme,
        "tva_detectee": tva_detectee,
        "siret": siret,
        "statut_apparent": statut_apparent,
    }


# Colonnes : (clé, en-tête, largeur, type)
# type "lien" -> valeur posée via formule =HYPERLINK(); "detecte" -> fond bleu ;
# "remplir" -> fond jaune, valeur vide (+ liste déroulante éventuelle).
COLONNES = [
    ("nom", "Nom dossier", 28, "texte"),
    ("lien_dossier", "Lien dossier (Ctrl+clic)", 22, "lien"),
    ("chemin_dossier", "Chemin dossier (copier-coller si le lien ne marche pas)", 45, "texte"),
    ("statut_apparent", "Statut apparent (détecté)", 26, "detecte"),
    ("siret", "SIRET (détecté)", 16, "texte"),
    ("forme_detectee", "Forme juridique (lue automatiquement dans Kbis/avis de situation si possible)", 30, "detecte"),
    ("source_forme", "Source de la détection", 30, "detecte"),
    ("lien_statuts", "Statuts/Kbis (lien, Ctrl+clic)", 26, "lien"),
    ("lien_avis", "Avis de situation INSEE (lien, Ctrl+clic)", 26, "lien"),
    ("tva_detectee", "Indice régime TVA (détecté)", 32, "detecte"),
    ("lien_tva", "Doc TVA (lien, Ctrl+clic)", 26, "lien"),
    ("lien_fec", "FEC (lien, Ctrl+clic)", 26, "lien"),
    ("lien_gl", "Grand livre / Balance (lien, Ctrl+clic)", 26, "lien"),
    ("sep", "--- À REMPLIR ---", 4, "texte"),
    ("forme_validee", "Forme juridique (validée)", 20,
     "remplir_liste:SASU,EURL,SAS,SARL,Entrepreneur individuel,Autre,Inconnu"),
    ("regime_valide", "Régime imposition (validé)", 20, "remplir_liste:IS,Option IR,Inconnu"),
    ("date_option_ir", "Date début option IR (si applicable)", 22, "remplir"),
    ("tva_achats_validee", "Régime TVA achats (validé)", 22,
     "remplir_liste:Réel normal,Réel simplifié (historique),Franchise,Inconnu"),
    ("tva_recettes_validee", "Régime TVA recettes (validé)", 22,
     "remplir_liste:Assujetti taux réduit 10%,Franchise,Inconnu"),
    ("statut_valide", "Statut dossier (validé)", 22, "remplir_liste:Actif,Clôturé,Résilié,Inconnu"),
    ("verifie_par", "Vérifié par / le", 18, "remplir"),
    ("notes", "Notes", 30, "remplir"),
]


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

    col_index = {cle: i + 1 for i, (cle, *_reste) in enumerate(COLONNES)}
    ws.append([entete for _cle, entete, _larg, _type in COLONNES])
    for col_idx in range(1, len(COLONNES) + 1):
        c = ws.cell(row=1, column=col_idx)
        c.fill = GRIS_HEADER
        c.font = BLANC_GRAS
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(COLONNES))}1"

    for i, d in enumerate(dossiers, start=2):
        info = analyser_dossier(d)
        m = info["matches"]

        statuts_ou_kbis = m["statuts"] + m["kbis"]
        docs_tva = m["franchise"] + m["acompte_tva"] + m["tva"]
        gl_bal = m["grand_livre"] + m["balance"]

        valeurs = {
            "nom": d.name,
            "lien_dossier": formule_hyperlien(d, "Ouvrir le dossier") or "—",
            "chemin_dossier": str(d),
            "statut_apparent": info["statut_apparent"],
            "siret": info["siret"],
            "forme_detectee": info["forme_detectee"],
            "source_forme": info["source_forme"],
            "lien_statuts": formule_hyperlien(statuts_ou_kbis[0], statuts_ou_kbis[0].name) if statuts_ou_kbis else "—",
            "lien_avis": formule_hyperlien(m["avis_situation"][0], m["avis_situation"][0].name) if m["avis_situation"] else "—",
            "tva_detectee": info["tva_detectee"],
            "lien_tva": formule_hyperlien(docs_tva[0], docs_tva[0].name) if docs_tva else "—",
            "lien_fec": formule_hyperlien(m["fec"][0], m["fec"][0].name) if m["fec"] else "—",
            "lien_gl": formule_hyperlien(gl_bal[0], gl_bal[0].name) if gl_bal else "—",
        }

        for cle, valeur in valeurs.items():
            ws.cell(row=i, column=col_index[cle], value=valeur)

        for cle, _entete, _larg, type_ in COLONNES:
            if type_ == "detecte":
                ws.cell(row=i, column=col_index[cle]).fill = BLEU_DETECTE
            elif type_.startswith("remplir"):
                ws.cell(row=i, column=col_index[cle]).fill = JAUNE_A_REMPLIR

        if i % 500 == 0:
            print(f"  {i - 1} dossiers traités...")

    for cle, _entete, largeur, _type in COLONNES:
        ws.column_dimensions[get_column_letter(col_index[cle])].width = largeur

    n = len(dossiers) + 1
    for cle, _entete, _larg, type_ in COLONNES:
        if type_.startswith("remplir_liste:"):
            options = type_.split(":", 1)[1]
            dv = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
            ws.add_data_validation(dv)
            lettre = get_column_letter(col_index[cle])
            dv.add(f"{lettre}2:{lettre}{n}")

    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    wb.save(sortie)
    print(f"\n{len(dossiers)} dossiers écrits dans {sortie}")
    print("Colonnes bleues = détecté automatiquement (à vérifier), colonnes jaunes = à remplir.")
    print("Liens en formule =HYPERLINK() : dans LibreOffice Calc, Ctrl+clic pour ouvrir.")
    print("Colonne 'Chemin dossier' = secours en texte brut si le lien ne s'ouvre pas.")


if __name__ == "__main__":
    main()
