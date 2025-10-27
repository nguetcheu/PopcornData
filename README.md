# 🎬 PopcornData Pipeline (Projet LDF)

Ce projet illustre un pipeline complet de collecte, nettoyage et visualisation des données de films à partir de IMDB + TMDB.

## Étapes du pipeline
1. **Scraping** : Extraction des films TMDB avec `requests` + `BeautifulSoup`
2. **Nettoyage** : Transformation et export CSV
3. **Automatisation CI/CD** : Mise à jour automatique chaque semaine via GitHub Actions
4. **Visualisation** : Tableau de bord interactif avec Streamlit

## Utilisation locale
```bash
pip install -r requirements.txt
python src/scraper/scrape_movie.py
python src/cleaning/clean_movie.py
streamlit run src/dashboard/app.py
```
