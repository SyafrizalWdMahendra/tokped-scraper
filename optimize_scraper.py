# import time
# import pandas as pd
# import re
# import random
# import os
# from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.by import By
# from selenium.common.exceptions import TimeoutException, NoSuchElementException
# from datetime import datetime


# class LazyLoadReviewScraper:
#     def __init__(self, headless=False):
#         options = Options()

#         if headless:
#             options.add_argument("--headless=new")

#         options.add_argument("--start-maximized")
#         options.add_argument("--disable-blink-features=AutomationControlled")
#         options.add_experimental_option(
#             "excludeSwitches", ["enable-automation"])
#         options.add_experimental_option('useAutomationExtension', False)

#         self.driver = webdriver.Chrome(options=options)
#         self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
#             "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
#         })

#         self.data = []
#         self.stats = {'total': 0, 'by_rating': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}

#     def wait_for_reviews_to_load(self, timeout=15):
#         """
#         KUNCI: Tunggu sampai review benar-benar muncul di DOM
#         """
#         print("   ⏳ Menunggu review dimuat...")

#         # Strategi 1: Wait untuk elemen review muncul
#         wait = WebDriverWait(self.driver, timeout)

#         selectors_to_try = [
#             (By.CSS_SELECTOR, "[data-testid='reviewCard']"),
#             (By.TAG_NAME, "article"),
#             (By.XPATH, "//div[contains(@class, 'review')]"),
#             # Indikator review Tokped
#             (By.XPATH, "//*[contains(text(), 'Beli di aplikasi')]"),
#         ]

#         for by, selector in selectors_to_try:
#             try:
#                 element = wait.until(
#                     EC.presence_of_element_located((by, selector)))
#                 if element:
#                     print(f"   ✓ Review terdeteksi via: {selector}")
#                     # Tunggu sebentar lagi untuk memastikan semua elemen termuat
#                     time.sleep(2)
#                     return True
#             except TimeoutException:
#                 continue

#         print("   ⚠ Timeout menunggu review!")
#         return False

#     def scroll_to_load_reviews(self):
#         """
#         Scroll bertahap untuk trigger lazy loading
#         """
#         print("   📜 Scrolling untuk trigger lazy load...")

#         # Scroll ke bawah bertahap
#         scroll_positions = [400, 800, 1200, 1600]

#         for pos in scroll_positions:
#             self.driver.execute_script(f"window.scrollTo(0, {pos});")
#             time.sleep(1.5)

#         # Scroll kembali ke posisi review section
#         self.driver.execute_script("window.scrollTo(0, 800);")
#         time.sleep(2)

#     def extract_review_data(self, container, source_url):
#         """
#         Ekstraksi review dengan MULTIPLE fallback strategies
#         """
#         try:
#             # USERNAME - Multiple strategies
#             username = "Anonymous"

#             # Try 1: data-testid
#             user_elem = container.find(
#                 'span', attrs={'data-testid': 'proName'})
#             if user_elem:
#                 username = user_elem.text.strip()
#             else:
#                 # Try 2: Cari span dengan text pendek (biasanya username)
#                 for span in container.find_all('span'):
#                     text = span.text.strip()
#                     if 3 < len(text) < 50 and not any(x in text for x in ['Beli', 'WIB', 'lalu', 'Variasi', 'bintang']):
#                         username = text
#                         break

#             # RATING - Multiple strategies
#             rating = "5"

#             # Try 1: aria-label pada svg/div rating
#             rating_elem = container.find(
#                 attrs={'aria-label': lambda x: x and 'bintang' in str(x).lower()})
#             if rating_elem:
#                 aria = rating_elem.get('aria-label', '')
#                 # Extract angka dari "5 bintang" atau "Rating 5"
#                 match = re.search(r'(\d)', aria)
#                 if match:
#                     rating = match.group(1)

#             # Try 2: Cari di data-testid
#             if not rating_elem:
#                 rating_elem = container.find(
#                     'div', attrs={'data-testid': 'icnStarRating'})
#                 if rating_elem and rating_elem.get('aria-label'):
#                     aria = rating_elem.get('aria-label')
#                     match = re.search(r'(\d)', aria)
#                     if match:
#                         rating = match.group(1)

#             # REVIEW TEXT - Multiple strategies
#             review_text = ""

#             # Try 1: data-testid
#             review_elem = container.find(
#                 'span', attrs={'data-testid': 'lblItemUlasan'})
#             if review_elem:
#                 review_text = review_elem.text.strip()

