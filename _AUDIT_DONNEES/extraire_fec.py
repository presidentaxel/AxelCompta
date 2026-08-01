"""Extraction des fichiers FEC réels (Dossier Chauffeurs) vers le schéma
transactions.csv attendu par audit_dataset.py (voir README.md).

Le champ `dossier_id` est **pseudonymisé dès l'extraction** (doc 07 §2.2,
doc 10 §4) : jamais le nom du chauffeur en clair dans le CSV de sortie. Une
table de correspondance nom -> id est écrite séparément, gitignorée, à ne
JAMAIS committer ni faire sortir de ce poste.

La colonne `categorie` (vérité terrain de la taxonomie VTC) n'est PAS déduite
ici : le FEC porte le compte PCG (`compte_pcg`), pas la catégorie métier. La
correspondance compte -> catégorie est la "table de mapping comptes
historiques -> taxonomie" à construire à la main (doc 07 §2.2) — étape
suivante, pas celle-ci.

Usage:
    python extraire_fec.py --racine "/chemin/vers/Dossier Chauffeurs" \
        --sortie sortie/transactions.csv --mapping-sortie sortie/mapping_dossiers.csv

Dépendances : pandas (pip install pandas)
"""
import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

FEC_COLONNES = [
    "JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum",
    "CompteLib", "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate",
    "EcritureLib", "Debit", "Credit", "EcritureLet", "DateLet", "ValidDate",
    "Montantdevise", "Idevise",
]


def pseudonymiser(nom_dossier: str, sel: str) -> str:
    h = hashlib.sha256((sel + "|" + nom_dossier).encode("utf-8")).hexdigest()[:12]
    return f"DOS_{h}"


def _lister_fec(racine: Path):
    import re
    motif = re.compile(r"FEC\d*\.(csv|txt)$", re.IGNORECASE)
    return [p for p in racine.rglob("*") if p.is_file() and motif.search(p.name)]


def parser_un_fec(path: Path) -> pd.DataFrame:
    for encodage in ("utf-8", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(path, sep="\t", dtype=str, encoding=encodage, engine="python")
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    else:
        print(f"  ! Impossible de lire {path.name} — ignoré", file=sys.stderr)
        return pd.DataFrame()

    manquantes = [c for c in ("EcritureDate", "CompteNum", "EcritureLib") if c not in df.columns]
    if manquantes:
        print(f"  ! {path.name} : colonnes FEC manquantes {manquantes} — ignoré", file=sys.stderr)
        return pd.DataFrame()

    debit = pd.to_numeric(df.get("Debit", "0").astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0)
    credit = pd.to_numeric(df.get("Credit", "0").astype(str).str.replace(",", ".", regex=False), errors="coerce").fillna(0)

    out = pd.DataFrame({
        "date": pd.to_datetime(df["EcritureDate"], format="%Y%m%d", errors="coerce"),
        "libelle_brut": df["EcritureLib"],
        "montant": debit - credit,
        "compte_pcg": df["CompteNum"],
        "journal": df.get("JournalCode"),
        "piece_ref": df.get("PieceRef"),
    })
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--racine", required=True, help="Dossier racine 'Dossier Chauffeurs'")
    parser.add_argument("--sortie", default="sortie/transactions.csv")
    parser.add_argument("--mapping-sortie", default="sortie/mapping_dossiers_NE_PAS_COMMIT.csv")
    parser.add_argument("--sel", default="axelcompta-audit-2026",
                         help="Sel de pseudonymisation — garder constant entre exécutions pour des id stables")
    args = parser.parse_args()

    racine = Path(args.racine)
    if not racine.is_dir():
        sys.exit(f"Dossier introuvable : {racine}")

    fichiers = _lister_fec(racine)
    print(f"{len(fichiers)} fichier(s) FEC trouvé(s) sous {racine}")

    frames = []
    mapping = []
    for f in fichiers:
        # Le premier segment sous la racine est le dossier du chauffeur ; les
        # FEC vivent souvent plusieurs niveaux plus bas (ex. .../NOM/Clôture 2019/FEC...csv).
        # Grouper sur f.parent.name mélangerait des chauffeurs différents qui
        # partagent un sous-dossier au nom générique (Clôture 2018, COMPTABILITE...).
        nom_dossier = f.relative_to(racine).parts[0]
        dossier_id = pseudonymiser(nom_dossier, args.sel)
        df = parser_un_fec(f)
        if df.empty:
            continue
        df["dossier_id"] = dossier_id
        df["source_format"] = "FEC"
        df["fichier_source"] = f.name
        frames.append(df)
        mapping.append({"dossier_id": dossier_id, "nom_dossier": nom_dossier, "fichier": str(f)})
        print(f"  ok  {dossier_id}  <-  {nom_dossier}  ({len(df)} lignes)")

    if not frames:
        sys.exit("Aucun FEC exploitable.")

    transactions = pd.concat(frames, ignore_index=True)
    transactions["categorie"] = pd.NA  # à remplir via la table de mapping compte -> taxonomie (doc 07 §2.2)

    colonnes_finales = ["dossier_id", "date", "libelle_brut", "montant", "compte_pcg",
                         "categorie", "source_format", "journal", "piece_ref", "fichier_source"]
    transactions = transactions[colonnes_finales]

    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    transactions.to_csv(sortie, index=False)
    print(f"\n{len(transactions)} lignes écrites dans {sortie}")

    mapping_sortie = Path(args.mapping_sortie)
    mapping_sortie.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(mapping).to_csv(mapping_sortie, index=False)
    print(f"Correspondance id -> nom écrite dans {mapping_sortie} — NE JAMAIS committer ce fichier.")

    print("\nProchaine étape : compléter la colonne 'categorie' via la table de "
          "mapping compte PCG -> taxonomie VTC (doc 07 §2.2), puis lancer "
          "audit_dataset.py sur ce fichier.")


if __name__ == "__main__":
    main()
