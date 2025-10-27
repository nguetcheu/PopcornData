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
    """Convertit le runtime en minutes (format: '1h 42m' -> 102)"""
    if pd.isna(runtime_str) or runtime_str == "N/A" or runtime_str == "":
        return None
    
    try:
        runtime_str = str(runtime_str).strip()
        total_minutes = 0
        
        # Extraction des heures
        hours_match = re.search(r'(\d+)h', runtime_str)
        if hours_match:
            total_minutes += int(hours_match.group(1)) * 60
        
        # Extraction des minutes
        minutes_match = re.search(r'(\d+)m', runtime_str)
        if minutes_match:
            total_minutes += int(minutes_match.group(1))
        
        return total_minutes if total_minutes > 0 else None
    except Exception as e:
        return None

def clean_genres(genre_str):
    """Nettoie et normalise les genres"""
    if pd.isna(genre_str) or genre_str == "N/A" or genre_str == "":
        return "Autre"
    
    try:
        # Séparer les genres, supprimer les doublons et trier
        genres = [g.strip() for g in str(genre_str).split(',')]
        genres = sorted(set(g for g in genres if g and g != "N/A"))
        return ', '.join(genres) if genres else "Autre"
    except:
        return "Autre"

def clean_text(text):
    """Nettoie les champs texte"""
    if pd.isna(text) or text == "N/A" or text == "":
        return "N/A"
    return str(text).strip()

def extract_year(date_str):
    """Extrait l'année depuis une date ISO (YYYY-MM-DD)"""
    if pd.isna(date_str) or date_str == "N/A":
        return None
    
    try:
        # Format attendu: YYYY-MM-DD
        match = re.search(r'(\d{4})', str(date_str))
        if match:
            year = int(match.group(1))
            if 1888 <= year <= 2030:
                return year
        return None
    except:
        return None

def clean_budget_revenue(value):
    """Nettoie les valeurs de budget/revenue (0 -> None)"""
    if pd.isna(value):
        return None
    try:
        value = float(value)
        return value if value > 0 else None
    except:
        return None

def calculate_roi(row):
    """Calcule le ROI si budget et revenue disponibles"""
    budget = row.get('Budget')
    revenue = row.get('Revenue')
    
    if pd.notna(budget) and pd.notna(revenue) and budget > 0:
        return round((revenue - budget) / budget, 2)
    return None

def calculate_profit(row):
    """Calcule le profit brut"""
    budget = row.get('Budget')
    revenue = row.get('Revenue')
    
    if pd.notna(budget) and pd.notna(revenue):
        return revenue - budget
    return None

# ===============================
# 🧹 FONCTION PRINCIPALE DE NETTOYAGE
# ===============================