#             # Try 2: Cari span dengan teks panjang
#             if not review_text:
#                 for span in container.find_all('span'):
#                     text = span.text.strip()
#                     # Review biasanya 20-2000 karakter
#                     if 20 < len(text) < 2000:
#                         # Pastikan bukan username atau metadata
#                         if not any(x in text for x in ['WIB', 'lalu yang', 'Variasi', 'Beli di', 'Terima kasih atas']):
#                             review_text = text
#                             break

#             # Try 3: Cari di <p> tag
#             if not review_text:
#                 for p in container.find_all('p'):
#                     text = p.text.strip()
#                     if 20 < len(text) < 2000 and 'WIB' not in text:
#                         review_text = text
#                         break

#             # DATE
#             date = "Unknown"
#             date_keywords = ['WIB', 'lalu', 'hari', 'minggu', 'bulan', 'tahun', 'Jan',
#                              'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

#             for elem in container.find_all(['p', 'span', 'div']):
#                 text = elem.text.strip()
#                 if any(keyword in text for keyword in date_keywords) and len(text) < 50:
#                     date = text
#                     break

#             # VALIDASI: Harus ada review text minimal
#             if not review_text or len(review_text) < 10:
#                 return None

#             # Clean text
#             cleaned = re.sub(r'[^\w\s]', '', review_text)
#             cleaned = re.sub(r'\d+', '', cleaned)
#             cleaned = cleaned.lower().strip()

#             return {
#                 'Source_URL': source_url,
#                 'Username': username,
#                 'Review': review_text,
#                 'Cleaned_Review': cleaned,
#                 'Rating': rating,
#                 'Date': date
#             }

#         except Exception as e:
#             print(f"      ✗ Error extract: {e}")
#             return None

#     def find_review_containers(self):
#         """
#         Cari container review dengan multiple strategies
#         """
#         soup = BeautifulSoup(self.driver.page_source, "html.parser")

#         # Strategy 1: data-testid
#         containers = soup.find_all("div", attrs={'data-testid': 'reviewCard'})
#         if containers:
#             print(
#                 f"      → Ditemukan {len(containers)} review (via data-testid)")
#             return containers

#         # Strategy 2: article tag
#         containers = soup.find_all("article")
#         if containers:
#             # Filter hanya article yang punya konten review
#             valid_containers = []
#             for article in containers:
#                 text = article.get_text(strip=True)
#                 # Heuristic: artikel review punya teks 50-3000 karakter dan ada indikator tanggal
#                 if 50 < len(text) < 3000 and ('WIB' in text or 'lalu' in text):
#                     valid_containers.append(article)

#             if valid_containers:
#                 print(
#                     f"      → Ditemukan {len(valid_containers)} review (via article)")
#                 return valid_containers

#         # Strategy 3: Cari div dengan pattern review
#         all_divs = soup.find_all("div")
#         potential_reviews = []

#         for div in all_divs:
#             text = div.get_text(strip=True)
#             # Review characteristics:
#             # - 50-2000 karakter
#             # - Ada tanggal (WIB/lalu)
#             # - Punya child elements tapi tidak terlalu banyak
#             if 50 < len(text) < 2000 and ('WIB' in text or 'lalu' in text):
#                 children_count = len(list(div.children))
#                 if 3 < children_count < 30:  # Review biasanya punya 5-20 child elements
#                     potential_reviews.append(div)

#         if potential_reviews:
#             print(
#                 f"      → Ditemukan {len(potential_reviews)} review (via pattern matching)")
#             return potential_reviews

#         print(f"      ✗ Tidak ditemukan review container!")
#         return []

#     def scrape_current_view(self, url, rating_filter=None):
#         """
#         Scrape review di view sekarang
#         """
#         page = 1
#         empty_count = 0
#         page_reviews = 0

#         while True:
#             print(f"      → Halaman {page}...")

#             # Tunggu review dimuat
#             time.sleep(2)

#             # Cari containers
#             containers = self.find_review_containers()

#             if not containers:
#                 print(f"      ✗ Halaman {page} tidak ada review")
#                 empty_count += 1
#                 if empty_count >= 2:
#                     break

#                 # Next page
#                 if not self.go_to_next_page():
#                     break
#                 page += 1
#                 continue

#             # Extract reviews
#             new_reviews = 0
#             for container in containers:
#                 review = self.extract_review_data(container, url)

