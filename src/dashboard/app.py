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

# Type de diffusion
if distribution_filter == "Cinéma uniquement":
    filtered_df = filtered_df[(filtered_df["Budget"].notna()) | (filtered_df["Revenue"].notna())]
elif distribution_filter == "Streaming uniquement":
    filtered_df = filtered_df[(filtered_df["Budget"].isna()) & (filtered_df["Revenue"].isna())]

# Autres filtres
if source_filter != "Toutes":
    filtered_df = filtered_df[filtered_df["Source"] == source_filter]
if genre_filter != "Tous":
    filtered_df = filtered_df[filtered_df["Genre"].str.contains(genre_filter, na=False)]
if decade_filter != "Toutes":
    filtered_df = filtered_df[filtered_df["Release_decade"] == decade_filter]

st.write(f"**{len(filtered_df)} films affichés** après filtrage")
# 🔹 Vérification : combien de films par réalisateur
#st.write("Nombre de films par réalisateur (top 20) :")
# st.write(filtered_df["Director"].value_counts().head(20))


# ===============================
# 🧭 Métriques principales (dynamiques)
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

# Métriques financières dynamiques
col4, col5, col6 = st.columns(3)
if "ROI" in filtered_df.columns and filtered_df["ROI"].notna().any():
    col4.metric("💰 ROI moyen", f"{filtered_df['ROI'].mean():.2f}x")
if "Is_profitable" in filtered_df.columns and filtered_df["Is_profitable"].notna().any():
    profitable_rate = filtered_df["Is_profitable"].mean() * 100
    col5.metric("📈 % Films rentables", f"{profitable_rate:.1f}%")
if "Profit" in filtered_df.columns and filtered_df["Profit"].notna().any():
    col6.metric("💵 Profit moyen", f"{filtered_df['Profit'].mean():,.0f}")

# ===============================
# 📊 KPI : Pertinence des genres sur 5 dernières années
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
    top_genre = genre_perf.index[0]
    top_genre_rating = genre_perf.iloc[0]
    worst_genre = genre_perf.index[-1]
    worst_genre_rating = genre_perf.iloc[-1]

    colA, colB = st.columns(2)
    with colA:
        st.success(f"🏆 **Genre le plus pertinent**\n🎭 {top_genre}\n⭐ {top_genre_rating:.1f}/10")
    with colB:
        st.error(f"📉 **Genre le moins pertinent**\n🎭 {worst_genre}\n⭐ {worst_genre_rating:.1f}/10")
else:
    st.info("Pas assez de données récentes pour calculer les tendances sur les 5 dernières années.")

# ===============================
# 🧾 Aperçu des données filtrées
# ===============================
with st.expander("🔍 Aperçu du jeu de données filtré"):
    st.dataframe(filtered_df.head(15), use_container_width=True, hide_index=True)

# ===============================
# ===============================
# 📊 Répartition par type de diffusion
# ===============================
st.subheader("📊 Répartition par type de diffusion")

# Création d'une colonne pour le type de diffusion
def diffusion_type(row):
    if pd.notna(row["Budget"]) or pd.notna(row["Revenue"]):
        return "Cinéma"
    else:
        return "Streaming"

filtered_df["Diffusion"] = filtered_df.apply(diffusion_type, axis=1)

diff_counts = filtered_df["Diffusion"].value_counts().reset_index()
diff_counts.columns = ["Type de diffusion", "Nombre"]

fig_diff = px.pie(
    diff_counts,
    values="Nombre",
    names="Type de diffusion",
    hole=0.4,
    color_discrete_sequence=px.colors.qualitative.Set2
)
st.plotly_chart(fig_diff, use_container_width=True)

# ===============================
# 📈 Évolution des notes dans le temps
# ===============================
st.subheader("📈 Note moyenne par année de sortie")
yearly = filtered_df.groupby("Release_year")["Rating"].mean().reset_index()
fig2 = px.line(yearly, x="Release_year", y="Rating", markers=True, labels={"Release_year":"Année","Rating":"Note moyenne (/10)"}, color_discrete_sequence=px.colors.qualitative.Bold)
fig2.update_layout(xaxis=dict(dtick=1))
st.plotly_chart(fig2, use_container_width=True)

# ===============================
# 🎭 Top 10 Genres
# ===============================
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
fig3 = px.bar(genre_ratings, x="Genre", y="Rating", color="Rating", color_continuous_scale="Blues", labels={"Rating":"Note moyenne (/10)","Genre":"Genre"})
fig3.update_xaxes(tickangle=45)
st.plotly_chart(fig3, use_container_width=True)

# ===============================
# 🏆 Top 10 Films
# ===============================
st.subheader("🏆 Top 10 Films selon le filtre")
cols_to_show = ["Movie_name","Release_year","Genre","Director","Rating","Rating_category","Source"]
cols_to_show = [c for c in cols_to_show if c in filtered_df.columns]
top_movies = filtered_df.nlargest(10, "Rating")[cols_to_show]
st.dataframe(top_movies, use_container_width=True, hide_index=True)

# ===============================
# 🎬 Réalisateurs et acteurs les plus rentables
# ===============================
st.subheader("🏆 Réalisateurs et Acteurs les plus rentables")

# 🔹 Top réalisateurs par profit moyen
if "Director" in filtered_df.columns and "Profit" in filtered_df.columns:
    director_profit = (
        filtered_df.dropna(subset=["Director", "Profit"])
        .groupby("Director")["Profit"]
        .agg(['mean', 'median', 'count'])
        .sort_values(by='mean', ascending=False)
        .head(10)
        .reset_index()
    )
    st.markdown("**🎬 Top 10 Réalisateurs par profit moyen**")
    st.dataframe(director_profit.style.format({
        'mean': '{:,.0f}',
        'median': '{:,.0f}',
        'count': '{:d}'
    }), use_container_width=True)

# 🔹 Top acteurs par profit moyen
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
    st.markdown("**⭐ Top 10 Acteurs par profit moyen**")
    st.dataframe(actor_profit.style.format({
        'mean': '{:,.0f}',
        'median': '{:,.0f}',
        'count': '{:d}'
    }), use_container_width=True)

