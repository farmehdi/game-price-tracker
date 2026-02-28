"""
scrapers/trend_scraper.py
--------------------------
Scraper de tendances Google Trends pour calculer un "Hype Score" par jeu.

Utilise la librairie pytrends pour interroger Google Trends et mesurer
l'interet du public pour chaque jeu video. Le Hype Score combine :
- Le volume de recherche relatif actuel (0-100)
- La tendance (hausse ou baisse sur les 3 derniers mois)
- Le nombre de pays ou le jeu est recherche

Ce module n'utilise PAS Selenium (pas de page web a scraper)
mais herite du pattern d'architecture du projet.
"""

import time
import random
import logging
from dataclasses import dataclass, field
from typing import Optional

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@dataclass
class HypeReport:
    """
    Rapport de hype pour un jeu video.

    Attributs :
        game_name       : Nom du jeu
        hype_score      : Score de hype calcule (0-100)
        current_interest: Interet actuel sur Google Trends (0-100)
        trend_direction : Direction de la tendance ("hausse", "baisse", "stable")
        trend_change    : Variation en % sur la periode
        top_region      : Region avec le plus d'interet
        related_queries : Requetes associees populaires
    """
    game_name: str
    hype_score: float = 0.0
    current_interest: int = 0
    trend_direction: str = "inconnu"
    trend_change: float = 0.0
    top_region: str = ""
    related_queries: list = field(default_factory=list)

    def __repr__(self):
        arrow = {"hausse": "^", "baisse": "v", "stable": "=", "inconnu": "?"}
        return (
            f"HypeReport('{self.game_name}', "
            f"score={self.hype_score:.1f}, "
            f"interest={self.current_interest}, "
            f"trend={arrow.get(self.trend_direction, '?')})"
        )


