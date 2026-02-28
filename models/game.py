"""
models/game.py
--------------
Dataclasses pour structurer les donnees de jeux video.
Utilisation de @dataclass pour un code propre et lisible.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Offer:
    """Represente une offre de prix chez un vendeur pour un jeu donne."""
    store_name: str
    price: float
    currency: str = "EUR"
    platform: str = ""
    edition: str = ""
    url: str = ""
    is_official: bool = False

    def __repr__(self):
        return f"{self.store_name}: {self.price:.2f}EUR ({self.platform})"


@dataclass
class Game:
    """Represente un jeu video avec ses informations et ses offres."""
    name: str
    release_date: str = ""
    platforms: list = field(default_factory=list)
    image_url: str = ""
    url: str = ""
    source: str = ""
    offers: list = field(default_factory=list)

    @property
    def best_price(self) -> Optional[float]:
        """Retourne le meilleur prix parmi toutes les offres."""
        if not self.offers:
            return None
        return min(offer.price for offer in self.offers)

    @property
    def best_offer(self) -> Optional['Offer']:
        """Retourne l'offre avec le meilleur prix."""
        if not self.offers:
            return None
        return min(self.offers, key=lambda o: o.price)

    @property
    def worst_price(self) -> Optional[float]:
        """Retourne le prix le plus eleve parmi toutes les offres."""
        if not self.offers:
            return None
        return max(offer.price for offer in self.offers)

    @property
    def price_spread(self) -> Optional[float]:
        """Retourne l'ecart entre le prix le plus haut et le plus bas."""
        if not self.offers or len(self.offers) < 2:
            return None
        return self.worst_price - self.best_price

    @property
    def nb_offers(self) -> int:
        """Retourne le nombre d'offres disponibles."""
        return len(self.offers)

    def add_offer(self, offer: Offer):
        """Ajoute une offre au jeu."""
        self.offers.append(offer)

    def __repr__(self):
        price_str = f"{self.best_price:.2f}EUR" if self.best_price else "N/A"
        return f"Game('{self.name}', best={price_str}, offers={self.nb_offers})"


@dataclass
class GameCollection:
    """Collection de jeux, avec methodes d'analyse et de recherche."""
    games: list = field(default_factory=list)
    source: str = ""

    def add_game(self, game: Game):
        """Ajoute un jeu a la collection."""
        self.games.append(game)

    def search(self, query: str) -> list:
        """Recherche un jeu par nom (insensible a la casse)."""
        query_lower = query.lower()
        return [g for g in self.games if query_lower in g.name.lower()]

    def get_top_deals(self, n: int = 10) -> list:
        """Retourne les N jeux avec le plus grand ecart de prix."""
        games_with_spread = [g for g in self.games if g.price_spread is not None]
        return sorted(games_with_spread, key=lambda g: g.price_spread, reverse=True)[:n]

    def get_cheapest(self, n: int = 10) -> list:
        """Retourne les N jeux les moins chers."""
        games_with_price = [g for g in self.games if g.best_price is not None]
        return sorted(games_with_price, key=lambda g: g.best_price)[:n]

    def get_by_platform(self, platform: str) -> list:
        """Filtre les jeux par plateforme."""
        platform_lower = platform.lower()
        return [g for g in self.games if any(platform_lower in p.lower() for p in g.platforms)]

    def get_upcoming(self) -> list:
        """Retourne les jeux dont la date de sortie est renseignee."""
        return [g for g in self.games if g.release_date]

    @property
    def nb_games(self) -> int:
        """Nombre total de jeux dans la collection."""
        return len(self.games)

    def __repr__(self):
        return f"GameCollection(source='{self.source}', games={self.nb_games})"
