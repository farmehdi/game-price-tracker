"""
scrapers/dlcompare_scraper.py
-----------------------------
Scraper specialise pour DLCompare.fr.
Herite de BaseScraper et implemente l'extraction des jeux et des prix.

Selecteurs CSS calibres via debug_selectors.py le 19/02/2026.
Structure reelle du site :
- Liste des jeux : <a class="game-list-item" href="/jeux/...">
  - Nom : <span class="name clickable">
  - Date : <span class="pre-order">Date de sortie: JJ/MM/AAAA</span>
  - Plateformes : <span class="catalog-game-support"> avec <span>PC</span> etc.
  - Prix : texte brut "XX.XX" suivi de "EUR" sur une ligne separee
  - Image : <img class="catalog-img clickable">

Format texte reel d'un element (repr) :
    'Diablo 4 Lord of Hatred\\nDate de sortie: 28/04/2026\\n  Kinguin\\nPC\\nPS5\\n...\\n\\n33.30\\nEUR'
    -> Le prix (33.30) et le symbole EUR sont sur des lignes SEPAREES.
    -> Le regex doit chercher un nombre decimal SANS exiger EUR sur la meme ligne.
"""

import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from scrapers.base_scraper import BaseScraper
from models.game import Game, Offer, GameCollection


class DLCompareScraper(BaseScraper):
    """
    Scraper pour le site DLCompare.fr.

    Recupere :
    - La liste des jeux (nom, date de sortie, plateformes, meilleur prix)
    - Les details de chaque jeu (toutes les offres chez tous les vendeurs)
    """

    BASE_URL = "https://www.dlcompare.fr"
    GAMES_URL = "https://www.dlcompare.fr/jeux"

    # Selecteurs CSS calibres depuis debug_selectors.py
    GAME_LIST_SELECTOR = "a.game-list-item"
    GAME_NAME_SELECTOR = "span.name.clickable"
    GAME_DATE_SELECTOR = "span.pre-order"
    GAME_IMG_SELECTOR = "img.catalog-img"

    # Selecteurs pour la page detail (offres des vendeurs)
    DETAIL_BUY_SELECTOR = "[class*='buy']"
    DETAIL_SHOP_SELECTOR = "[class*='shop']"

    # Plateformes connues (pour filtrage du texte)
    KNOWN_PLATFORMS = [
        "PC", "PS5", "PS4", "PS3", "Xbox Series X", "XboxOne",
        "Switch", "Switch 2", "Mac"
    ]

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)

    def _handle_cookies(self):
        """Gere le pop-up de consentement cookies sur DLCompare."""
        try:
            cookie_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "#didomi-notice-agree-button, button[id*='accept'], .cookie-accept"
                ))
            )
            cookie_btn.click()
            self.logger.info("Pop-up cookies accepte.")
        except TimeoutException:
            self.logger.info("Pas de pop-up cookies detecte.")

    def _scroll_to_load(self, scrolls: int = 3):
        """Scroll vers le bas pour charger plus de jeux (lazy loading)."""
        for i in range(scrolls):
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(2)

    def get_games_list(self, max_games: int = 50) -> GameCollection:
        """
        Recupere la liste des jeux depuis la page catalogue de DLCompare.

        Args:
            max_games: Nombre maximum de jeux a recuperer.

        Returns:
            GameCollection contenant les jeux trouves.
        """
        self.logger.info(f"Scraping de la liste des jeux sur DLCompare (max={max_games})...")
        collection = GameCollection(source="DLCompare")

        self._get_page(self.GAMES_URL)
        self._handle_cookies()

        if max_games > 20:
            self._scroll_to_load(scrolls=3)

        # Selecteur calibre
        game_elements = self._wait_for_elements(
            By.CSS_SELECTOR, self.GAME_LIST_SELECTOR
        )

        # Fallback
        if not game_elements:
            self.logger.warning("Selecteur principal echoue, essai du fallback...")
            game_elements = self._wait_for_elements(
                By.CSS_SELECTOR, "li a[href*='/jeux/']"
            )

        if not game_elements:
            self.logger.warning("Aucun jeu trouve sur la page.")
            return collection

        self.logger.info(f"{len(game_elements)} elements de jeux trouves.")

        for element in game_elements[:max_games]:
            try:
                game = self._parse_game_element(element)
                if game:
                    collection.add_game(game)
            except Exception as e:
                self.logger.warning(f"Erreur lors du parsing d'un jeu : {e}")
                continue

        self.logger.info(f"{collection.nb_games} jeux recuperes avec succes.")
        return collection

    def _parse_game_element(self, element) -> Game:
        """
        Parse un element HTML <a class="game-list-item">.

        IMPORTANT : Le prix et le symbole EUR sont sur des lignes SEPAREES
        dans element.text. Exemple :
            '39.99\\nEUR'
        Le regex cherche donc juste un nombre decimal (XX.XX) sans exiger EUR.
        """
        try:
            # URL du jeu
            url = element.get_attribute("href")
            if not url or "/jeux/" not in url:
                return None

            # Texte complet
            text = element.text.strip()
            if not text:
                return None

            lines = [l.strip() for l in text.split("\n") if l.strip()]

            # Nom du jeu (via selecteur specifique)
            name = ""
            try:
                name_elem = element.find_element(
                    By.CSS_SELECTOR, self.GAME_NAME_SELECTOR
                )
                name = name_elem.text.strip()
            except Exception:
                pass
            if not name and lines:
                name = lines[0]
            if not name:
                return None

            # Date de sortie
            release_date = ""
            try:
                date_elem = element.find_element(
                    By.CSS_SELECTOR, self.GAME_DATE_SELECTOR
                )
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', date_elem.text)
                if date_match:
                    release_date = date_match.group(1)
            except Exception:
                pass

            # Plateformes
            platforms = []
            try:
                platform_spans = element.find_elements(
                    By.CSS_SELECTOR, "span.catalog-game-support span"
                )
                platforms = [p.text.strip() for p in platform_spans if p.text.strip()]
            except Exception:
                pass
            if not platforms:
                platforms = [p for p in self.KNOWN_PLATFORMS if p in text]

            # Image
            image_url = ""
            try:
                img_elem = element.find_element(
                    By.CSS_SELECTOR, self.GAME_IMG_SELECTOR
                )
                image_url = img_elem.get_attribute("src") or ""
            except Exception:
                pass

            # --- PRIX ---
            # Le prix apparait comme "39.99\n€" dans le texte.
            # On cherche un nombre decimal (XX.XX) n'importe ou dans le texte.
            price = None
            price_match = re.search(r'(\d+\.\d{2})', text)
            if price_match:
                price = float(price_match.group(1))

            # Vendeur : ligne qui n'est ni le nom, ni une date, ni un prix,
            # ni une plateforme, ni le symbole EUR
            store_name = ""
            skip_words = set(platforms + ["€", name])
            for line in lines:
                if (line not in skip_words and
                    not re.search(r'\d+\.\d{2}', line) and
                    not line.lower().startswith("date") and
                    len(line) > 1):
                    store_name = line
                    break

            # Creer l'objet Game
            game = Game(
                name=name,
                release_date=release_date,
                platforms=platforms,
                image_url=image_url,
                url=url,
                source="DLCompare"
            )

            # Ajouter l'offre si un prix a ete trouve
            if price is not None and 0 < price < 500:
                offer = Offer(
                    store_name=store_name or "Inconnu",
                    price=price,
                    platform=platforms[0] if platforms else "",
                    url=url
                )
                game.add_offer(offer)

            return game

        except Exception as e:
            self.logger.warning(f"Erreur lors du parsing : {e}")
            return None

    def get_game_details(self, game: Game) -> Game:
        """
        Recupere les details d'un jeu (toutes les offres de tous les vendeurs).

        Args:
            game: Objet Game avec au minimum l'URL renseignee.

        Returns:
            Le meme objet Game enrichi avec toutes les offres.
        """
        if not game.url:
            self.logger.warning(f"Pas d'URL pour le jeu '{game.name}'.")
            return game

        self.logger.info(f"Scraping des details pour '{game.name}'...")
        self._get_page(game.url)
        self._handle_cookies()

        # Selecteurs calibres pour les offres
        offer_elements = self._wait_for_elements(
            By.CSS_SELECTOR, self.DETAIL_BUY_SELECTOR, timeout=10
        )
        if not offer_elements:
            offer_elements = self._wait_for_elements(
                By.CSS_SELECTOR, self.DETAIL_SHOP_SELECTOR, timeout=5
            )

        if not offer_elements:
            self.logger.info(f"Aucune offre detaillee pour '{game.name}'.")
            return game

        game.offers = []

        for offer_elem in offer_elements:
            try:
                offer = self._parse_offer_element(offer_elem)
                if offer:
                    game.add_offer(offer)
            except Exception as e:
                self.logger.warning(f"Erreur parsing offre : {e}")
                continue

        self.logger.info(f"{game.nb_offers} offres pour '{game.name}'.")
        return game

    def _parse_offer_element(self, element) -> Offer:
        """Parse un element d'offre de la page detail."""
        try:
            text = element.text.strip()
            if not text:
                return None

            price_match = re.search(r'(\d+\.\d{2})', text)
            if not price_match:
                return None

            price = float(price_match.group(1))
            if price <= 0 or price > 500:
                return None

            lines = [l.strip() for l in text.split("\n") if l.strip()]
            store_name = "Inconnu"
            for line in lines:
                if not re.search(r'\d+\.\d{2}', line) and line != '€':
                    store_name = line
                    break

            is_official = any(
                kw in text.lower()
                for kw in ["officiel", "official", "steam store", "epic games"]
            )

            return Offer(store_name=store_name, price=price, is_official=is_official)

        except Exception:
            return None

    def scrape_all(self, max_games: int = 30, with_details: bool = False) -> GameCollection:
        """
        Methode principale : scrape la liste et optionnellement les details.

        Args:
            max_games: Nombre maximum de jeux a recuperer.
            with_details: Si True, scrape aussi les pages detaillees.

        Returns:
            GameCollection complete.
        """
        collection = self.get_games_list(max_games=max_games)

        if with_details:
            self.logger.info("Scraping des details pour chaque jeu...")
            for game in collection.games:
                try:
                    self.get_game_details(game)
                except Exception as e:
                    self.logger.warning(f"Erreur details '{game.name}' : {e}")
                    continue

        return collection
