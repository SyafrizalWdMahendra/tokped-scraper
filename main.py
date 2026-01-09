import time
import pandas as pd
import re
import nltk
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

# Download NLTK resources (Cukup sekali run)
# nltk.download('punkt')
# nltk.download('stopwords')
# nltk.download('wordnet')


class ReviewScraper:
    def __init__(self):
        options = Options()
        # options.add_argument("--headless")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option(
            "excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=options)
        self.data = []
        self.stop_words = set(stopwords.words('indonesian'))
        self.lemmatizer = WordNetLemmatizer()

    def clean_text(self, text: str) -> str:
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)
        text = text.lower()
        return text.strip()

    def get_review_data(self, container, source_url) -> dict:
        try:
            # 1. Username
            username = "Anonymous"
            user_elem = container.find(
                'span', attrs={'data-testid': 'proName'})
            if not user_elem:
                user_elem = container.find(
                    'span', class_=re.compile(r'name', re.I))
            if user_elem:
                username = user_elem.text

            # 2. Rating (Ambil dari aria-label bintang)
            rating = "5"
            rating_elem = container.find(
                'div', attrs={'data-testid': 'icnStarRating'})
            if rating_elem:
                try:
                    rating = rating_elem.get('aria-label').split(' ')[1]
                except:
                    pass

            # 3. Ulasan Text
            ulasan = ""
            ulasan_elem = container.find(
                'span', attrs={'data-testid': 'lblItemUlasan'})
            if not ulasan_elem:
                ulasan_elem = container.find('span', attrs={'data-testid': ''})
            if ulasan_elem:
                ulasan = ulasan_elem.text

            # Fallback jika ulasan kosong
            if not ulasan:
                paragraphs = container.find_all('p')
                for p in paragraphs:
                    if len(p.text) > 10 and "WIB" not in p.text:
                        ulasan = p.text
                        break

            # 4. Tanggal
            waktu_komentar = "Unknown"
            date_elem = container.find(
                'p', class_=re.compile(r'timestamp|date', re.I))
            if date_elem:
                waktu_komentar = date_elem.text
            else:
                for span in container.find_all('p'):
                    if 'WIB' in span.text or 'lalu' in span.text:
                        waktu_komentar = span.text
                        break

            # VALIDASI: Jangan simpan jika kosong
            if not ulasan:
                return None

            ulasan_cleaned = self.clean_text(ulasan)

            return {
                'Source_URL': source_url,
                'Username': username,
                'Review': ulasan,
                'Cleaned_Review': ulasan_cleaned,
                'Rating': rating,
                'Date': waktu_komentar
            }
        except Exception as e:
            return None

    def toggle_filter(self, rating: str, action: str, max_retries: int = 2):
        """
        Logika Baru:
        1. Coba cari elemen dengan Timeout SINGKAT (2 detik).
        2. Jika TimeoutException -> Artinya filter tidak ada (0 review) -> RETURN FALSE (Jangan Retry).
        3. Jika Error Klik -> Baru lakukan Retry.
        """
        print(f"   ...Mencoba {action} filter Bintang {rating}...")

        # Scroll agar elemen masuk viewport
        self.driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(1)

        # STRATEGI XPATH
        strategies = [
            # Spesifik Tokped baru
            f"//label[contains(@for, 'rating') and .//text()='{rating}']",
            f"//label[.//text()='{rating}' and .//*[name()='img' or name()='svg']]",
            f"//*[text()='Rating']/ancestor::div[2]//label[contains(., '{rating}')]",
            f"//label[text()='{rating}']"
        ]

        for attempt in range(max_retries):
            found_element = None

            # Coba cari elemen dengan salah satu strategi
            for xpath in strategies:
                try:
                    # Timeout dipendekkan ke 2 detik agar cepat skip jika tidak ada
                    found_element = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )

                    # Cek apakah visible & clickable
                    if found_element.is_displayed():
                        # Cek apakah disabled (kelas CSS atau atribut)
                        if "disabled" in found_element.get_attribute("class") or found_element.get_attribute("disabled"):
                            print(
                                f"   [SKIP] Filter Bintang {rating} ada tapi DISABLED (Non-aktif).")
                            return False

                        # Jika elemen ketemu, siap diklik
                        break
                    else:
                        found_element = None  # Ketemu di DOM tapi hidden
                except TimeoutException:
                    continue  # Coba strategi xpath berikutnya

            # HASIL PENCARIAN
            if found_element:
                try:
                    # KLIK!
                    self.driver.execute_script(
                        "arguments[0].click();", found_element)
                    print(
                        f"   [SUKSES] Filter Bintang {rating} berhasil di-{action}!")
                    time.sleep(3)  # Tunggu loading data
                    return True
                except Exception as click_error:
                    if attempt < max_retries - 1:
                        print(
                            f"   [RETRY {attempt + 1}] Elemen ada tapi gagal klik. Mencoba lagi...")
                        time.sleep(2)
                        continue
                    else:
                        print(
                            f"   [ERROR] Gagal klik filter setelah retry: {click_error}")
                        return False
            else:
                # PENTING: Jika di attempt pertama tidak ketemu di semua strategi,
                # asumsikan filter TIDAK ADA. Jangan retry.
                print(
                    f"   [SKIP] Filter Bintang {rating} TIDAK DITEMUKAN (Mungkin 0 ulasan). Lanjut.")
                return False

        return False

    def scrape_pages_current_view(self, url, current_rating_context):
        page_number = 1
        empty_page_count = 0

        while True:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            containers = soup.find_all(
                "div", attrs={'data-testid': 'reviewCard'})

            if not containers:
                containers = soup.find_all("article")

            if not containers:
                # Double check: kadang loading lambat
                time.sleep(2)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                containers = soup.find_all(
                    "div", attrs={'data-testid': 'reviewCard'})

                if not containers:
                    print(
                        f"      [INFO] Halaman {page_number} kosong. Berhenti pagination.")
                    break

            found_new = False
            for container in containers:
                review_data = self.get_review_data(container, url)
                if review_data:
                    # Validasi Rating sesuai Filter
                    if current_rating_context != "ALL" and review_data['Rating'] != current_rating_context:
                        continue

                    if review_data not in self.data:
                        self.data.append(review_data)
                        found_new = True

            if found_new:
                print(
                    f"      + Halaman {page_number} ok (Filter: {current_rating_context}). Total: {len(self.data)}")
                empty_page_count = 0
            else:
                print(f"      . Halaman {page_number} tidak ada data baru.")
                empty_page_count += 1
                if empty_page_count >= 2:  # Stop jika 2 halaman berturut-turut zonk
                    print(
                        "      [STOP] 2 halaman tanpa data baru. Pindah filter.")
                    break

            # Navigasi Next Button
            try:
                next_button = self.driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label^='Laman berikutnya']")
                if not next_button.is_enabled():
                    break

                self.driver.execute_script(
                    "arguments[0].click();", next_button)
                time.sleep(random.uniform(2, 4))
                page_number += 1
            except:
                break

    def scrape_single_product(self, url: str):
        print(f"\n--- Memproses URL: {url} ---")
        try:
            self.driver.get(url)
            time.sleep(4)
            self.driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(2)

            # TARGET: Negatif (1,2) & Netral (3)
            target_filters = ['1', '2', '3']

            for rating in target_filters:
                # 1. KLIK FILTER
                success = self.toggle_filter(rating, action="CHECK")

                if success:
                    # 2. SCRAPE
                    self.scrape_pages_current_view(
                        url, current_rating_context=rating)

                    # 3. UNCHECK (PENTING: Gunakan logic toggle yang sama)
                    # Scroll dikit ke atas biar tombol filter kelihatan lagi
                    self.driver.execute_script("window.scrollBy(0, -300);")
                    time.sleep(1)

                    uncheck_success = self.toggle_filter(
                        rating, action="UNCHECK")
                    if not uncheck_success:
                        # Jika gagal uncheck, refresh page adalah jalan ninja
                        print(
                            "   [REFRESH] Gagal uncheck, refresh halaman untuk reset filter...")
                        self.driver.refresh()
                        time.sleep(4)
                        self.driver.execute_script("window.scrollBy(0, 800);")
                else:
                    # Jika toggle CHECK gagal/tidak ketemu -> LANJUT ke rating berikutnya
                    # Tidak perlu scrape, tidak perlu uncheck
                    continue

                time.sleep(1)

        except Exception as e:
            print(f"   [ERROR FATAL URL] {e}")

    def label_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df['Sentiment'] = df['Rating'].apply(lambda x: 'positif' if float(
            x) >= 4 else ('netral' if float(x) == 3 else 'negatif'))
        return df

    def run(self, url_list: list) -> None:
        print(f"Total {len(url_list)} URL antrian.")
        for idx, url in enumerate(url_list, 1):
            print(f"Proses {idx}/{len(url_list)}...")
            self.scrape_single_product(url)

        self.driver.quit()

        if self.data:
            df = pd.DataFrame(self.data)
            df = self.label_data(df)
            print("\n=== HASIL ===")
            print(df['Sentiment'].value_counts())
            filename = 'dataset_fix_balanced.csv'
            df.to_csv(filename, index=False)
            print(f"Saved to {filename}")
        else:
            print("\n[!] Data Kosong.")


def main():
    target_urls = [
        "https://www.tokopedia.com/distri-laptop/axioo-hype-3-g11-intel-core-i3-1125g4-ram-8gb-256gb-ssd-14-full-hd-ips-1731414926525761037/review",
        "https://www.tokopedia.com/studioponsel/apple-macbook-air-2022-m2-chip-13-inch-512gb-256gb-ram-8gb-apple-512gb-silver-4eb7c/review",
        "https://www.tokopedia.com/amd-id/asus-vivobook-14-m1407ka-ryzen-ai-5-330-16gb-512gb-w11-ohs-m365b-14-0-wuxga-1731837127225476475/review",  # KOMA DITAMBAHKAN DISINI
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
    ]

    scraper = ReviewScraper()
    scraper.run(target_urls)


if __name__ == "__main__":
    main()
