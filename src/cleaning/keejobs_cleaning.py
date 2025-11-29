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

def clean_list_string(text):
    """
    Nettoie les chaînes de type "['item1', 'item2']" et les convertit en chaîne simple.
    Exemple: "['banque', 'finance']" -> "banque, finance"
    """
    if pd.isna(text) or text == "":
        return ""
    
    # Enlever les crochets et quotes
    text = str(text).strip()
    text = re.sub(r"[\[\]'\"]", "", text)
    
    # Si vide après nettoyage
    if not text:
        return ""
    
    # Séparer par virgule et nettoyer chaque élément
    items = [item.strip() for item in text.split(",") if item.strip()]
    
    # Retourner une chaîne propre
    return ", ".join(items)

def extract_location_parts(location_str):
    """
    Extrait ville et région depuis une chaîne comme 'Tunis, Tunisie' ou 'La Marsa, Tunis, Tunisie'
    Retourne (city, region)
    """
    if not location_str or pd.isna(location_str):
        return "", ""
    
    location_str = str(location_str).strip()
    
    # Enlever "Tunisie" à la fin
    location_str = re.sub(r',?\s*Tunisie\s*$', '', location_str, flags=re.IGNORECASE)
    
    if "," in location_str:
        parts = [p.strip() for p in location_str.split(",")]
        # Si 2 parties: ville, région
        if len(parts) >= 2:
            return parts[0], parts[-1]
        else:
            return parts[0], ""
    else:
        return location_str, ""