class TrendScraper:
    """
    Scraper de tendances Google Trends.

    Utilise pytrends pour recuperer les donnees de tendance et
    calculer un Hype Score pour chaque jeu.

    Attributs de classe :
        TIMEFRAME  : Periode d'analyse (3 derniers mois)
        GEO        : Zone geographique (France)
        MIN_DELAY  : Delai minimum entre requetes (secondes)
        MAX_DELAY  : Delai maximum entre requetes (secondes)
    """

    TIMEFRAME = "today 3-m"  # 3 derniers mois
    GEO = "FR"               # France
    MIN_DELAY = 3
    MAX_DELAY = 8

    def __init__(self):
        """Initialise le TrendScraper avec pytrends."""
        self.logger = logging.getLogger(self.__class__.__name__)

        if not PYTRENDS_AVAILABLE:
            self.logger.warning(
                "pytrends n'est pas installe. "
                "Installez-le avec : pip install pytrends"
            )
            self.pytrends = None
            return

        try:
            self.pytrends = TrendReq(
                hl='fr-FR',
                tz=60,  # UTC+1 (France)
            )
            self.logger.info("TrendScraper initialise avec succes.")
        except Exception as e:
            self.logger.error(f"Erreur initialisation pytrends : {e}")
            self.pytrends = None

    def _respectful_delay(self):
        """Pause ethique entre les requetes Google Trends."""
        delay = self.MIN_DELAY + random.uniform(0, self.MAX_DELAY - self.MIN_DELAY)
        self.logger.info(f"Pause de {delay:.1f}s avant requete Google Trends...")
        time.sleep(delay)

    def get_interest(self, game_name: str) -> dict:
        """
        Recupere les donnees d'interet Google Trends pour un jeu.

        Args:
            game_name: Nom du jeu a rechercher.

        Returns:
            Dictionnaire avec les donnees brutes de trends.
        """
        if not self.pytrends:
            self.logger.warning("pytrends non disponible.")
            return {}

        self._respectful_delay()

        try:
            # Construire la requete
            self.pytrends.build_payload(
                kw_list=[game_name],
                timeframe=self.TIMEFRAME,
                geo=self.GEO,
            )

            # Recuperer l'interet dans le temps
            interest_over_time = self.pytrends.interest_over_time()

            # Recuperer l'interet par region
            interest_by_region = self.pytrends.interest_by_region(
                resolution='COUNTRY',
                inc_low_vol=True
            )

            # Recuperer les requetes associees
            related = self.pytrends.related_queries()

            return {
                'interest_over_time': interest_over_time,
                'interest_by_region': interest_by_region,
                'related_queries': related,
            }

        except Exception as e:
            self.logger.warning(f"Erreur Google Trends pour '{game_name}' : {e}")
            return {}

    def compute_hype_score(self, game_name: str) -> HypeReport:
        """
        Calcule le Hype Score pour un jeu donne.

        Le Hype Score est une moyenne ponderee de :
        - Interet actuel (poids 50%) : valeur Google Trends la plus recente
        - Tendance (poids 30%) : hausse/baisse sur la periode
        - Diversite geographique (poids 20%) : nombre de regions avec interet > 0

        Args:
            game_name: Nom du jeu.

        Returns:
            HypeReport avec toutes les metriques.
        """
        report = HypeReport(game_name=game_name)

        data = self.get_interest(game_name)
        if not data:
            return report

        # --- Interet actuel ---
        interest_df = data.get('interest_over_time')
        if interest_df is not None and not interest_df.empty and game_name in interest_df.columns:
            values = interest_df[game_name].values
            current_interest = int(values[-1])
            report.current_interest = current_interest

            # --- Tendance ---
            if len(values) >= 4:
                # Comparer la moyenne du dernier quart vs premier quart
                quarter = len(values) // 4
                recent_avg = values[-quarter:].mean()
                early_avg = values[:quarter].mean()

                if early_avg > 0:
                    change = ((recent_avg - early_avg) / early_avg) * 100
                else:
                    change = 100.0 if recent_avg > 0 else 0.0

                report.trend_change = round(change, 1)

                if change > 15:
                    report.trend_direction = "hausse"
                elif change < -15:
                    report.trend_direction = "baisse"
                else:
                    report.trend_direction = "stable"

        # --- Diversite geographique ---
        region_df = data.get('interest_by_region')
        nb_regions = 0
        top_region = ""
        if region_df is not None and not region_df.empty and game_name in region_df.columns:
            active_regions = region_df[region_df[game_name] > 0]
            nb_regions = len(active_regions)
            if not active_regions.empty:
                top_region = active_regions[game_name].idxmax()
                report.top_region = top_region

        # --- Requetes associees ---
        related = data.get('related_queries', {})
        if related and game_name in related:
            top_queries = related[game_name].get('top')
            if top_queries is not None and not top_queries.empty:
                report.related_queries = top_queries['query'].head(5).tolist()

        # --- Calcul du Hype Score ---
        # Interet actuel : 50% (deja sur 100)
        score_interest = report.current_interest * 0.50

        # Tendance : 30% (normalise entre 0 et 100)
        # Une hausse de +100% donne 100, -100% donne 0, 0% donne 50
        trend_normalized = max(0, min(100, 50 + report.trend_change / 2))
        score_trend = trend_normalized * 0.30

        # Diversite geo : 20% (normalise, max 50 pays = 100)
        geo_normalized = min(100, (nb_regions / 50) * 100)
        score_geo = geo_normalized * 0.20

        report.hype_score = round(score_interest + score_trend + score_geo, 1)

        self.logger.info(
            f"Hype Score '{game_name}' : {report.hype_score:.1f} "
            f"(interet={report.current_interest}, "
            f"tendance={report.trend_direction} {report.trend_change:+.1f}%, "
            f"regions={nb_regions})"
        )

        return report

    def compute_batch(self, game_names: list) -> list:
        """
        Calcule le Hype Score pour une liste de jeux.

        Args:
            game_names: Liste de noms de jeux.

        Returns:
            Liste de HypeReport triee par hype_score decroissant.
        """
        self.logger.info(f"Calcul du Hype Score pour {len(game_names)} jeux...")
        reports = []

        for name in game_names:
            try:
                report = self.compute_hype_score(name)
                reports.append(report)
            except Exception as e:
                self.logger.warning(f"Erreur Hype Score '{name}' : {e}")
                reports.append(HypeReport(game_name=name))

        # Trier par hype_score decroissant
        reports.sort(key=lambda r: r.hype_score, reverse=True)

        self.logger.info("Calcul Hype Score termine.")
        return reports

    def display_hype_ranking(self, reports: list):
        """Affiche le classement des jeux par Hype Score."""
        print("\n" + "=" * 60)
        print("  CLASSEMENT HYPE SCORE")
        print("=" * 60)

        arrows = {"hausse": "^", "baisse": "v", "stable": "=", "inconnu": "?"}

        for i, r in enumerate(reports, 1):
            arrow = arrows.get(r.trend_direction, "?")
            bar = "#" * int(r.hype_score / 5)  # Barre visuelle
            print(
                f"  {i:2d}. [{r.hype_score:5.1f}] {bar:20s} "
                f"{r.game_name[:30]:30s} {arrow} ({r.trend_change:+.0f}%)"
            )

        print("=" * 60)
