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

def clean_list_or_text(text, limit=3):
    """Nettoie les listes ou textes multi-valeurs."""
    if pd.isna(text) or text == "":
        return ""
    
    text = str(text).strip()
    text = re.sub(r"[\[\]'\"]", "", text)  # Remove brackets and quotes
    
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
    if pd.isna(relative_str) or str(relative_str).strip() == "":
        return ""
    
    rel = str(relative_str).lower().strip()
    
    # Gestion des dates relatives existantes
    if any(word in rel for word in ['aujourd', 'today', 'now']):
        return datetime.now().strftime("%Y-%m-%d")
    if any(word in rel for word in ['hier', 'yesterday']):
        return (datetime.now() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Gestion "il y a X jours/heures"
    match = re.search(r'(\d+)\s*(jour|jours|day|days|heure|heures|hour|hours|h)', rel)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if unit in ['jour', 'jours', 'day', 'days']:
            return (datetime.now() - pd.Timedelta(days=num)).strftime("%Y-%m-%d")
        else:  # heures
            return datetime.now().strftime("%Y-%m-%d")
    
    # Dictionnaire des mois français
    mois_fr = {
        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
    }
    
    # Vérifier si la date contient un mois en lettres
    for mois, num in mois_fr.items():
        if mois in rel:
            rel_num = re.sub(mois, num, rel)
            try:
                return datetime.strptime(rel_num, "%d %m %Y").strftime("%Y-%m-%d")
            except:
                break
    
    # Gestion des formats numériques existants
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(rel.replace("/", "."), fmt).strftime("%Y-%m-%d")
        except:
            continue
    
    return relative_str


def parse_salary(salary_str):
    """Parse le salaire et retourne (salary_min, salary_max)."""
    if pd.isna(salary_str) or salary_str == "":
        return "", ""
    
    salary_str = str(salary_str)
    
    # Tuple format
    if salary_str.startswith("("):
        matches = re.findall(r"'(\d+)'", salary_str)
        if matches:
            if len(matches) == 1:
                return matches[0], matches[0]
            elif len(matches) >= 2:
                return matches[0], matches[1]
    
    salary_str = salary_str.replace("TND", "").replace("DT", "").replace("dt", "")
    salary_str = salary_str.replace(" ", "").replace(".", "")
    
    # < or >
    if "<" in salary_str or ">" in salary_str:
        salary_str = re.sub(r'[<>]', '', salary_str)
        try:
            val = int(salary_str)
            return "", str(val) if "<" in str(salary_str) else (str(val), "")
        except:
            return "", ""
    
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

def generate_job_id_row(row):
    """Génère un job_id unique."""
    link = row.get("detail_link") if "detail_link" in row.index else None
    if pd.notna(link) and str(link).strip():
        return re.sub(r'\W+', '', str(link).lower())
    base = f"{row.get('title','')}-{row.get('source','')}-{row.get('scraped_at','')}"
    base = clean_text(base).lower().replace(" ", "-")
    return re.sub(r'\W+', '', base)

# KEEJOB SPECIFIC MAPPER

def map_keejob_to_standard(df_raw):
    """Mappe Keejob vers format standardisé."""
    df = pd.DataFrame()
    
    df["title"] = df_raw["title"].apply(clean_text) if "title" in df_raw.columns else ""
    df["detail_link"] = df_raw["detail_link"].apply(clean_text) if "detail_link" in df_raw.columns else ""
    df["company"] = ""  # Keejob doesn't have company
    df["date_publication"] = df_raw["date_publication"].apply(parse_relative_date) if "date_publication" in df_raw.columns else ""
    df["sector"] = df_raw["sector"].apply(clean_list_or_text) if "sector" in df_raw.columns else ""
    df["contract_type"] = df_raw["contract_type"].apply(clean_list_or_text) if "contract_type" in df_raw.columns else ""
    df["study_level"] = df_raw["study_level"].apply(clean_list_or_text) if "study_level" in df_raw.columns else ""
    df["experience"] = df_raw["experience"].apply(clean_list_or_text) if "experience" in df_raw.columns else ""
    df["availability"] = df_raw["availability"].apply(clean_list_or_text) if "availability" in df_raw.columns else ""
    
    if "location" in df_raw.columns:
        df["location"] = df_raw["location"].apply(clean_text)
        location_parts = df_raw["location"].apply(extract_location_parts)
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
    
    df["skills"] = df["description"].apply(extract_skills_from_description)
    
    df["source"] = df_raw["source"] if "source" in df_raw.columns else "keejob"
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

def clean_keejob_csv(input_path, output_path):
    """
    Nettoie le CSV Keejob et le transforme en format standardisé.
    """
    print("\n" + "="*80)
    print("NETTOYAGE DES DONNÉES KEEJOB")
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
    df_new = map_keejob_to_standard(df_raw)

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
    print(f"\Statistiques:")
    print(f"  - Secteurs       : {(df_final['sector'] != '').sum()}/{len(df_final)} ({(df_final['sector'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Niveaux études : {(df_final['study_level'] != '').sum()}/{len(df_final)} ({(df_final['study_level'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Expérience     : {(df_final['experience'] != '').sum()}/{len(df_final)} ({(df_final['experience'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Compétences    : {(df_final['skills'] != '').sum()}/{len(df_final)} ({(df_final['skills'] != '').sum()/len(df_final)*100:.1f}%)")
    print(f"  - Salaires       : {(df_final['salary_min'] != '').sum()}/{len(df_final)} ({(df_final['salary_min'] != '').sum()/len(df_final)*100:.1f}%)")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    clean_keejob_csv(
        "src/Data/rawData/job_keejobs.csv",
        "src/Data/cleanedData/job_keejobs_cleaned.csv"
    )