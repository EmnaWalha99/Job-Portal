import pandas as pd
import unicodedata
import re
import os
from datetime import datetime, timedelta

# UTILITY FUNCTIONS

def clean_text(text):
    """Nettoyage de texte : accents, espaces multiples, strip."""
    if pd.isna(text):
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_date_from_description(description):
    """Extrait la date de publication depuis la description ou raw_content"""
    if not description:
        return ""
    
    # Chercher "Date de publication : XX/XX/XXXX" ou variantes
    match = re.search(r'Date de publication\s*[:\-]?\s*(\d{1,2}[./-]\d{1,2}[./-]\d{4})', description, re.IGNORECASE)
    if match:
        date_str = match.group(1)
        # Utiliser parse_relative_date pour convertir
        return parse_relative_date(date_str)
    
    # Si non trouvé, renvoyer vide
    return ""


def parse_relative_date(relative_str):
    """Convertit dates relatives en YYYY-MM-DD."""
    if pd.isna(relative_str) or relative_str == "":
        return ""
    
    rel = str(relative_str).lower().strip()
    
    try:
        # Aujourd'hui
        if any(word in rel for word in ['aujourd', 'today', 'now']):
            return datetime.now().strftime("%Y-%m-%d")
        
        # Hier
        if any(word in rel for word in ['hier', 'yesterday']):
            return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Il y a X jours/heures
        match = re.search(r'(\d+)\s*(jour|day|heure|hour|h)', rel)
        if match:
            num = int(match.group(1))
            unit = match.group(2)
            if 'jour' in unit or 'day' in unit:
                return (datetime.now() - timedelta(days=num)).strftime("%Y-%m-%d")
            elif 'heure' in unit or 'hour' in unit or unit == 'h':
                return datetime.now().strftime("%Y-%m-%d")
        
        # Try parsing DD.MM.YYYY or DD/MM/YYYY
        for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(rel.replace("/", "."), fmt).strftime("%Y-%m-%d")
            except:
                continue
    except:
        pass
    
    return relative_str

def parse_salary(salary_str):
    """Parse le salaire et retourne (salary_min, salary_max)."""
    if pd.isna(salary_str) or salary_str == "":
        return "", ""
    
    salary_str = str(salary_str)
    
    salary_str = salary_str.replace("TND", "").replace("DT", "").replace("dt", "")
    salary_str = salary_str.replace(" ", "").replace(".", "")
    
    # Range
    if "-" in salary_str:
        parts = salary_str.split("-")
        try:
            return str(int(parts[0])), str(int(parts[1]))
        except:
            return "", ""
    
    # Single value
    try:
        val = int(salary_str)
        return str(val), str(val)
    except:
        return "", ""

def extract_location_parts(location_str):
    """Extrait (city, region) depuis location."""
    if not location_str or pd.isna(location_str):
        return "", ""
    
    location_str = str(location_str).strip()
    location_str = re.sub(r',?\s*Tunisie\s*$', '', location_str, flags=re.IGNORECASE)
    
    if "," in location_str:
        parts = [p.strip() for p in location_str.split(",")]
        parts = list(dict.fromkeys(parts))
        if len(parts) >= 2:
            return parts[0], parts[-1]
        else:
            return parts[0], ""
    else:
        return location_str, ""

def extract_skills_from_description(description):
    """Extrait les compétences depuis la description."""
    if not description:
        return ""
    
    common_skills = {
        'communication': r'\bcommunication\b',
        'gestion': r'\bgestion\b',
        'management': r'\bmanagement\b',
        'leadership': r'\bleadership\b',
        'travail en equipe': r'(?:travail\s+en\s+equipe|esprit\s+d.?equipe)',
        'autonomie': r'\bautonomie\b',
        'organisation': r'\borganis[ée]\w*\b',
        'anglais': r'\banglais\b',
        'francais': r'\bfrancais\b',
        'informatique': r'\binformatique\b',
        'excel': r'\bexcel\b',
        'word': r'\bword\b',
        'powerpoint': r'\bpowerpoint\b',
    }
    
    skills = []
    description_lower = description.lower()
    for skill_name, pattern in common_skills.items():
        if re.search(pattern, description_lower):
            skills.append(skill_name)
    
    return ', '.join(skills[:8]) if skills else ""