def clean_movie_data(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie et enrichit les données de films"""
    
    print(f"🧹 Nettoyage des données... ({len(df)} films)")
    
    # ===========================================
    # 1️⃣ SUPPRESSION DES DOUBLONS
    # ===========================================
    initial_count = len(df)
    df = df.drop_duplicates(subset=["Movie_name", "Source"], keep='first')
    duplicates_removed = initial_count - len(df)
    if duplicates_removed > 0:
        print(f"   🗑️  {duplicates_removed} doublons supprimés")
    
    # ===========================================
    # 2️⃣ NETTOYAGE DES COLONNES EXISTANTES
    # ===========================================
    
    # Nettoyage du titre
    df['Movie_name'] = df['Movie_name'].apply(clean_text)
    df['Original_Title'] = df['Original_Title'].apply(clean_text)
    
    # Extraction de l'année
    df['Release_year'] = df['Release_date'].apply(extract_year)
    
    # Nettoyage des genres
    df['Genre'] = df['Genre'].apply(clean_genres)
    
    # Conversion du runtime en minutes
    df['Runtime_minutes'] = df['Run_time'].apply(parse_runtime)
    
    # Nettoyage de l'overview, director, actors
    df['Overview'] = df['Overview'].apply(clean_text)
    df['Director'] = df['Director'].apply(clean_text)
    df['Top_Actors'] = df['Top_Actors'].apply(clean_text)
    
    # Nettoyage budget et revenue
    df['Budget'] = df['Budget'].apply(clean_budget_revenue)
    df['Revenue'] = df['Revenue'].apply(clean_budget_revenue)
    
    # Conversion de la note (Rating_Numeric -> Rating)
    df['Rating'] = pd.to_numeric(df['Rating_Numeric'], errors='coerce')
    
    # Recalcul du ROI (au cas où il serait manquant)
    df['ROI'] = df.apply(calculate_roi, axis=1)
    
    # ===========================================
    # 3️⃣ CRÉATION DE NOUVELLES COLONNES
    # ===========================================
    
    # Calcul du profit
    df['Profit'] = df.apply(calculate_profit, axis=1)
    
    # Indicateur de rentabilité
    df['Is_profitable'] = df['ROI'].apply(
        lambda x: True if pd.notna(x) and x > 0 else (False if pd.notna(x) else None)
    )
    
    # Nombre d'acteurs principaux
    df['Actor_count'] = df['Top_Actors'].apply(
        lambda x: len(str(x).split(',')) if pd.notna(x) and x != "N/A" else 0
    )
    
    # Catégorie de budget
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
    
    # Catégorie de note
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
    df['Release_decade'] = df['Release_year'].apply(
        lambda y: f"{(y // 10) * 10}s" if pd.notna(y) else None
    )
    
    # ===========================================
    # 4️⃣ SUPPRESSION DES LIGNES INVALIDES
    # ===========================================
    
    before_filter = len(df)
    
    # Supprimer les films sans note ni année (critères essentiels)
    df = df.dropna(subset=['Rating', 'Release_year'])
    
    after_filter = len(df)
    filtered_count = before_filter - after_filter
    
    if filtered_count > 0:
        print(f"   🗑️  {filtered_count} films supprimés (sans note ou année)")
    
    # ===========================================
    # 5️⃣ RÉORGANISATION DES COLONNES
    # ===========================================
    
    columns_order = [
        'Movie_name',
        'Original_Title',
        'Release_date',
        'Release_year',
        'Release_decade',
        'Genre',
        'Runtime_minutes',
        'Director',
        'Top_Actors',
        'Actor_count',
        'Overview',
        'Budget',
        'Budget_category',
        'Revenue',
        'Profit',
        'ROI',
        'Is_profitable',
        'Rating',
        'Rating_category',
        'Source'
    ]
    
    # Garder seulement les colonnes qui existent
    available_columns = [col for col in columns_order if col in df.columns]
    df = df[available_columns]
    
    print(f"✅ {len(df)} films valides après nettoyage.")
    
    return df

# ===============================
# 📊 AFFICHAGE DES STATISTIQUES
# ===============================

def display_statistics(df: pd.DataFrame):
    """Affiche des statistiques sur les données nettoyées"""
    
    print("\n" + "="*60)
    print("📊 STATISTIQUES DES DONNÉES NETTOYÉES")
    print("="*60)
    
    print(f"\n📈 Nombre total de films: {len(df)}")
    
    # Statistiques temporelles
    if 'Release_year' in df.columns:
        print(f"\n📅 Période couverte:")
        print(f"   - Année la plus ancienne: {df['Release_year'].min()}")
        print(f"   - Année la plus récente: {df['Release_year'].max()}")
    
    # Statistiques sur les notes
    if 'Rating' in df.columns:
        print(f"\n⭐ Notes:")
        print(f"   - Note moyenne: {df['Rating'].mean():.2f}/10")
        print(f"   - Note médiane: {df['Rating'].median():.2f}/10")
        print(f"   - Note min: {df['Rating'].min():.1f}/10")
        print(f"   - Note max: {df['Rating'].max():.1f}/10")
    
    # Statistiques financières
    if 'Budget' in df.columns:
        budget_count = df['Budget'].notna().sum()
        print(f"\n💰 Budget:")
        print(f"   - Films avec budget: {budget_count} ({budget_count/len(df)*100:.1f}%)")
        if budget_count > 0:
            print(f"   - Budget moyen: ${df['Budget'].mean():,.0f}")
    
    if 'Revenue' in df.columns:
        revenue_count = df['Revenue'].notna().sum()
        print(f"\n💵 Revenue:")
        print(f"   - Films avec revenue: {revenue_count} ({revenue_count/len(df)*100:.1f}%)")
        if revenue_count > 0:
            print(f"   - Revenue moyen: ${df['Revenue'].mean():,.0f}")
    
    if 'ROI' in df.columns:
        roi_count = df['ROI'].notna().sum()
        print(f"\n📈 ROI:")
        print(f"   - Films avec ROI: {roi_count} ({roi_count/len(df)*100:.1f}%)")
        if roi_count > 0:
            profitable = (df['ROI'] > 0).sum()
            print(f"   - Films rentables: {profitable} ({profitable/roi_count*100:.1f}%)")
            print(f"   - ROI moyen: {df['ROI'].mean():.2f}")
    
    # Top 5 genres
    if 'Genre' in df.columns:
        print(f"\n🎬 Top 5 genres:")
        genre_counts = {}
        for genres in df['Genre'].dropna():
            for genre in str(genres).split(','):
                genre = genre.strip()
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        top_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)[:5]
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
    
    # Chargement
    print(f"\n📂 Chargement du fichier: {INPUT_FILE}")
    try:
        df = pd.read_json(INPUT_FILE)
        print(f"✅ {len(df)} films chargés depuis TMDb")
    except FileNotFoundError:
        print(f"❌ Erreur: Le fichier {INPUT_FILE} n'existe pas!")
        print("   Assurez-vous d'avoir exécuté le script de scraping d'abord.")
        return
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return
    
    # Nettoyage
    print()
    df_clean = clean_movie_data(df)
    
    # Statistiques
    display_statistics(df_clean)
    
    # Sauvegarde
    print(f"\n💾 Sauvegarde du fichier nettoyé: {OUTPUT_FILE}")
    df_clean.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"✅ Fichier nettoyé sauvegardé avec succès!")
    
    print("\n" + "="*60)
    print("✨ NETTOYAGE TERMINÉ")
    print("="*60)

if __name__ == "__main__":
    main()