"""
analysis/price_analyzer.py
--------------------------
Module d'analyse des prix de jeux video.
Utilise pandas pour la manipulation de donnees et matplotlib/seaborn pour les visualisations.

Analyses disponibles :
- Statistiques descriptives (moyenne, mediane, ecart-type des prix)
- Distribution des prix par plateforme
- Classement des vendeurs les moins chers
- Ecarts de prix (spread) entre vendeurs
- Comparaison entre sites (DLCompare vs GoCleCD)
- Top des meilleurs deals
- Visualisations graphiques exportees en PNG
"""

import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif (headless)
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Optional

from models.game import GameCollection, Game


class PriceAnalyzer:
    """
    Analyseur de prix de jeux video.

    Transforme une ou plusieurs GameCollection en DataFrames pandas,
    puis genere des statistiques et des visualisations.

    Attributs :
        df_games  : DataFrame avec un jeu par ligne
        df_offers : DataFrame avec une offre par ligne
        output_dir: Dossier de sortie pour les graphiques
    """

    def __init__(self, output_dir: str = "data"):
        self.df_games = pd.DataFrame()
        self.df_offers = pd.DataFrame()
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        sns.set_theme(style="whitegrid", palette="muted")
        plt.rcParams.update({
            'figure.figsize': (12, 7),
            'font.size': 11,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
        })

    def load_from_collection(self, collection: GameCollection):
        """Charge les donnees depuis une GameCollection."""
        games_data = []
        offers_data = []

        for game in collection.games:
            games_data.append({
                'nom': game.name,
                'date_sortie': game.release_date,
                'plateformes': ', '.join(game.platforms),
                'nb_plateformes': len(game.platforms),
                'meilleur_prix': game.best_price,
                'pire_prix': game.worst_price,
                'ecart_prix': game.price_spread,
                'nb_offres': game.nb_offers,
                'meilleur_vendeur': game.best_offer.store_name if game.best_offer else '',
                'source': game.source,
                'url': game.url,
            })

            for offer in game.offers:
                offers_data.append({
                    'jeu': game.name,
                    'vendeur': offer.store_name,
                    'prix': offer.price,
                    'plateforme': offer.platform,
                    'edition': offer.edition,
                    'officiel': offer.is_official,
                    'source': game.source,
                })

        new_games = pd.DataFrame(games_data)
        new_offers = pd.DataFrame(offers_data)

        # Convertir les colonnes numeriques (evite les erreurs dtype)
        for col in ['meilleur_prix', 'pire_prix', 'ecart_prix']:
            if col in new_games.columns:
                new_games[col] = pd.to_numeric(new_games[col], errors='coerce')
        if 'nb_offres' in new_games.columns:
            new_games['nb_offres'] = pd.to_numeric(new_games['nb_offres'], errors='coerce').fillna(0).astype(int)

        # Concatener avec les donnees existantes (multi-sources)
        if not self.df_games.empty:
            self.df_games = pd.concat([self.df_games, new_games], ignore_index=True)
        else:
            self.df_games = new_games

        if not self.df_offers.empty:
            self.df_offers = pd.concat([self.df_offers, new_offers], ignore_index=True)
        else:
            self.df_offers = new_offers

        print(f"[Analyzer] {len(new_games)} jeux et {len(new_offers)} offres chargees depuis {collection.source}.")

    def load_from_csv(self, filepath: str):
        """Charge les donnees depuis un fichier CSV."""
        self.df_games = pd.read_csv(filepath)
        for col in ['meilleur_prix', 'pire_prix', 'ecart_prix']:
            if col in self.df_games.columns:
                self.df_games[col] = pd.to_numeric(self.df_games[col], errors='coerce')
        print(f"[Analyzer] {len(self.df_games)} jeux charges depuis {filepath}.")

    # =====================================================================
    # STATISTIQUES
    # =====================================================================

    def summary_stats(self) -> pd.DataFrame:
        """Statistiques descriptives des prix."""
        if self.df_games.empty:
            print("[Analyzer] Aucune donnee chargee.")
            return pd.DataFrame()

        price_data = self.df_games['meilleur_prix'].dropna()
        if price_data.empty:
            print("[Analyzer] Aucun prix disponible.")
            return pd.DataFrame()

        stats = price_data.describe()
        print("\n" + "=" * 50)
        print("  STATISTIQUES DESCRIPTIVES DES PRIX")
        print("=" * 50)
        print(f"  Nombre de jeux     : {stats['count']:.0f}")
        print(f"  Prix moyen         : {stats['mean']:.2f} EUR")
        print(f"  Ecart-type         : {stats['std']:.2f} EUR")
        print(f"  Prix minimum       : {stats['min']:.2f} EUR")
        print(f"  Mediane (Q2)       : {stats['50%']:.2f} EUR")
        print(f"  Prix maximum       : {stats['max']:.2f} EUR")
        print(f"  1er quartile (Q1)  : {stats['25%']:.2f} EUR")
        print(f"  3eme quartile (Q3) : {stats['75%']:.2f} EUR")
        print("=" * 50)
        return stats

    def top_cheapest(self, n: int = 10) -> pd.DataFrame:
        """Retourne les N jeux les moins chers."""
        df = self.df_games.dropna(subset=['meilleur_prix'])
        return df.nsmallest(n, 'meilleur_prix')[['nom', 'meilleur_prix', 'meilleur_vendeur', 'source']]

    def top_deals(self, n: int = 10) -> pd.DataFrame:
        """Retourne les N jeux avec le plus grand ecart de prix."""
        df = self.df_games.dropna(subset=['ecart_prix']).copy()
        if df.empty:
            return df
        df['ecart_prix'] = pd.to_numeric(df['ecart_prix'], errors='coerce')
        df = df.dropna(subset=['ecart_prix'])
        return df.nlargest(n, 'ecart_prix')[['nom', 'meilleur_prix', 'pire_prix', 'ecart_prix', 'nb_offres']]

    def top_vendors(self, n: int = 10) -> pd.DataFrame:
        """Vendeurs les plus souvent les moins chers."""
        if self.df_games.empty:
            return pd.DataFrame()
        counts = self.df_games['meilleur_vendeur'].value_counts().head(n)
        return counts.reset_index().rename(
            columns={'meilleur_vendeur': 'vendeur', 'count': 'nb_fois_moins_cher'}
        )

    def price_by_platform(self) -> pd.DataFrame:
        """Prix moyen par plateforme."""
        if self.df_offers.empty:
            return pd.DataFrame()
        return self.df_offers.groupby('plateforme')['prix'].agg(
            ['mean', 'median', 'min', 'max', 'count']
        ).round(2).sort_values('mean')

    def compare_sources(self) -> pd.DataFrame:
        """Compare les prix moyens entre DLCompare et GoCleCD."""
        if self.df_games.empty or self.df_games['source'].nunique() < 2:
            print("[Analyzer] Comparaison impossible : il faut au moins 2 sources.")
            return pd.DataFrame()

        comparison = self.df_games.groupby('source')['meilleur_prix'].agg(
            ['mean', 'median', 'min', 'max', 'count']
        ).round(2)
        print("\n" + "=" * 50)
        print("  COMPARAISON DES SOURCES")
        print("=" * 50)
        print(comparison.to_string())
        print("=" * 50)
        return comparison

    # =====================================================================
    # VISUALISATIONS
    # =====================================================================

    def _save_plot(self, filename: str):
        """Sauvegarde le graphique courant."""
        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"[Analyzer] Graphique sauvegarde : {filepath}")

    def plot_price_distribution(self):
        """Histogramme de la distribution des prix."""
        df = self.df_games.dropna(subset=['meilleur_prix'])
        if df.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 7))
        sns.histplot(data=df, x='meilleur_prix', bins=25, kde=True, ax=ax, color='#2196F3')
        ax.set_title('Distribution des prix des jeux video')
        ax.set_xlabel('Prix (EUR)')
        ax.set_ylabel('Nombre de jeux')

        mean_price = df['meilleur_prix'].mean()
        median_price = df['meilleur_prix'].median()
        ax.axvline(mean_price, color='red', linestyle='--', label=f'Moyenne : {mean_price:.2f} EUR')
        ax.axvline(median_price, color='green', linestyle='--', label=f'Mediane : {median_price:.2f} EUR')
        ax.legend()
        self._save_plot('distribution_prix.png')

    def plot_top_cheapest(self, n: int = 15):
        """Barplot horizontal des jeux les moins chers."""
        top = self.top_cheapest(n)
        if top.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 8))
        colors = sns.color_palette('viridis', n_colors=len(top))
        bars = ax.barh(top['nom'], top['meilleur_prix'], color=colors)
        ax.set_title(f'Top {n} des jeux les moins chers')
        ax.set_xlabel('Prix (EUR)')
        ax.invert_yaxis()

        for bar, price in zip(bars, top['meilleur_prix']):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                    f'{price:.2f} EUR', va='center', fontsize=9)
        self._save_plot('top_moins_chers.png')

    def plot_top_deals(self, n: int = 10):
        """Barplot des jeux avec le plus grand ecart de prix."""
        deals = self.top_deals(n)
        if deals.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 8))
        y_pos = range(len(deals))
        bar_height = 0.35

        ax.barh([y - bar_height/2 for y in y_pos], deals['meilleur_prix'],
                bar_height, label='Meilleur prix', color='#4CAF50')
        ax.barh([y + bar_height/2 for y in y_pos], deals['pire_prix'],
                bar_height, label='Prix le plus eleve', color='#F44336', alpha=0.7)

        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(deals['nom'])
        ax.set_xlabel('Prix (EUR)')
        ax.set_title(f'Top {n} des plus grands ecarts de prix')
        ax.legend()
        ax.invert_yaxis()
        self._save_plot('top_deals_ecarts.png')

    def plot_vendor_ranking(self, n: int = 10):
        """Barplot du nombre de fois ou chaque vendeur est le moins cher."""
        vendors = self.top_vendors(n)
        if vendors.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 7))
        sns.barplot(data=vendors, x='nb_fois_moins_cher', y='vendeur',
                    ax=ax, hue='vendeur', palette='coolwarm', legend=False)
        ax.set_title(f'Top {n} des vendeurs les plus competitifs')
        ax.set_xlabel('Nombre de fois le moins cher')
        ax.set_ylabel('Vendeur')
        self._save_plot('classement_vendeurs.png')

    def plot_price_by_platform(self):
        """Boxplot des prix par plateforme."""
        if self.df_offers.empty:
            return

        df = self.df_offers[self.df_offers['plateforme'] != '']
        if df.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 7))
        sns.boxplot(data=df, x='plateforme', y='prix', ax=ax,
                    hue='plateforme', palette='Set2', legend=False)
        ax.set_title('Distribution des prix par plateforme')
        ax.set_xlabel('Plateforme')
        ax.set_ylabel('Prix (EUR)')
        plt.xticks(rotation=45)
        self._save_plot('prix_par_plateforme.png')

    def plot_source_comparison(self):
        """Comparaison des prix entre DLCompare et GoCleCD."""
        if self.df_games['source'].nunique() < 2:
            return

        fig, axes = plt.subplots(1, 2, figsize=(16, 7))

        sns.boxplot(data=self.df_games, x='source', y='meilleur_prix',
                    ax=axes[0], hue='source', palette='Set1', legend=False)
        axes[0].set_title('Comparaison des prix par source')
        axes[0].set_xlabel('Source')
        axes[0].set_ylabel('Meilleur prix (EUR)')

        for source in self.df_games['source'].unique():
            subset = self.df_games[self.df_games['source'] == source]
            sns.histplot(subset['meilleur_prix'], kde=True, ax=axes[1],
                         label=source, alpha=0.5, bins=20)
        axes[1].set_title('Distribution des prix par source')
        axes[1].set_xlabel('Prix (EUR)')
        axes[1].legend()
        self._save_plot('comparaison_sources.png')

    def plot_offers_count(self, n: int = 15):
        """Barplot du nombre d'offres par jeu (concurrence)."""
        df = self.df_games.nlargest(n, 'nb_offres')
        if df.empty:
            return

        fig, ax = plt.subplots(figsize=(12, 8))
        sns.barplot(data=df, x='nb_offres', y='nom', ax=ax,
                    hue='nom', palette='rocket', legend=False)
        ax.set_title(f'Top {n} des jeux avec le plus d\'offres (concurrence)')
        ax.set_xlabel('Nombre d\'offres')
        ax.set_ylabel('Jeu')
        self._save_plot('nb_offres_par_jeu.png')

    # =====================================================================
    # RAPPORT COMPLET
    # =====================================================================

    def generate_full_report(self):
        """Genere un rapport complet avec statistiques et visualisations."""
        print("\n" + "#" * 60)
        print("  RAPPORT D'ANALYSE — GAME PRICE TRACKER")
        print(f"  Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print("#" * 60)

        self.summary_stats()

        print("\nTOP 10 — Jeux les moins chers :")
        cheapest = self.top_cheapest(10)
        if not cheapest.empty:
            print(cheapest.to_string(index=False))

        print("\nTOP 10 — Meilleurs deals (ecarts de prix) :")
        deals = self.top_deals(10)
        if not deals.empty:
            print(deals.to_string(index=False))

        print("\nVendeurs les plus competitifs :")
        vendors = self.top_vendors(10)
        if not vendors.empty:
            print(vendors.to_string(index=False))

        self.compare_sources()

        print("\nGeneration des graphiques...")
        self.plot_price_distribution()
        self.plot_top_cheapest(15)
        self.plot_top_deals(10)
        self.plot_vendor_ranking(10)
        self.plot_price_by_platform()
        self.plot_source_comparison()
        self.plot_offers_count(15)

        csv_path = os.path.join(self.output_dir, 'rapport_complet.csv')
        self.df_games.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"\n[Analyzer] Rapport CSV sauvegarde : {csv_path}")

        print("\n" + "#" * 60)
        print("  RAPPORT TERMINE")
        print("#" * 60)