def extract_sector_from_description(description):
    """Extrait le secteur depuis la description."""
    if not description:
        return ""
    
    # Chercher "Domaine : XXX" jusqu'au prochain champ
    match = re.search(
        r'Domaine\s*:\s*([^:]+?)(?=\s*(?:Niveau|Diplome|Profession|Lieu de travail))', 
        description, 
        re.IGNORECASE
    )
    if match:
        return clean_text(match.group(1))
    
    # Chercher "Activite de l'entreprise : XXX"
    match = re.search(
        r"Activite de l'entreprise\s*:\s*([^:]+?)(?=\s*Domaine)", 
        description, 
        re.IGNORECASE
    )
    if match:
        return clean_text(match.group(1))
    
    return ""

def extract_study_level_from_description(description):
    """Extrait le niveau d'études depuis la description."""
    if not description:
        return ""
    
    # Chercher "Niveau : XXX" jusqu'au prochain champ
    match = re.search(
        r'Niveau\s*:\s*([^:]+?)(?=\s*(?:Specialite|Poste|Profession|Lieu de travail|Experience))', 
        description, 
        re.IGNORECASE
    )
    if match:
        level = clean_text(match.group(1))
        if len(level) > 100:
            level = level[:100]
        return level
    
    # Chercher "Diplome d'etude : XXX" ou "Diplome de la formation : XXX"
    match = re.search(
        r'Diplome[^:]*:\s*([^:]+?)(?=\s*(?:Specialite|Profession|Lieu de travail))', 
        description, 
        re.IGNORECASE
    )
    if match:
        level = clean_text(match.group(1))
        if len(level) > 100:
            level = level[:100]
        return level
    
    return ""

def extract_experience_from_description(description):
    """Extrait l'expérience depuis la description."""
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
    
    return ""

def extract_salary_from_description(description):
    """Extrait le salaire depuis la description."""
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
    """Génère un job_id unique."""
    link = row.get("detail_link") if "detail_link" in row.index else None
    if pd.notna(link) and str(link).strip():
        return re.sub(r'\W+', '', str(link).lower())
    base = f"{row.get('title','')}-{row.get('company','')}-{row.get('scraped_at','')}"
    base = clean_text(base).lower().replace(" ", "-")
    return re.sub(r'\W+', '', base)

# OPTIONCARRIERE SPECIFIC MAPPER

def map_optioncarriere_to_standard(df_raw):
    """Mappe OptionCarriere vers format standardisé."""
    df = pd.DataFrame()
    
    df["title"] = df_raw["title"].apply(clean_text) if "title" in df_raw.columns else ""
    df["detail_link"] = df_raw["detail_link"].apply(clean_text) if "detail_link" in df_raw.columns else ""
    df["company"] = df_raw["company"].apply(clean_text) if "company" in df_raw.columns else ""
    df["date_publication"] = df_raw.apply(
        lambda row: extract_date_from_description(row["raw_content"]) 
        if pd.notna(row.get("raw_content")) else parse_relative_date(row.get("posted_relative","")),
        axis=1
)
    df["contract_type"] = df_raw["contract"].apply(clean_text) if "contract" in df_raw.columns else ""
    df["availability"] = df_raw["work_type"].apply(clean_text) if "work_type" in df_raw.columns else ""
    
    if "location" in df_raw.columns:
        df["location"] = df_raw["location"].apply(clean_text)
        location_parts = df_raw["location"].apply(extract_location_parts)
        df["city"] = location_parts.apply(lambda x: x[0])
        df["region"] = location_parts.apply(lambda x: x[1])
    else:
        df["location"] = ""
        df["city"] = ""
        df["region"] = ""
    
    df["description"] = df_raw["raw_content"].apply(clean_text) if "raw_content" in df_raw.columns else ""
    
    # Extract from description
    df["sector"] = df["description"].apply(extract_sector_from_description)
    df["study_level"] = df["description"].apply(extract_study_level_from_description)
    df["experience"] = df["description"].apply(extract_experience_from_description)
    df["skills"] = df["description"].apply(extract_skills_from_description)
    
    # Extract salary
    salary_data = df["description"].apply(extract_salary_from_description)
    df["salary_min"] = salary_data.apply(lambda x: x[0])
    df["salary_max"] = salary_data.apply(lambda x: x[1])
    
    df["source"] = df_raw["source"] if "source" in df_raw.columns else "optioncarriere"
    df["scraped_at"] = df_raw["scraped_at"] if "scraped_at" in df_raw.columns else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df["job_id"] = df.apply(generate_job_id_row, axis=1)
    
    return df