#                 if review:
#                     # Filter by rating if specified
#                     if rating_filter and review['Rating'] != str(rating_filter):
#                         continue

#                     # Check duplicate
#                     is_duplicate = any(
#                         d['Review'] == review['Review'] and d['Username'] == review['Username']
#                         for d in self.data
#                     )

#                     if not is_duplicate:
#                         self.data.append(review)
#                         new_reviews += 1
#                         page_reviews += 1

#             if new_reviews > 0:
#                 print(
#                     f"      ✓ +{new_reviews} review baru | Total sesi: {page_reviews}")
#                 empty_count = 0
#             else:
#                 empty_count += 1
#                 print(f"      - Tidak ada review baru")
#                 if empty_count >= 2:
#                     break

#             # Next page
#             if not self.go_to_next_page():
#                 print(f"      ✓ Halaman terakhir")
#                 break

#             page += 1

#             # Safety limit
#             if page > 100:
#                 print(f"      ⚠ Limit 100 halaman tercapai")
#                 break

#         return page_reviews

#     def go_to_next_page(self):
#         """Navigate ke halaman berikutnya"""
#         try:
#             next_btn = self.driver.find_element(
#                 By.CSS_SELECTOR, "button[aria-label^='Laman berikutnya']")

#             if not next_btn.is_enabled():
#                 return False

#             self.driver.execute_script("arguments[0].click();", next_btn)
#             time.sleep(random.uniform(2, 3))
#             return True

#         except NoSuchElementException:
#             return False
#         except Exception:
#             return False

#     def click_rating_filter(self, rating):
#         """Klik filter rating"""
#         print(f"   → Filter rating {rating}...")

#         self.driver.execute_script("window.scrollTo(0, 600);")
#         time.sleep(1)

#         xpath_list = [
#             f"//label[contains(., '{rating}')]",
#             f"//label[text()='{rating}']",
#             f"//*[contains(text(), '{rating} Bintang')]//ancestor::label",
#         ]

#         for xpath in xpath_list:
#             try:
#                 elem = self.driver.find_element(By.XPATH, xpath)
#                 if elem.is_displayed():
#                     self.driver.execute_script("arguments[0].click();", elem)
#                     time.sleep(2)
#                     print(f"   ✓ Filter {rating} aktif")
#                     return True
#             except:
#                 continue

#         print(f"   ✗ Filter {rating} tidak ditemukan")
#         return False

#     def scrape_product(self, url, target_ratings=[1, 2, 3]):
#         """Main scraping untuk satu produk"""
#         print(f"\n{'='*70}")
#         print(f"📦 {url}")
#         print(f"{'='*70}")

#         try:
#             # Load halaman
#             self.driver.get(url)
#             time.sleep(5)

#             # Scroll untuk trigger lazy load
#             self.scroll_to_load_reviews()

#             # Wait sampai review muncul
#             if not self.wait_for_reviews_to_load():
#                 print("   ✗ Review tidak muncul, skip produk ini")
#                 return

#             # Scrape per rating
#             for rating in target_ratings:
#                 print(f"\n   ⭐ RATING {rating}")

#                 if self.click_rating_filter(rating):
#                     count = self.scrape_current_view(url, rating)
#                     self.stats['by_rating'][rating] += count

#                     # Uncheck filter
#                     self.driver.execute_script("window.scrollBy(0, -300);")
#                     time.sleep(1)
#                     self.click_rating_filter(rating)  # Klik lagi untuk uncheck
#                     time.sleep(1)
#                 else:
#                     print(f"   - Skip rating {rating}")

#             print(f"\n   ✓ Produk selesai | Total: {len(self.data)} review")

#         except Exception as e:
#             print(f"\n   ✗ ERROR: {e}")

#     def save_results(self, filename='dataset_balanced.csv'):
#         """Simpan hasil"""
#         if not self.data:
#             print("\n⚠ Tidak ada data!")
#             return

#         df_new = pd.DataFrame(self.data)
#         df_new['Sentiment'] = df_new['Rating'].apply(
#             lambda x: 'positif' if int(x) >= 4 else (
#                 'netral' if int(x) == 3 else 'negatif')
#         )

#         # Merge dengan file lama
#         if os.path.exists(filename):
#             df_old = pd.read_csv(filename)
#             df_combined = pd.concat([df_old, df_new], ignore_index=True)
#             df_combined.drop_duplicates(
#                 subset=['Username', 'Cleaned_Review', 'Date'], inplace=True)
#             df_final = df_combined
#             print(f"\n✓ Merged dengan data lama")
#         else:
#             df_final = df_new

