# Game Price Tracker

**Outil de comparaison automatique des prix de jeux video** — Scraping multi-sites avec analyse economique.

Projet realise dans le cadre du cours **Web Scraping & Data Science** (M1 APE-DS2E, Universite de Strasbourg).

## Objectif

Comparer automatiquement les prix de jeux video entre differentes plateformes de vente en ligne, analyser les strategies de pricing des vendeurs, et mesurer la popularite (hype) de chaque jeu.

## Fonctionnalites

- **Scraping multi-sites** : DLCompare.fr et GoCleCD.fr
- **Architecture OOP extensible** : `BaseScraper` → scrapers specialises (heritage)
- **Hype Score** : integration Google Trends pour mesurer la popularite
- **Analyse economique** : statistiques descriptives, classement vendeurs, ecarts de prix
- **7 visualisations** : distribution, top deals, comparaison sources, boxplots par plateforme
- **Export** : CSV et JSON avec horodatage
- **18 tests unitaires**
- **Scraping ethique** : delais aleatoires (2-6s), User-Agent, respect des sites

## Architecture

```
game-price-tracker/
├── main.py                    # Point d'entree (pipeline CLI)
├── debug_selectors.py         # Outil de calibration des selecteurs CSS
├── requirements.txt
├── .gitignore
├── README.md
├── scrapers/
│   ├── base_scraper.py        # BaseScraper (classe mere reutilisable)
│   ├── dlcompare_scraper.py   # Scraper DLCompare.fr
│   ├── goclecd_scraper.py     # Scraper GoCleCD.fr
│   └── trend_scraper.py       # Google Trends (Hype Score)
├── models/
│   └── game.py                # @dataclass Game, Offer, GameCollection
├── analysis/
│   └── price_analyzer.py      # Analyse pandas + 7 visualisations
├── data/                      # Donnees exportees (CSV, JSON, PNG)
└── tests/
    └── test_models.py         # 18 tests unitaires
```

## Installation

```bash
git clone https://github.com/VOTRE_USERNAME/game-price-tracker.git
cd game-price-tracker
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# ou : venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

**Pre-requis** : Python 3.10+, Google Chrome installe.

## Utilisation

### Pipeline complet

```bash
python main.py                          # Tout (DLCompare + GoCleCD + Hype Score + Analyse)
python main.py --no-trends              # Sans Google Trends
python main.py --dlcompare --no-trends  # DLCompare uniquement (rapide, ~3 min)
python main.py --analyze-only           # Re-analyser des CSV existants
```

### Utilisation en module Python

```python
from scrapers.dlcompare_scraper import DLCompareScraper

with DLCompareScraper(headless=True) as scraper:
    collection = scraper.scrape_all(max_games=20)

for game in collection.get_cheapest(5):
    print(f"{game.name} -> {game.best_price:.2f} EUR")
```

### Hype Score (Google Trends)

```python
from scrapers.trend_scraper import TrendScraper

trend = TrendScraper()
reports = trend.compute_batch(["GTA VI", "Elden Ring", "Zelda"])
trend.display_hype_ranking(reports)
```

### Interface web (Streamlit)

```bash
streamlit run app.py
```

L'interface s'ouvre dans le navigateur. Cliquer sur les boutons pour lancer le scraping, visualiser les résultats et exporter les données.

### Tests unitaires

```bash
python -m unittest tests.test_models -v   # 18 tests
```

### Calibration des selecteurs

Si les selecteurs CSS ne fonctionnent plus (changement du HTML du site) :

```bash
python debug_selectors.py
```

Ce script ouvre Chrome, teste les selecteurs sur les sites cibles, et affiche ceux qui fonctionnent.

## Resultats attendus

Apres execution du pipeline complet, le dossier `data/` contient :

| Fichier | Description |
|---|---|
| `dlcompare_YYYYMMDD_HHMMSS.csv` | Donnees brutes DLCompare |
| `goclecd_YYYYMMDD_HHMMSS.csv` | Donnees brutes GoCleCD |
| `rapport_complet.csv` | Toutes les donnees fusionnees |
| `distribution_prix.png` | Histogramme + KDE des prix |
| `top_moins_chers.png` | Top 15 jeux les moins chers |
| `top_deals_ecarts.png` | Top 10 meilleurs ecarts de prix |
| `classement_vendeurs.png` | Vendeurs les plus competitifs |
| `prix_par_plateforme.png` | Boxplot par plateforme |
| `comparaison_sources.png` | DLCompare vs GoCleCD |
| `nb_offres_par_jeu.png` | Nombre d'offres (concurrence) |

## Dependances

| Package | Version | Usage |
|---|---|---|
| selenium | >= 4.15.0 | Automatisation navigateur |
| webdriver-manager | >= 4.0.0 | Gestion ChromeDriver |
| pandas | >= 2.1.0 | Manipulation de donnees |
| matplotlib | >= 3.8.0 | Graphiques |
| seaborn | >= 0.13.0 | Graphiques statistiques |
| pytrends | >= 4.9.0 | Google Trends API |

## Ethique du scraping

- **Delais aleatoires** : 2 a 6 secondes entre chaque requete
- **User-Agent** : identification comme navigateur standard
- **Mode headless** : minimise l'impact sur les serveurs
- **Donnees publiques uniquement** : prix affiches publiquement
- **Usage academique** : projet universitaire, pas d'exploitation commerciale

## Auteurs

- Mehdi FAR — M1 APE-DS2E, Universite de Strasbourg
- Chaima Seif Al islam - M1 APE-DS2E, Universite de Strasbourg
- Marwan Saidani - M1 APE-DS2E, Universite de Strasbourg

## Licence

Projet academique — Cours de Web Scraping & Data Science, P. Pelletier, 2025-2026.
