"""
tests/test_models.py
--------------------
Tests unitaires pour les modeles de donnees (dataclasses).
Verifie le bon fonctionnement de Game, Offer, GameCollection.

Lancer les tests :
    python -m pytest tests/ -v
    ou
    python -m unittest tests.test_models -v
"""

import unittest
from models.game import Offer, Game, GameCollection


class TestOffer(unittest.TestCase):
    """Tests pour la dataclass Offer."""

    def test_creation_simple(self):
        """Test de creation d'une offre basique."""
        offer = Offer(store_name="Steam", price=29.99)
        self.assertEqual(offer.store_name, "Steam")
        self.assertEqual(offer.price, 29.99)
        self.assertEqual(offer.currency, "EUR")

    def test_creation_complete(self):
        """Test de creation d'une offre avec tous les champs."""
        offer = Offer(
            store_name="Fnac",
            price=49.99,
            currency="EUR",
            platform="PS5",
            edition="Deluxe",
            url="https://fnac.com/jeu",
            is_official=True
        )
        self.assertEqual(offer.platform, "PS5")
        self.assertTrue(offer.is_official)

    def test_repr(self):
        """Test de la representation textuelle."""
        offer = Offer(store_name="CDKeys", price=15.50, platform="PC")
        text = repr(offer)
        self.assertIn("CDKeys", text)
        self.assertIn("15.50", text)


class TestGame(unittest.TestCase):
    """Tests pour la dataclass Game."""

    def setUp(self):
        """Cree un jeu de test avec des offres."""
        self.game = Game(
            name="Elden Ring",
            release_date="25/02/2022",
            platforms=["PC", "PS5", "Xbox Series X"],
            source="DLCompare"
        )
        self.game.add_offer(Offer(store_name="Steam", price=39.99))
        self.game.add_offer(Offer(store_name="CDKeys", price=29.99))
        self.game.add_offer(Offer(store_name="Fnac", price=49.99))

    def test_best_price(self):
        """Le meilleur prix doit etre le minimum."""
        self.assertEqual(self.game.best_price, 29.99)

    def test_worst_price(self):
        """Le pire prix doit etre le maximum."""
        self.assertEqual(self.game.worst_price, 49.99)

    def test_price_spread(self):
        """L'ecart de prix doit etre correct."""
        self.assertAlmostEqual(self.game.price_spread, 20.00, places=2)

    def test_best_offer(self):
        """La meilleure offre doit etre celle avec le prix le plus bas."""
        self.assertEqual(self.game.best_offer.store_name, "CDKeys")

    def test_nb_offers(self):
        """Le nombre d'offres doit etre correct."""
        self.assertEqual(self.game.nb_offers, 3)

    def test_empty_game(self):
        """Un jeu sans offres doit retourner None pour les prix."""
        empty_game = Game(name="Test")
        self.assertIsNone(empty_game.best_price)
        self.assertIsNone(empty_game.worst_price)
        self.assertIsNone(empty_game.price_spread)
        self.assertIsNone(empty_game.best_offer)
        self.assertEqual(empty_game.nb_offers, 0)

    def test_single_offer(self):
        """Un jeu avec une seule offre : spread = None."""
        game = Game(name="Solo")
        game.add_offer(Offer(store_name="Steam", price=10.0))
        self.assertEqual(game.best_price, 10.0)
        self.assertIsNone(game.price_spread)  # Pas d'ecart avec 1 seule offre


class TestGameCollection(unittest.TestCase):
    """Tests pour la GameCollection."""

    def setUp(self):
        """Cree une collection de test."""
        self.collection = GameCollection(source="Test")

        # Jeu 1 : cher, gros ecart
        game1 = Game(name="AAA Game", platforms=["PC", "PS5"])
        game1.add_offer(Offer(store_name="Steam", price=59.99))
        game1.add_offer(Offer(store_name="CDKeys", price=39.99))
        self.collection.add_game(game1)

        # Jeu 2 : pas cher
        game2 = Game(name="Indie Game", platforms=["PC"])
        game2.add_offer(Offer(store_name="Steam", price=9.99))
        game2.add_offer(Offer(store_name="Humble", price=7.99))
        self.collection.add_game(game2)

        # Jeu 3 : prix moyen
        game3 = Game(name="AA Game", platforms=["PC", "Xbox Series X"])
        game3.add_offer(Offer(store_name="Epic", price=24.99))
        self.collection.add_game(game3)

    def test_nb_games(self):
        """Le nombre de jeux doit etre correct."""
        self.assertEqual(self.collection.nb_games, 3)

    def test_search(self):
        """La recherche par nom doit fonctionner (insensible a la casse)."""
        results = self.collection.search("indie")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Indie Game")

    def test_search_no_results(self):
        """La recherche sans resultats doit retourner une liste vide."""
        results = self.collection.search("inexistant")
        self.assertEqual(len(results), 0)

    def test_get_cheapest(self):
        """Les jeux les moins chers doivent etre tries correctement."""
        cheapest = self.collection.get_cheapest(2)
        self.assertEqual(len(cheapest), 2)
        self.assertEqual(cheapest[0].name, "Indie Game")  # 7.99
        self.assertEqual(cheapest[1].name, "AA Game")      # 24.99

    def test_get_top_deals(self):
        """Les meilleurs deals doivent avoir le plus grand ecart."""
        deals = self.collection.get_top_deals(2)
        self.assertEqual(deals[0].name, "AAA Game")  # ecart = 20.00
        self.assertEqual(deals[1].name, "Indie Game")  # ecart = 2.00

    def test_get_by_platform(self):
        """Le filtre par plateforme doit fonctionner."""
        ps5_games = self.collection.get_by_platform("PS5")
        self.assertEqual(len(ps5_games), 1)
        self.assertEqual(ps5_games[0].name, "AAA Game")

        pc_games = self.collection.get_by_platform("PC")
        self.assertEqual(len(pc_games), 3)


class TestHypeReport(unittest.TestCase):
    """Tests pour la dataclass HypeReport du TrendScraper."""

    def _import_hype_report(self):
        """Import HypeReport sans passer par scrapers/__init__ (evite selenium)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "trend_scraper", "scrapers/trend_scraper.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.HypeReport

    def test_creation(self):
        """Test de creation d'un HypeReport."""
        HypeReport = self._import_hype_report()

        report = HypeReport(
            game_name="GTA VI",
            hype_score=85.5,
            current_interest=92,
            trend_direction="hausse",
            trend_change=45.0,
            top_region="France"
        )
        self.assertEqual(report.game_name, "GTA VI")
        self.assertEqual(report.hype_score, 85.5)
        self.assertEqual(report.trend_direction, "hausse")

    def test_default_values(self):
        """Test des valeurs par defaut."""
        HypeReport = self._import_hype_report()

        report = HypeReport(game_name="Unknown")
        self.assertEqual(report.hype_score, 0.0)
        self.assertEqual(report.current_interest, 0)
        self.assertEqual(report.trend_direction, "inconnu")
        self.assertEqual(report.related_queries, [])


if __name__ == "__main__":
    unittest.main()