#         df_final.to_csv(filename, index=False, encoding='utf-8-sig')

#         print(f"\n{'='*70}")
#         print(f"✅ SELESAI")
#         print(f"{'='*70}")
#         print(f"Total: {len(df_final)} review")
#         print(f"\nDistribusi Sentimen:")
#         print(df_final['Sentiment'].value_counts())
#         print(f"\nDistribusi Rating:")
#         print(df_final['Rating'].value_counts().sort_index())
#         print(f"\nFile: {filename}")

#     def run(self, urls, target_ratings=[1, 2, 3]):
#         """Main runner"""
#         print(f"\n🚀 MULAI SCRAPING")
#         print(f"Total URL: {len(urls)}")
#         print(f"Target Rating: {target_ratings}\n")

#         for idx, url in enumerate(urls, 1):
#             print(f"\n[{idx}/{len(urls)}]")
#             self.scrape_product(url, target_ratings)

#             if idx < len(urls):
#                 delay = random.uniform(4, 6)
#                 print(f"\n⏸ Delay {delay:.1f}s...")
#                 time.sleep(delay)

#         self.driver.quit()
#         self.save_results()


# def main():
#     urls = [
#         "https://www.tokopedia.com/wdcomputer/wd-computer-lenovo-thinkpad-x270-intel-core-i5-gen-7-ram-8gb-ssd-128gb-layar-12-5-inch-garansi-30-hari-bonus-tas-laptop-mouse-wireless-aplikasi-kantor-1733035942694126786/review",
#         "https://www.tokopedia.com/electrocom/laptop-lenovo-thinkpad-t470-core-i5-gen7-ram-8gb-ssd-256gb-mulus-1733881974291989762/review",
#         "https://www.tokopedia.com/onestopgaming/laptop-axioo-mybook-hype-5-ryzen-5-8gb-ram-256gb-ssd-14-ips-fhd-windows-11-pro-resmi-axioo-indonesia-adp-1731304871960085762/review",
#         "https://www.tokopedia.com/alvinluo-shop/laptop-lenovo-thinkpad-t470-t470s-core-i5-i7-gen7-layar-14-murah-1733601541745641257/review",
#         "https://www.tokopedia.com/thinkpadofficial/lenovo-ideapad-slim-3-core-i5-13420h-8gb-ram-512gb-ssd-windows-11-ohs-2021-14-inch-fhd-ips-14irh10-1732843180746769802/review",
#         "https://www.tokopedia.com/onestopgaming/apple-macbook-pro-m4-pro-max-14-inch-1tb-512gb-ssd-ram-36gb-24gb-resmi-apple-1732224792438539522/review",
#         "https://www.tokopedia.com/agresid/asus-vivobook-14-a1404va-i3-1315-8gb-256-512gb-w11-ohs-14-0fhd-1731346463187829827/review",
#         "https://www.tokopedia.com/acer-jakarta/acer-aspire-go-14-ag14-72p-51tb-intel-core-i5-120u-16-1tb-ssd-windows-11-ohs-m365b-14-inch-wuxga-ips-light-silver-1732960503790077076/review",
#         "https://www.tokopedia.com/distri-laptop/axioo-mybook-hype-3-i3-1005g1-ram-8gb-256gb-ssd-14-fhd-ips-w11-1730808512282855337/review",
#         "https://www.tokopedia.com/royalltech/laptop-lenovo-v14-g4-ryzen-5-7430u-16gb-ram-512gb-ssd-14-fhd-windows-11-office-laptop-kuliah-kerja-best-seller-performance-laptop-1733450995415287287/review",
#         "https://www.tokopedia.com/toptech/lenovo-ideapad-slim-3-14arp10-ryzen-5-7535hs-16gb-1tb-ssd-14-wuxga-ips-w11-ohs-1733400328445789300/review",
#         "https://www.tokopedia.com/amd-id/asus-vivobook-go-15-e1504fa-ryzen-3-7320-16gb-512gb-w11-ohs-m365b-15-6fhd-vips-1732291127544219003/review",
#         "https://www.tokopedia.com/protechcom/lenovo-ideapad-slim-3-14-i3-1315-8gb-512gb-14-0fhd-w11-ohs-m365b-1732063140069083040/review",
#         "https://www.tokopedia.com/gugellaptop/thinkpad-x380-x390-yoga-i7-8th-thinkpad-x390-x380-yoga-i5-8th-thinkpad-x390-yoga-x380-yoga-thinkpad-yoga-1731426883390178594/review",
#         "https://www.tokopedia.com/protechcom/asus-vivobook-go-14-e1404ga-i3-n305-8g-512gb-14-fhd-intel-uhd-w11-ohs-256gb-4745a/review",
#         "https://www.tokopedia.com/studioponsel/apple-macbook-air-2022-m2-chip-13-inch-512gb-256gb-ram-16gb-8gb-1731935275689346866/review",
#         "https://www.tokopedia.com/agresid/lenovo-ideapad-slim-3-14-i5-13420h-8-16gb-512gb-w11-ohs-14-0-wuxga-ips-1731231402747003971/review",
#         "https://www.tokopedia.com/oceanla/lenovo-thinkpad-l13-yoga-2-in-1-intel-core-i7-i5-gen-12-ram-16gb-i5gen10-ram16gb-ssd-256gb-fee4a/review",
#         "https://www.tokopedia.com/spacetech/asus-vivobook-go-14-e1404fa-ryzen-3-7320u-8gb-512gb-ssd-14-fhd-w11-ohs-1731264027127678585/review",
#         "https://www.tokopedia.com/alvinluo-shop/laptop-lenovo-thinkpad-t490-t490s-core-i5-i7-8th-16gb-512gb-1733601602496071465/review",
#         "https://www.tokopedia.com/amd-id/asus-vivobook-go-14-e1404fa-ryzen-5-7520u-8gb-16gb-512gb-w11-ohs-14-0fhd-ips-vips-1730040134793135483/review",
#         "https://www.tokopedia.com/houselaptop-1/laptop-lenovo-thinkpad-t14-t14s-gen-3rd-ryzen-7-i7-ram-32gb-ssd-1730000980634666756/review",
#     ]

