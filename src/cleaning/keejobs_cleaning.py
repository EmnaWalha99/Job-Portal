import pandas as pd
import re
import unicodedata
from datetime import datetime
import os

def clean_text(text):
    """Normalise le texte : accents, espaces inutiles, minuscules."""
    if pd.isna(text):
        return None
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")  # enlever accents
    text = re.sub(r"\s+", " ", text).strip()  # enlever espaces multiples
    return text

# Date cleaning
def clean_date(d):
    """Normalise les dates en format YYYY-MM-DD"""
    if pd.isna(d):
        return None
    d = str(d).replace("/", ".").strip()
    for fmt in ("%d.%m.%Y", "%d %B %Y"):  # exemple : '29 novembre 2025'
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except:
            continue
    return None

# Parse salaire
def parse_salary(s):
    """Retourne un tuple (min, max) du salaire"""
    if pd.isna(s) or s == "":
        return None, None
    s = s.replace("TND", "").replace(" ", "").replace("<", "").replace(">", "")
    if "-" in s:
        parts = s.split("-")
        try:
            return int(parts[0]), int(parts[1])
        except:
            return None, None
    else:
        try:
            return int(s), None
        except:
            return None, None

# COLONNES MULTI-VAL
def split_multi(x):
    """Split les colonnes multi-valeurs (ex: skills) en liste propre"""
    if pd.isna(x):
        return []
    # supprime les crochets si présents
    x = re.sub(r"[\[\]]", "", str(x))
    return [clean_text(i) for i in re.split(r"[,-/;]", x) if i.strip()]

#JOB ID
def generate_job_id(row):
    """Génère un identifiant unique pour chaque job"""
    base = f"{row.get('title', '')}-{row.get('sector', '')}-{row.get('date_publication', '')}"
    return clean_text(base.lower().replace(" ", "-"))

def clean_keejob_csv(input_path, output_path):
    #Charger ancien fichier nettoyé si existe et non vide
    df_old = pd.DataFrame()
    try:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            df_old = pd.read_csv(output_path)
    except pd.errors.EmptyDataError:
        df_old = pd.DataFrame()

    #S'assurer que le dossier de sortie existe
    out_dir = os.path.dirname(output_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    #Lire le fichier d'entrée
    try:
        df_new = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"Input file not found: {input_path}")
        return
    except pd.errors.EmptyDataError:
        print(f"Input file is empty: {input_path}")
        return

    #Nettoyage texte simple
    for col in df_new.columns:
        df_new[col] = df_new[col].apply(lambda x: clean_text(x) if isinstance(x, str) else x)

    #Nettoyage date
    if "date_publication" in df_new.columns:
        df_new["date_publication"] = df_new["date_publication"].apply(clean_date)

    #Parsing salaire
    if "salary" in df_new.columns:
        df_new["salary_min"], df_new["salary_max"] = zip(*df_new["salary"].apply(parse_salary))
        df_new.drop(columns=["salary"], inplace=True)

    #Colonnes multi-valeurs
    multi_cols = ["sector", "contract_type", "study_level", "experience", "availability"]
    for col in multi_cols:
        if col in df_new.columns:
            df_new[col] = df_new[col].apply(split_multi)

    #Ajouter scraped_at
    df_new["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    #Ajouter job_id
    df_new["job_id"] = df_new.apply(generate_job_id, axis=1)

    # Concaténer avec ancien fichier et supprimer doublons
    if not df_old.empty:
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new
    df_final = df_final.drop_duplicates(subset=["job_id"])

    #Sauvegarde
    df_final.to_csv(output_path, index=False)
    print(f"Fichier nettoyé sauvegardé : {output_path}")


if __name__ == "__main__":
    clean_keejob_csv(
        "src/Data/rawData/job_keejobs.csv",
        "src/Data/cleanedData/job_keejobs_cleaned.csv"
    )
