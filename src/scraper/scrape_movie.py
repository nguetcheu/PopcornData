import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
import re
from datetime import datetime

# ===============================
# 📁 CONFIGURATION ET CHEMINS
# ===============================
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = RAW_DIR / "all_movies_datas.json"

TMDB_API_KEY = "6b99e30943b6075d408c1a836c07c94c"
TMDB_BASE_URL = "https://api.themoviedb.org/3"

all_movies = []

# ===============================
# 🧩 UTILITAIRES
# ===============================
def normalize_date(date_str):
    """Normalise la date en format ISO (YYYY-MM-DD)"""
    if not date_str or date_str == "N/A":
        return "N/A"
    try:
        clean_date = re.sub(r"\s*\(.*?\)", "", date_str).strip()
        if re.match(r"\d{2}/\d{2}/\d{4}", clean_date):
            parsed = datetime.strptime(clean_date, "%d/%m/%Y")
            return parsed.strftime("%Y-%m-%d")
        elif re.match(r"\d{4}-\d{2}-\d{2}", clean_date):
            return clean_date
        return clean_date
    except Exception:
        return date_str

def normalize_json_dates(df):
    df["Release_date"] = df["Release_date"].apply(normalize_date)
    return df

# ===============================
# 🎭 GENRES COMMUNS
# ===============================
COMMON_GENRES = {
    "Action": ["Action"],
    "Adventure": ["Adventure", "Aventure"],
    "Animation": ["Animation"],
    "Comedy": ["Comedy", "Comédie"],
    "Crime": ["Crime", "Policier"],
    "Documentary": ["Documentary", "Documentaire"],
    "Drama": ["Drama", "Drame"],
    "Family": ["Family", "Famille"],
    "Fantasy": ["Fantasy", "Fantastique"],
    "History": ["History", "Historique"],
    "Horror": ["Horror", "Horreur"],
    "Music": ["Music", "Musique"],
    "Mystery": ["Mystery", "Mystère"],
    "Romance": ["Romance", "Romantique"],
    "Science Fiction": ["Science Fiction", "Science-Fiction", "Sci-Fi"],
    "TV Movie": ["TV Movie", "Téléfilm"],
    "Thriller": ["Thriller", "Suspense"],
    "War": ["War", "Guerre"],
    "Western": ["Western"]
}

def normalize_genres(genre_list):
    if not genre_list:
        return "N/A"
    normalized = set()
    for genre in genre_list:
        genre_clean = genre.strip()
        for common, variants in COMMON_GENRES.items():
            if genre_clean in variants or genre_clean == common:
                normalized.add(common)
                break
    return ', '.join(sorted(normalized)) if normalized else "N/A"

# ===============================
# 🔑 TMDb API - Récupération complète
# ===============================
def get_tmdb_full_data(movie_id):
    try:
        api_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "append_to_response": "credits,external_ids",
            "language": "fr-FR"
        }
        
        resp = requests.get(api_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Si overview vide, réessayer en anglais
        overview = data.get("overview", "")
        if not overview.strip():
            params_en = params.copy()
            params_en["language"] = "en-US"
            resp_en = requests.get(api_url, params=params_en, timeout=10)
            if resp_en.status_code == 200:
                overview = resp_en.json().get("overview", "N/A")
        
        # Top acteurs
        actors_list = [a["name"] for a in data.get("credits", {}).get("cast", [])[:5]]
        
        # Réalisateur
        crew = data.get("credits", {}).get("crew", [])
        directors = [p["name"] for p in crew if p.get("job") == "Director"]
        director = ", ".join(directors) if directors else "N/A"
        
        # Genres
        genres = [g["name"] for g in data.get("genres", [])]
        
        # Runtime formaté
        runtime = data.get("runtime")
        if runtime:
            h, m = divmod(runtime, 60)
            runtime_formatted = f"{h}h {m}m" if h else f"{m}m"
        else:
            runtime_formatted = "N/A"

        # Nettoyage de la date
        release_date = normalize_date(data.get("release_date", "N/A"))

        return {
            "original_title": data.get("original_title", "N/A"),
            "budget": data.get("budget") or 0,
            "revenue": data.get("revenue") or 0,
            "vote_count": data.get("vote_count", 0),
            "vote_average": data.get("vote_average", 0),
            "runtime": runtime_formatted,
            "genres": genres,
            "overview": overview if overview else "N/A",
            "director": director,
            "actors": actors_list,
            "release_date": release_date,
            "popularity": data.get("popularity", 0),
            "imdb_id": data.get("external_ids", {}).get("imdb_id")
        }
    except Exception as e:
        print(f"⚠️ TMDb API erreur pour movie_id {movie_id}: {e}")
        return None

# ===============================
# 🎬 Scraping TMDb HTML + API
# ===============================
base_url = 'https://www.themoviedb.org/movie?page='

for page in range(1, 40):  # ⇦ change ici pour plus de pages
    print(f"📄 Scraping TMDb page {page}")
    try:
        resp = requests.get(base_url + str(page), timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'lxml')
        cards = soup.find_all('div', class_='card style_1')

        for card in cards:
            inner = card.find('div', class_='content')
            if not inner:
                continue

            title_tag = inner.find('h2')
            movie_name_fr = title_tag.text.strip() if title_tag else "N/A"

            inner_link_tag = inner.find('a')
            if not inner_link_tag or 'href' not in inner_link_tag.attrs:
                continue
            full_link = "https://www.themoviedb.org" + inner_link_tag['href']

            match = re.search(r'/movie/(\d+)', full_link)
            if not match:
                continue
            movie_id = match.group(1)

            print(f"  🎬 Traitement: {movie_name_fr} (ID: {movie_id})")

            tmdb_data = get_tmdb_full_data(movie_id)
            if not tmdb_data:
                print(f"    ⚠️ Données absentes, film ignoré.")
                continue

            # Calcul du ROI (si budget et revenue présents)
            roi_value = None
            if tmdb_data["budget"] > 0 and tmdb_data["revenue"] > 0:
                roi_value = round((tmdb_data["revenue"] - tmdb_data["budget"]) / tmdb_data["budget"], 2)

            movie_data = {
                "Movie_name": movie_name_fr,
                "Original_Title": tmdb_data["original_title"],
                "Release_date": tmdb_data["release_date"],
                "Genre": normalize_genres(tmdb_data["genres"]),
                "Run_time": tmdb_data["runtime"],
                "Overview": tmdb_data["overview"],
                "Director": tmdb_data["director"],
                "Top_Actors": ", ".join(tmdb_data["actors"]) if tmdb_data["actors"] else "N/A",
                "Budget": tmdb_data["budget"],
                "Revenue": tmdb_data["revenue"],
                "Rating_Numeric": tmdb_data["vote_average"],
                "ROI": roi_value,
                "Source": "TMDb HTML + API"
            }

            all_movies.append(movie_data)
            time.sleep(0.3)

        time.sleep(1)

    except Exception as e:
        print(f"❌ Erreur page {page}: {e}")
        continue

# ===============================
# 💾 SAUVEGARDE
# ===============================
if all_movies:
    df = pd.DataFrame(all_movies)
    df = normalize_json_dates(df)

    import json
    OUT_FILE.write_text(json.dumps(json.loads(df.to_json(orient="records")), indent=2, ensure_ascii=False), encoding="utf-8")
    csv_file = OUT_FILE.with_suffix('.csv')
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')

    print(f"\n✅ {len(all_movies)} films sauvegardés dans {OUT_FILE}")
    print(f"✅ CSV sauvegardé dans {csv_file}")
else:
    print("❌ Aucun film récupéré")
