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
import os
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
            # 1. Siapkan Data Baru
            df_new = pd.DataFrame(self.data)
            df_new = self.label_data(df_new)
            
            filename = 'dataset_fix_balanced_7.csv'
            
            # 2. Cek apakah file sudah ada (Smart Merge Logic)
            if os.path.exists(filename):
                try:
                    print(f"\n[INFO] File '{filename}' ditemukan. Membaca data lama...")
                    df_old = pd.read_csv(filename)
                    
                    # Gabungkan data lama dan baru
                    df_combined = pd.concat([df_old, df_new], ignore_index=True)
                    
                    # 3. Hapus Duplikat
                    # Kita anggap duplikat jika Username, Review (yang sudah dibersihkan), dan Tanggal sama persis
                    total_before = len(df_combined)
                    df_combined.drop_duplicates(subset=['Username', 'Cleaned_Review', 'Date'], keep='first', inplace=True)
                    total_after = len(df_combined)
                    
                    print(f"   - Data Lama: {len(df_old)}")
                    print(f"   - Data Baru (Scraping saat ini): {len(df_new)}")
                    print(f"   - Duplikat Dibuang: {total_before - total_after}")
                    
                    df_final = df_combined
                except Exception as e:
                    print(f"[WARNING] Gagal membaca file lama ({e}). Membuat file baru.")
                    df_final = df_new
            else:
                print(f"\n[INFO] File '{filename}' belum ada. Membuat file baru.")
                df_final = df_new

            # 4. Simpan Hasil Akhir
            print("\n=== TOTAL DATASET SETELAH UPDATE ===")
            print(df_final['Sentiment'].value_counts())
            
            df_final.to_csv(filename, index=False)
            print(f"Data berhasil disimpan/diupdate ke: {filename}")
        else:
            print("\n[!] Tidak ada data baru yang didapatkan dari sesi ini.")

