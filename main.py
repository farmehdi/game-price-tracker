"""
main.py
-------
Point d'entree principal du Game Price Tracker.

Pipeline complet :
1. Scraping DLCompare.fr (liste des jeux + prix)
2. Scraping GoCleCD.fr (prix des memes jeux pour comparaison)
2b. Calcul du Hype Score via Google Trends
3. Analyse avec pandas + visualisations matplotlib/seaborn
4. Export CSV/JSON

Usage :
    python main.py                          # Pipeline complet
    python main.py --dlcompare              # DLCompare uniquement
    python main.py --no-trends              # Sans Google Trends
    python main.py --dlcompare --no-trends  # Le plus rapide
    python main.py --analyze-only           # Analyse depuis CSV existant
"""

import json
import csv
import os
import sys
from datetime import datetime

from scrapers.dlcompare_scraper import DLCompareScraper
from scrapers.goclecd_scraper import GoclecdScraper
from scrapers.trend_scraper import TrendScraper
from analysis.price_analyzer import PriceAnalyzer
from models.game import GameCollection


# =====================================================================
# FONCTIONS D'EXPORT
# =====================================================================

def export_to_csv(collection: GameCollection, filename: str):
    """Exporte une GameCollection en fichier CSV."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "nom", "date_sortie", "plateformes", "meilleur_prix",
            "pire_prix", "ecart_prix", "nb_offres", "meilleur_vendeur",
            "source", "url"
        ])
        for game in collection.games:
            best = game.best_offer
            writer.writerow([
                game.name, game.release_date,
                " | ".join(game.platforms),
                f"{game.best_price:.2f}" if game.best_price else "",
                f"{game.worst_price:.2f}" if game.worst_price else "",
                f"{game.price_spread:.2f}" if game.price_spread else "",
                game.nb_offers,
                best.store_name if best else "",
                game.source, game.url
            ])
    print(f"[Export] CSV sauvegarde : {filename}")


def export_to_json(collection: GameCollection, filename: str):
    """Exporte une GameCollection en fichier JSON."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    data = {
        "source": collection.source,
        "scraped_at": datetime.now().isoformat(),
        "nb_games": collection.nb_games,
        "games": [
            {
                "name": g.name,
                "release_date": g.release_date,
                "platforms": g.platforms,
                "best_price": g.best_price,
                "worst_price": g.worst_price,
                "price_spread": g.price_spread,
                "nb_offers": g.nb_offers,
                "source": g.source,
                "url": g.url,
                "offers": [
                    {
                        "store": o.store_name,
                        "price": o.price,
                        "platform": o.platform,
                        "is_official": o.is_official
                    }
                    for o in g.offers
                ]
            }
            for g in collection.games
        ]
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[Export] JSON sauvegarde : {filename}")


# =====================================================================
# PIPELINE
# =====================================================================

def scrape_dlcompare(max_games: int = 30) -> GameCollection:
    """Etape 1 : Scraping de DLCompare.fr"""
    print("\n" + "=" * 60)
    print("  ETAPE 1 : Scraping DLCompare.fr")
    print("=" * 60)

    with DLCompareScraper(headless=True) as scraper:
        collection = scraper.scrape_all(max_games=max_games, with_details=False)

    print(f"  -> {collection.nb_games} jeux recuperes depuis DLCompare.")
    return collection


def scrape_goclecd(game_names: list) -> GameCollection:
    """Etape 2 : Scraping de GoCleCD.fr pour les memes jeux."""
    print("\n" + "=" * 60)
    print("  ETAPE 2 : Scraping GoCleCD.fr (comparaison croisee)")
    print("=" * 60)

    with GoclecdScraper(headless=True) as scraper:
        collection = scraper.scrape_games(game_names)

    print(f"  -> {collection.nb_games} jeux recuperes depuis GoCleCD.")
    return collection


def run_analysis(dlcompare_col: GameCollection, goclecd_col: GameCollection = None):
    """Etape 3 : Analyse des donnees et generation de graphiques."""
    print("\n" + "=" * 60)
    print("  ETAPE 3 : Analyse des donnees")
    print("=" * 60)

    analyzer = PriceAnalyzer(output_dir="data")
    analyzer.load_from_collection(dlcompare_col)

    if goclecd_col and goclecd_col.nb_games > 0:
        analyzer.load_from_collection(goclecd_col)

    analyzer.generate_full_report()


# =====================================================================
# MAIN
# =====================================================================

def main():
    """Fonction principale — Pipeline complet du Game Price Tracker."""
    print("#" * 60)
    print("  GAME PRICE TRACKER")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("#" * 60)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    # --- Mode analyse uniquement ---
    if "--analyze-only" in args:
        print("\nMode : Analyse depuis CSV existant")
        analyzer = PriceAnalyzer(output_dir="data")
        csv_files = [f for f in os.listdir("data") if f.endswith(".csv") and f.startswith("dlcompare_")]
        if csv_files:
            latest = sorted(csv_files)[-1]
            analyzer.load_from_csv(f"data/{latest}")
            analyzer.generate_full_report()
        else:
            print("Aucun fichier CSV trouve dans data/. Lancez d'abord un scraping.")
        return

    # --- Pipeline normal ---
    # Etape 1 : DLCompare
    dlcompare_col = scrape_dlcompare(max_games=30)
    export_to_csv(dlcompare_col, f"data/dlcompare_{timestamp}.csv")
    export_to_json(dlcompare_col, f"data/dlcompare_{timestamp}.json")

    # Etape 2 : GoCleCD
    goclecd_col = None
    if "--dlcompare" not in args:
        game_names = [g.name for g in dlcompare_col.games[:15]]
        if game_names:
            goclecd_col = scrape_goclecd(game_names)
            export_to_csv(goclecd_col, f"data/goclecd_{timestamp}.csv")
            export_to_json(goclecd_col, f"data/goclecd_{timestamp}.json")

    # Etape 2b : Hype Score (Google Trends)
    if "--no-trends" not in args:
        print("\n" + "=" * 60)
        print("  ETAPE 2b : Calcul du Hype Score (Google Trends)")
        print("=" * 60)
        try:
            trend_scraper = TrendScraper()
            game_names_for_trends = [g.name for g in dlcompare_col.games[:10]]
            hype_reports = trend_scraper.compute_batch(game_names_for_trends)
            trend_scraper.display_hype_ranking(hype_reports)
        except Exception as e:
            print(f"  Hype Score indisponible : {e}")
            print("  (Installez pytrends : pip install pytrends)")

    # Etape 3 : Analyse
    run_analysis(dlcompare_col, goclecd_col)

    print("\n" + "#" * 60)
    print("  GAME PRICE TRACKER — TERMINE")
    print(f"  Resultats dans : data/")
    print("#" * 60)


if __name__ == "__main__":
    main()
