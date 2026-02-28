"""
app.py
------
Interface web Streamlit pour le Game Price Tracker.

Lance avec :
    streamlit run app.py

Fonctionnalites :
- Bouton pour lancer le scraping DLCompare
- Bouton pour lancer le scraping GoCleCD (comparaison croisee)
- Bouton pour calculer le Hype Score
- Affichage des statistiques en temps reel
- Affichage des graphiques generes
- Telechargement des resultats en CSV
"""

import streamlit as st
import pandas as pd
import os
import time
import json
from datetime import datetime

# Import des modules du projet
from scrapers.dlcompare_scraper import DLCompareScraper
from scrapers.goclecd_scraper import GoclecdScraper
from models.game import GameCollection
from analysis.price_analyzer import PriceAnalyzer

# ==================================================================
# CONFIGURATION DE LA PAGE
# ==================================================================

st.set_page_config(
    page_title="Game Price Tracker",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS custom
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #0891B2;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #94A3B8;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 1.2rem;
        border-radius: 12px;
        text-align: center;
        color: white;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #22D3EE;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94A3B8;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ==================================================================
# FONCTIONS UTILITAIRES
# ==================================================================

def collection_to_dataframe(collection: GameCollection) -> pd.DataFrame:
    """Convertit une GameCollection en DataFrame."""
    data = []
    for game in collection.games:
        data.append({
            'Jeu': game.name,
            'Meilleur Prix (€)': game.best_price,
            'Pire Prix (€)': game.worst_price,
            'Ecart (€)': game.price_spread,
            'Nb Offres': game.nb_offers,
            'Vendeur': game.best_offer.store_name if game.best_offer else '',
            'Plateformes': ', '.join(game.platforms),
            'Source': game.source,
        })
    df = pd.DataFrame(data)
    for col in ['Meilleur Prix (€)', 'Pire Prix (€)', 'Ecart (€)']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def export_csv(collection: GameCollection, prefix: str) -> str:
    """Exporte une collection en CSV et retourne le chemin."""
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"data/{prefix}_{timestamp}.csv"
    df = collection_to_dataframe(collection)
    df.to_csv(filepath, index=False, encoding='utf-8')
    return filepath


# ==================================================================
# INITIALISATION SESSION STATE
# ==================================================================

if 'dlcompare_collection' not in st.session_state:
    st.session_state.dlcompare_collection = None
if 'goclecd_collection' not in st.session_state:
    st.session_state.goclecd_collection = None
if 'scraping_done' not in st.session_state:
    st.session_state.scraping_done = False


# ==================================================================
# SIDEBAR
# ==================================================================

with st.sidebar:
    st.markdown("## 🎮 Game Price Tracker")
    st.markdown("---")

    st.markdown("### ⚙️ Configuration")
    max_games = st.slider("Nombre de jeux à scraper", 5, 50, 30, step=5)
    max_goclecd = st.slider("Jeux pour GoCleCD", 5, 20, 15, step=5)

    st.markdown("---")
    st.markdown("### 🚀 Lancer le scraping")

    # Bouton DLCompare
    if st.button("🔍 Scraper DLCompare", type="primary", use_container_width=True):
        with st.spinner("Scraping DLCompare.fr en cours... (2-4 min)"):
            try:
                with DLCompareScraper(headless=True) as scraper:
                    collection = scraper.scrape_all(max_games=max_games)
                st.session_state.dlcompare_collection = collection
                st.session_state.scraping_done = True
                export_csv(collection, "dlcompare")
                st.success(f"✅ {collection.nb_games} jeux récupérés !")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")

    # Bouton GoCleCD
    if st.button("🔍 Scraper GoCleCD", use_container_width=True):
        if st.session_state.dlcompare_collection is None:
            st.warning("⚠️ Lance d'abord le scraping DLCompare.")
        else:
            game_names = [
                g.name for g in st.session_state.dlcompare_collection.games[:max_goclecd]
            ]
            with st.spinner(f"Scraping GoCleCD.fr ({len(game_names)} jeux)... (5-8 min)"):
                try:
                    with GoclecdScraper(headless=True) as scraper:
                        collection = scraper.scrape_games(game_names)
                    st.session_state.goclecd_collection = collection
                    export_csv(collection, "goclecd")
                    st.success(f"✅ {collection.nb_games} jeux récupérés !")
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

    # Bouton Hype Score
    if st.button("📈 Calculer Hype Score", use_container_width=True):
        if st.session_state.dlcompare_collection is None:
            st.warning("⚠️ Lance d'abord le scraping DLCompare.")
        else:
            with st.spinner("Calcul du Hype Score via Google Trends..."):
                try:
                    from scrapers.trend_scraper import TrendScraper
                    trend = TrendScraper()
                    names = [g.name for g in st.session_state.dlcompare_collection.games[:10]]
                    reports = trend.compute_batch(names)
                    st.session_state.hype_reports = reports
                    st.success("✅ Hype Score calculé !")
                except Exception as e:
                    st.error(f"❌ Erreur : {e}")

    st.markdown("---")
    st.markdown("### 📊 Générer l'analyse")

    if st.button("📊 Générer les graphiques", use_container_width=True):
        if st.session_state.dlcompare_collection is None:
            st.warning("⚠️ Lance d'abord le scraping.")
        else:
            with st.spinner("Génération des graphiques..."):
                analyzer = PriceAnalyzer(output_dir="data")
                analyzer.load_from_collection(st.session_state.dlcompare_collection)
                if st.session_state.goclecd_collection:
                    analyzer.load_from_collection(st.session_state.goclecd_collection)
                analyzer.generate_full_report()
                st.session_state.analysis_done = True
                st.success("✅ Rapport complet généré !")

    st.markdown("---")
    st.markdown(
        "<small>M1 APE-DS2E — Web Scraping & Data Science<br>"
        "Université de Strasbourg</small>",
        unsafe_allow_html=True
    )


# ==================================================================
# CONTENU PRINCIPAL
# ==================================================================

st.markdown('<div class="main-title">🎮 Game Price Tracker</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Comparaison automatique des prix de jeux vidéo — '
    'DLCompare.fr & GoCleCD.fr</div>',
    unsafe_allow_html=True
)

# --- Métriques en haut ---
if st.session_state.dlcompare_collection:
    dlc = st.session_state.dlcompare_collection
    df_dlc = collection_to_dataframe(dlc)

    gc = st.session_state.goclecd_collection
    nb_gc = gc.nb_games if gc else 0

    total_games = len(df_dlc) + nb_gc
    avg_price = df_dlc['Meilleur Prix (€)'].mean()
    min_price = df_dlc['Meilleur Prix (€)'].min()
    max_price = df_dlc['Meilleur Prix (€)'].max()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("🎮 Jeux DLCompare", dlc.nb_games)
    with col2:
        st.metric("🎮 Jeux GoCleCD", nb_gc)
    with col3:
        st.metric("💰 Prix moyen", f"{avg_price:.2f}€")
    with col4:
        st.metric("📉 Prix min", f"{min_price:.2f}€")
    with col5:
        st.metric("📈 Prix max", f"{max_price:.2f}€")

    st.markdown("---")

    # --- Onglets ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Données", "📊 Graphiques", "🏆 Classements", "📥 Export"
    ])

    # TAB 1 : Données brutes
    with tab1:
        st.markdown("### Données DLCompare")
        st.dataframe(
            df_dlc.style.format({
                'Meilleur Prix (€)': '{:.2f}',
                'Pire Prix (€)': '{:.2f}',
                'Ecart (€)': '{:.2f}',
            }).background_gradient(subset=['Meilleur Prix (€)'], cmap='RdYlGn_r'),
            use_container_width=True,
            height=400
        )

        if gc and gc.nb_games > 0:
            st.markdown("### Données GoCleCD")
            df_gc = collection_to_dataframe(gc)
            st.dataframe(
                df_gc.style.format({
                    'Meilleur Prix (€)': '{:.2f}',
                    'Pire Prix (€)': '{:.2f}',
                    'Ecart (€)': '{:.2f}',
                }).background_gradient(subset=['Meilleur Prix (€)'], cmap='RdYlGn_r'),
                use_container_width=True,
                height=300
            )

    # TAB 2 : Graphiques
    with tab2:
        st.markdown("### Visualisations")

        # Graphiques Streamlit natifs
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### Distribution des prix")
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import seaborn as sns

            fig1, ax1 = plt.subplots(figsize=(8, 5))
            prices = df_dlc['Meilleur Prix (€)'].dropna()
            sns.histplot(prices, bins=20, kde=True, ax=ax1, color='#0891B2')
            ax1.axvline(prices.mean(), color='red', linestyle='--',
                        label=f'Moyenne: {prices.mean():.2f}€')
            ax1.axvline(prices.median(), color='green', linestyle='--',
                        label=f'Médiane: {prices.median():.2f}€')
            ax1.set_xlabel('Prix (€)')
            ax1.set_ylabel('Nombre de jeux')
            ax1.legend()
            st.pyplot(fig1)
            plt.close()

        with col_b:
            st.markdown("#### Top 10 jeux les moins chers")
            top10 = df_dlc.nsmallest(10, 'Meilleur Prix (€)')
            fig2, ax2 = plt.subplots(figsize=(8, 5))
            colors = sns.color_palette('viridis', n_colors=len(top10))
            bars = ax2.barh(top10['Jeu'], top10['Meilleur Prix (€)'], color=colors)
            ax2.invert_yaxis()
            ax2.set_xlabel('Prix (€)')
            for bar, price in zip(bars, top10['Meilleur Prix (€)']):
                ax2.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                        f'{price:.2f}€', va='center', fontsize=9)
            st.pyplot(fig2)
            plt.close()

        col_c, col_d = st.columns(2)

        with col_c:
            st.markdown("#### Classement des vendeurs")
            vendors = df_dlc['Vendeur'].value_counts().head(10)
            fig3, ax3 = plt.subplots(figsize=(8, 5))
            sns.barplot(x=vendors.values, y=vendors.index, ax=ax3,
                        hue=vendors.index, palette='coolwarm', legend=False)
            ax3.set_xlabel('Nombre de fois le moins cher')
            ax3.set_ylabel('Vendeur')
            st.pyplot(fig3)
            plt.close()

        with col_d:
            if gc and gc.nb_games > 0:
                st.markdown("#### Comparaison DLCompare vs GoCleCD")
                df_gc = collection_to_dataframe(gc)
                df_all = pd.concat([df_dlc, df_gc], ignore_index=True)
                fig4, ax4 = plt.subplots(figsize=(8, 5))
                sns.boxplot(data=df_all, x='Source', y='Meilleur Prix (€)',
                            hue='Source', palette='Set1', legend=False, ax=ax4)
                ax4.set_ylabel('Prix (€)')
                st.pyplot(fig4)
                plt.close()
            else:
                st.info("Lance le scraping GoCleCD pour voir la comparaison.")

        # Graphiques PNG déjà générés
        st.markdown("---")
        st.markdown("### Graphiques PNG générés")
        png_files = [f for f in os.listdir("data") if f.endswith(".png")] if os.path.exists("data") else []
        if png_files:
            cols = st.columns(3)
            for i, png in enumerate(sorted(png_files)):
                with cols[i % 3]:
                    st.image(f"data/{png}", caption=png, use_container_width=True)
        else:
            st.info("Clique sur 'Générer les graphiques' dans la sidebar pour créer les PNG.")

    # TAB 3 : Classements
    with tab3:
        col_e, col_f = st.columns(2)

        with col_e:
            st.markdown("### 🏆 Top 15 — Jeux les moins chers")
            top15 = df_dlc.nsmallest(15, 'Meilleur Prix (€)')[
                ['Jeu', 'Meilleur Prix (€)', 'Vendeur', 'Source']
            ]
            st.dataframe(top15, use_container_width=True, hide_index=True)

        with col_f:
            st.markdown("### 📊 Vendeurs les plus compétitifs")
            vendor_counts = df_dlc['Vendeur'].value_counts().reset_index()
            vendor_counts.columns = ['Vendeur', 'Nb fois moins cher']
            st.dataframe(vendor_counts, use_container_width=True, hide_index=True)

        # Hype Score si disponible
        if 'hype_reports' in st.session_state and st.session_state.hype_reports:
            st.markdown("### 🔥 Hype Score (Google Trends)")
            hype_data = []
            for report in st.session_state.hype_reports:
                hype_data.append({
                    'Jeu': report.game_name,
                    'Hype Score': report.hype_score,
                    'Intérêt actuel': report.current_interest,
                    'Tendance': report.trend_direction,
                })
            df_hype = pd.DataFrame(hype_data).sort_values('Hype Score', ascending=False)
            st.dataframe(df_hype, use_container_width=True, hide_index=True)

    # TAB 4 : Export
    with tab4:
        st.markdown("### 📥 Télécharger les résultats")

        csv_data = df_dlc.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇️ Télécharger DLCompare (CSV)",
            csv_data,
            "dlcompare_resultats.csv",
            "text/csv",
            use_container_width=True
        )

        if gc and gc.nb_games > 0:
            df_gc = collection_to_dataframe(gc)
            csv_gc = df_gc.to_csv(index=False).encode('utf-8')
            st.download_button(
                "⬇️ Télécharger GoCleCD (CSV)",
                csv_gc,
                "goclecd_resultats.csv",
                "text/csv",
                use_container_width=True
            )

        # Rapport complet
        if gc and gc.nb_games > 0:
            df_all = pd.concat([df_dlc, collection_to_dataframe(gc)], ignore_index=True)
        else:
            df_all = df_dlc
        csv_all = df_all.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇️ Télécharger rapport complet (CSV)",
            csv_all,
            "rapport_complet.csv",
            "text/csv",
            use_container_width=True
        )

else:
    # Page d'accueil si pas encore de données
    st.markdown("---")

    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        st.markdown("""
        ### 👋 Bienvenue !

        Cet outil compare automatiquement les prix de jeux vidéo
        entre **DLCompare.fr** et **GoCleCD.fr**.

        **Pour commencer :**
        1. Clique sur **🔍 Scraper DLCompare** dans la barre latérale
        2. Attends que le scraping se termine (~3 min)
        3. Explore les résultats dans les onglets

        **Options avancées :**
        - Scraper GoCleCD pour la comparaison croisée
        - Calculer le Hype Score via Google Trends
        - Générer les 7 graphiques PNG
        - Exporter les données en CSV
        """)

    st.markdown("---")
    st.markdown(
        "<center><small>Game Price Tracker — M1 APE-DS2E — "
        "Web Scraping & Data Science — Université de Strasbourg</small></center>",
        unsafe_allow_html=True
    )
