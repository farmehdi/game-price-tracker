"""
debug_selectors.py
------------------
Script de debug a lancer EN PREMIER sur ta machine.
Il ouvre DLCompare.fr et teste differents selecteurs CSS
pour trouver ceux qui fonctionnent vraiment.

Usage :
    python debug_selectors.py

Resultat : affiche dans la console quels selecteurs marchent
et a quoi ressemble le HTML de chaque jeu.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def setup_driver(headless=False):
    """Initialise Chrome. headless=False pour VOIR ce qui se passe."""
    opts = Options()
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36")
    if headless:
        opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )
    return driver


def test_dlcompare_listing(driver):
    """Teste les selecteurs sur la page catalogue de DLCompare."""
    print("\n" + "=" * 70)
    print("  TEST 1 : Page catalogue DLCompare.fr/jeux")
    print("=" * 70)

    driver.get("https://www.dlcompare.fr/jeux")
    time.sleep(5)  # Attendre le chargement JS

    # Gerer les cookies
    try:
        cookie_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "#didomi-notice-agree-button, button[id*='accept'], .cookie-accept"
            ))
        )
        cookie_btn.click()
        print("[OK] Pop-up cookies ferme.")
        time.sleep(1)
    except Exception:
        print("[INFO] Pas de pop-up cookies.")

    # Tester plusieurs selecteurs pour trouver les jeux
    selectors_to_test = [
        ("li a[href*='/jeux/']", "Liens <a> dans <li> vers /jeux/"),
        ("a[href*='/acheter-']", "Liens <a> vers /acheter-"),
        (".game-card", "Classe .game-card"),
        ("[class*='game']", "Elements avec 'game' dans la classe"),
        ("[class*='product']", "Elements avec 'product' dans la classe"),
        ("div[class*='card'] a", "Liens dans des cards"),
        (".catalog-game", "Classe .catalog-game"),
        ("ul li a", "Tous les liens dans des listes"),
    ]

    print("\n--- Test des selecteurs CSS ---\n")

    best_selector = None
    best_count = 0

    for selector, description in selectors_to_test:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            count = len(elements)
            status = "OK" if count > 0 else "--"
            print(f"  [{status}] {selector:40s} -> {count:3d} elements  ({description})")

            if count > best_count and count < 500:  # Pas trop large
                best_count = count
                best_selector = selector
        except Exception as e:
            print(f"  [ERR] {selector:40s} -> {e}")

    if best_selector:
        print(f"\n  >>> MEILLEUR SELECTEUR : '{best_selector}' ({best_count} elements)")

    # Afficher le HTML brut des 3 premiers elements du meilleur selecteur
    if best_selector:
        print(f"\n--- Contenu des 3 premiers elements ({best_selector}) ---\n")
        elements = driver.find_elements(By.CSS_SELECTOR, best_selector)
        for i, elem in enumerate(elements[:3]):
            print(f"  --- Element {i+1} ---")
            print(f"  Tag     : {elem.tag_name}")
            print(f"  Href    : {elem.get_attribute('href')}")
            print(f"  Classes : {elem.get_attribute('class')}")
            text = elem.text.strip().replace('\n', '\n          ')
            print(f"  Texte   : {text[:500]}")
            # HTML interne
            inner = elem.get_attribute('innerHTML')[:800]
            print(f"  HTML    : {inner[:500]}")
            print()

    return best_selector


def test_dlcompare_detail(driver):
    """Teste les selecteurs sur une page detail d'un jeu."""
    print("\n" + "=" * 70)
    print("  TEST 2 : Page detail DLCompare (page d'un jeu)")
    print("=" * 70)

    # Aller sur un jeu populaire
    test_urls = [
        "https://www.dlcompare.fr/jeux/506/acheter-grand-theft-auto-v",
        "https://www.dlcompare.fr/jeux/100013325/acheter-black-myth-wukong",
    ]

    for url in test_urls:
        print(f"\n--- Test : {url} ---")
        driver.get(url)
        time.sleep(4)

        # Tester les selecteurs pour les offres de prix
        offer_selectors = [
            ("div[class*='offer']", "Divs avec 'offer'"),
            ("tr[class*='offer']", "TR avec 'offer'"),
            ("[class*='merchant']", "Elements avec 'merchant'"),
            ("[class*='price']", "Elements avec 'price'"),
            ("table tr", "Lignes de tableau"),
            (".price-row", "Classe .price-row"),
            ("[class*='shop']", "Elements avec 'shop'"),
            ("[class*='store']", "Elements avec 'store'"),
            ("[class*='vendor']", "Elements avec 'vendor'"),
            ("[class*='buy']", "Elements avec 'buy'"),
        ]

        print("\n  Selecteurs pour les offres de prix :")
        for selector, desc in offer_selectors:
            try:
                elems = driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    print(f"    [OK] {selector:40s} -> {len(elems):3d} elements  ({desc})")
                    if len(elems) < 20:
                        for j, e in enumerate(elems[:2]):
                            txt = e.text.strip()[:150].replace('\n', ' | ')
                            print(f"         Elem {j+1}: {txt}")
            except Exception:
                pass

        # Aussi chercher directement les prix dans le texte de la page
        print("\n  Recherche de prix dans le body :")
        body_text = driver.find_element(By.TAG_NAME, "body").text
        import re
        prices = re.findall(r'(\d+[.,]\d{2})\s*€', body_text)
        if prices:
            print(f"    Trouves {len(prices)} prix : {prices[:10]}")

        break  # Un seul test suffit pour commencer


