import pandas as pd
import numpy as np
from pathlib import Path
import re

# ===============================
# 📁 CONFIGURATION DES CHEMINS
# ===============================
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = RAW_DIR / "all_movies_datas.json"
OUTPUT_FILE = PROCESSED_DIR / "movies_clean.csv"

# ===============================
# 🧼 FONCTIONS DE NETTOYAGE
# ===============================
def parse_runtime(runtime_str):
    if pd.isna(runtime_str) or runtime_str == "N/A" or runtime_str == "":
        return None
    try:
        total_minutes = 0
        hours_match = re.search(r'(\d+)h', str(runtime_str))
        if hours_match:
            total_minutes += int(hours_match.group(1)) * 60
        minutes_match = re.search(r'(\d+)m', str(runtime_str))
        if minutes_match:
            total_minutes += int(minutes_match.group(1))
        return total_minutes if total_minutes > 0 else None
    except:
        return None

def clean_genres(genre_str):
    if pd.isna(genre_str) or genre_str == "N/A" or genre_str == "":
        return "Autre"
    try:
        genres = [g.strip() for g in str(genre_str).split(',')]
        genres = sorted(set(g for g in genres if g and g != "N/A"))
        return ', '.join(genres) if genres else "Autre"
    except:
        return "Autre"

def clean_text(text):
    if isinstance(text, list):
        text = ', '.join(str(t).strip() for t in text)
    if pd.isna(text) or text == "N/A" or text == "":
        return "N/A"
    return str(text).strip()

def extract_year(date_str):
    if pd.isna(date_str) or date_str == "N/A":
        return None
    try:
        match = re.search(r'(\d{4})', str(date_str))
        if match:
            year = int(match.group(1))
            if 1888 <= year <= 2030:
                return year
        return None
    except:
        return None

def clean_budget_revenue(value):
    if pd.isna(value):
        return None
    try:
        value = float(value)
        return value if value > 0 else None
    except:
        return None

def calculate_roi(row):
    budget = row.get('Budget')
    revenue = row.get('Revenue')
    if pd.notna(budget) and pd.notna(revenue) and budget > 0:
        return round((revenue - budget) / budget, 2)
    return None

def calculate_profit(row):
    budget = row.get('Budget')
    revenue = row.get('Revenue')
    if pd.notna(budget) and pd.notna(revenue):
        return revenue - budget
    return None

