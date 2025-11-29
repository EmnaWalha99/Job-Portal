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

def extract_location_parts(location_str):
    """
    Extrait ville et région depuis une chaîne comme 'Ksar Hellal, Monastir' ou 'Tunis'
    Retourne (city, region)
    """
    if not location_str or pd.isna(location_str):
        return "", ""
    
    location_str = str(location_str).strip()
    if "," in location_str:
        parts = [p.strip() for p in location_str.split(",")]
        return parts[0], parts[1] if len(parts) > 1 else ""
    else:
        return location_str, ""

def extract_sector_from_description(description):
    """Extrait le secteur/domaine depuis la description."""
    if not description:
        return ""
    
    # Chercher "Domaine : XXX" jusqu'au prochain champ (Niveau, Diplome, etc.)
    match = re.search(r'Domaine\s*:\s*([^:]+?)(?=\s*(?:Niveau|Diplome|Profession|Lieu de travail))', description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Chercher "Activite de l'entreprise : XXX"
    match = re.search(r"Activite de l'entreprise\s*:\s*([^:]+?)(?=\s*Domaine)", description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return ""

def extract_study_level_from_description(description):
    """Extrait le niveau d'études depuis la description."""
    if not description:
        return ""
    
    # Chercher "Niveau : XXX" jusqu'au prochain champ
    match = re.search(r'Niveau\s*:\s*([^:]+?)(?=\s*(?:Specialite|Poste|Profession|Lieu de travail|Experience))', description, re.IGNORECASE)
    if match:
        level = match.group(1).strip()
        # Nettoyer si trop long
        if len(level) > 100:
            level = level[:100]
        return level
    
    # Chercher "Diplome d'etude : XXX" ou "Diplome de la formation : XXX"
    match = re.search(r'Diplome[^:]*:\s*([^:]+?)(?=\s*(?:Specialite|Profession|Lieu de travail))', description, re.IGNORECASE)
    if match:
        level = match.group(1).strip()
        if len(level) > 100:
            level = level[:100]
        return level
    
    return ""

def extract_experience_from_description(description):
    """Extrait l'expérience requise depuis la description."""
    if not description:
        return ""
    
    # Chercher "Experience souhaitee : X an(s)"
    match = re.search(r'Experience\s+souhaitee\s*:\s*(\d+)\s*an', description, re.IGNORECASE)
    if match:
        return f"{match.group(1)} ans"
    
    # Chercher des patterns d'expérience généraux
    patterns = [
        r'(\d+)\s*(?:ans?|annees?)\s*(?:d.)?experience',
        r'experience\s*(?:de\s*)?(\d+)\s*(?:ans?|annees?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return f"{match.group(1)} ans"
    
    # Chercher des mentions qualitatives
    if re.search(r'experience\s+significative', description, re.IGNORECASE):
        return "Experience significative"
    if re.search(r'experience\s+similaire', description, re.IGNORECASE):
        return "Experience similaire"
    if re.search(r'experience\s+requise', description, re.IGNORECASE):
        return "Experience requise"
    
    return ""

def extract_skills_from_description(description):
    """Extrait les compétences depuis la description."""
    if not description:
        return ""
    
    skills = []
    
    # Chercher "Competences : XXX" ou "Qualifications : XXX"
    match = re.search(r'(?:Competences?|Qualifications?|Skills?)\s*incluent?\s*:\s*([^:]+?)(?=\s*(?:Informations|Bureau de|Responsable))', description, re.IGNORECASE)
    if match:
        skills_text = match.group(1).strip()
        return skills_text[:200]
    
    # Chercher des compétences communes mentionnées
    common_skills = {
        'communication': r'communication',
        'gestion': r'gestion',
        'management': r'management',
        'leadership': r'leadership',
        'travail en equipe': r'travail\s+en\s+equipe',
        'autonomie': r'autonomie',
        'organisation': r'organisation',
        'anglais': r'anglais',
        'francais': r'francais|maitrise\s+du\s+francais',
        'informatique': r'informatique|outils?\s+digitaux?|pack\s+office',
    }
    
    description_lower = description.lower()
    for skill_name, pattern in common_skills.items():
        if re.search(pattern, description_lower):
            skills.append(skill_name)
    
    if skills:
        return ', '.join(skills[:5])
    
    return ""

def extract_salary_from_description(description):
    """
    Extrait le salaire depuis la description.
    Retourne (salary_min, salary_max)
    """
    if not description:
        return "", ""
    
    # Pattern: "Salaire : 2000dt" ou "Salaire : 2000 dt"
    match = re.search(r'Salaire\s*:\s*(\d+)\s*dt', description, re.IGNORECASE)
    if match:
        salary = match.group(1)
        return salary, salary
    
    # Pattern: "1500-2000 dt" ou "1500 a 2000 dt"
    match = re.search(r'(\d+)\s*[-a]\s*(\d+)\s*dt', description, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2)
    
    return "", ""

def generate_job_id_row(row):
    """Génère un job_id robuste en préférant detail_link puis fallback sur title/company/date."""
    link = row.get("detail_link") if "detail_link" in row.index else None
    if pd.notna(link) and str(link).strip():
        return re.sub(r'\W+', '', str(link).lower())
    base = f"{row.get('title','')}-{row.get('company','')}-{row.get('scraped_at','')}"
    base = clean_text(base).lower().replace(" ", "-")
    return re.sub(r'\W+', '', base)

def map_raw_to_cleaned(df_raw):
    """
    Mappe les colonnes brutes du scraper vers les colonnes nettoyées attendues.
    Extrait les informations cachées dans la description.
    """
    df_mapped = pd.DataFrame()
    
    # Mappages directs
    df_mapped["title"] = df_raw["title"].apply(clean_text)
    df_mapped["detail_link"] = df_raw["detail_link"].apply(clean_text)
    df_mapped["company"] = df_raw["company"].apply(clean_text)
    df_mapped["date_publication"] = df_raw["posted_relative"].apply(clean_text)
    df_mapped["contract_type"] = df_raw["contract"].apply(clean_text)
    df_mapped["availability"] = df_raw["work_type"].apply(clean_text)
    df_mapped["location"] = df_raw["location"].apply(clean_text)
    
    # Extraire city et region depuis location
    location_parts = df_raw["location"].apply(extract_location_parts)
    df_mapped["city"] = location_parts.apply(lambda x: x[0])
    df_mapped["region"] = location_parts.apply(lambda x: x[1])
    
    # raw_content → description
    df_mapped["description"] = df_raw["raw_content"].apply(clean_text)
    
    # Conserver scraped_at original
    df_mapped["scraped_at"] = df_raw["scraped_at"]
    
    # EXTRAIRE les informations depuis la description
    print("Extraction des informations depuis les descriptions...")
    df_mapped["sector"] = df_mapped["description"].apply(extract_sector_from_description)
    df_mapped["study_level"] = df_mapped["description"].apply(extract_study_level_from_description)
    df_mapped["experience"] = df_mapped["description"].apply(extract_experience_from_description)
    df_mapped["skills"] = df_mapped["description"].apply(extract_skills_from_description)
    
    # Extraire les salaires
    salary_data = df_mapped["description"].apply(extract_salary_from_description)
    df_mapped["salary_min"] = salary_data.apply(lambda x: x[0])
    df_mapped["salary_max"] = salary_data.apply(lambda x: x[1])
    
    # Générer job_id unique
    df_mapped["job_id"] = df_mapped.apply(generate_job_id_row, axis=1)
    
    # Statistiques d'extraction
    print(f"  - Secteurs extraits: {(df_mapped['sector'] != '').sum()}/{len(df_mapped)}")
    print(f"  - Niveaux d'études extraits: {(df_mapped['study_level'] != '').sum()}/{len(df_mapped)}")
    print(f"  - Expériences extraites: {(df_mapped['experience'] != '').sum()}/{len(df_mapped)}")
    print(f"  - Compétences extraites: {(df_mapped['skills'] != '').sum()}/{len(df_mapped)}")
    print(f"  - Salaires extraits: {(df_mapped['salary_min'] != '').sum()}/{len(df_mapped)}")
    
    return df_mapped

def clean_optioncarriere_csv(input_path, output_path):
    """
    Nettoie le CSV brut du scraper et le transforme en format standardisé.
    Évite les doublons en se basant sur job_id.
    """
    print("\n" + "="*80)
    print("NETTOYAGE DES DONNÉES OPTIONCARRIERE")
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

    # Mapper les colonnes brutes vers les colonnes nettoyées
    print(f"\n Transformation des données...")
    df_new = map_raw_to_cleaned(df_raw)

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

    # Ordre final des colonnes
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
    
    print(f"\n Fichier nettoyé sauvegardé : {output_path}")
    print(f" Total final : {len(df_final)} offres d'emploi")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    clean_optioncarriere_csv(
        "src/Data/rawData/jobs_optioncarriere.csv",
        "src/Data/cleanedData/jobs_optioncarriere_cleaned.csv"
    )