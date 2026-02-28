"""
scrapers/base_scraper.py
------------------------
Classe de base pour tous les scrapers du projet.
Gere le driver Selenium, les delais ethiques, le user-agent et la fermeture.
Tout scraper specialise herite de cette classe.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException
)
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class BaseScraper:
    """
    Classe de base pour le web scraping avec Selenium.

    Fournit :
    - Initialisation du driver Chrome (headless)
    - User-Agent personnalise
    - Delais ethiques entre les requetes
    - Gestion des erreurs
    - Logging

    Attributs de classe :
        USER_AGENT : str - User-Agent pour simuler un navigateur classique
        MIN_DELAY  : int - Delai minimum entre deux requetes (en secondes)
        MAX_DELAY  : int - Delai maximum entre deux requetes (en secondes)
        TIMEOUT    : int - Timeout pour les waits explicites (en secondes)
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    MIN_DELAY = 2
    MAX_DELAY = 6
    TIMEOUT = 15

    def __init__(self, headless: bool = True):
        """
        Initialise le scraper.

        Args:
            headless: Si True, le navigateur tourne sans interface graphique.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver = None
        self.headless = headless
        self._init_driver()

    def _init_driver(self):
        """Initialise le driver Chrome avec les options configurees."""
        chrome_options = Options()
        chrome_options.add_argument(f"user-agent={self.USER_AGENT}")

        if self.headless:
            chrome_options.add_argument("--headless")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            self.driver.implicitly_wait(10)
            self.logger.info("Driver Chrome initialise avec succes.")
        except WebDriverException as e:
            self.logger.error(f"Erreur lors de l'initialisation du driver : {e}")
            raise

    def _get_page(self, url: str):
        """
        Navigue vers une URL avec un delai ethique aleatoire.

        Args:
            url: L'URL de la page a visiter.
        """
        delay = self.MIN_DELAY + random.uniform(0, self.MAX_DELAY - self.MIN_DELAY)
        self.logger.info(f"Attente de {delay:.1f}s avant requete...")
        time.sleep(delay)

        try:
            self.driver.get(url)
            self.logger.info(f"Page chargee : {url}")
        except WebDriverException as e:
            self.logger.error(f"Erreur lors du chargement de {url} : {e}")
            raise

    def _wait_for_element(self, by, value, timeout=None):
        """Attend qu'un element soit present dans le DOM."""
        wait_time = timeout or self.TIMEOUT
        try:
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.warning(f"Element non trouve : {by}='{value}' (timeout={wait_time}s)")
            return None

    def _wait_for_elements(self, by, value, timeout=None):
        """Attend que des elements soient presents dans le DOM."""
        wait_time = timeout or self.TIMEOUT
        try:
            elements = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_all_elements_located((by, value))
            )
            return elements
        except TimeoutException:
            self.logger.warning(f"Elements non trouves : {by}='{value}' (timeout={wait_time}s)")
            return []

    def _handle_cookies(self):
        """Gere les pop-ups de cookies. A surcharger dans les classes enfant."""
        pass

    def close(self):
        """Ferme le navigateur et libere les ressources."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logger.info("Driver ferme.")

    def __enter__(self):
        """Support du context manager (with)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ferme automatiquement le driver en sortant du context manager."""
        self.close()