# ===============================
# 🧹 NETTOYAGE DES DONNÉES
# ===============================
def clean_movie_data(df: pd.DataFrame) -> pd.DataFrame:
    from datetime import datetime

    print(f"🧹 Nettoyage des données... ({len(df)} films)")

    CURRENT_YEAR = datetime.now().year

    # Suppression des doublons
    initial_count = len(df)
    df = df.drop_duplicates(subset=["Movie_name", "Source"], keep='first')
    duplicates_removed = initial_count - len(df)
    if duplicates_removed > 0:
        print(f"   🗑️  {duplicates_removed} doublons supprimés")

    # Nettoyage des champs texte
    df['Movie_name'] = df['Movie_name'].apply(clean_text)
    if 'Original_Title' in df.columns:
        df['Original_Title'] = df['Original_Title'].apply(clean_text)
    else:
        df['Original_Title'] = df['Movie_name']

    # ✅ Nouveau : Nettoyage de Poster_URL
    if 'Poster_URL' in df.columns:
        df['Poster_URL'] = df['Poster_URL'].apply(clean_text)
    else:
        df['Poster_URL'] = "N/A"

    # Extraction de l'année
    df['Release_year'] = df['Release_date'].apply(extract_year)

    # Filtrage des films futurs
    df = df[df['Release_year'] <= CURRENT_YEAR]

    # Nettoyage et transformation des autres colonnes
    df['Genre'] = df['Genre'].apply(clean_genres)
    df['Runtime_minutes'] = df['Run_time'].apply(parse_runtime)
    df['Overview'] = df['Overview'].apply(clean_text)
    df['Director'] = df['Director'].apply(clean_text)
    df['Top_Actors'] = df['Top_Actors'].apply(clean_text)
    df['Budget'] = df['Budget'].apply(clean_budget_revenue)
    df['Revenue'] = df['Revenue'].apply(clean_budget_revenue)
    df['Rating'] = pd.to_numeric(df['Rating_Numeric'], errors='coerce')
    df['ROI'] = df.apply(calculate_roi, axis=1)
    df['Profit'] = df.apply(calculate_profit, axis=1)
    df['Is_profitable'] = df['ROI'].apply(lambda x: True if pd.notna(x) and x > 0 else (False if pd.notna(x) else None))
    df['Actor_count'] = df['Top_Actors'].apply(lambda x: len(str(x).split(',')) if pd.notna(x) and x != "N/A" else 0)

    # Catégories de budget et note
    def categorize_budget(budget):
        if pd.isna(budget):
            return "Unknown"
        if budget < 1_000_000:
            return "Low (<1M)"
        elif budget < 10_000_000:
            return "Low-Medium (1-10M)"
        elif budget < 50_000_000:
            return "Medium (10-50M)"
        elif budget < 100_000_000:
            return "Medium-High (50-100M)"
        else:
            return "High (>100M)"
    df['Budget_category'] = df['Budget'].apply(categorize_budget)

    def categorize_rating(rating):
        if pd.isna(rating):
            return "Not Rated"
        if rating >= 8.0:
            return "Excellent (8+)"
        elif rating >= 7.0:
            return "Very Good (7-8)"
        elif rating >= 6.0:
            return "Good (6-7)"
        elif rating >= 5.0:
            return "Average (5-6)"
        else:
            return "Below Average (<5)"
    df['Rating_category'] = df['Rating'].apply(categorize_rating)

    # Décennie de sortie
    df['Release_decade'] = df['Release_year'].apply(lambda y: f"{(y // 10) * 10}s" if pd.notna(y) else None)

    # Supprimer les films sans note ni année
    before_filter = len(df)
    df = df.dropna(subset=['Rating', 'Release_year'])
    after_filter = len(df)
    if before_filter - after_filter > 0:
        print(f"   🗑️  {before_filter - after_filter} films supprimés (sans note ou année)")

    # Réorganisation des colonnes
    columns_order = [
        'Movie_name', 'Original_Title', 'Release_date', 'Release_year', 'Release_decade',
        'Genre', 'Runtime_minutes', 'Director', 'Top_Actors', 'Actor_count', 'Overview',
        'Budget', 'Budget_category', 'Revenue', 'Profit', 'ROI', 'Is_profitable',
        'Rating', 'Rating_category', 'Poster_URL', 'Source'  
    ]
    available_columns = [col for col in columns_order if col in df.columns]
    df = df[available_columns]

    print(f"✅ {len(df)} films valides après nettoyage.")
    return df

# ===============================
# 📊 STATISTIQUES
# ===============================
def display_statistics(df: pd.DataFrame):
    print("\n" + "="*60)
    print("📊 STATISTIQUES DES DONNÉES NETTOYÉES")
    print("="*60)
    print(f"\n📈 Nombre total de films: {len(df)}")

    if 'Release_year' in df.columns:
        print(f"\n📅 Période couverte: {df['Release_year'].min()} - {df['Release_year'].max()}")

    if 'Rating' in df.columns:
        print(f"\n⭐ Notes: Moyenne={df['Rating'].mean():.2f}, Min={df['Rating'].min():.1f}, Max={df['Rating'].max():.1f}")

    if 'Budget' in df.columns:
        budget_count = df['Budget'].notna().sum()
        print(f"\n💰 Budget: {budget_count} films avec budget")

    if 'Revenue' in df.columns:
        revenue_count = df['Revenue'].notna().sum()
        print(f"\n💵 Revenue: {revenue_count} films avec revenue")

    if 'ROI' in df.columns:
        roi_count = df['ROI'].notna().sum()
        profitable = (df['ROI'] > 0).sum()
        print(f"\n📈 ROI: {roi_count} films, {profitable} rentables")

    if 'Genre' in df.columns:
        genre_counts = {}
        for genres in df['Genre'].dropna():
            for g in str(genres).split(','):
                g = g.strip()
                genre_counts[g] = genre_counts.get(g, 0) + 1
        top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n🎬 Top 5 genres:")
        for genre, count in top_genres:
            print(f"   - {genre}: {count} films")

    # Données manquantes
    print(f"\n❓ Données manquantes:")
    for col in df.columns:
        missing = df[col].isna().sum()
        if missing > 0:
            print(f"   - {col}: {missing} ({missing/len(df)*100:.1f}%)")

# ===============================
# 🚀 PIPELINE PRINCIPAL
# ===============================
def main():
    print("="*60)
    print("🎬 NETTOYAGE DES DONNÉES TMDB")
    print("="*60)

    try:
        df = pd.read_json(INPUT_FILE)
        print(f"\n✅ {len(df)} films chargés depuis TMDb")
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return

    df_clean = clean_movie_data(df)
    display_statistics(df_clean)
    df_clean.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"\n💾 Fichier nettoyé sauvegardé: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
