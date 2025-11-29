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

def clean_list_or_text(text, limit=3):
    """
    Nettoie les listes ou textes multi-valeurs et les convertit en chaîne simple.
    Limite le nombre d'items pour éviter les listes trop longues.
    Exemple: "item1, item2, item3, item4" -> "item1, item2, item3" (avec limit=3)
    """
    if pd.isna(text) or text == "":
        return ""
    
    text = str(text).strip()
    
    # Séparer par virgule, slash ou tiret
    items = re.split(r'[,/;]', text)
    items = [clean_text(item) for item in items if item.strip()]
    
    # Enlever doublons en gardant l'ordre
    seen = set()
    unique_items = []
    for item in items:
        if item and item.lower() not in seen:
            seen.add(item.lower())
            unique_items.append(item)
            # Limiter le nombre d'items
            if len(unique_items) >= limit:
                break
    
    return ", ".join(unique_items) if unique_items else ""

def clean_date(date_str):
    """
    Convertit les dates au format DD.MM.YYYY ou DD/MM/YYYY en YYYY-MM-DD.
    Retourne chaîne vide si impossible à parser.
    """
    if pd.isna(date_str) or date_str == "":
        return ""
    
    date_str = str(date_str).replace("/", ".").strip()
    
    # Essayer différents formats
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except:
            continue
    
    return ""

def parse_salary(salary_str):
    """
    Parse le salaire et retourne (salary_min, salary_max).
    Gère: "1500 TND", "1500-2000", "< 2000", "> 1500", "('1200', '')"
    """
    if pd.isna(salary_str) or salary_str == "":
        return "", ""
    
    salary_str = str(salary_str)
    
    # Pattern: "('1200', '')" ou "('1200', '1500')" - format tuple Python
    if salary_str.startswith("("):
        # Extraire les valeurs du tuple
        matches = re.findall(r"'(\d+)'", salary_str)
        if matches:
            if len(matches) == 1:
                return matches[0], matches[0]
            elif len(matches) >= 2:
                return matches[0], matches[1]
    
    salary_str = salary_str.replace("TND", "").replace("DT", "").replace("dt", "")
    salary_str = salary_str.replace(" ", "").replace(".", "")
    
    # Pattern: "< 2000" ou "> 1500"
    if "<" in salary_str or ">" in salary_str:
        salary_str = re.sub(r'[<>]', '', salary_str)
        try:
            val = int(salary_str)
            return "", str(val) if "<" in str(salary_str) else (str(val), "")
        except:
            return "", ""
    
    # Pattern: "1500-2000"
    if "-" in salary_str:
        parts = salary_str.split("-")
        try:
            return str(int(parts[0])), str(int(parts[1]))
        except:
            return "", ""
    
    # Pattern: "2000" (valeur unique)
    try:
        val = int(salary_str)
        return str(val), str(val)
    except:
        return "", ""

def extract_location_parts(location_str):
    """
    Extrait ville et région depuis une chaîne de localisation.
    Retourne (city, region)
    """
    if not location_str or pd.isna(location_str):
        return "", ""
    
    location_str = str(location_str).strip()
    
    # Enlever "Tunisie" à la fin
    location_str = re.sub(r',?\s*Tunisie\s*$', '', location_str, flags=re.IGNORECASE)
    
    if "," in location_str:
        parts = [p.strip() for p in location_str.split(",")]
        # Enlever doublons
        parts = list(dict.fromkeys(parts))
        if len(parts) >= 2:
            return parts[0], parts[-1]
        else:
            return parts[0], ""
    else:
        return location_str, ""

def extract_skills_from_description(description):
    """Extrait les compétences depuis la description (version keywords uniquement)."""
    if not description:
        return ""
    
    skills = []
    
    # Chercher des compétences communes (keywords seulement)
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
        'production': r'\bproduction\b',
        'maintenance': r'\bmaintenance\b',
        'qualite': r'\bqualit[ée]\b',
    }
    
    description_lower = description.lower()
    for skill_name, pattern in common_skills.items():
        if re.search(pattern, description_lower):
            skills.append(skill_name)
    
    return ', '.join(skills[:8]) if skills else ""  # Max 8 compétences

def generate_job_id_row(row):
    """Génère un job_id robuste en préférant detail_link puis fallback sur title/company/date."""
    link = row.get("detail_link") if "detail_link" in row.index else None
    if pd.notna(link) and str(link).strip():
        return re.sub(r'\W+', '', str(link).lower())
    base = f"{row.get('title','')}-{row.get('company','')}-{row.get('date_publication','')}"
    base = clean_text(base).lower().replace(" ", "-")
    return re.sub(r'\W+', '', base)

