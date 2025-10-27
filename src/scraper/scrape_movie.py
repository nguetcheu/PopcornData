import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
import time
import re

# ===============================
# 📁 CONFIGURATION ET CHEMINS
# ===============================
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = RAW_DIR / "all_movies_datas.json"

all_movies = []

# ===============================
# 🎭 LISTE DES GENRES COMMUNS
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

def normalize_genres(genre_str):
    if not genre_str or genre_str == "N/A":
        return "N/A"
    normalized = set()
    for genre in genre_str.split(','):
        genre_clean = genre.strip().capitalize()
        for common, variants in COMMON_GENRES.items():
            if genre_clean in variants:
                normalized.add(common)
    return ', '.join(sorted(normalized)) if normalized else "N/A"

# ===============================
# 💰 PARSE MONEY & ROI
# ===============================
def parse_money(value_str):
    """Transforme $60,000,000.00 en int 60000000"""
    if not value_str or "N/A" in value_str or "-" in value_str:
        return 0
    digits = ''.join(c for c in value_str if c.isdigit())
    return int(digits) if digits else 0

# ===============================
# 🎬 SCRAPING TMDb
# ===============================
print("📡 Scraping TMDb...")

base_url = 'https://www.themoviedb.org/movie?page='

for page_num in range(1, 40):  # exemple: 10 pages
    print(f"📄 Scraping page {page_num}...")
    resp = requests.get(base_url + str(page_num)).text
    soup = BeautifulSoup(resp, 'lxml')
    all_div = soup.find_all('div', class_='card style_1')

    for item in all_div:
        inner_div = item.find('div', class_='content')
        if not inner_div:
            continue

        movie_name = inner_div.find('h2').text.strip() if inner_div.find('h2') else "N/A"
        release_date = inner_div.find('p').text.strip() if inner_div.find('p') else "N/A"
        inner_link = inner_div.find('a')['href']
        full_link = 'https://www.themoviedb.org' + inner_link

        # page détail
        detail_resp = requests.get(full_link).text
        detail_soup = BeautifulSoup(detail_resp, 'lxml')

        # --- Original Title ---
        original_title_tag = detail_soup.find('h2', class_='original_title')
        if original_title_tag and original_title_tag.text.strip():
            original_title = original_title_tag.text.strip()
        else:
            original_title = movie_name

        # --- Rating Numeric ---
        rating_div = detail_soup.find('div', 'user_score_chart')
        rating_numeric = float(rating_div["data-percent"]) if rating_div else "N/A"

        # --- Genres ---
        genre_spans = detail_soup.find_all('span', class_='genres')
        genres_list = []
        for g in genre_spans:
            genres_list.extend([a.text.strip() for a in g.find_all('a')])
        genres = normalize_genres(', '.join(genres_list))

        # --- Run Time ---
        run_time_tag = detail_soup.find('span', class_='runtime')
        run_time = run_time_tag.text.strip() if run_time_tag else "N/A"

        # --- Overview ---
        overview_tag = detail_soup.find('div', class_='overview')
        overview = overview_tag.find('p').text.strip() if overview_tag and overview_tag.find('p') else "N/A"

        # --- Director ---
        directors = []
        people_list = detail_soup.find('ol', class_='people no_image')
        if people_list:
            first_li = people_list.find('li', class_='profile')
            if first_li:
                a_tag = first_li.find('a')
                if a_tag:
                    directors.append(a_tag.text.strip())
        director = directors[0] if directors else "N/A"

        # --- Top Actors ---
        top_actors = []
        ol_actors = detail_soup.find('ol', class_='people scroller')
        if ol_actors:
            actor_lis = ol_actors.find_all('li', class_='card')
            for li in actor_lis[:5]:  # Top 5
                img_tag = li.find('img')
                if img_tag and img_tag.get('alt'):
                    top_actors.append(img_tag['alt'].strip())
        top_actors_str = ', '.join(top_actors) if top_actors else "N/A"

        # --- Budget & Revenue ---
        facts_section = detail_soup.find('section', class_='facts left_column')
        budget_tag = revenue_tag = None
        if facts_section:
            for p_tag in facts_section.find_all('p'):
                strong_tag = p_tag.find('strong')
                if strong_tag and 'Budget' in strong_tag.text:
                    budget_tag = p_tag
                if strong_tag and 'Recette' in strong_tag.text:
                    revenue_tag = p_tag
        budget = parse_money(budget_tag.text if budget_tag else "N/A")
        revenue = parse_money(revenue_tag.text if revenue_tag else "N/A")
        roi = round((revenue - budget) / budget, 2) if budget > 0 and revenue > 0 else None

        # --- Dictionnaire final du film ---
        movie_data = {
            "Movie_name": movie_name,
            "Original_Title": original_title,
            "Release_date": release_date,
            "Rating_Numeric": rating_numeric,
            "Genre": genres,
            "Run_time": run_time,
            "Overview": overview,
            "Director": director,
            "Top_Actors": top_actors,
            "Budget": budget,
            "Revenue": revenue,
            "ROI": roi,
            "Source": "TMDb"
        }

        all_movies.append(movie_data)
        time.sleep(0.3)

    time.sleep(1)

# ===============================
# 💾 SAUVEGARDE FINALE
# ===============================
df = pd.DataFrame(all_movies)
df.to_json(OUT_FILE, orient='records', indent=2, force_ascii=False)
print(f"✅ Total : {len(all_movies)} films sauvegardés dans : {OUT_FILE}")