def extract_salary_from_description(description):
    """
    Extrait le salaire depuis la description.
    Retourne (salary_min, salary_max)
    """
    if not description:
        return "", ""
    
    # Pattern: "Salaire : 2000 TND" ou "2000dt"
    match = re.search(r'(?:Salaire|salaire)\s*:\s*(\d+)\s*(?:TND|dt|DT)', description, re.IGNORECASE)
    if match:
        salary = match.group(1)
        return salary, salary
    
    # Pattern: "1500-2000 TND" ou "1500 a 2000 dt"
    match = re.search(r'(\d+)\s*[-a]\s*(\d+)\s*(?:TND|dt|DT)', description, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    
    return "", ""

def extract_skills_from_description(description):
    """Extrait les compétences depuis la description."""
    if not description:
        return ""
    
    skills = []
    
    # Chercher des compétences communes
    common_skills = {
        'communication': r'communication',
        'gestion': r'gestion',
        'management': r'management',
        'leadership': r'leadership',
        'travail en equipe': r'(?:travail\s+en\s+equipe|esprit\s+d.?equipe)',
        'autonomie': r'autonomie',
        'organisation': r'organis[ée]',
        'anglais': r'anglais',
        'francais': r'francais',
        'informatique': r'informatique',
        'excel': r'excel',
        'word': r'word',
        'powerpoint': r'powerpoint',
    }
    
    description_lower = description.lower()
    for skill_name, pattern in common_skills.items():
        if re.search(pattern, description_lower):
            skills.append(skill_name)
    
    if skills:
        return ', '.join(skills)
    
    return ""

def clean_date_relative(date_str):
    """
    Convertit les dates relatives en format lisible.
    Garde le format relatif pour cohérence avec Optioncarriere.
    """
    if pd.isna(date_str) or date_str == "":
        return ""
    
    # Garder tel quel si déjà propre
    return clean_text(str(date_str))

def generate_job_id_row(row):
    """Génère un job_id robuste en préférant detail_link puis fallback sur title/company/date."""
    link = row.get("detail_link") if "detail_link" in row.index else None
    if pd.notna(link) and str(link).strip():
        return re.sub(r'\W+', '', str(link).lower())
    base = f"{row.get('title','')}-{row.get('sector','')}-{row.get('scraped_at','')}"
    base = clean_text(base).lower().replace(" ", "-")
    return re.sub(r'\W+', '', base)

def map_keejob_to_standard(df_raw):
    """
    Mappe les colonnes Keejob vers le format standardisé (même que Optioncarriere).
    """
    df_mapped = pd.DataFrame()
    
    # Colonnes de base
    df_mapped["title"] = df_raw["title"].apply(clean_text) if "title" in df_raw.columns else ""
    df_mapped["detail_link"] = df_raw["detail_link"].apply(clean_text) if "detail_link" in df_raw.columns else ""
    
    # Company n'existe pas dans Keejob, laisser vide
    df_mapped["company"] = ""
    
    # Date publication
    df_mapped["date_publication"] = df_raw["date_publication"].apply(clean_date_relative) if "date_publication" in df_raw.columns else ""
    
    # Sector - nettoyer les listes
    if "sector" in df_raw.columns:
        df_mapped["sector"] = df_raw["sector"].apply(clean_list_string)
    else:
        df_mapped["sector"] = ""
    
    # Contract type - nettoyer les listes
    if "contract_type" in df_raw.columns:
        df_mapped["contract_type"] = df_raw["contract_type"].apply(clean_list_string)
    else:
        df_mapped["contract_type"] = ""
    
    # Study level - nettoyer les listes
    if "study_level" in df_raw.columns:
        df_mapped["study_level"] = df_raw["study_level"].apply(clean_list_string)
    else:
        df_mapped["study_level"] = ""
    
    # Experience - nettoyer les listes
    if "experience" in df_raw.columns:
        df_mapped["experience"] = df_raw["experience"].apply(clean_list_string)
    else:
        df_mapped["experience"] = ""
    
    # Availability - nettoyer les listes
    if "availability" in df_raw.columns:
        df_mapped["availability"] = df_raw["availability"].apply(clean_list_string)
    else:
        df_mapped["availability"] = ""
    
    # Location
    if "location" in df_raw.columns:
        df_mapped["location"] = df_raw["location"].apply(clean_text)
        location_parts = df_raw["location"].apply(extract_location_parts)
        df_mapped["city"] = location_parts.apply(lambda x: x[0])
        df_mapped["region"] = location_parts.apply(lambda x: x[1])
    else:
        df_mapped["location"] = ""
        df_mapped["city"] = ""
        df_mapped["region"] = ""
    
    # Description
    if "description" in df_raw.columns:
        df_mapped["description"] = df_raw["description"].apply(clean_text)
    else:
        df_mapped["description"] = ""
    
    # Salaire - soit depuis colonnes existantes, soit extraire de description
    if "salary_min" in df_raw.columns and "salary_max" in df_raw.columns:
        df_mapped["salary_min"] = df_raw["salary_min"].apply(lambda x: str(x) if pd.notna(x) else "")
        df_mapped["salary_max"] = df_raw["salary_max"].apply(lambda x: str(x) if pd.notna(x) else "")
    else:
        salary_data = df_mapped["description"].apply(extract_salary_from_description)
        df_mapped["salary_min"] = salary_data.apply(lambda x: x[0])
        df_mapped["salary_max"] = salary_data.apply(lambda x: x[1])
    
    # Skills - extraire depuis description
    df_mapped["skills"] = df_mapped["description"].apply(extract_skills_from_description)
    
    # Scraped_at
    if "scraped_at" in df_raw.columns:
        df_mapped["scraped_at"] = df_raw["scraped_at"]
    else:
        df_mapped["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Job ID
    df_mapped["job_id"] = df_mapped.apply(generate_job_id_row, axis=1)
    
    # Statistiques
    print(f"  - Secteurs extraits: {(df_mapped['sector'] != '').sum()}/{len(df_mapped)}")
    print(f"  - Niveaux d'études extraits: {(df_mapped['study_level'] != '').sum()}/{len(df_mapped)}")
    print(f"  - Expériences extraites: {(df_mapped['experience'] != '').sum()}/{len(df_mapped)}")
    print(f"  - Compétences extraites: {(df_mapped['skills'] != '').sum()}/{len(df_mapped)}")
    print(f"  - Salaires extraits: {(df_mapped['salary_min'] != '').sum()}/{len(df_mapped)}")
    
    return df_mapped

def clean_keejob_csv(input_path, output_path):
    """
    Nettoie le CSV Keejob et le transforme en format standardisé.
    """
    print("\n" + "="*80)
    print("NETTOYAGE DES DONNÉES KEEJOB")
    print("="*80 + "\n")
    
    # Créer le dossier de sortie si nécessaire
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Charger ancien fichier nettoyé si existe
    df_old = pd.DataFrame()
    try:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            df_old = pd.read_csv(output_path, encoding='utf-8-sig')
            print(f" Fichier existant chargé : {len(df_old)} lignes")
    except pd.errors.EmptyDataError:
        df_old = pd.DataFrame()

    # Lire fichier brut d'entrée
    try:
        df_raw = pd.read_csv(input_path, encoding='utf-8-sig')
        print(f" Fichier brut chargé : {len(df_raw)} lignes")
    except FileNotFoundError:
        print(f" Fichier introuvable : {input_path}")
        return
    except pd.errors.EmptyDataError:
        print(f" Fichier vide : {input_path}")
        return

    # Mapper vers format standard
    print(f"\n Transformation des données...")
    df_new = map_keejob_to_standard(df_raw)

    # Concaténer avec l'ancien fichier
    if not df_old.empty:
        df_final = pd.concat([df_old, df_new], ignore_index=True)
        print(f"\n Total après fusion : {len(df_final)} lignes")
    else:
        df_final = df_new
        print(f"\n Nouvelles données : {len(df_final)} lignes")

    # Supprimer les doublons basés sur job_id
    before_dedup = len(df_final)
    df_final = df_final.drop_duplicates(subset=["job_id"], keep="first")
    after_dedup = len(df_final)
    
    if before_dedup > after_dedup:
        print(f"  Doublons supprimés : {before_dedup - after_dedup}")

    # Ordre final des colonnes (MÊME FORMAT que Optioncarriere)
    CLEANED_COLUMNS = [
        "title", "detail_link", "company", "date_publication",
        "sector", "contract_type", "study_level", "experience", "availability",
        "location", "region", "city",
        "salary_min", "salary_max",
        "description", "skills",
        "scraped_at", "job_id"
    ]

    # S'assurer que toutes les colonnes existent
    for col in CLEANED_COLUMNS:
        if col not in df_final.columns:
            df_final[col] = ""

    # Réordonner les colonnes
    df_final = df_final[CLEANED_COLUMNS]

    # Sauvegarder
    df_final.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\nFichier nettoyé sauvegardé : {output_path}")
    print(f"Total final : {len(df_final)} offres d'emploi")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    clean_keejob_csv(
        "src/Data/rawData/job_keejobs.csv",
        "src/Data/cleanedData/job_keejobs_cleaned.csv"
    )