def main():
    target_urls = [
        "https://www.tokopedia.com/rogsstoreid/asus-vivobook-14-core-i5-120u-16gb-512gb-ssd-windows-11-ohs-office-365-basic-14-fhd-ips-keyboard-backlit-fingerprint-a1404vap-laptop-kerja-sekolah-coding-1731827615960761676/review",
        "https://www.tokopedia.com/spacetech/asus-vivobook-s14-s3407ca-ultra-5-225h-16gb-1tb-ssd-14-wuxga-ips-win11-ohs-1731482091377231481/review",
        "https://www.tokopedia.com/lenovo-authorized-jakartautara/lenovo-v15-g5-irl-i3-1315u-8gb-512gb-15-6-fhd-ips-w11-ohs-1733266392511775855/review",
        "https://www.tokopedia.com/brankaslaptop/lenovo-thinkpad-x1-carbon-4th-5th-6th-i5-gen-6-7-8-original-bergaransi-murah-1731365559779558769/review",
        "https://www.tokopedia.com/kalealaptop/laptop-lenovo-x1-yoga-core-i5gen6-ram-8gb-ssd-256gb-touchscreen-mulus-core-i7-gen-8-ram-8-ssd-256-300c8/review",
        "https://www.tokopedia.com/decacom/asus-vivobook-go-14-e1404ga-i3-n305-8gb-256gb-512ssd-win11-ohs-14-0fhd-backlit-keyboard-1730522008203003871/review",
        "https://www.tokopedia.com/techpoint/asus-vivobook-14-e1404ga-i3-n305-8core-8gb-256gb-w11-ohs-14-0fhd-black-8-512-unit-only-4f6f0/review",
        "https://www.tokopedia.com/agresidbogor/lenovo-ideapad-slim-3-14-2025-intel-core-i3-1315-ram-8gb-ddr5-512gb-windows-11-ohs-full-hd-garansi-resmi-1730811700200113583/review",
        "https://www.tokopedia.com/collinsofficial/laptop-lenovo-ideapad-slim-3i-i3-1315u-ram-8gb-ssd-512gb-14-fhd-w11-ohs-1732144789641069767/review",
        "https://www.tokopedia.com/himalaya-hbcomputer/lenovo-thinkpad-x270-core-i5-gen6-8gb-ssd-256gb-12in-laptop-murah-1731382052822812329/review",
        "https://www.tokopedia.com/msi-official-store/msi-modern-14-f13mg-i5-1334u-8gb-512gb-14-0-fhd-ips-2yr-w11-ohs-1732147735620847405/review",
        "https://www.tokopedia.com/centu/obral-macbook-air-11-inch-2015-corei5-ram-4gb-ssd128-mulusss-1729829003059299820/review",
        "https://www.tokopedia.com/gugellaptop/hp-elitebook-745-g6-ryzen-5-pro-hp-elitebook-745-g5-ryzen-5-pro-1731426883007513890/review",
        "https://www.tokopedia.com/sinarmulia/lenovo-ideapad-slim-3-ryzen-3-7320u-512gb-ssd-8gb-fhd-win11-ohs-1731955926830515999/review",
        "https://www.tokopedia.com/worldoflaptop/laptop-v15-g4-amn-amd-ryzen-5-ram-8gb-ddr5-512gb-ssd-1731950871857760199/review",
        "https://www.tokopedia.com/tokohapedia-idn/apple-macbook-air-m2-2022-13-256gb-512gb-midnight-silver-grey-256gb-ibox-midnight/review",
        "https://www.tokopedia.com/agresid/asus-vivobook-pro-15-oled-n6506cu-rtx4050-ultra-9-285h-24gb-1tb-w11-ohs-15-6-3k-120hz-1731685586651087939/review",
        "https://www.tokopedia.com/start-comp/lenovo-thinkpad-x280-laptop-core-i5-i7-gen-8-ram-8gb-16gb-ssd-128gb-256gb-512gb-windows-10-11-office-365-ready-12-5-inch-display-garansi-toko-1731903029053850642/review",
        "https://www.tokopedia.com/gaminglaptopid/laptop-asus-vivobook-s-14-oled-s5406ma-intel-ultra-9-185h-16gb-1tb-windows-11-14-fhd-ips-120hz-1731434154086008427/review",
        "https://www.tokopedia.com/specialistlaptop/lenovo-thinkpad-x1-yoga-3rd-core-i5-8th-gen-ram-8gb-ssd-touchscreen-1730770373266278253/review",
        "https://www.tokopedia.com/laptopmurahid/axioo-hype-3-g11-i3-1125g4-16gb-1tb-ssd-14-fhd-ips-win-11-office-1731132501940667670/review",
        "https://www.tokopedia.com/collinsofficial/collins-x-k-lenovo-ideapad-slim-3-i3-1315u-ram-8gb-256gb-512gb-ssd-14-fhd-w11-ohs-1732712710254789831/review",
        "https://www.tokopedia.com/agresidbandung/apple-macbook-air-13-m4-10c-cpu-16gb-256gb-8c-gpu-13-6-liquid-retina-ips-1731544493548471480/review",
        "https://www.tokopedia.com/agreshpauthorized/laptop-hp-14s-ryzen-3-7320u-8gb-512gb-w11-ohs-14-0fhd-blit-1729904632229495970/review",
        "https://www.tokopedia.com/simonecomindocv/laptop-advan-soulmate-celeron-n4020-4gb-128gb-4-gb-384gb-w11-14-hd-black-8gb-384gb-3e4db/review",
        "https://www.tokopedia.com/alienwarestore/asus-vivobook-x1404va-intel-core-i7-1355u-i5-1335u-i3-1315u-16gb-512gb-windows-11-14-fhd-ips-1733314605857211736/review",
        "https://www.tokopedia.com/decacom/axioo-hype-10-hype-1-celeron-n4020-4gb-8gb-128gb-256gb-384gb-dos-win-11-14-0-1730850467872606175/review",
        "https://www.tokopedia.com/winselindo/apple-macbook-air-2020-13-3-256gb-up-to-3-2ghz-mwtj2-mwtk2-mwtl2-inter-grey/review",
        "https://www.tokopedia.com/electrocom/lenovo-thinkpad-t490-t490s-core-i7-gen8-ram-16gb-ssd-512gb-14inch-1734379427104589058/review",
        "https://www.tokopedia.com/rogsstoreid/lenovo-ideapad-slim-5-14-oled-core-i5-13420h-ram-32gb-ssd-1tb-w11-ohs-14-wuxga-1732373865238594892/review",
        "https://www.tokopedia.com/agresid/lenovo-ideapad-slim-5-14-oled-ultra-7-255h-16gb-512gb-w11-ohs-14-0-wuxga-1733882745251529795/review",
        "https://www.tokopedia.com/gateway/asus-vivobook-14-core-i3-1315-16gb-512gb-ssd-14-fhd-ips-x1404va-1733362269264250293/review",
        "https://www.tokopedia.com/zxcomputer/hp-14s-dq3133tu-dq3134tu-intel-celeron-n4500-8gb-512gb-ssd-14-0-full-hd-windows-11-1731241377377453500/review",
        "https://www.tokopedia.com/diamondhandphone/apple-macbook-air-13-inch-m4-13-256gb-512gb-ram-16gb-24gb-16-256gb-16-512gb-24-512gb-garansi-resmi-1733120782635795982/review",
        "https://www.tokopedia.com/diamondhandphone/macbook-air-m2-2022-13-inch-8gb-ssd-256gb-512gb-16gb-24gb-1tb-2tb-1733120506257114638/review",
        "https://www.tokopedia.com/gamer-id-jakarta-timur/laptop-pelajar-axioo-hype-5-x3-lollipop-series-amd-ryzen-5-3500u-ram-8gb-ssd-256gb-layar-14-0-full-hd-ips-windows-11-home-1733124488644822513/review",
        "https://www.tokopedia.com/bigberry-store/apple-magic-trackpad-2-3-multi-touch-surface-black-white-2022-ipad-1730875777662289691/review",
        "https://www.tokopedia.com/super-laris-it/advan-soulmate-laptop-intel-n4020-ram-8gb-128gb-14-hd-windows-11-garansi-resmi-free-mouse-mousepad-1731195203567978372/review",
        "https://www.tokopedia.com/spacetech/asus-vivobook-14-a1404va-i7-1355u-16gb-512gb-1tb-ssd-14-fhd-ips-w11-ohs-1731263839632197241/review",
        "https://www.tokopedia.com/herlinacom/laptop-hp-14-amd-ryzen-5-7530u-ram-16gb-512gb-ssd-windows-11-ori-office-14-0-fhd-ips-1733756274892637582/review",
        "https://www.tokopedia.com/raja-murah-pedia/dell-latitude-e6410-core-i5-kondisi-mulus-normal-bergaransi-e6410-core-i5-ram-4-hdd-160/review",
        "https://www.tokopedia.com/collinsofficial/acer-aspire-lite-14-al14-32p-intel-n150-8gb-512gb-256gb-14-wuxga-w11-ohs-1731565924151231687/review",
        "https://www.tokopedia.com/justin-shop/lenovo-v14-ada-amd-3020e-4gb-ssd256gb-4-gb/review",
        "https://www.tokopedia.com/kanglaptop/laptop-axioo-hype-r-5-oled-core-i5-1235u-24gb-512gb-14-fhd-1733438818112866121/review",
        "https://www.tokopedia.com/distromart/lenovo-core-i3-1215u-gen-12-terbaru-ram-8gb-256gb-512gb-fhd-intel-w10-lenovo-8-256-gb-7d7fe/review",
        "https://www.tokopedia.com/intelgamingid/lenovo-ideapad-slim-3-14-i5-13420h-ram-16gb-512gb-wuxga-ips-ohs-1734212635803223360/review",
    ]

    scraper = ReviewScraper()
    scraper.run(target_urls)


if __name__ == "__main__":
    main()
