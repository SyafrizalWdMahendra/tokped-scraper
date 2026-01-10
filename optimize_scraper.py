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


def main():
    urls = [
        "https://www.tokopedia.com/agreshpauthorized/hp-245-g10-ryzen-3-7320-8gb-256gb-w11-ohs-14-0-hd-3y-garansi-resmi-1733010085551703202/review",
        "https://www.tokopedia.com/distri-laptop/axioo-hype-3-g11-intel-core-i3-1125g4-ram-8gb-256gb-ssd-14-full-hd-ips-1731414926525761037/review",
        "https://www.tokopedia.com/studioponsel/apple-macbook-air-2022-m2-chip-13-inch-512gb-256gb-ram-8gb-apple-512gb-silver-4eb7c/review",
        "https://www.tokopedia.com/amd-id/asus-vivobook-14-m1407ka-ryzen-ai-5-330-16gb-512gb-w11-ohs-m365b-14-0-wuxga-1731837127225476475/review"
        "https://www.tokopedia.com/trinitycomp/murah-laptop-notebook-8gb-ram-lenovo-thinkpad-t430-core-i5-mantaf-4gb-no-hdd-d3057/review",
        "https://www.tokopedia.com/distri-laptop/laptop-murah-advan-workmate-intel-core-i3-1215u-ram-8gb-ssd-256gb-14-w11-1732567457837647373/review",
        "https://www.tokopedia.com/teknotrend/laptop-advan-soulmate-x-14-ips-fhd-amd-3020e-8gb-128gb-free-windows-11-original-notebook-upgradeable-1732567592007075778/review",
        "https://www.tokopedia.com/oceanla/lenovo-thinkpad-t480-intel-core-i5-i7-gen-8-ram-8gb-ssd-256gb-mulus-t480-i5-gen-8-ram-8gb-ssd256/review",
        "https://www.tokopedia.com/gugellaptop/thinkpad-t480-core-i7-16gb-512gb-thinkpad-t480-core-i5-thinkpad-t480-1731426868832142626/review",
        "https://www.tokopedia.com/gugellaptop/thinkpad-t490-t490s-core-i7-16gb-512gb-thinkpad-t490s-t490-t490-t490s-1731506693531796770/review",
        "https://www.tokopedia.com/agresid/asus-vivobook-go-e1404fa-ryzen-3-7320u-8gb-512gb-radeon-610m-14-fhd-256gb-ssd-non-bundle/review",
        "https://www.tokopedia.com/bigberry888/apple-macbook-air-13-15-inch-m2-m3-m4-chip-256gb-512gb-ram-8gb-16gb-24gb-2022-2024-2025-1731216392714552806/review",
        "https://www.tokopedia.com/agresid/tecno-megabook-t1-14-ryzen-5-7430-16gb-512gb-w11-14-0wuxga-100srgb-75wh-1-39kg-1731662694231475267/review",
        "https://www.tokopedia.com/electrocom/lenovo-thinkpad-x270-touchscreen-core-i5-gen6-8-256gb-ultrabook-mulus-dengan-keyboard-us-uk-garansi-1-bulan-instalasi-software-gratis-1733656621630915842/review",
        "https://www.tokopedia.com/gitechlaptop/lenovo-thinkpad-x240-x250-x260-x270-x280-original-bergaransi-murah-x240-ram-4-hdd-500-24b26/review",
        "https://www.tokopedia.com/collinsofficial/asus-vivobook-go-14-e1404fa-amd-ryzen-3-7320u-ddr5-8gb-14-fhd-w11-ohs-ssd-256gb-a1b9b/review",
        "https://www.tokopedia.com/intelstore-id/axioo-mybook-hype-10-celeron-n4020-ram-8gb-256gb-ssd-14-1731407846855378346/review",
        "https://www.tokopedia.com/gameridos/acer-aspire-lite-al14-intel-n150-8gb-ram-512gb-ssd-w11-ohs-m365b-14-0fhd-ips-pink-1733280498613323361/review",
        "https://www.tokopedia.com/intelgamingid/asus-vivobook-go-14-e410ka-n4500-8gb-512gb-w11-ohs-14-0fhd-blit-blu-fhd455-1731441530400048448/review",
        "https://www.tokopedia.com/raja-murah-pedia/laptop-lenovo-thinkpad-x1-carbon-i7-gen11-ram-16-gb-nvme-2tb-touch-good-promo-murah-bergarnsi-1731606218518988084/review",
        "https://www.tokopedia.com/agresid/asus-vivobook-go-14-e1404fa-ryzen-5-7520-8-16gb-512gb-w11-ohs-14-0fhd-1731231393346782275/review",
        "https://www.tokopedia.com/tokohapedia-idn/apple-macbook-air-2020-13-3-256gb-up-to-3-2ghz-mwtj2-touch-id-gold-inter/review",
        "https://www.tokopedia.com/protechcom/acer-aspire-lite-al14-intel-n150-8gb-512gb-14-0-wuxga-w11-ohs-1731191932179613600/review",
        "https://www.tokopedia.com/amolilaptop/touchscreen-amoli-laptop-2-in-1-intel-n4020-11-6-inch-laptop-8gb-256gb-ssd-gratis-instalasi-windows-11-office-garansi-1-tahun-laptop-gaming-laptop-pembelajaran-1733476128223757770/review",
        "https://www.tokopedia.com/distri-laptop/laptop-asus-vivobook-14-go-e410ka-celeron-n4500-ram-8gb-512gb-ssd-ohs-1730447402695427597/review",
        "https://www.tokopedia.com/oceanla/lenovo-thinkpad-t470-t460-intel-core-i7-i5-gen-6-7-laptop-murah-ram-8gb-1733307103300454180/review",
        "https://www.tokopedia.com/collinsofficial/apple-macbook-air-m2-chip-2022-13-inch-m2-8-core-16gb-256gb-512gb-13-3-resmi-ibox-1733501718985737415/review",
        "https://www.tokopedia.com/agresid/asus-vivobook-go-14-e1404fa-ryzen-3-7320-8gb-512gb-w11-ohs-14-0fhd-1731231392943735875/review",
        "https://www.tokopedia.com/advanstore/advan-workmate-amd-ryzen-5-3500u-8gb-256gb-14-inch-fhd-16-10-ips-wifi-5-upgradable-free-windows-11-garansi-resmi-1-tahun-1732195776192677735/review",
        "https://www.tokopedia.com/advanstore/free-tas-advan-soulmate-x-14-ips-fhd-amd-3020e-4gb-128gb-free-windows-11-original-laptop-notebook-upgradeable-1733887140422125415/review",
        "https://www.tokopedia.com/advanstore/advan-tbook-x-transformers-intel-n100-4gb-128gb-14-hd-laptop-notebook-free-windows-11-upgradeable-1731956993680967527/review",
        "https://www.tokopedia.com/advanstore/advan-workplus-heritage-ryzen-5-7535hs-16gb-1tb-14-ips-fhd-wuxga-1920-x-1200-16-10-lightweigth-free-windows-11-garansi-resmi-1-tahun-laptop-notebook-desain-eksklusif-batik-megamendung-1732205440219055975/review",
        "https://www.tokopedia.com/advanofficialitstore/advan-tbook-laptop-notebook-intel-n100-4gb-128gb-14-inch-hd-free-windows-11-upgradeable-1731558425008047926/review",
        "https://www.tokopedia.com/gugellaptop/thinkpad-t480s-core-i7-thinkpad-t480s-i5-t480s-t480s-1731426848524305698/review",
        "https://www.tokopedia.com/sinarmulia/lenovo-ideapad-slim-3i-i3-1315u-512gb-ssd-8gb-win11-ohs-1731664281210160927/review",
        "https://www.tokopedia.com/gateway/asus-vivobook-go-14-e1404ga-i3-n305-8gb-256gb-512gb-ssd-14-fhd-win11-ohs-1730347394411824565/review",
        "https://www.tokopedia.com/toptech/asus-vivobook-go-14-e1404fa-amd-ryzen-3-7320u-8gb-512gb-ssd-w11-ohs-14-0fhd-1731200419434497140/review",
        "https://www.tokopedia.com/gugellaptop/thinkpad-x390-thinkpad-x390-thinkpad-x390-x390-1731544112072983842/review",
        "https://www.tokopedia.com/ismile-indonesia/apple-macbook-air-m4-chip-2024-13-10-10core-10-8core-ssd-256gb-512gb-ram-16gb-24gb-1732667206971852683/review",
        "https://www.tokopedia.com/studioponsel/apple-macbook-air-m3-2024-13-inch-512gb-256gb-ram-16gb-1730958539678254399/review",
        "https://www.tokopedia.com/collinsofficial/asus-vivobook-go-14-e1404ga-i3-n305-8gb-ssd-256-512gb-14-fhd-w11-ohs-ssd-256gb-7d4bd/review",
        "https://www.tokopedia.com/axiooslimbook/laptop-axioo-hype-10-n4020-8gb-256gb-windows-10-pro-normal-dos-11f61/review",
        "https://www.tokopedia.com/advanstore/free-tas-advan-soulmate-x-14-ips-fhd-amd-3020e-4gb-128gb-free-windows-11-original-laptop-notebook-upgradeable-1733887140422125415/review",
        "https://www.tokopedia.com/agresid/asus-vivobook-14-a1404va-i3-1315-8gb-512gb-w11-ohs-14-0fhd-1731231392455689283/review",
        "https://www.tokopedia.com/intelgamingid/acer-aspire-lite-14-al14-i3-n355-8gb-512gb-w11-ohs-14-0fhd-ips-37p-36aw-1731571585509393728/review",
        "https://www.tokopedia.com/protechcom/tecno-megabook-t1-14-ryzen-5-7430u-16gb-512gb-14-w11-1732064921439668128/review",
        "https://www.tokopedia.com/teknotrend/apple-macbook-air-m2-chip-13-8gb-256gb-512gb-ssd-silver-512gb-apple-89ca1/review",
        "https://www.tokopedia.com/spacetech/infinix-inbook-x2-2025-i3-1315u-8gb-256gb-ssd-14-fhd-100-srgb-win11-1731385878083110521/review",
        "https://www.tokopedia.com/rogsstoreid/laptop-lenovo-v14-g4-core-i3-1315u-16gb-512gb-ssd-14-intel-uhd-1732830831630124364/review",
        "https://www.tokopedia.com/intelstore-id/laptop-lenovo-v14-g4-iru-core-i3-1315u-8gb-256ssd-14-fhd-w11-1733386294732096938/review",
        "https://www.tokopedia.com/amd-id/asus-vivobook-14-m1405ya-ryzen-7-7730u-16gb-512gb-w11-ohs-14-0wuxga-vips-1729896393440265595/review",
        "https://www.tokopedia.com/gitechlaptop/laptop-lenovo-thinkpad-t470-t480-t490-t14-core-i7-ram-32gb-ssd-1tb-laptop-1730881799003735695/review"
        "https://www.tokopedia.com/dwicompany/apple-macbook-air-m3-8gb-16gb-24gb-2024-256gb-512gb-1tb-13-15-inch-1732537202757829644/review",
        "https://www.tokopedia.com/amd-id/asus-vivobook-go-15-e1504fa-ryzen-5-7520-16gb-512gb-w11-ohs-m365b-15-6fhd-1732291174656214395/review",
        "https://www.tokopedia.com/teknotrend/laptop-asus-vivobook-go-14-e1404fa-amd-ryzen-3-7320u-8gb-256gb-512gb-14-fhd-1731262196135397314/review",
        "https://www.tokopedia.com/hp/laptop-hp-intel-core-i3-uhd-4gb-8gb-ram-512gb-ssd-silver-windows-11-home-14-inch-garansi-2-tahun-official-1732138607355594627/review",
        "https://www.tokopedia.com/collinsofficial/lenovo-ideapad-slim-3-i3-1315u-ram-8gb-256gb-512gb-ssd-14-fhd-w11-ohs-1732497278775755975/review",
        "https://www.tokopedia.com/digitalisme/apple-macbook-air-m4-2025-13-inch-24-512gb-16-512gb-10-core-gpu-16-256gb-8-core-gpu-resmi-1733446914166195409/review",
        "https://www.tokopedia.com/bigberry888/apple-macbook-pro-m2-m3-14-16-inch-512gb-1tb-ram-16gb-32gb-18gb-36gb-48gb-1732954912362431974/review",
        "https://www.tokopedia.com/collinsofficial/lenovo-ideapad-slim-3-i5-13420h-8gb-16gb-ddr5-512gb-ssd-14-wuxga-w11-ohs-1731203948778456263/review",
        "https://www.tokopedia.com/thinkpadofficial/lenovo-ideapad-slim-3i-14iru8-core-i3-1315u-8gb-512ssd-windows-11-ohs-14-inch-fhd-laptop-intel-5pid-1732471246595851658/review",
        "https://www.tokopedia.com/toptech/lenovo-v14-g5-irl-core-i3-1315-16gb-512gb-ssd-14-0fhd-w11-1731363639737484404/review",
        "https://www.tokopedia.com/onestopgaming/laptop-axioo-hype-1-intel-celeron-n4020-ram-4gb-8gb-ssd-128gb-14-hd-windows-11-1731304931508651266/review",
        "https://www.tokopedia.com/agreshpauthorized/hp-14-ryzen-5-7530-8gb-512gb-w11-ohs-m365b-14-0fhd-ips-blit-2y-gld-em0531au-1732302025059697826/review",
        "https://www.tokopedia.com/gugellaptop/thinkpad-t495-ryzen-7-pro-3700u-16gb-512gb-vega-2gb-thinkpad-t495-1730790073994217447/review",
        "https://www.tokopedia.com/teknotrend/laptop-axioo-mybook-hype-3-g11-intel-i3-1125g4-8gb-256gb-14-fhd-ips-1731298731986487234/review",
        "https://www.tokopedia.com/royalltech/laptop-lenovo-ideapad-slim-3-14-intel-celeron-n4500-n100-ram-8gb-ssd-512gb-windows-11-office-fhd-laptop-consumer-murah-cepat-ringan-ssd-kencang-ram-besar-anti-panas-cocok-untuk-office-kuliah-zoom-netflix-editing-kerja-harian-1733020603418314231/review",
        "https://www.tokopedia.com/sinarmulia/lenovo-ideapad-slim-3i-i3-1315u-256gb-ssd-8gb-win11-ohs-1731146440050247455/review",
        "https://www.tokopedia.com/collinsofficial/asus-vivobook-go-14-e1404ga-i3-n305-8gb-ssd-256-512gb-14-fhd-w11-ohs-1731003949706151111/review",
        "https://www.tokopedia.com/tokohapedia-idn/apple-macbook-air-m2-chip-2022-13-256gb-512gb-midnight-silver-inter-256-midnight/review",
        "https://www.tokopedia.com/lenovo-official/lenovo-v14-g4-iru-core-core-i3-1315u-8gb-512gb-w11-ohs-1733870723701310624/review",
        "https://www.tokopedia.com/electrocom/lenovo-thinkpad-x280-touchscreen-i5-gen8-ram-16gb-512gb-ultrabook-1733657196012995842/review",
        "https://www.tokopedia.com/kaitocorner/laptop-lenovo-thinkpad-t480-t480s-core-i5-i7-gen-8-layar-14-inch-1733712642338227987/review",
        "https://www.tokopedia.com/amd-id/asus-expertbook-pm1403cda-ryzen-7-7735hs-16gb-512gb-w11-ohs-m365b-140-fhd-ips-1731712946619385211/review",
        "https://www.tokopedia.com/gameridos/asus-vivobook-go-e410ka-n4500-ram-8gb-ssd-512gb-windows-11-ohs-m365b-14-0fhd-rose-pink-fhd4852m-1731601832835450465/review",
        "https://www.tokopedia.com/redstarelectronic/lenovo-thinkpad-t480s-core-i7-8650u-24gb-ram-512gb-nvme-ssd-tc-full-hd-windows-11-1729822537494135859/review",
        "https://www.tokopedia.com/royalltech/laptop-lenovo-ideapad-slim-3-x-thinkpad-v14-i3-1315u-ram-8gb-512gb-ssd-layar-14-fhd-windows-11-ohs-laptop-kuliah-laptop-kerja-laptop-tahan-banting-1733205589272462839/review",
        "https://www.tokopedia.com/toptech/hp-pavilion-aero-13-bg0111au-i-bg0222au-amd-ryzen-5-8640u-16gb-512gb-ssd-13-3-wuxga-ips-w11-ohs-1731216357464179828/review",
        "https://www.tokopedia.com/teknotrend/laptop-hp-14-ep0260tu-14-ep0261tu-core-i3-1315u-8gb-512gb-14-fhd-intel-uhd-graphics-w11-ohs-1733882228962330562/review",
        "https://www.tokopedia.com/spacetech/acer-aspire-lite-al14-i3-n355-8gb-512gb-ssd-14-wuxga-ips-win11-ohs-1731233517590382201/review",
    ]

    scraper = LazyLoadReviewScraper(headless=False)
    scraper.run(urls, target_ratings=[1, 2, 3])


if __name__ == "__main__":
    main()