def map_emploistunisie_to_standard(df_raw):
    """
    Mappe les colonnes EmploisTunisie vers le format standardisé.
    """
    df_mapped = pd.DataFrame()
    
    # Colonnes de base
    df_mapped["title"] = df_raw["title"].apply(clean_text) if "title" in df_raw.columns else ""
    df_mapped["detail_link"] = df_raw["detail_link"].apply(clean_text) if "detail_link" in df_raw.columns else ""
    df_mapped["company"] = df_raw["company"].apply(clean_text) if "company" in df_raw.columns else ""
    
    # Date publication
    if "date_publication" in df_raw.columns:
        df_mapped["date_publication"] = df_raw["date_publication"].apply(clean_date)
    else:
        df_mapped["date_publication"] = ""
    
    # Sector - nettoyer multi-valeurs
    if "sector" in df_raw.columns:
        df_mapped["sector"] = df_raw["sector"].apply(clean_list_or_text)
    else:
        df_mapped["sector"] = ""
    
    # Contract type
    if "contract_type" in df_raw.columns:
        df_mapped["contract_type"] = df_raw["contract_type"].apply(clean_list_or_text)
    else:
        df_mapped["contract_type"] = ""
    
    # Study level
    if "study_level" in df_raw.columns:
        df_mapped["study_level"] = df_raw["study_level"].apply(clean_list_or_text)
    else:
        df_mapped["study_level"] = ""
    
    # Experience
    if "experience" in df_raw.columns:
        df_mapped["experience"] = df_raw["experience"].apply(clean_list_or_text)
    else:
        df_mapped["experience"] = ""
    
    # Availability
    if "availability" in df_raw.columns:
        df_mapped["availability"] = df_raw["availability"].apply(clean_list_or_text)
    else:
        df_mapped["availability"] = ""
    
    # Location
    if "location" in df_raw.columns:
        # Nettoyer location en enlevant doublons
        df_mapped["location"] = df_raw["location"].apply(clean_list_or_text)
        location_parts = df_mapped["location"].apply(extract_location_parts)
        df_mapped["city"] = location_parts.apply(lambda x: x[0])
        df_mapped["region"] = location_parts.apply(lambda x: x[1])
    else:
        df_mapped["location"] = ""
        df_mapped["city"] = ""
        df_mapped["region"] = ""
    
    # Gérer city et region si elles existent déjà
    if "city" in df_raw.columns:
        df_mapped["city"] = df_raw["city"].apply(clean_text)
    if "region" in df_raw.columns:
        df_mapped["region"] = df_raw["region"].apply(clean_text)
    
    # Description
    if "description" in df_raw.columns:
        df_mapped["description"] = df_raw["description"].apply(clean_text)
    else:
        df_mapped["description"] = ""
    
    # Salaire
    if "salary" in df_raw.columns:
        salary_data = df_raw["salary"].apply(parse_salary)
        df_mapped["salary_min"] = salary_data.apply(lambda x: x[0])
        df_mapped["salary_max"] = salary_data.apply(lambda x: x[1])
    elif "salary_min" in df_raw.columns and "salary_max" in df_raw.columns:
        df_mapped["salary_min"] = df_raw["salary_min"].apply(lambda x: str(x) if pd.notna(x) else "")
        df_mapped["salary_max"] = df_raw["salary_max"].apply(lambda x: str(x) if pd.notna(x) else "")
    else:
        df_mapped["salary_min"] = ""
        df_mapped["salary_max"] = ""
    
    # Skills
    if "skills" in df_raw.columns:
        df_mapped["skills"] = df_raw["skills"].apply(clean_list_or_text)
    else:
        # Extraire depuis description si pas de colonne skills
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

def clean_emploistunisie_csv(input_path, output_path):
    """
    Nettoie le CSV EmploisTunisie et le transforme en format standardisé.
    """
    print("\n" + "="*80)
    print("NETTOYAGE DES DONNÉES EMPLOISTUNISIE")
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
    df_new = map_emploistunisie_to_standard(df_raw)

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

    # Ordre final des colonnes (MÊME FORMAT que les autres)
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
    clean_emploistunisie_csv(
        "src/Data/rawData/job_emploisTunisie.csv",
        "src/Data/cleanedData/job_emploisTunisie_cleaned.csv"
    )