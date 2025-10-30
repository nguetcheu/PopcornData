import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ===============================
# ⚙️ Configuration de la page
# ===============================
st.set_page_config(page_title="🎬 PopcornData", layout="wide")
st.title("🎬 PopcornData")

# ===============================
# 📁 Chargement des données
# ===============================
DATA_PATH = Path("data") / "movies_clean.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    df = df.drop_duplicates(subset=["Movie_name", "Source"])
    df = df[df["Rating"].notna()]
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    df["Release_year"] = pd.to_numeric(df["Release_year"], errors="coerce")
    df = df.dropna(subset=["Release_year"])
    df["Release_year"] = df["Release_year"].astype(int)
    df["Genre"] = df["Genre"].fillna("Autre")

    for col in ["ROI", "Profit", "Budget", "Revenue"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    
    return df

df = load_data()

# ===============================
# 📦 Sidebar structurée
# ===============================
st.sidebar.title("🎛️ Panneau de configuration")
st.sidebar.markdown("Filtrez et explorez les films selon vos préférences.")

max_films = len(df)
nb_films = st.sidebar.slider(
    "🎬 Nombre de films à charger :",
    min_value=50,
    max_value=max_films,
    step=50,
    value=min(500, max_films)
)
df = df.head(nb_films)

# Initialiser un compteur de réinitialisation
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

if st.sidebar.button("♻️ Réinitialiser les filtres"):
    st.session_state.reset_counter += 1  # Incrémenter pour forcer la réinitialisation
    st.rerun()

st.sidebar.divider()

st.sidebar.subheader("🔎 Rechercher un film")
search_query = st.sidebar.text_input(
    "Nom du film (ex : Inception) :",
    key=f"search_input_{st.session_state.reset_counter}"  # Clé dynamique
)

if search_query:
    df = df[df["Movie_name"].str.contains(search_query, case=False, na=False)]
    st.sidebar.success(f"{len(df)} film(s) trouvé(s) correspondant à '{search_query}'")

# ===============================
# 🎭 Filtres dynamiques
# ===============================
col1, col2, col3 = st.columns(3)
with col1:
    all_genres = sorted({g.strip() for sublist in df["Genre"].dropna().str.split(',') for g in sublist})
    genre_filter = st.selectbox("🎭 Genre :", ["Tous"] + all_genres)
with col2:
    source_filter = st.selectbox("📊 Source :", ["Toutes"] + sorted(df["Source"].unique()))
with col3:
    if "Release_decade" in df.columns:
        decade_filter = st.selectbox("🕰️ Décennie :", ["Toutes"] + sorted(df["Release_decade"].dropna().unique().tolist()))
    else:
        decade_filter = "Toutes"

distribution_filter = st.radio(
    "🎞️ Type de diffusion",
    ["Tous", "Cinéma uniquement", "Streaming uniquement"],
    horizontal=True
)

# ===============================
# 🔍 Application des filtres
# ===============================
filtered_df = df.copy()

if distribution_filter == "Cinéma uniquement":
    filtered_df = filtered_df[(filtered_df["Budget"].notna()) | (filtered_df["Revenue"].notna())]
elif distribution_filter == "Streaming uniquement":
    filtered_df = filtered_df[(filtered_df["Budget"].isna()) & (filtered_df["Revenue"].isna())]

if source_filter != "Toutes":
    filtered_df = filtered_df[filtered_df["Source"] == source_filter]
if genre_filter != "Tous":
    filtered_df = filtered_df[filtered_df["Genre"].str.contains(genre_filter, na=False)]
if decade_filter != "Toutes":
    filtered_df = filtered_df[filtered_df["Release_decade"] == decade_filter]

st.write(f"**{len(filtered_df)} films affichés** après filtrage")

# ===============================
# 🧭 Métriques principales
# ===============================
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("🎞️ Total Films", len(filtered_df))
with col2:
    st.metric("⭐ Note moyenne", f"{filtered_df['Rating'].mean():.1f}/10" if len(filtered_df)>0 else "N/A")
with col3:
    if len(filtered_df) > 0:
        st.metric("📆 Période", f"{filtered_df['Release_year'].min()} - {filtered_df['Release_year'].max()}")
    else:
        st.metric("📆 Période", "N/A")

col4, col5, col6 = st.columns(3)
if "ROI" in filtered_df.columns and filtered_df["ROI"].notna().any():
    col4.metric("💰 ROI moyen", f"{filtered_df['ROI'].mean():.2f}x")
if "Is_profitable" in filtered_df.columns and filtered_df["Is_profitable"].notna().any():
    profitable_rate = filtered_df["Is_profitable"].mean() * 100
    col5.metric("📈 % Films rentables", f"{profitable_rate:.1f}%")
if "Profit" in filtered_df.columns and filtered_df["Profit"].notna().any():
    col6.metric("💵 Profit moyen", f"{filtered_df['Profit'].mean():,.0f}")

# ===============================
# 📊 KPI : Pertinence des genres
# ===============================
st.subheader("📈 Pertinence des genres sur les 5 dernières années")
kpi_df = filtered_df.copy()
recent_years = kpi_df[kpi_df["Release_year"] >= kpi_df["Release_year"].max() - 5]

if not recent_years.empty:
    genre_perf = (
        recent_years.assign(Genre=recent_years["Genre"].str.split(",")) 
        .explode("Genre")
        .groupby("Genre")["Rating"]
        .mean()
        .sort_values(ascending=False)
    )
    colA, colB = st.columns(2)
    with colA:
        st.success(f"🏆 **Genre le plus pertinent : {genre_perf.index[0]} ({genre_perf.iloc[0]:.1f}/10)**")
    with colB:
        st.error(f"📉 **Genre le moins pertinent : {genre_perf.index[-1]} ({genre_perf.iloc[-1]:.1f}/10)**")
else:
    st.info("Pas assez de données récentes pour calculer les tendances.")

# ===============================
# 🎯 Recommandation de films similaires
# ===============================
st.subheader("🎯 Recommandation de films similaires")

if not filtered_df.empty:
    selected_movie = st.selectbox("Choisissez un film :", filtered_df["Movie_name"].unique())
    
    def recommend_movies(title, df, n=5):
        try:
            genres = df[df['Movie_name'] == title]['Genre'].iloc[0].split(',')
            mask = df['Genre'].apply(lambda g: any(genre.strip() in g for genre in genres))
            recos = df[mask & (df["Movie_name"] != title)].sort_values(by="Rating", ascending=False).head(n)
            return recos[["Movie_name", "Genre", "Rating", "Release_year"]]
        except Exception:
            return pd.DataFrame()
    
    recos = recommend_movies(selected_movie, df)
    if not recos.empty:
        st.dataframe(recos, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune recommandation disponible pour ce film.")

# ===============================
# 🧾 Aperçu des données
# ===============================
with st.expander("🔍 Aperçu du jeu de données filtré"):
    st.dataframe(filtered_df.head(15), use_container_width=True, hide_index=True)

# ===============================
# 🎯 Affichage conditionnel
# ===============================
if len(filtered_df) == 0:
    st.warning("🔍 Aucun film ne correspond à votre recherche. Veuillez modifier vos critères de filtrage.")

elif len(filtered_df) == 1:
    st.info("🔍 Un seul film trouvé : affichage détaillé.")

    film = filtered_df.iloc[0]

    # --- Affichage du poster et des infos principales ---
    col1, col2 = st.columns([1, 3])
    with col1:
        if pd.notna(film.get("Poster_URL")) and film["Poster_URL"] != "N/A":
            st.image(film["Poster_URL"], width=250)
        else:
            st.image("https://via.placeholder.com/250x350?text=No+Image", width=250)

    with col2:
        st.markdown(f"### 🎬 {film['Movie_name']} ({film['Release_year']})")
        st.markdown(f"🎭 **Genre :** {film['Genre']}")
        st.markdown(f"⭐ **Note :** {film['Rating']} / 10")
        st.markdown(f"🎬 **Réalisateur :** {film['Director']}")
        st.markdown(f"👥 **Acteurs :** {film['Top_Actors']}")
        st.markdown(f"🕒 **Durée :** {film.get('Runtime_minutes', 'N/A')} min")
        st.markdown(f"💰 **Budget :** {film.get('Budget', 'N/A'):,}" if pd.notna(film.get("Budget")) else "💰 **Budget : N/A**")
        st.markdown(f"💵 **Revenus :** {film.get('Revenue', 'N/A'):,}" if pd.notna(film.get("Revenue")) else "💵 **Revenus : N/A**")

    st.divider()

else:  # len(filtered_df) > 1
    # --- Graphiques & stats ---
    st.subheader("📊 Répartition par type de diffusion")

    def diffusion_type(row):
        return "Cinéma" if pd.notna(row["Budget"]) or pd.notna(row["Revenue"]) else "Streaming"

    filtered_df["Diffusion"] = filtered_df.apply(diffusion_type, axis=1)
    diff_counts = filtered_df["Diffusion"].value_counts().reset_index()
    diff_counts.columns = ["Type de diffusion", "Nombre"]

    fig_diff = px.pie(diff_counts, values="Nombre", names="Type de diffusion", hole=0.4)
    st.plotly_chart(fig_diff, use_container_width=True)

    st.subheader("📈 Note moyenne par année de sortie")
    yearly = filtered_df.groupby("Release_year")["Rating"].mean().reset_index()
    fig2 = px.line(yearly, x="Release_year", y="Rating", markers=True)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("🎭 Top 10 Genres (note moyenne)")
    genre_ratings = (
        filtered_df.assign(Genre=filtered_df["Genre"].str.split(","))
        .explode("Genre")
        .groupby("Genre")["Rating"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    st.plotly_chart(px.bar(genre_ratings, x="Genre", y="Rating", color="Rating"), use_container_width=True)

    # Remplacez la section "TOP 10 FILMS AVEC IMAGES" par :

    # --- TOP 10 FILMS AVEC IMAGES ---
    st.subheader("🏆 Top 10 Films selon le filtre")
    cols_to_show = ["Poster_URL", "Movie_name", "Release_year", "Genre", "Director", "Rating", "Overview"]
    top_movies = filtered_df.nlargest(10, "Rating")[cols_to_show]

    for _, row in top_movies.iterrows():
        col1, col2 = st.columns([1, 5])  # Augmenté de [1, 4] à [1, 5] pour plus d'espace texte
        with col1:
            if pd.notna(row["Poster_URL"]) and row["Poster_URL"] != "N/A":
                st.image(row["Poster_URL"], width=120)  # Augmenté de 110 à 120
            else:
                st.image("https://via.placeholder.com/100x150?text=No+Image", width=120)
        with col2:
            st.markdown(f"**{row['Movie_name']}** ({row['Release_year']})")
            st.markdown(f"🎭 *{row['Genre']}*")
            st.markdown(f"⭐ **{row['Rating']} / 10**")
            st.markdown(f"🎬 Réalisateur : *{row['Director']}*")
            
            # Ajout de la description si elle existe
            if pd.notna(row.get("Overview")) and row["Overview"] != "N/A":
                description = row["Overview"]
                # Limiter la longueur si trop longue
                if len(description) > 200:
                    description = description[:200] + "..."
                st.markdown(f"📝 {description}")
        
        st.divider()

# ===============================
# 🎬 Réalisateurs et Acteurs les plus rentables
# ===============================
if len(filtered_df) > 0:
    st.subheader("🏆 Réalisateurs et Acteurs les plus rentables")

    if "Director" in filtered_df.columns and "Profit" in filtered_df.columns:
        director_profit = (
            filtered_df.dropna(subset=["Director", "Profit"])
            .groupby("Director")["Profit"]
            .agg(['mean', 'median', 'count'])
            .sort_values(by='mean', ascending=False)
            .head(10)
            .reset_index()
        )
        if not director_profit.empty:
            st.markdown("**🎬 Top 10 Réalisateurs par profit moyen**")
            st.dataframe(director_profit.style.format({'mean': '{:,.0f}', 'median': '{:,.0f}', 'count': '{:d}'}), use_container_width=True)

    if "Top_Actors" in filtered_df.columns and "Profit" in filtered_df.columns:
        actors_df = (
            filtered_df.dropna(subset=["Top_Actors", "Profit"])
            .assign(Actor=filtered_df["Top_Actors"].str.split(","))
            .explode("Actor")
        )
        actors_df["Actor"] = actors_df["Actor"].str.strip()
        actor_profit = (
            actors_df.groupby("Actor")["Profit"]
            .agg(['mean', 'median', 'count'])
            .sort_values(by='mean', ascending=False)
            .head(10)
            .reset_index()
        )
        if not actor_profit.empty:
            st.markdown("**⭐ Top 10 Acteurs par profit moyen**")
            st.dataframe(actor_profit.style.format({'mean': '{:,.0f}', 'median': '{:,.0f}', 'count': '{:d}'}), use_container_width=True)