# ============================================================================
# STANDARD COLUMNS
# ============================================================================

STANDARD_COLUMNS = [
    "title", "detail_link", "company", "date_publication",
    "sector", "contract_type", "study_level", "experience", "availability",
    "location", "region", "city",
    "salary_min", "salary_max",
    "description", "skills",
    "source", "scraped_at", "job_id"
]

# MAIN CLEANING FUNCTION


def clean_optioncarriere_csv(input_path, output_path):
    """
    Nettoie le CSV OptionCarriere et le transforme en format standardisé.
    """
    print("\n" + "="*80)
    print("NETTOYAGE DES DONNÉES OPTIONCARRIERE")
    print("="*80 + "\n")
    
    # Create output directory
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Load existing cleaned data
    df_old = pd.DataFrame()
    try:
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            df_old = pd.read_csv(output_path, encoding='utf-8-sig')
            print(f"Fichier existant chargé : {len(df_old)} lignes")
    except:
        df_old = pd.DataFrame()

    # Load raw data
    try:
        df_raw = pd.read_csv(input_path, encoding='utf-8-sig')
        print(f"Fichier brut chargé : {len(df_raw)} lignes")
    except FileNotFoundError:
        print(f"Fichier introuvable : {input_path}")
        return
    except pd.errors.EmptyDataError:
        print(f"Fichier vide : {input_path}")
        return

    # Map to standard format
    print(f"\nTransformation des données...")
    df_new = map_optioncarriere_to_standard(df_raw)

    # Merge with existing data
    if not df_old.empty:
        df_final = pd.concat([df_old, df_new], ignore_index=True)
        print(f"\nTotal après fusion : {len(df_final)} lignes")
    else:
        df_final = df_new
        print(f"\nNouvelles données : {len(df_final)} lignes")

    # Remove duplicates
    before_dedup = len(df_final)
    df_final = df_final.drop_duplicates(subset=["job_id"], keep="first")
    after_dedup = len(df_final)
    
    if before_dedup > after_dedup:
        print(f"Doublons supprimés : {before_dedup - after_dedup}")

    # Ensure all columns exist
    for col in STANDARD_COLUMNS:
        if col not in df_final.columns:
            df_final[col] = ""

    # Reorder columns
    df_final = df_final[STANDARD_COLUMNS]

    # Save
    df_final.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    print(f"\nFichier nettoyé sauvegardé : {output_path}")
    print(f"Total final : {len(df_final)} offres d'emploi")
    
    # Statistics
    print(f"\nStatistiques:")
    print(f"  - Secteurs       : {(df_final['sector'] != '').sum()}/{len(df_final)} ({(df_final['sector'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Entreprises    : {(df_final['company'] != '').sum()}/{len(df_final)} ({(df_final['company'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Niveaux études : {(df_final['study_level'] != '').sum()}/{len(df_final)} ({(df_final['study_level'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Expérience     : {(df_final['experience'] != '').sum()}/{len(df_final)} ({(df_final['experience'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Compétences    : {(df_final['skills'] != '').sum()}/{len(df_final)} ({(df_final['skills'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Salaires       : {(df_final['salary_min'] != '').sum()}/{len(df_final)} ({(df_final['salary_min'] != '').sum()/len(df_final)*100:.1f}%)")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    clean_optioncarriere_csv(
        "src/Data/rawData/jobs_optioncarriere.csv",
        "src/Data/cleanedData/jobs_optioncarriere_cleaned.csv"
    )