#     scraper = LazyLoadReviewScraper(headless=False)
#     scraper.run(urls, target_ratings=[1, 2, 3])


# if __name__ == "__main__":
#     main()

import time
import pandas as pd
import re
import random
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime


class LazyLoadReviewScraper:
    def __init__(self, headless=False):
        options = Options()

        if headless:
            options.add_argument("--headless=new")

        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=options)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

        self.data = []
        self.stats = {'total': 0, 'by_rating': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}

    def wait_for_reviews_to_load(self, timeout=15):
        """
        KUNCI: Tunggu sampai review benar-benar muncul di DOM
        """
        print("   ⏳ Menunggu review dimuat...")

        # Strategi 1: Wait untuk elemen review muncul
        wait = WebDriverWait(self.driver, timeout)

        selectors_to_try = [
            (By.CSS_SELECTOR, "[data-testid='reviewCard']"),
            (By.TAG_NAME, "article"),
            (By.XPATH, "//div[contains(@class, 'review')]"),
            # Indikator review Tokped
            (By.XPATH, "//*[contains(text(), 'Beli di aplikasi')]"),
        ]

        for by, selector in selectors_to_try:
            try:
                element = wait.until(
                    EC.presence_of_element_located((by, selector)))
                if element:
                    print(f"   ✓ Review terdeteksi via: {selector}")
                    # Tunggu sebentar lagi untuk memastikan semua elemen termuat
                    time.sleep(2)
                    return True
            except TimeoutException:
                continue

        print("   ⚠ Timeout menunggu review!")
        return False

    def scroll_to_load_reviews(self):
        """
        Scroll bertahap untuk trigger lazy loading
        """
        print("   📜 Scrolling untuk trigger lazy load...")

        # Scroll ke bawah bertahap
        scroll_positions = [400, 800, 1200, 1600]

        for pos in scroll_positions:
            self.driver.execute_script(f"window.scrollTo(0, {pos});")
            time.sleep(1.5)

        # Scroll kembali ke posisi review section
        self.driver.execute_script("window.scrollTo(0, 800);")
        time.sleep(2)

    def extract_review_data(self, container, source_url):
        """
        Ekstraksi review dengan MULTIPLE fallback strategies
        """
        try:
            # USERNAME - Multiple strategies
            username = "Anonymous"

            # Try 1: data-testid
            user_elem = container.find(
                'span', attrs={'data-testid': 'proName'})
            if user_elem:
                username = user_elem.text.strip()
            else:
                # Try 2: Cari span dengan text pendek (biasanya username)
                for span in container.find_all('span'):
                    text = span.text.strip()
                    if 3 < len(text) < 50 and not any(x in text for x in ['Beli', 'WIB', 'lalu', 'Variasi', 'bintang']):
                        username = text
                        break

            # RATING - Multiple strategies
            rating = "5"

            # Try 1: aria-label pada svg/div rating
            rating_elem = container.find(
                attrs={'aria-label': lambda x: x and 'bintang' in str(x).lower()})
            if rating_elem:
                aria = rating_elem.get('aria-label', '')
                # Extract angka dari "5 bintang" atau "Rating 5"
                match = re.search(r'(\d)', aria)
                if match:
                    rating = match.group(1)

            # Try 2: Cari di data-testid
            if not rating_elem:
                rating_elem = container.find(
                    'div', attrs={'data-testid': 'icnStarRating'})
                if rating_elem and rating_elem.get('aria-label'):
                    aria = rating_elem.get('aria-label')
                    match = re.search(r'(\d)', aria)
                    if match:
                        rating = match.group(1)

            # REVIEW TEXT - Multiple strategies
            review_text = ""

            # Try 1: data-testid
            review_elem = container.find(
                'span', attrs={'data-testid': 'lblItemUlasan'})
            if review_elem:
                review_text = review_elem.text.strip()

            # Try 2: Cari span dengan teks panjang
            if not review_text:
                for span in container.find_all('span'):
                    text = span.text.strip()
                    # Review biasanya 20-2000 karakter
                    if 20 < len(text) < 2000:
                        # Pastikan bukan username atau metadata
                        if not any(x in text for x in ['WIB', 'lalu yang', 'Variasi', 'Beli di', 'Terima kasih atas']):
                            review_text = text
                            break

            # Try 3: Cari di <p> tag
            if not review_text:
                for p in container.find_all('p'):
                    text = p.text.strip()
                    if 20 < len(text) < 2000 and 'WIB' not in text:
                        review_text = text
                        break

            # DATE
            date = "Unknown"
            date_keywords = ['WIB', 'lalu', 'hari', 'minggu', 'bulan', 'tahun', 'Jan',
                             'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']

            for elem in container.find_all(['p', 'span', 'div']):
                text = elem.text.strip()
                if any(keyword in text for keyword in date_keywords) and len(text) < 50:
                    date = text
                    break

            # VALIDASI: Harus ada review text minimal
            if not review_text or len(review_text) < 10:
                return None

            # Clean text
            cleaned = re.sub(r'[^\w\s]', '', review_text)
            cleaned = re.sub(r'\d+', '', cleaned)
            cleaned = cleaned.lower().strip()

            return {
                'Source_URL': source_url,
                'Username': username,
                'Review': review_text,
                'Cleaned_Review': cleaned,
                'Rating': rating,
                'Date': date
            }

        except Exception as e:
            print(f"      ✗ Error extract: {e}")
            return None

    def find_review_containers(self):
        """
        Cari container review dengan multiple strategies
        """
        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        # Strategy 1: data-testid
        containers = soup.find_all("div", attrs={'data-testid': 'reviewCard'})
        if containers:
            print(
                f"      → Ditemukan {len(containers)} review (via data-testid)")
            return containers

        # Strategy 2: article tag
        containers = soup.find_all("article")
        if containers:
            # Filter hanya article yang punya konten review
            valid_containers = []
            for article in containers:
                text = article.get_text(strip=True)
                # Heuristic: artikel review punya teks 50-3000 karakter dan ada indikator tanggal
                if 50 < len(text) < 3000 and ('WIB' in text or 'lalu' in text):
                    valid_containers.append(article)

            if valid_containers:
                print(
                    f"      → Ditemukan {len(valid_containers)} review (via article)")
                return valid_containers

        # Strategy 3: Cari div dengan pattern review
        all_divs = soup.find_all("div")
        potential_reviews = []

        for div in all_divs:
            text = div.get_text(strip=True)
            # Review characteristics:
            # - 50-2000 karakter
            # - Ada tanggal (WIB/lalu)
            # - Punya child elements tapi tidak terlalu banyak
            if 50 < len(text) < 2000 and ('WIB' in text or 'lalu' in text):
                children_count = len(list(div.children))
                if 3 < children_count < 30:  # Review biasanya punya 5-20 child elements
                    potential_reviews.append(div)

        if potential_reviews:
            print(
                f"      → Ditemukan {len(potential_reviews)} review (via pattern matching)")
            return potential_reviews

        print(f"      ✗ Tidak ditemukan review container!")
        return []

    def scrape_current_view(self, url, rating_filter=None):
        """
        Scrape review di view sekarang
        """
        page = 1
        empty_count = 0
        page_reviews = 0

        while True:
            print(f"      → Halaman {page}...")

            # Tunggu review dimuat
            time.sleep(2)

            # Cari containers
            containers = self.find_review_containers()

            if not containers:
                print(f"      ✗ Halaman {page} tidak ada review")
                empty_count += 1
                if empty_count >= 2:
                    break

                # Next page
                if not self.go_to_next_page():
                    break
                page += 1
                continue

            # Extract reviews
            new_reviews = 0
            for container in containers:
                review = self.extract_review_data(container, url)

                if review:
                    # Filter by rating if specified
                    if rating_filter and review['Rating'] != str(rating_filter):
                        continue

                    # Check duplicate
                    is_duplicate = any(
                        d['Review'] == review['Review'] and d['Username'] == review['Username']
                        for d in self.data
                    )

                    if not is_duplicate:
                        self.data.append(review)
                        new_reviews += 1
                        page_reviews += 1

            if new_reviews > 0:
                print(
                    f"      ✓ +{new_reviews} review baru | Total sesi: {page_reviews}")
                empty_count = 0
            else:
                empty_count += 1
                print(f"      - Tidak ada review baru")
                if empty_count >= 2:
                    break

            # Next page
            if not self.go_to_next_page():
                print(f"      ✓ Halaman terakhir")
                break

            page += 1

            # Safety limit
            if page > 100:
                print(f"      ⚠ Limit 100 halaman tercapai")
                break

        return page_reviews

    def go_to_next_page(self):
        """Navigate ke halaman berikutnya"""
        try:
            next_btn = self.driver.find_element(
                By.CSS_SELECTOR, "button[aria-label^='Laman berikutnya']")

            if not next_btn.is_enabled():
                return False

            self.driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(random.uniform(2, 3))
            return True

        except NoSuchElementException:
            return False
        except Exception:
            return False

    def click_rating_filter(self, rating):
        """Klik filter rating"""
        print(f"   → Filter rating {rating}...")

        self.driver.execute_script("window.scrollTo(0, 600);")
        time.sleep(1)

        xpath_list = [
            f"//label[contains(., '{rating}')]",
            f"//label[text()='{rating}']",
            f"//*[contains(text(), '{rating} Bintang')]//ancestor::label",
        ]

        for xpath in xpath_list:
            try:
                elem = self.driver.find_element(By.XPATH, xpath)
                if elem.is_displayed():
                    self.driver.execute_script("arguments[0].click();", elem)
                    time.sleep(2)
                    print(f"   ✓ Filter {rating} aktif")
                    return True
            except:
                continue

        print(f"   ✗ Filter {rating} tidak ditemukan")
        return False

    def scrape_product(self, url, target_ratings=[1, 2, 3]):
        """Main scraping untuk satu produk"""
        print(f"\n{'='*70}")
        print(f"📦 {url}")
        print(f"{'='*70}")

        try:
            # Load halaman
            self.driver.get(url)
            time.sleep(5)

            # Scroll untuk trigger lazy load
            self.scroll_to_load_reviews()

            # Wait sampai review muncul
            if not self.wait_for_reviews_to_load():
                print("   ✗ Review tidak muncul, skip produk ini")
                return

            # Scrape per rating
            for rating in target_ratings:
                print(f"\n   ⭐ RATING {rating}")

                if self.click_rating_filter(rating):
                    count = self.scrape_current_view(url, rating)
                    self.stats['by_rating'][rating] += count

                    # Uncheck filter
                    self.driver.execute_script("window.scrollBy(0, -300);")
                    time.sleep(1)
                    self.click_rating_filter(rating)  # Klik lagi untuk uncheck
                    time.sleep(1)
                else:
                    print(f"   - Skip rating {rating}")

            print(f"\n   ✓ Produk selesai | Total: {len(self.data)} review")

        except Exception as e:
            print(f"\n   ✗ ERROR: {e}")

    def save_results(self, filename='dataset_balanced.csv'):
        """Simpan hasil"""
        if not self.data:
            print("\n⚠ Tidak ada data!")
            return

        df_new = pd.DataFrame(self.data)
        df_new['Sentiment'] = df_new['Rating'].apply(
            lambda x: 'positif' if int(x) >= 4 else (
                'netral' if int(x) == 3 else 'negatif')
        )

        # Merge dengan file lama
        if os.path.exists(filename):
            df_old = pd.read_csv(filename)
            df_combined = pd.concat([df_old, df_new], ignore_index=True)
            df_combined.drop_duplicates(
                subset=['Username', 'Cleaned_Review', 'Date'], inplace=True)
            df_final = df_combined
            print(f"\n✓ Merged dengan data lama")
        else:
            df_final = df_new

        df_final.to_csv(filename, index=False, encoding='utf-8-sig')

        print(f"\n{'='*70}")
        print(f"✅ SELESAI")
        print(f"{'='*70}")
        print(f"Total: {len(df_final)} review")
        print(f"\nDistribusi Sentimen:")
        print(df_final['Sentiment'].value_counts())
        print(f"\nDistribusi Rating:")
        print(df_final['Rating'].value_counts().sort_index())
        print(f"\nFile: {filename}")

    def run(self, urls, target_ratings=[1, 2, 3]):
        """Main runner"""
        print(f"\n🚀 MULAI SCRAPING")
        print(f"Total URL: {len(urls)}")
        print(f"Target Rating: {target_ratings}\n")

        for idx, url in enumerate(urls, 1):
            print(f"\n[{idx}/{len(urls)}]")
            self.scrape_product(url, target_ratings)

            if idx < len(urls):
                delay = random.uniform(4, 6)
                print(f"\n⏸ Delay {delay:.1f}s...")
                time.sleep(delay)

        self.driver.quit()
        self.save_results()