def test_goclecd(driver):
    """Teste les selecteurs sur GoCleCD."""
    print("\n" + "=" * 70)
    print("  TEST 3 : GoCleCD.fr")
    print("=" * 70)

    # Tester la page d'accueil
    driver.get("https://www.goclecd.fr/")
    time.sleep(4)

    # Gerer cookies
    try:
        cookie_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((
                By.CSS_SELECTOR,
                "#didomi-notice-agree-button, button[id*='accept'], .cc-btn.cc-dismiss"
            ))
        )
        cookie_btn.click()
        print("[OK] Pop-up cookies GoCleCD ferme.")
        time.sleep(1)
    except Exception:
        print("[INFO] Pas de pop-up cookies GoCleCD.")

    # Tester la recherche
    search_selectors = [
        ("input[type='search']", "Input type search"),
        ("input[name='q']", "Input name=q"),
        ("input[id*='search']", "Input avec id search"),
        (".search input", "Input dans .search"),
        ("input[placeholder*='herch']", "Input placeholder cherch..."),
    ]

    print("\n  Barre de recherche :")
    for sel, desc in search_selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            if elems:
                print(f"    [OK] {sel:45s} ({desc})")
        except Exception:
            pass

    # Tester un jeu specifique
    test_url = "https://www.goclecd.fr/acheter-grand-theft-auto-v-cle-cd-comparateur-prix/"
    print(f"\n  Test page jeu : {test_url}")
    driver.get(test_url)
    time.sleep(4)

    offer_selectors = [
        ("div[class*='offer']", "Divs 'offer'"),
        ("[class*='merchant']", "'merchant'"),
        ("table tr", "Lignes de tableau"),
        ("[class*='shop']", "'shop'"),
        ("[class*='price']", "'price'"),
        ("[class*='buy']", "'buy'"),
        ("[class*='edition']", "'edition'"),
    ]

    print("\n  Selecteurs offres GoCleCD :")
    for selector, desc in offer_selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, selector)
            if elems:
                print(f"    [OK] {selector:40s} -> {len(elems):3d} ({desc})")
                for j, e in enumerate(elems[:2]):
                    txt = e.text.strip()[:150].replace('\n', ' | ')
                    if txt:
                        print(f"         Elem {j+1}: {txt}")
        except Exception:
            pass

    # Dump HTML de la zone de prix
    print("\n  Dump HTML zone principale (2000 premiers chars) :")
    try:
        main = driver.find_element(By.CSS_SELECTOR, "main, #content, .content, body")
        html = main.get_attribute('innerHTML')[:2000]
        print(f"    {html[:2000]}")
    except Exception as e:
        print(f"    Erreur : {e}")


def save_page_source(driver, filename):
    """Sauvegarde le HTML complet pour analyse offline."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    print(f"  [SAVE] HTML sauvegarde dans {filename}")


def main():
    print("#" * 70)
    print("  GAME PRICE TRACKER — Debug des selecteurs")
    print("  Ouvre Chrome et teste les selecteurs CSS sur les sites cibles")
    print("#" * 70)

    # headless=False pour voir le navigateur (utile pour debug)
    driver = setup_driver(headless=False)

    try:
        # Test 1 : DLCompare catalogue
        best_sel = test_dlcompare_listing(driver)
        save_page_source(driver, "data/debug_dlcompare_listing.html")

        # Test 2 : DLCompare page detail
        test_dlcompare_detail(driver)
        save_page_source(driver, "data/debug_dlcompare_detail.html")

        # Test 3 : GoCleCD
        test_goclecd(driver)
        save_page_source(driver, "data/debug_goclecd.html")

    finally:
        driver.quit()

    print("\n" + "#" * 70)
    print("  DEBUG TERMINE")
    print("  Regarde les resultats ci-dessus pour voir quels selecteurs marchent.")
    print("  Les HTML complets sont sauvegardes dans data/debug_*.html")
    print("  ")
    print("  PROCHAINE ETAPE :")
    print("  1. Note les selecteurs qui marchent ([OK] avec le plus d'elements)")
    print("  2. Envoie-moi les resultats et je mettrai a jour les scrapers")
    print("#" * 70)


if __name__ == "__main__":
    main()
