import pandas as pd
import re
import unicodedata
from datetime import datetime



def clean_text(text, capitalize=False):
    """Normalise le texte : accents, espaces, retours à la ligne."""
    if pd.isna(text):
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text).strip()
    if capitalize:
        text = text.title()
    return text

def clean_date(d):
    if pd.isna(d):
        return None
    d = str(d).replace("/", ".")
    try:
        return datetime.strptime(d, "%d.%m.%Y").strftime("%Y-%m-%d")
    except:
        return None

def parse_salary(s):
    if pd.isna(s) or s == "":
        return None, None
    s = str(s).replace("TND", "").replace(" ", "").replace(".", "")
    s = s.replace("<", "").replace(">", "")
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

def split_multi(x):
    if pd.isna(x):
        return []
    items = [clean_text(i) for i in re.split(r"[,-/]", x) if i.strip()]
    return list(dict.fromkeys(items))

def clean_description(desc):
    """Supprime retours à la ligne, tabulations et espaces multiples pour affichage."""
    if pd.isna(desc):
        return ""
    desc = str(desc)
    desc = desc.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc

def generate_job_id(row):
    base = f"{row['title']}-{row['company']}-{row['date_publication']}"
    return clean_text(base.lower().replace(" ", "-"))



def clean_csv(input_path, output_path):
    df = pd.read_csv(input_path, encoding='utf-8-sig')
    
    # Nettoyage général
    for col in df.columns:
        if col in ["description"]:
            df[col] = df[col].apply(clean_description)
        else:
            df[col] = df[col].apply(lambda x: clean_text(x) if isinstance(x, str) else x)
    
    # Nettoyage date
    df["date_publication"] = df["date_publication"].apply(clean_date)
    
    # Parse salaire
    df["salary_min"], df["salary_max"] = zip(*df["salary"].apply(parse_salary))
    df.drop(columns=["salary"], inplace=True)
    
    # Colonnes multi-valeurs
    multi_cols = ["skills", "study_level", "experience", "sector", "contract_type"]
    for col in multi_cols:
        if col not in df.columns:
            df[col] = [[] for _ in range(len(df))]
        else:
            df[col] = df[col].apply(split_multi)
    
    # Localisation : supprimer doublons et espaces inutiles
    for loc_col in ["location", "region", "city"]:
        if loc_col in df.columns:
            df[loc_col] = df[loc_col].apply(lambda x: ", ".join(list(dict.fromkeys([clean_text(i) for i in str(x).split(",")]))))
    
    # Ajout scraped_at
    df["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Génération job_id
    df["job_id"] = df.apply(generate_job_id, axis=1)
    
    # Supprimer doublons
    df = df.drop_duplicates(subset=["job_id"])
    
    # Sauvegarde
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Fichier nettoyé et prêt pour affichage : {output_path}")


if __name__ == "__main__":
    clean_csv(
        "src/Data/rawData/job_emploisTunisie.csv",
        "src/Data/cleanedData/job_emploisTunisie_cleaned.csv"
    )
