import pandas as pd
import unicodedata
import re
import os
from datetime import datetime, timedelta

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clean_text(text):
    """Nettoyage de texte : accents, espaces multiples, strip."""
    if pd.isna(text):
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def clean_list_or_text(text, limit=3):
    """Nettoie les listes ou textes multi-valeurs."""
    if pd.isna(text) or text == "":
        return ""
    
    text = str(text).strip()
    
    items = re.split(r'[,/;]', text)
    items = [clean_text(item) for item in items if item.strip()]
    
    seen = set()
    unique_items = []
    for item in items:
        if item and item.lower() not in seen:
            seen.add(item.lower())
            unique_items.append(item)
            if len(unique_items) >= limit:
                break
    
    return ", ".join(unique_items) if unique_items else ""

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
    """Parse le salaire et retourne (salary_min, salary_max) sous forme int ou None."""
    if pd.isna(salary_str) or salary_str.strip() == "":
        return None, None

    s = str(salary_str).replace("TND", "").replace("DT", "").replace("dt", "")
    s = s.replace(" ", "").replace(".", "")

    # Si "<" ou ">"
    if s.startswith("<"):
        try:
            return None, int(re.sub(r"[^\d]", "", s))
        except:
            return None, None
    if s.startswith(">"):
        try:
            return int(re.sub(r"[^\d]", "", s)), None
        except:
            return None, None

    # Si plage avec "-"
    if "-" in s:
        parts = s.split("-")
        try:
            return int(parts[0]), int(parts[1])
        except:
            return None, None

    # Si valeur unique
    try:
        val = int(s)
        return val, val
    except:
        return None, None


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
        'comptabilite': r'\bcomptabilit[ée]\b',
        'finance': r'\bfinance\b',
        'marketing': r'\bmarketing\b',
        'vente': r'\bvente\b',
    }
    
    skills = []
    description_lower = description.lower()
    for skill_name, pattern in common_skills.items():
        if re.search(pattern, description_lower):
            skills.append(skill_name)
    
    return ', '.join(skills[:8]) if skills else ""

def generate_job_id_row(row):
    """Génère un job_id unique."""
    link = row.get("detail_link") if "detail_link" in row.index else None
    if pd.notna(link) and str(link).strip():
        return re.sub(r'\W+', '', str(link).lower())
    base = f"{row.get('title','')}-{row.get('company','')}-{row.get('scraped_at','')}"
    base = clean_text(base).lower().replace(" ", "-")
    return re.sub(r'\W+', '', base)

# EMPLOITUNISIE SPECIFIC MAPPER

def map_emploitunisie_to_standard(df_raw):
    """Mappe EmploiTunisie vers format standardisé."""
    df = pd.DataFrame()
    
    df["title"] = df_raw["title"].apply(
        lambda x: ' - '.join(re.sub(r'\s+', ' ', re.sub(r',+', ',', str(x).strip())).split(' - ')[:-1]) 
        if isinstance(x, str) and '-' in x else str(x).strip()
    ) if "title" in df_raw.columns else ""    
    df["detail_link"] = df_raw["detail_link"].apply(clean_text) if "detail_link" in df_raw.columns else ""
    df["company"] = df_raw["company"].apply(clean_text) if "company" in df_raw.columns else ""
    df["date_publication"] = df_raw["date_publication"].apply(parse_relative_date) if "date_publication" in df_raw.columns else ""
    df["sector"] = df_raw["sector"].apply(clean_list_or_text) if "sector" in df_raw.columns else ""
    df["contract_type"] = df_raw["contract_type"].apply(clean_list_or_text) if "contract_type" in df_raw.columns else ""
    df["study_level"] = df_raw["study_level"].apply(clean_list_or_text) if "study_level" in df_raw.columns else ""
    df["experience"] = df_raw["experience"].apply(clean_list_or_text) if "experience" in df_raw.columns else ""
    
    # Availability = remote work field
    df["availability"] = df_raw.get("remote", pd.Series([""] * len(df_raw))).apply(clean_text)
    
    # Location handling
    if "city" in df_raw.columns and "region" in df_raw.columns:
        df["city"] = df_raw["city"].apply(clean_text)
        df["region"] = df_raw["region"].apply(clean_text)
        df["location"] = df.apply(
            lambda x: f"{x['city']}, {x['region']}" if x['city'] and x['region'] 
            else (x['city'] or x['region']), 
            axis=1
        )
    elif "location" in df_raw.columns:
        df["location"] = df_raw["location"].apply(clean_text)
        location_parts = df["location"].apply(extract_location_parts)
        df["city"] = location_parts.apply(lambda x: x[0])
        df["region"] = location_parts.apply(lambda x: x[1])
    else:
        df["location"] = ""
        df["city"] = ""
        df["region"] = ""
    
    df["description"] = df_raw["description"].apply(clean_text) if "description" in df_raw.columns else ""
    
    if "salary" in df_raw.columns:
        salary_data = df_raw["salary"].apply(parse_salary)
        df["salary_min"] = salary_data.apply(lambda x: x[0])
        df["salary_max"] = salary_data.apply(lambda x: x[1])
    else:
        df["salary_min"] = ""
        df["salary_max"] = ""
    
    # Skills
    if "skills" in df_raw.columns:
        df["skills"] = df_raw["skills"].apply(clean_list_or_text)
    else:
        df["skills"] = ""
    
    # If no skills, extract from description
    if (df["skills"] == "").all():
        df["skills"] = df["description"].apply(extract_skills_from_description)
    
    df["source"] = df_raw["source"] if "source" in df_raw.columns else "emploitunisie"
    df["scraped_at"] = df_raw["scraped_at"] if "scraped_at" in df_raw.columns else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df["job_id"] = df.apply(generate_job_id_row, axis=1)
    
    return df

# STANDARD COLUMNS

STANDARD_COLUMNS = [
    "title", "detail_link", "company", "date_publication",
    "sector", "contract_type", "study_level", "experience", "availability",
    "location", "region", "city",
    "salary_min", "salary_max",
    "description", "skills",
    "source", "scraped_at", "job_id"
]

# MAIN CLEANING FUNCTION

def clean_emploitunisie_csv(input_path, output_path):
    """
    Nettoie le CSV EmploiTunisie et le transforme en format standardisé.
    """
    print("\n" + "="*80)
    print("NETTOYAGE DES DONNÉES EMPLOITUNISIE")
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
    df_new = map_emploitunisie_to_standard(df_raw)

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
    print(f"\n Statistiques:")
    print(f"  - Secteurs       : {(df_final['sector'] != '').sum()}/{len(df_final)} ({(df_final['sector'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Entreprises    : {(df_final['company'] != '').sum()}/{len(df_final)} ({(df_final['company'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Niveaux études : {(df_final['study_level'] != '').sum()}/{len(df_final)} ({(df_final['study_level'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Expérience     : {(df_final['experience'] != '').sum()}/{len(df_final)} ({(df_final['experience'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Compétences    : {(df_final['skills'] != '').sum()}/{len(df_final)} ({(df_final['skills'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Salaires       : {(df_final['salary_min'] != '').sum()}/{len(df_final)} ({(df_final['salary_min'] != '').sum()/len(df_final)*100:.1f}%)")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    clean_emploitunisie_csv(
        "src/Data/rawData/job_emploisTunisie.csv",
        "src/Data/cleanedData/job_emploisTunisie_cleaned.csv"
    )