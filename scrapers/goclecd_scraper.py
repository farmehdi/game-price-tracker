"""
scrapers/goclecd_scraper.py
----------------------------
Scraper specialise pour GoCleCD.fr.
Herite de BaseScraper et implemente la recherche et l'extraction des prix.

Recalibre le 23/02/2026 apres changement de structure du site.
Nouvelle structure :
- URL recherche : goclecd.fr/produits/?search_name=NOM_DU_JEU
- Barre de recherche : input#quicksearch_input (name=search_name)
- Resultats : liens <a> vers goclecd.fr/acheter-...-comparateur-prix/
- Prix : <span class='leading-none py-2 uppercase ml-[12%]'> contenant XX,XX€
- Prix alternatif : <a class='x-set-currency'>
"""

import re
import time
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from scrapers.base_scraper import BaseScraper
from models.game import Game, Offer, GameCollection


class GoclecdScraper(BaseScraper):
    """
    Scraper pour le site GoCleCD.fr.

    Strategie :
    1. Aller sur goclecd.fr
    2. Pour chaque jeu, utiliser la barre de recherche
    3. Extraire les resultats et les prix
    """

    BASE_URL = "https://www.goclecd.fr"
    SEARCH_URL = "https://www.goclecd.fr/produits/?search_name="

    # Selecteurs CSS calibres le 23/02/2026
    SEARCH_INPUT_ID = "quicksearch_input"
    PRICE_SELECTOR = "span.leading-none.py-2.uppercase"
    PRICE_LINK_SELECTOR = "a.x-set-currency"
    GAME_LINK_PATTERN = "/acheter-"

    def __init__(self, headless: bool = True):
        super().__init__(headless=headless)

    def _handle_cookies(self):
        """Gere le pop-up de consentement cookies sur GoCleCD."""
        try:
            cookie_btn = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "#didomi-notice-agree-button, button[id*='accept'], .cookie-accept, [class*='cookie'] button"
                ))
            )
            cookie_btn.click()
            self.logger.info("Pop-up cookies accepte.")
        except TimeoutException:
            self.logger.info("Pas de pop-up cookies detecte.")

    def _search_game(self, game_name: str) -> str:
        """
        Recherche un jeu via la barre de recherche.

        Returns:
            URL de la page de resultats, ou chaine vide si echec.
        """
        try:
            # Aller sur la page d'accueil
            self._get_page(self.BASE_URL)
            self._handle_cookies()

            # Trouver la barre de recherche
            search_input = self._wait_for_element(
                By.ID, self.SEARCH_INPUT_ID, timeout=10
            )

            if not search_input:
                search_input = self._wait_for_element(
                    By.CSS_SELECTOR, "input[name='search_name']", timeout=5
                )

            if not search_input:
                self.logger.warning("Barre de recherche introuvable.")
                return ""

            # Taper le nom du jeu et soumettre
            search_input.clear()
            time.sleep(0.5)
            search_input.send_keys(game_name)
            time.sleep(0.5)
            search_input.send_keys(Keys.RETURN)

            # Attendre le chargement des resultats
            time.sleep(4)

            current_url = self.driver.current_url
            self.logger.info(f"Page de resultats : {current_url}")
            return current_url

        except Exception as e:
            self.logger.warning(f"Erreur lors de la recherche de '{game_name}' : {e}")
            return ""

    def _extract_game_from_search(self, game_name: str) -> Game:
        """
        Extrait les informations d'un jeu depuis la page de resultats.

        Methodes (par ordre de priorite) :
        1. Liens <a> contenant /acheter- avec un prix dans le texte
        2. Spans avec classe leading-none py-2 uppercase
        3. Fallback regex sur tout le body
        """
        game = Game(
            name=game_name,
            source="GoCleCD",
            url=self.driver.current_url
        )

        try:
            # ---- METHODE 1 : Liens avec prix ----
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            game_links = []
            name_words = game_name.lower().split()

            for link in all_links:
                href = link.get_attribute("href") or ""
                text = link.text.strip()

                if self.GAME_LINK_PATTERN in href and "goclecd.fr" in href:
                    href_clean = href.lower().replace("-", "")
                    matches = sum(1 for w in name_words if w in href_clean)
                    if matches >= min(2, len(name_words)):
                        game_links.append({
                            'href': href,
                            'text': text,
                        })

            self.logger.info(f"  {len(game_links)} liens trouves pour '{game_name}'")

            prices_found = []
            for gl in game_links:
                price_match = re.search(r'(\d+[.,]\d{2})', gl['text'])
                if price_match:
                    price_str = price_match.group(1).replace(',', '.')
                    price = float(price_str)
                    if 0 < price < 500:
                        prices_found.append({
                            'price': price,
                            'href': gl['href'],
                        })

            # ---- METHODE 2 : Spans de prix ----
            if not prices_found:
                price_spans = self.driver.find_elements(
                    By.CSS_SELECTOR, self.PRICE_SELECTOR
                )
                for span in price_spans:
                    price_match = re.search(r'(\d+[.,]\d{2})', span.text)
                    if price_match:
                        price_str = price_match.group(1).replace(',', '.')
                        price = float(price_str)
                        if 0 < price < 500:
                            prices_found.append({
                                'price': price,
                                'href': '',
                            })

            # ---- METHODE 3 : Fallback regex ----
            if not prices_found:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                all_prices = re.findall(r'(\d+[.,]\d{2})\s*€', body_text)
                for p in all_prices[:10]:
                    price = float(p.replace(',', '.'))
                    if 1 < price < 500:
                        prices_found.append({
                            'price': price,
                            'href': '',
                        })

            if not prices_found:
                self.logger.info(f"  Aucun prix trouve pour '{game_name}'")
                return game

            # Deduplication et tri
            unique_prices = list({p['price']: p for p in prices_found}.values())
            unique_prices.sort(key=lambda x: x['price'])

            self.logger.info(
                f"  {len(unique_prices)} prix uniques pour '{game_name}' : "
                f"{[p['price'] for p in unique_prices[:5]]}"
            )

            # Creer les offres
            for i, p in enumerate(unique_prices[:10]):
                if p['href']:
                    game.url = p['href']

                offer = Offer(
                    store_name=f"Vendeur {i+1}",
                    price=p['price'],
                    platform="PC",
                    url=p.get('href', '')
                )
                game.add_offer(offer)

            # URL du jeu
            if game_links and not game.url:
                game.url = game_links[0]['href']

        except Exception as e:
            self.logger.warning(f"Erreur extraction pour '{game_name}' : {e}")

        return game

    def scrape_game(self, game_name: str) -> Game:
        """
        Scrape un seul jeu : recherche + extraction.

        Args:
            game_name: Nom du jeu a chercher.

        Returns:
            Objet Game avec les offres trouvees.
        """
        self.logger.info(f"Recherche de '{game_name}' sur GoCleCD...")

        search_url = self._search_game(game_name)
        if not search_url:
            return Game(name=game_name, source="GoCleCD")

        game = self._extract_game_from_search(game_name)
        return game

    def scrape_games(self, game_names: list) -> GameCollection:
        """
        Scrape une liste de jeux.

        Args:
            game_names: Liste des noms de jeux a chercher.

        Returns:
            GameCollection contenant les jeux trouves.
        """
        self.logger.info(f"Scraping GoCleCD pour {len(game_names)} jeux...")
        collection = GameCollection(source="GoCleCD")

        for i, name in enumerate(game_names):
            self.logger.info(f"[{i+1}/{len(game_names)}] {name}")
            try:
                game = self.scrape_game(name)
                if game.nb_offers > 0:
                    collection.add_game(game)
                    self.logger.info(
                        f"  -> {game.nb_offers} offres, "
                        f"meilleur prix : {game.best_price:.2f}€"
                    )
                else:
                    self.logger.info(f"  -> Aucune offre trouvee")
            except Exception as e:
                self.logger.warning(f"  Erreur pour '{name}' : {e}")
                continue

        self.logger.info(f"GoCleCD : {collection.nb_games} jeux recuperes.")
        return collection