def load_urls_from_csv(csv_file='target_urls.csv'):
    """
    Membaca URL dari file CSV
    
    Format CSV yang didukung:
    1. Kolom bernama 'url' atau 'URL'
    2. Kolom pertama jika tidak ada header
    3. Satu URL per baris
    
    Returns:
        list: Daftar URL yang valid
    """
    try:
        # Coba baca CSV
        df = pd.read_csv(csv_file)
        
        # Cari kolom URL
        url_column = None
        for col in df.columns:
            if col.lower() in ['url', 'urls', 'link', 'links']:
                url_column = col
                break
        
        # Jika tidak ada kolom URL, gunakan kolom pertama
        if url_column is None:
            url_column = df.columns[0]
            print(f"⚠ Tidak ada kolom 'url', menggunakan kolom: {url_column}")
        
        # Ambil URLs dan filter yang valid
        urls = df[url_column].dropna().tolist()
        
        # Filter hanya URL yang valid (mengandung http/https)
        valid_urls = [url for url in urls if isinstance(url, str) and url.startswith('http')]
        
        print(f"✓ Berhasil membaca {len(valid_urls)} URL dari {csv_file}")
        
        if len(valid_urls) == 0:
            print("⚠ Tidak ada URL valid yang ditemukan!")
            print("Format yang diharapkan:")
            print("  - File CSV dengan kolom 'url' atau 'URL'")
            print("  - Atau satu kolom berisi URL")
            return []
        
        return valid_urls
        
    except FileNotFoundError:
        print(f"✗ File {csv_file} tidak ditemukan!")
        print(f"Pastikan file berada di direktori yang sama dengan script ini.")
        return []
    except Exception as e:
        print(f"✗ Error membaca file CSV: {e}")
        return []


def main():
    # Load URLs dari CSV
    csv_filename = 'target_urls.csv'
    urls = load_urls_from_csv(csv_filename)
    
    if not urls:
        print("\n✗ Tidak ada URL untuk di-scrape!")
        print(f"\nContoh format {csv_filename}:")
        print("url")
        print("https://www.tokopedia.com/product1/review")
        print("https://www.tokopedia.com/product2/review")
        return
    
    # Tampilkan preview URLs
    print(f"\n📋 Preview URL yang akan di-scrape:")
    for i, url in enumerate(urls[:5], 1):
        print(f"  {i}. {url[:80]}{'...' if len(url) > 80 else ''}")
    if len(urls) > 5:
        print(f"  ... dan {len(urls) - 5} URL lainnya")
    
    # Konfirmasi
    print(f"\nTotal: {len(urls)} URL")
    confirmation = input("\nLanjutkan scraping? (y/n): ").lower()
    
    if confirmation != 'y':
        print("Scraping dibatalkan.")
        return
    
    # Mulai scraping
    scraper = LazyLoadReviewScraper(headless=False)
    scraper.run(urls, target_ratings=[1, 2, 3])


if __name__ == "__main__":
    main()