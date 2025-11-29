import pandas as pd
import unicodedata
import re
import os
from datetime import datetime

def clean_text(text):
    """Nettoyage de texte : accents, espaces multiples, strip. Retourne chaîne vide si NA."""
    if pd.isna(text):
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def generate_job_id_row(row):
    """Génère un job_id robuste en préférant detail_link puis fallback sur title/company/date."""
    link = row.get("detail_link") if "detail_link" in row.index else None
    if pd.notna(link) and str(link).strip():
        return re.sub(r'\W+', '', str(link).lower())
    base = f"{row.get('title','')}-{row.get('company','')}-{row.get('date_publication','')}"
    base = clean_text(base).lower().replace(" ", "-")
    return re.sub(r'\W+', '', base)

def clean_optioncarriere_csv(input_path, output_path):
    # s'assurer du dossier de sortie
    out_dir = os.path.dirname(output_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    # Charger ancien fichier nettoyé si existe et non vide
    df_old = pd.DataFrame()
    try:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            df_old = pd.read_csv(output_path, encoding='utf-8-sig')
    except pd.errors.EmptyDataError:
        df_old = pd.DataFrame()

    # Lire fichier d'entrée
    try:
        df_new = pd.read_csv(input_path, encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"Input file not found: {input_path}")
        return
    except pd.errors.EmptyDataError:
        print(f"Input file is empty: {input_path}")
        return

    # Nettoyage de toutes les colonnes
    for col in df_new.columns:
        df_new[col] = df_new[col].apply(lambda x: clean_text(x) if not pd.isna(x) else "")

    # Normaliser la date relative en format "scraped_at"
    df_new["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Générer job_id robuste
    df_new["job_id"] = df_new.apply(generate_job_id_row, axis=1)

    # Concaténer avec ancien fichier et supprimer doublons
    if not df_old.empty:
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new

    # Choisir colonnes pour déduplication selon disponibilité
    dedup_subset = []
    if "detail_link" in df_final.columns:
        dedup_subset.append("detail_link")
    if "job_id" in df_final.columns:
        dedup_subset.append("job_id")

    if dedup_subset:
        df_final = df_final.drop_duplicates(subset=dedup_subset)
    else:
        df_final = df_final.drop_duplicates()

    # --- NEW: forcer nom et ordre des colonnes dans le CSV nettoyé ---
    CLEANED_COLUMNS = [
        "title", "detail_link", "company", "date_publication",
        "sector", "contract_type", "study_level", "experience", "availability",
        "location", "region", "city",
        "salary_min", "salary_max",
        "description", "skills",
        "scraped_at", "job_id"
    ]

    # créer les colonnes manquantes (valeur vide) et réordonner
    for c in CLEANED_COLUMNS:
        if c not in df_final.columns:
            df_final[c] = ""
    df_final = df_final[CLEANED_COLUMNS]

    # Sauvegarder
    df_final.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Fichier nettoyé sauvegardé : {output_path}")


if __name__ == "__main__":
    clean_optioncarriere_csv(
        "src/Data/rawData/jobs_optioncarriere.csv",
        "src/Data/cleanedData/jobs_optioncarriere_cleaned.csv"
    )